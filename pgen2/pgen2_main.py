#!/usr/bin/python
"""
pgen2_main.py
"""
from __future__ import print_function

import cStringIO
import os
import sys

from opy.pgen2 import token
from opy.pgen2 import tokenize
from opy.pgen2 import driver, parse, pgen, grammar

from opy.opy_main import Symbols, ParseTreePrinter, log

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen import syntax_asdl
from _devbuild.gen.syntax_asdl import source, oil_expr, oil_expr_t, regex
from _devbuild.gen.types_asdl import lex_mode_e
from core import alloc
from core import meta
from frontend import lexer, match, reader


def NoSingletonAction(gr, pnode):
  """Collapse parse tree."""
  # collapse
  # hm this was so easy!  Why does it materialize so much then?
  # Does CPython do it, or only pgen2?
  # I think you already know
  children = pnode.children
  if children is not None and len(children) == 1:
    return children[0]

  return pnode


# I can't get custom actions to work?  I think I would have to understand more
# how the stack in pgen2/parse.py works.

SEMANTIC_ACTIONS = {
    #'calc': CalcAction,
}


class CalcTransformer(object):
  
  def __init__(self, gr):
    self.number2symbol = gr.number2symbol

  def _AssocBinary(self, children):
    """For an associative binary operation.

    We don't care if it's (1+2)+3 or 1+(2+3).
    """
    assert len(children) >= 3, children
    # NOTE: opy/compiler2/transformer.py has an interative version of this in
    # com_binary.

    left, op = children[0], children[1]
    if len(children) == 3:
      right = self.Transform(children[2])
    else:
      right = self._AssocBinary(children[2:])

    assert isinstance(op.tok, syntax_asdl.token)
    return oil_expr.Binary(op.tok, self.Transform(left), right)

  def _Trailer(self, base, p_trailer):
    children = p_trailer.children
    op_tok = children[0].tok

    if op_tok.id == Id.Arith_LParen:
       p_args = children[1]

       # NOTE: This doesn't take into account kwargs and so forth.
       if p_args.children is not None:
         # a, b, c -- every other one is a comma
         arglist = children[1].children[::2]
       else:
         arg = children[1]
         arglist = [arg]
       return oil_expr.FuncCall(base, [self.Transform(a) for a in arglist])

    if op_tok.id == Id.Arith_LBracket:
       p_args = children[1]

       # NOTE: This doens't take into account slices
       if p_args.children is not None:
         # a, b, c -- every other one is a comma
         arglist = children[1].children[::2]
       else:
         arg = children[1]
         arglist = [arg]
       return oil_expr.Subscript(base, [self.Transform(a) for a in arglist])

    if op_tok.id == Id.Arith_Dot:
      return self._GetAttr(base, nodelist[2])

    raise AssertionError(tok)

  def Transform(self, pnode):
    """Walk the homogeneous parse tree and create a typed AST."""
    typ = pnode.typ
    if pnode.tok:
      value = pnode.tok.val
    else:
      value = None
    tok = pnode.tok
    children = pnode.children

    if typ in self.number2symbol:  # non-terminal
      nt_name = self.number2symbol[typ]

      c = '-' if not children else len(children)
      log('non-terminal %s %s', nt_name, c)

      if nt_name == 'test_input':
        # test_input: test NEWLINE* ENDMARKER
        return self.Transform(children[0])

      elif nt_name == 'expr':
        # expr: term (('+'|'-') term)*
        return self._AssocBinary(children)

      elif nt_name == 'term':
        # term: factor (('*'|'/'|'div'|'mod') factor)*
        return self._AssocBinary(children)

      elif nt_name == 'factor':
        # factor: ('+'|'-'|'~') factor | power
        # the power would have already been reduced
        assert len(children) == 2, children
        op, e = children
        assert isinstance(op.tok, syntax_asdl.token)
        return oil_expr.Unary(op.tok, self.Transform(e))

      elif nt_name == 'power':
        # power: atom trailer* ['^' factor]

        # atom is already reduced to a token

        # NOTE: This would be shorter in a recursive style.

        base = self.Transform(children[0])
        n = len(children)
        for i in xrange(1, n):
          pnode = children[i]
          tok = pnode.tok
          if tok and tok.id == Id.Arith_Caret:
            return oil_expr.Binary(tok, base, self.Transform(children[i+1]))
          base = self._Trailer(base, pnode)

        return base

      elif nt_name == 'array_literal':
        left_tok = children[0].tok

        # Approximation for now.
        items = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Lit_Chars
        ]

        return oil_expr.ArrayLiteral(left_tok, items)

      elif nt_name == 'regex_literal':
        left_tok = children[0].tok

        # Approximation for now.
        items = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Expr_Name
        ]

        return oil_expr.RegexLiteral(left_tok, regex.Concat(items))

      else:
        raise AssertionError(nt_name)

    else:  # Terminals should have a token
      log('terminal %s', tok)

      if tok.id == Id.Expr_Name:
        return oil_expr.Var(tok)
      elif tok.id == Id.Expr_Digits:
        return oil_expr.Const(tok)
      else:
        raise AssertionError(tok.id)


