"""
parse_lib.py - Consolidate various parser instantiations here.
"""

from _devbuild.gen.id_kind_asdl import Id_t
from _devbuild.gen.syntax_asdl import (
    Token, compound_word,
    command_t, command__VarDecl, command__PlaceMutation, command__Proc,
    command__Func,
    expr_t, word_t, redir_t,
    arg_list, name_type,
)
from _devbuild.gen.types_asdl import lex_mode_e
from _devbuild.gen import grammar_nt

from core import meta
from core.util import p_die
from frontend import lexer
from frontend import reader
from frontend import match

from oil_lang import expr_parse
from oil_lang import expr_to_ast
from osh import tdop
from osh import arith_parse
from osh import cmd_parse
from osh import word_parse
from mycpp import mylib

from typing import Any, List, Tuple, Dict, Optional, IO, TYPE_CHECKING
if TYPE_CHECKING:
  from core.alloc import Arena
  from core.util import DebugFile
  from frontend.lexer import Lexer
  from frontend.reader import _Reader
  from osh.tdop import TdopParser
  from osh.word_parse import WordParser
  from osh.cmd_parse import CommandParser
  from pgen2.grammar import Grammar
  from pgen2.parse import PNode

class _BaseTrail(object):

  def __init__(self):
    # type: () -> None
    # word from a partially completed command.
    # Filled in by _ScanSimpleCommand in osh/cmd_parse.py.
    self.words = []  # type: List[compound_word]
    self.redirects = []  # type: List[redir_t]
    # TODO: We should maintain the LST invariant and have a single list, but
    # that I ran into the "cases classes are better than variants" problem.

    # Non-ignored tokens, after PushHint translation.  Used for variable name
    # completion.  Filled in by _Peek() in osh/word_parse.py.
    #
    # Example:
    # $ echo $\
    # f<TAB>   
    # This could complete $foo.
    # Problem: readline doesn't even allow that, because it spans more than one
    # line!
    self.tokens = []  # type: List[Token]

    self.alias_words = []  # type: List[compound_word]  # words INSIDE an alias expansion
    self.expanding_alias = False

  def Clear(self):
    # type: () -> None
    pass

  def SetLatestWords(self, words, redirects):
    # type: (List[compound_word], List[redir_t]) -> None
    pass

  def AppendToken(self, token):
    # type: (Token) -> None
    pass

  def BeginAliasExpansion(self):
    # type: () -> None
    pass

  def EndAliasExpansion(self):
    # type: () -> None
    pass

  if mylib.PYTHON:
    def PrintDebugString(self, debug_f):
      # type: (DebugFile) -> None

      # note: could cast DebugFile to IO[str] instead of ignoring?
      debug_f.log('  words:')
      for w in self.words:
        w.PrettyPrint(f=debug_f)  # type: ignore
      debug_f.log('')

      debug_f.log('  redirects:')
      for r in self.redirects:
        r.PrettyPrint(f=debug_f)  # type: ignore
      debug_f.log('')

      debug_f.log('  tokens:')
      for p in self.tokens:
        p.PrettyPrint(f=debug_f)  # type: ignore
      debug_f.log('')

      debug_f.log('  alias_words:')
      for w in self.alias_words:
        w.PrettyPrint(f=debug_f)  # type: ignore
      debug_f.log('')

  def __repr__(self):
    # type: () -> str
    return '<Trail %s %s %s %s>' % (
        self.words, self.redirects, self.tokens, self.alias_words)


class _NullTrail(_BaseTrail):
  """Used when we're not completing."""
  pass


class Trail(_BaseTrail):
  """Info left by the parser to help us complete shell syntax and commands.

  It's also used for history expansion.
  """
  def Clear(self):
    # type: () -> None
    del self.words[:]
    del self.redirects[:]
    # The other ones don't need to be reset?
    del self.tokens[:]
    del self.alias_words[:]

  def SetLatestWords(self, words, redirects):
    # type: (List[compound_word], List[redir_t]) -> None
    if self.expanding_alias:
      self.alias_words = words  # Save these separately
      return
    self.words = words
    self.redirects = redirects

  def AppendToken(self, token):
    # type: (Token) -> None
    if self.expanding_alias:  # We don't want tokens inside aliases
      return
    self.tokens.append(token)

  def BeginAliasExpansion(self):
    # type: () -> None
    """Called by CommandParser so we know to be ready for FIRST alias word.

    For example, for

    alias ll='ls -l'

    Then we want to capture 'ls' as the first word.

    We do NOT want SetLatestWords or AppendToken to be active, because we don't
    need other tokens from 'ls -l'.
    
    It would also probably cause bugs in history expansion, e.g. echo !1 should
    be the first word the user typed, not the first word after alias expansion.
    """
    self.expanding_alias = True

  def EndAliasExpansion(self):
    # type: () -> None
    """Go back to the normal trail collection mode."""
    self.expanding_alias = False


