"""
tdop.py - Library for expression parsing.
"""

from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str
from _devbuild.gen.syntax_asdl import (
    arith_expr, arith_expr_e, arith_expr_t,
    arith_expr__VarRef, arith_expr__Binary,
    sh_lhs_expr, sh_lhs_expr_t,
    word_t,
)
from _devbuild.gen.types_asdl import lex_mode_e
from core.util import p_die
from osh import word_
from mycpp import mylib
from mycpp.mylib import tagswitch, NewStr

from typing import (
    Callable, List, Dict, Tuple, Any, cast, TYPE_CHECKING
)

if TYPE_CHECKING:  # break circular dep
  from osh.word_parse import WordParser
  LeftFunc = Callable[['TdopParser', word_t, arith_expr_t, int], arith_expr_t]
  NullFunc = Callable[['TdopParser', word_t, int], arith_expr_t]


def IsIndexable(node):
  # type: (arith_expr_t) -> bool
  """
  a[1] is allowed but a[1][1] isn't
  """
  return node.tag_() == arith_expr_e.VarRef


def ToLValue(node):
  # type: (arith_expr_t) -> sh_lhs_expr_t
  """Determine if a node is a valid L-value by whitelisting tags.

  Valid:
    x = y
    a[1] = y
  Invalid:
    a[0][0] = y
  """
  UP_node = node
  with tagswitch(node) as case:
    if case(arith_expr_e.VarRef):
      node = cast(arith_expr__VarRef, UP_node)
      # For consistency with osh/cmd_parse.py, append a span_id.
      # TODO: (( a[ x ] = 1 )) and a[x]=1 should use different LST nodes.
      n = sh_lhs_expr.Name(node.token.val)
      n.spids.append(node.token.span_id)
      return n

    elif case(arith_expr_e.Binary):
      node = cast(arith_expr__Binary, UP_node)
      if (node.op_id == Id.Arith_LBracket and
          node.left.tag_() == arith_expr_e.VarRef):
        left = cast(arith_expr__VarRef, node.left)
        return sh_lhs_expr.IndexedName(left.token.val, node.right)
      # But a[0][0] = 1 is NOT valid.

  return None


#
# Null Denotation
#


def NullError(p, t, bp):
  # type: (TdopParser, word_t, int) -> arith_expr_t
  # TODO: I need position information
  p_die("Token can't be used in prefix position", word=t)
  return None  # never reached


def NullConstant(p, w, bp):
  # type: (TdopParser, word_t, int) -> arith_expr_t
  var_name_token = word_.LooksLikeArithVar(w)
  if var_name_token:
    return arith_expr.VarRef(var_name_token)

  return arith_expr.ArithWord(w)


def NullParen(p, t, bp):
  # type: (TdopParser, word_t, int) -> arith_expr_t
  """ Arithmetic grouping """
  r = p.ParseUntil(bp)
  p.Eat(Id.Arith_RParen)
  return r


def NullPrefixOp(p, w, bp):
  # type: (TdopParser, word_t, int) -> arith_expr_t
  """Prefix operator.

  Low precedence:  return, raise, etc.
    return x+y is return (x+y), not (return x) + y

  High precedence: logical negation, bitwise complement, etc.
    !x && y is (!x) && y, not !(x && y)
  """
  right = p.ParseUntil(bp)
  return arith_expr.Unary(word_.ArithId(w), right)


#
# Left Denotation
#

def LeftError(p, t, left, rbp):
  # type: (TdopParser, word_t, arith_expr_t, int) -> arith_expr_t
  # Hm is this not called because of binding power?
  p_die("Token can't be used in infix position", word=t)
  return None  # never reached


def LeftBinaryOp(p, w, left, rbp):
  # type: (TdopParser, word_t, arith_expr_t, int) -> arith_expr_t
  """ Normal binary operator like 1+2 or 2*3, etc. """
  # TODO: w shoudl be a Token, and we should extract the token from it.
  return arith_expr.Binary(word_.ArithId(w), left, p.ParseUntil(rbp))


def LeftAssign(p, w, left, rbp):
  # type: (TdopParser, word_t, arith_expr_t, int) -> arith_expr_t
  """ Normal binary operator like 1+2 or 2*3, etc. """
  # x += 1, or a[i] += 1
  lhs = ToLValue(left)
  if lhs is None:
    # TODO: It would be nice to point at 'left', but osh/word.py doesn't
    # support arbitrary arith_expr_t.
    #p_die("Can't assign to this expression", word=w)
    p_die("Left-hand side of this assignment is invalid", word=w)
  return arith_expr.BinaryAssign(word_.ArithId(w), lhs, p.ParseUntil(rbp))


#
# Parser definition
#