def MakeOilLexer(code_str, arena):
  arena.PushSource(source.MainFile('pgen2_main'))
  line_reader = reader.StringLineReader(code_str, arena)
  line_lexer = lexer.LineLexer(match.MATCHER, '', arena)
  lex = lexer.Lexer(line_lexer, line_reader)
  return lex


# Used at grammar BUILD time.
OPS = {
    '+': Id.Arith_Plus,
    '-': Id.Arith_Minus,
    '*': Id.Arith_Star,

    '/': Id.Arith_Slash,  # floating point division
    '%': Id.Arith_Percent,

    #'div': Id.Expr_Div,

    '^': Id.Arith_Caret,  # exponent

    '(': Id.Arith_LParen,
    ')': Id.Arith_RParen,

    '[': Id.Arith_LBracket,
    ']': Id.Arith_RBracket,  # Problem: in OilOuter, this is OP_RBracket.
                             # OK I think the metalanguage needs to be
                             # extended to take something other than ']'
                             # It needs proper token names!

    '~': Id.Arith_Tilde,
    ',': Id.Arith_Comma,

    '==': Id.Arith_DEqual,
    '!=': Id.Arith_NEqual,
    '<': Id.Arith_Less,
    '>': Id.Arith_Great,
    '<=': Id.Arith_LessEqual,
    '>=': Id.Arith_GreatEqual,

    '@[': Id.Expr_LeftArray,
    '$/': Id.Expr_LeftRegex,
}

TERMINALS = {
    # What happens in the grammar when you see NAME | NUMBER
    # atom: NAME | NUMBER | STRING+

    'NAME': Id.Expr_Name,
    'NUMBER': Id.Expr_Digits,

    # The grammar seems something like 'for' or '>='
    # These need to be looked up at "_Classify" time?
    #'STRING': Id.Expr_Name,

    'NEWLINE': Id.Op_Newline,

    'ENDMARKER': Id.Eof_Real,

    # For @[]
    # Instead of ']', we can also write the name directly
    'Op_RBracket': Id.Op_RBracket,
    'Lit_Chars': Id.Lit_Chars,

    'WS_Space': Id.WS_Space,

    # For $//
    'Arith_Slash': Id.Arith_Slash,
    'Expr_Name': Id.Expr_Name,
}


if 0:  # unused because the grammar compile keeps track of keywords!
  KEYWORDS = {
      'div': Id.Expr_Div,
      'xor': Id.Expr_Xor,

      'and': Id.Expr_And,
      'or': Id.Expr_Or,
      'not': Id.Expr_Not,

      'for': Id.Expr_For,
      'is': Id.Expr_Is,
      'in': Id.Expr_In,
      'if': Id.Expr_If,
      'else': Id.Expr_Else,

      'match': Id.Expr_Match,
      'func': Id.Expr_Func,
  }


class OilTokenDef(object):

  def GetTerminalNum(self, label):
    id_ = TERMINALS[label]
    return id_.enum_id

  def GetOpNum(self, value):
    id_ = OPS[value]
    return id_.enum_id


def _Classify(gr, tok):
  # We have to match up what ParserGenerator.make_grammar() did when
  # calling make_label() and make_first().  See classify() in
  # opy/pgen2/driver.py.

  # 'x' and 'for' are both tokenized as Expr_Name.  This handles the 'for'
  # case.
  if tok.id == Id.Expr_Name:
    ilabel = gr.keywords.get(tok.val)
    if ilabel is not None:
      return ilabel

  # This handles 'x'.
  typ = tok.id.enum_id
  ilabel = gr.tokens.get(typ)
  if ilabel is not None:
    return ilabel

  #log('NAME = %s', tok.id.name)
  # 'Op_RBracket' ->
  id_ = TERMINALS.get(tok.id.name)
  if id_ is not None:
    return id_.enum_id

  raise AssertionError('%d not a keyword and not in gr.tokens: %s' % (typ, tok))


POP = lex_mode_e.Undefined

# NOTE: Also want something for UNCHANGED?
# echo $(f(x)) -- you don't change lexer mode on (, but
#
# this is NOT expressive enough for:
#
# x = func(x, y='default', z={}) {
#   echo hi
# }

# That can probably be handled with some state machine.  Or maybe:
# https://en.wikipedia.org/wiki/Dyck_language
# When you see "func", start matching () and {}, until you hit a new {.
# It's not a regular expression.


_ACTIONS = {
    # PUSH

    # should this be a special array state?

    # This should OilWords or OilArray?  Is that the only place it's used?
    # (x ~ '*.[c h]')  # this is a string

    (lex_mode_e.Expr, Id.Expr_LeftArray): lex_mode_e.Command,  # x + @[1 2]
    (lex_mode_e.Expr, Id.Expr_LeftRegex): lex_mode_e.Regex,  # $/ any + /

    # POP
    (lex_mode_e.Command, Id.Op_RBracket): POP,
    (lex_mode_e.Regex, Id.Arith_Slash): POP,  # $/ any+ / 
}