if TYPE_CHECKING:
  AliasesInFlight = List[Tuple[str, int]]


if mylib.PYTHON:
  def MakeGrammarNames(oil_grammar):
    # type: (Grammar) -> Dict[int, str]

    # TODO: Break this dependency
    from frontend import lex

    names = {}

    #from _devbuild.gen.id_kind_asdl import _Id_str
    # This is a dictionary

    # _Id_str()

    for id_name, k in lex.ID_SPEC.id_str2int.items():
      # Hm some are out of range
      #assert k < 256, (k, id_name)

      # HACK: Cut it off at 256 now!  Expr/Arith/Op doesn't go higher than
      # that.  TODO: Change NT_OFFSET?  That might affect C code though.
      # Best to keep everything fed to pgen under 256.  This only affects
      # pretty printing.
      if k < 256:
        names[k] = id_name

    for k, v in oil_grammar.number2symbol.items():
      # eval_input == 256.  Remove?
      assert k >= 256, (k, v)
      names[k] = v

    return names


class OilParseOptions(object):

  def __init__(self):
    # type: () -> None
    self.parse_at = False  # @foo, @array(a, b)
    self.parse_brace = False  # cd /bin { ... }
    self.parse_paren = False  # if (x > 0) ...

    # Should this also change r''' c''' and and c"""?  Those are hard to
    # do in command mode without changing the lexer, but useful because of
    # redirects.  Maybe r' and c' are tokens, and then you look for '' after
    # it?  If it's off and you get the token, then you change it into
    # word_part::Literal and start parsing.
    #
    # proc foo {
    #   cat << c'''
    #   hello\n
    #   '''
    # }
    self.parse_rawc = False  # echo r'' c''
    self.parse_index_expr = False  # ${a[1 + f(x)]}

    # all:nice
    self.parse_equals = False  # x = 'var'
    self.parse_set = False  # set x = 'var'

    self.parse_do = False  # do f(x)

  #def __str__(self):
  #  return str(self.__dict__)