if mylib.PYTHON:

  def _ModuleAndFuncName(f):
    # type: (Any) -> Tuple[str, str]
    namespace = f.__module__.split('.')[-1]
    return namespace, f.__name__

  def _CppFuncName(f):
    # type: (Any) -> str
    return '%s::%s' % _ModuleAndFuncName(f)

  class LeftInfo(object):
    """Row for operator.

    In C++ this should be a big array.
    """
    def __init__(self, led=None, lbp=0, rbp=0):
      # type: (LeftFunc, int, int) -> None
      self.led = led or LeftError
      self.lbp = lbp
      self.rbp = rbp

    def __str__(self):
      # type: () -> str
      """Used by C++ code generation."""
      return '{ %s, %d, %d },' % (_CppFuncName(self.led), self.lbp, self.rbp)

    def ModuleAndFuncName(self):
      # type: () -> Tuple[str, str]
      """Used by C++ code generation."""
      return _ModuleAndFuncName(self.led)


  class NullInfo(object):
    """Row for operator.

    In C++ this should be a big array.
    """
    def __init__(self, nud=None, bp=0):
      # type: (NullFunc, int) -> None
      self.nud = nud or LeftError
      self.bp = bp

    def __str__(self):
      # type: () -> str
      """Used by C++ code generation."""
      return '{ %s, %d },' % (_CppFuncName(self.nud), self.bp)

    def ModuleAndFuncName(self):
      # type: () -> Tuple[str, str]
      """Used by C++ code generation."""
      return _ModuleAndFuncName(self.nud)


  class ParserSpec(object):
    """Specification for a TDOP parser.

    This can be compiled to a table in C++.
    """
    def __init__(self):
      # type: () -> None
      self.nud_lookup = {}  # type: Dict[Id_t, NullInfo]
      self.led_lookup = {}  # type: Dict[Id_t, LeftInfo]

    def Null(self, bp, nud, tokens):
      # type: (int, NullFunc, List[Id_t]) -> None
      """Register a token that doesn't take anything on the left.

      Examples: constant, prefix operator, error.
      """
      for token in tokens:
        self.nud_lookup[token] = NullInfo(nud=nud, bp=bp)
        if token not in self.led_lookup:
          self.led_lookup[token] = LeftInfo()  # error

    def _RegisterLed(self, lbp, rbp, led, tokens):
      # type: (int, int, LeftFunc, List[Id_t]) -> None
      for token in tokens:
        if token not in self.nud_lookup:
          self.nud_lookup[token] = NullInfo(NullError)
        self.led_lookup[token] = LeftInfo(lbp=lbp, rbp=rbp, led=led)

    def Left(self, bp, led, tokens):
      # type: (int, LeftFunc, List[Id_t]) -> None
      """Register a token that takes an expression on the left."""
      self._RegisterLed(bp, bp, led, tokens)

    def LeftRightAssoc(self, bp, led, tokens):
      # type: (int, LeftFunc, List[Id_t]) -> None
      """Register a right associative operator."""
      self._RegisterLed(bp, bp - 1, led, tokens)

    def LookupNud(self, token):
      # type: (Id_t) -> NullInfo
      try:
        nud = self.nud_lookup[token]
      except KeyError:
        raise AssertionError('No nud for token %r' % token)
      return nud

    def LookupLed(self, token):
      # type: (Id_t) -> LeftInfo
      """Get a left_info for the token."""
      return self.led_lookup[token]


class TdopParser(object):
  """
  Parser state.  Current token and lookup stack.
  """
  def __init__(self, spec, w_parser):
    # type: (ParserSpec, WordParser) -> None
    self.spec = spec
    self.w_parser = w_parser
    self.cur_word = None  # type: word_t  # current token
    self.op_id = Id.Undefined_Tok

  def AtToken(self, token_type):
    # type: (Id_t) -> bool
    return self.op_id == token_type

  def Eat(self, token_type):
    # type: (Id_t) -> None
    """Assert that we're at the current token and advance."""
    if not self.AtToken(token_type):
      p_die('Parser expected %s, got %s',
            NewStr(Id_str(token_type)), NewStr(Id_str(self.op_id)),
            word=self.cur_word)
    self.Next()

  def Next(self):
    # type: () -> bool
    self.cur_word = self.w_parser.ReadWord(lex_mode_e.Arith)
    self.op_id = word_.ArithId(self.cur_word)
    return True

  def ParseUntil(self, rbp):
    # type: (int) -> arith_expr_t
    """
    Parse to the right, eating tokens until we encounter a token with binding
    power LESS THAN OR EQUAL TO rbp.
    """
    # TODO: use Kind.Eof
    if self.op_id in (Id.Eof_Real, Id.Eof_RParen, Id.Eof_Backtick):
      p_die('Unexpected end of input', word=self.cur_word)

    t = self.cur_word
    null_info = self.spec.LookupNud(self.op_id)

    self.Next()  # skip over the token, e.g. ! ~ + -
    node = null_info.nud(self, t, null_info.bp)

    while True:
      t = self.cur_word
      try:
        left_info = self.spec.LookupLed(self.op_id)
      except KeyError:
        raise AssertionError('Invalid token %s' % t)

      # Examples:
      # If we see 1*2+  , rbp = 27 and lbp = 25, so stop.
      # If we see 1+2+  , rbp = 25 and lbp = 25, so stop.
      # If we see 1**2**, rbp = 26 and lbp = 27, so keep going.
      if rbp >= left_info.lbp:
        break
      self.Next()  # skip over the token, e.g. / *

      node = left_info.led(self, t, node, left_info.rbp)

    return node

  def Parse(self):
    # type: () -> arith_expr_t
    self.Next()  # may raise ParseError
    return self.ParseUntil(0)