# Problem: lex_mode_e.Regex is VERY similar to other lex_mode_e.Expr, except
# that [[ ]] are tokens
# Is there a way to express this similarity?
# Ditto for arrays.
# [[]] conflicts with nested lists?  Though that is a somewhat rare syntax.
# [ [a, b], [a, b] ] avoids it.


def PushOilTokens(p, lex, gr, debug=False):
  """Parse a series of tokens and return the syntax tree."""
  #log('keywords = %s', gr.keywords)
  #log('tokens = %s', gr.tokens)

  mode = lex_mode_e.Expr
  mode_stack = [mode]

  while True:
    tok = lex.Read(mode)
    log('tok = %s', tok)

    # TODO: Use Kind.Ignored
    if tok.id == Id.Ignored_Space:
      continue

    action = _ACTIONS.get((mode, tok.id))
    if action == POP:
      mode_stack.pop()
      mode = mode_stack[-1]
      log('POPPED to %s', mode)
    elif action:  # it's an Id
      new_mode = action
      mode_stack.append(new_mode)
      mode = new_mode
      log('PUSHED to %s', mode)

    # otherwise leave it alone

    #if tok.id == Id.Expr_Name and tok.val in KEYWORDS:
    #  tok.id = KEYWORDS[tok.val]
    #  log('Replaced with %s', tok.id)

    ilabel = _Classify(gr, tok)
    #log('tok = %s, ilabel = %d', tok, ilabel)
    if p.addtoken(tok.id.enum_id, tok, ilabel):
        if debug:
            log("Stop.")
        break
  else:
      # We never broke out -- EOF is too soon (how can this happen???)
      raise parse.ParseError("incomplete input",
                             type_, value, (prefix, start))


def main(argv):
  action = argv[1]
  argv = argv[2:]

  if action == 'parse':
    grammar_path = argv[0]
    start_symbol = argv[1]
    code_str = argv[2]

    # For choosing lexer and semantic actions
    grammar_name, _ = os.path.splitext(os.path.basename(grammar_path))

    using_oil_lexer = (grammar_name in ('calc', 'minimal'))
    #using_oil_lexer = grammar_name in ('calc',)

    tok_def = OilTokenDef() if using_oil_lexer else None

    pg = pgen.ParserGenerator(grammar_path, tok_def=tok_def)
    gr = pg.make_grammar()

    # Semantic actions are registered in this code.
    convert = SEMANTIC_ACTIONS.get(grammar_name, NoSingletonAction)

    if using_oil_lexer:
      arena = alloc.Arena()
      lex = MakeOilLexer(code_str, arena)

      p = parse.Parser(gr, convert=convert)

      p.setup(gr.symbol2number[start_symbol])
      try:
        PushOilTokens(p, lex, gr)
      except parse.ParseError as e:
        log('Parse Error: %s', e)
        return 1

      root_node = p.rootnode

    else:
      f = cStringIO.StringIO(code_str)
      tokens = tokenize.generate_tokens(f.readline)

      p = parse.Parser(gr, convert=convert)

      try:
        root_node = driver.PushTokens(p, tokens, gr, start_symbol)
      except parse.ParseError as e:
        # Extract location information and show it.
        unused, (lineno, offset) = e.context
        # extra line needed for '\n' ?
        lines = code_str.splitlines() + ['']

        line = lines[lineno-1]
        log('  %s', line)
        log('  %s^', ' '*offset)
        log('Parse Error: %s', e)
        return 1

    # Calculate names for pretty-printing.  TODO: Move this into TOK_DEF?
    names = {}

    if using_oil_lexer:
      for id_ in (OPS.values() + TERMINALS.values()):
        k = id_.enum_id
        assert k < 256, (k, id_)
        names[k] = id_.name
    else:
      # NOTE: Similar work for Python is done in transformer.Init()
      for k, v in token.tok_name.items():
          if v == 'NT_OFFSET':
            continue
          assert k < 256, (k, v)
          names[k] = v

    for k, v in gr.number2symbol.items():
        # eval_input == 256.  Remove?
        assert k >= 256, (k, v)
        names[k] = v

    if 1:
      if isinstance(root_node, parse.PNode):
        #print(root_node)
        printer = ParseTreePrinter(names)  # print raw nodes
        printer.Print(root_node)
      else:
        assert isinstance(root_node, oil_expr_t)
        root_node.PrettyPrint()

    if grammar_name == 'calc':
      tr = CalcTransformer(gr)
      ast_root = tr.Transform(root_node)
      print('')
      ast_root.PrettyPrint()
      print('')

  elif action == 'stdlib-test':
    # This shows how deep Python's parse tree is.  It doesn't use semantic
    # actions to prune on the fly!

    import parser
    t = parser.expr('1+2')
    print(t)
    t2 = parser.st2tuple(t)
    print(t2)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
