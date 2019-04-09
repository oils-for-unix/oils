#!/usr/bin/python -S
"""
oil_parse.py
"""
from __future__ import print_function

import sys

from core.meta import syntax_asdl, types_asdl, Id, Kind, LookupKind
from core.util import p_die, log

lex_mode_e = types_asdl.lex_mode_e
oil_cmd = syntax_asdl.oil_cmd
oil_word = syntax_asdl.oil_word
oil_word_part = syntax_asdl.oil_word_part



class OilParser(object):
  """
  This parser does everything in an 'ideal' fashion, all-in-one.

  Issues:
  - Whitespace handling.
    - in WORDS, whitespace is significant, because it delimits words
    - commands, e.g. for loop or while loop, it's not significant.
    - maybe retain word parser?
  - Ignored tokens should be ignored
  - Here strings
    - What about here strings in expression mode?  Maybe don't even go to
      expression mode.
  """
  def __init__(self, parse_ctx, lexer, line_reader, arena=None):
    self.parse_ctx = parse_ctx
    self.lexer = lexer
    self.line_reader = line_reader
    self.Reset()

  def Reset(self):
    """Called by interactive loop."""
    # For _Peek()
    self.cur_token = None
    self.token_kind = Kind.Undefined
    self.token_type = Id.Undefined_Tok

    self.next_lex_mode = lex_mode_e.OilOuter

  def _Peek(self):
    """Helper method."""
    if self.next_lex_mode is not None:
      self.prev_token = self.cur_token  # for completion
      self.cur_token = self.lexer.Read(self.next_lex_mode)
      self.token_kind = LookupKind(self.cur_token.id)
      self.token_type = self.cur_token.id

      if 0:
        log('cur token = %s', self.cur_token)

      self.next_lex_mode = None
    return self.cur_token

  def _Next(self, lex_mode):
    """Set the next lex state, but don't actually read a token.

    We need this for proper interactive parsing.
    """
    self.next_lex_mode = lex_mode

  # NOTE: Copied from osh/word_parse.py
  def _NextNonSpace(self):
    """Same logic as _ReadWord, but for ReadForExpresion."""
    while True:
      self._Next(lex_mode_e.OilOuter)
      self._Peek()
      if self.token_kind not in (Kind.Ignored, Kind.WS):
        break

  # NOTE: copied from osh/cmd_parse.py
  def _NewlineOk(self):
    """Check for optional newline and consume it."""
    self._Peek()
    if self.token_type == Id.Op_Newline:
      self._Next()
      self._Peek()

  def ResetInputObjects(self):
    pass

  def ParseExpr(self):
    """
    expr = TODO: use pratt parser.  For Python-like expressions.

    It calls back here for set x = [a $var ${foo.bar}]
    """

  def ParseWord(self):
    """
    TODO: What about tildesub?  That goes somewhere else?

    command_sub = line*
    word_part = splice                # echo @x
              | literal_part          # echo foo/$bar
              | var_sub               # $foo
              | '$[' command_sub ']'  # $[echo hi]
              | '${' Expr '}'         # ${1 + 2} or ${foo.bar}
              | '$(' Expr ')'         # $(foo.bar)  safe substitution?
                                      # repetition / alternation?
              | func_sub              # $str_func(x, 1) or @array_func(z)

    tilde_prefix = ~([^/]+)
    unquoted_word = tilde_prefix? word_part*

    # Multiline string constants are hard to parse!
    word = unquoted_word
         | singled_quoted_word
         | double_quoted_word
         | multiline_string
    """
    words = []
    w = oil_word.Compound()
    done = False
    while not done:
      if self.token_kind == Kind.Lit:
        w.parts.append(oil_word_part.Literal(self.cur_token))
        self._Next(lex_mode_e.Outer)
      elif self.token_kind in (Kind.WS, Kind.Eof):
        done = True
      else:
        raise AssertionError(self.token_kind)

      self._Peek()
    return w
      
  def ParseRedirect(self):
    """
    # Here docs are triple quoted strings!
    redir_op = '>' | '<' | >>' | '<<'
    file_desc = Fd_Number | Fd_Name  # &2 or &stderr
    redir_arg = word | file_desc
    redirect = redir_op redir_arg
             | file_desc redir_op redir_arg
    """

  def ParseBlockLiteral(self):
    """
    TODO:
    - What about terminators?
    - Can do/fork/shell/time be special functions rather than language
      constructs?
      - What about 'with'?

    block_literal = { command_line* }
    """

  def ParseSimpleCommand(self):
    """
    command_part = word | redirect
    simple_command = command_part* block_literal?
    """
    redirects = []
    words = []
    while True:
      self._Peek()
      if self.token_kind == Kind.Redir:
        node = self.ParseRedirect()
        redirects.append(node)

      elif self.token_kind == Kind.Lit:
        log('ParseSimpleCommand literal')
        w = self.ParseWord()
        words.append(w)

      else:
        break

      self._Next(lex_mode_e.OilOuter)
    return oil_cmd.Simple(words)

  def ParseCommand(self, cur_aliases=None):
    """
    command          : simple_command
                     | compound_command io_redirect*
                     | function_def
                     | ksh_function_def
                     ;
    """
    return self.ParseSimpleCommand()

  def ParsePipeline(self):
    """
    pipeline  = Bang? command ('|' Newline? command)*
    """
    negated = False

    self._Peek()
    if self.token_type == Id.KW_Bang:
      negated = True
      self._Next()

    child = self.ParseCommand()
    assert child is not None

    children = [child]

    self._Peek()
    if self.token_type not in (Id.Op_Pipe,):
      if negated:
        node = oil_cmd.Pipeline(children, negated)
        return node
      else:
        return child

    while True:
      self._Next()  # skip past Id.Op_Pipe or Id.Op_PipeAmp

      self._NewlineOk()

      child = self.ParseCommand()
      assert child is not None
      children.append(child)

      self._Peek()
      if self.token_type  not in (Id.Op_Pipe,):
        break

    node = oil_cmd.Pipeline(children, negated)
    return node

  def ParseAndOr(self):
    """
    and_or_op = '||' | '&&'
    and_or = pipeline (and_or_op Newline? pipeline)*
    """
    child = self.ParsePipeline()
    assert child is not None

    self._Peek()
    if self.token_type  not in (Id.Op_DPipe, Id.Op_DAmp):
      return child

    ops = []
    children = [child]

    while True:
      ops.append(self.c_id)

      self._Next()  # skip past || &&
      self._NewlineOk()

      child = self.ParsePipeline()
      assert child is not None

      children.append(child)

      self._Peek()
      if self.c_id not in (Id.Op_DPipe, Id.Op_DAmp):
        break

    node = oil_cmd.AndOr(ops, children)
    return node

  def ParseCommandSeq(self):
    """
    NOTE: no newlines allowed here because this is a single line.

    command_seq = and_or (';' and_or)*
    """

  def ParseConstBinding(self):
    """
    const_binding = VarName '=' Expr
    """

  def ParseAssignment(self):
    """
    assign_keyword = Const | Set | SetGlobal | Var
    assignment = assign_keyword VarName '=' Expr (',' VarName = Expr)*
    """

  # The interface that main_loop.py expects.  What about interactive?
  def _ParseCommandLine(self):
    """
    TODO:
    - semi-colon or newline is required after all of these?
    - compound command has redirect*
    - Equivalent of command_list inside blocks.  It allows newlines.


    command_line = and_or (';' and_or)* Newline?


    line = command_seq
         | const_binding  # This one requires lookahead to '='
         | assignment

         | proc
         | func
           # Could these 4 be builtins?  They have redirects too?
         | do
         | fork
         | shell
         | time

         | for
         | while
         | if
         | match

    NOTE: ! is not a command prefix like in bash?  Must be part of if?
    What about context like 'cd' and 'with env'?
    """
    # TODO: or ] for the end of command sub
    END_LIST = (Id.Eof_Real, Id.Op_Newline)

    children = []
    done = False
    while not done:
      child = self.ParseAndOr()
      self._Peek()
      if self.token_type == Id.Op_Semi:
        # Should be oil_command_t.Simple?  No sentence?  It has its own
        # terminator for LST purposes?
        child = oil_cmd.Sentence(child) 
        self._Next()

        self._Peek()
        if self.token_type in END_LIST:
          done = True

      if self.token_type in END_LIST:
        done = True

      else:
        # e.g. echo a(b)
        p_die('Unexpected token while parsing command line',
              token=self.cur_token)

      children.append(child)

    # Simplify the AST.
    if len(children) > 1:
      return oil_cmd.CommandList(children)
    else:
      return children[0]

  def ParseLogicalLine(self):
    self._NewlineOk()
    self._Peek()

    if self.token_type == Id.Eof_Real:
      return None

    return self._ParseCommandLine()

  def CheckForPendingHereDocs(self):
    return None


def main(argv):
  parse_methods = []
  for name in dir(OilParser):
    if name.startswith('Parse') or name.startswith('_Parse'):
      method = getattr(OilParser, name)
      line_number = method.im_func.func_code.co_firstlineno
      parse_methods.append((line_number, name, method.__doc__))
      
  # Sort by line number!
  parse_methods.sort()
  for _, name, docstring in parse_methods:
    print('[%s]' % name)
    print(docstring)
    print()


if __name__ == '__main__':
  main(sys.argv)