class ParseContext(object):
  """Context shared between the mutually recursive Command and Word parsers.

  In constrast, STATE is stored in the CommandParser and WordParser instances.
  """

  def __init__(self, arena, parse_opts, aliases, oil_grammar):
    # type: (Arena, OilParseOptions, Dict[str, str], Grammar) -> None
    self.arena = arena
    self.parse_opts = parse_opts
    self.aliases = aliases

    self.e_parser = expr_parse.ExprParser(self, oil_grammar)
    # NOTE: The transformer is really a pure function.
    if oil_grammar:
      self.tr = expr_to_ast.Transformer(oil_grammar)
      if mylib.PYTHON:
        names = MakeGrammarNames(oil_grammar)
    else:  # hack for unit tests, which pass None
      self.tr = None
      if mylib.PYTHON:  # TODO: Simplify
        names = {}

    if mylib.PYTHON:
      self.p_printer = expr_parse.ParseTreePrinter(names)  # print raw nodes

    self.parsing_expr = False  # "single-threaded" state

    # Completion state lives here since it may span multiple parsers.
    self.trail = _NullTrail()  # type: _BaseTrail
    self.one_pass_parse = False

  def Init_Trail(self, trail):
    # type: (_BaseTrail) -> None
    self.trail = trail

  def Init_OnePassParse(self, b):
    # type: (bool) -> None
    self.one_pass_parse = b

  def _MakeLexer(self, line_reader):
    # type: (_Reader) -> Lexer
    """Helper function.

    NOTE: I tried to combine the LineLexer and Lexer, and it didn't perform
    better.
    """
    line_lexer = lexer.LineLexer('', self.arena)
    return lexer.Lexer(line_lexer, line_reader)

  def MakeOshParser(self, line_reader, emit_comp_dummy=False):
    # type: (_Reader, bool) -> CommandParser
    lx = self._MakeLexer(line_reader)
    if emit_comp_dummy:
      lx.EmitCompDummy()  # A special token before EOF!

    w_parser = word_parse.WordParser(self, lx, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lx, line_reader)
    return c_parser

  def MakeWordParserForHereDoc(self, line_reader):
    # type: (_Reader) -> WordParser
    lx = self._MakeLexer(line_reader)
    return word_parse.WordParser(self, lx, line_reader)

  def MakeWordParser(self, lx, line_reader):
    # type: (Lexer, _Reader) -> WordParser
    return word_parse.WordParser(self, lx, line_reader)

  def MakeArithParser(self, code_str):
    # type: (str) -> TdopParser
    """Used for a[x+1]=foo in the CommandParser."""
    line_reader = reader.StringLineReader(code_str, self.arena)
    lx = self._MakeLexer(line_reader)
    w_parser = word_parse.WordParser(self, lx, line_reader)
    w_parser.Init(lex_mode_e.Arith)  # Special initialization
    a_parser = tdop.TdopParser(arith_parse.Spec(), w_parser)
    return a_parser

  def MakeParserForCommandSub(self, line_reader, lexer, eof_id):
    # type: (_Reader, Lexer, Id_t) -> CommandParser
    """To parse command sub, we want a fresh word parser state."""
    w_parser = word_parse.WordParser(self, lexer, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lexer, line_reader)
    c_parser.Init_EofId(eof_id)
    return c_parser

  def MakeWordParserForPlugin(self, code_str):
    # type: (str) -> WordParser
    """For $PS1, $PS4, etc."""
    line_reader = reader.StringLineReader(code_str, self.arena)
    lx = self._MakeLexer(line_reader)
    return word_parse.WordParser(self, lx, line_reader)

  def _ParseOil(self, lexer, start_symbol):
    # type: (Lexer, int) -> Tuple[PNode, Token]
    """Helper Oil expression parsing."""
    self.parsing_expr = True
    try:
      return self.e_parser.Parse(lexer, start_symbol)
    finally:
      self.parsing_expr = False

  def ParseVarDecl(self, kw_token, lexer):
    # type: (Token, Lexer) -> Tuple[command__VarDecl, Token]
    """e.g. var mylist = [1, 2, 3]"""

    # TODO: We do need re-entrancy for var x = @[ (1+2) ] and such
    if self.parsing_expr:
      p_die("ShAssignment expression can't be nested like this", token=kw_token)

    self.parsing_expr = True
    try:
      pnode, last_token = self.e_parser.Parse(lexer, grammar_nt.oil_var_decl)
    finally:
      self.parsing_expr = False

    if 0:
      self.p_printer.Print(pnode)

    ast_node = self.tr.MakeVarDecl(pnode)
    ast_node.keyword = kw_token  # VarDecl didn't fill this in
    return ast_node, last_token

  def ParsePlaceMutation(self, kw_token, lexer):
    # type: (Token, Lexer) -> Tuple[command__PlaceMutation, Token]

    # TODO: Create an ExprParser so it's re-entrant.
    pnode, last_token = self.e_parser.Parse(lexer,
                                            grammar_nt.oil_place_mutation)
    if 0:
      self.p_printer.Print(pnode)
    ast_node = self.tr.MakePlaceMutation(pnode)
    ast_node.keyword = kw_token  # VarDecl didn't fill this in
    return ast_node, last_token

  def ParseOilArgList(self, lexer, out):
    # type: (Lexer, arg_list) -> Token
    if self.parsing_expr:
      # TODO: get rid of parsing_expr
      raise AssertionError()

    pnode, last_token = self._ParseOil(lexer, grammar_nt.oil_arglist)

    if 0:
      self.p_printer.Print(pnode)

    self.tr.ArgList(pnode, out)
    return last_token

  def ParseOilExpr(self, lexer, start_symbol):
    # type: (Lexer, int) -> Tuple[expr_t, Token]
    """For Oil expressions that aren't assignments."""
    pnode, last_token = self.e_parser.Parse(lexer, start_symbol)

    if 0:
      self.p_printer.Print(pnode)

    ast_node = self.tr.Expr(pnode)
    return ast_node, last_token

  def ParseOilForExpr(self, lexer, start_symbol):
    # type: (Lexer, int) -> Tuple[List[name_type], expr_t, Token]
    """ for (x Int, y Int in foo) """
    pnode, last_token = self.e_parser.Parse(lexer, start_symbol)

    if 0:
      self.p_printer.Print(pnode)

    lvalue, iterable = self.tr.OilForExpr(pnode)
    return lvalue, iterable, last_token

  def ParseProc(self, lexer, out):
    # type: (Lexer, command__Proc) -> Token
    """ proc f(x, y, @args) { """
    pnode, last_token = self.e_parser.Parse(lexer, grammar_nt.oil_proc)

    if 0:
      self.p_printer.Print(pnode)

    out.sig = self.tr.Proc(pnode)
    return last_token

  def ParseFunc(self, lexer, out):
    # type: (Lexer, command__Func) -> Token
    """ func f(x Int, y Int = 0, ...args; z Int = 3, ...named) { """
    pnode, last_token = self.e_parser.Parse(lexer, grammar_nt.oil_func)

    if 0:
      self.p_printer.Print(pnode)

    self.tr.Func(pnode, out)
    return last_token

# Another parser instantiation:
# - For Array Literal in word_parse.py WordParser:
#   w_parser = WordParser(self.lexer, self.line_reader)
