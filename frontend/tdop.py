#!/usr/bin/env python
"""
tdop.py - Library for expression parsing.
"""

from core import util
from core.meta import syntax_asdl, types_asdl, Id
from osh import word

from typing import Callable, List, Dict, NoReturn, TYPE_CHECKING

if TYPE_CHECKING:  # break circular dep
  from osh.word_parse import WordParser

from _devbuild.gen.id_kind_asdl import Id_t
from _devbuild.gen.syntax_asdl import (
    arith_expr_t,
    arith_expr__ArithWord, arith_expr__UnaryAssign, arith_expr__ArithVarRef,
    arith_expr__ArithBinary, arith_expr__BinaryAssign, arith_expr__FuncCall,
    lhs_expr_t,
    lhs_expr__LhsName,
    word_t,
)
from _devbuild.gen.syntax_asdl import (word__TokenWord, word__CompoundWord)

p_die = util.p_die

arith_expr = syntax_asdl.arith_expr
arith_expr_e = syntax_asdl.arith_expr_e

lhs_expr = syntax_asdl.lhs_expr

word_e = syntax_asdl.word_e
lex_mode_e = types_asdl.lex_mode_e

if TYPE_CHECKING:
  NullFunc = Callable[[TdopParser, word_t, int], arith_expr_t]
  LeftFunc = Callable[[TdopParser, word_t, arith_expr_t, int], arith_expr_t]


def IsCallable(node):
  # type: (arith_expr_t) -> bool
  """Is the word callable or indexable?

  Args:
    node: ExprNode
  """
  # f(x), or f[1](x)
  # I guess function calls can be callable?  Return a function later.  Not
  # sure.  Python allows f(3)(4).
  if isinstance(node, arith_expr__ArithVarRef):
    return True
  if isinstance(node, arith_expr__ArithBinary):
    return node.op_id == Id.Arith_LBracket
  return False


def IsIndexable(node):
  # type: (arith_expr_t) -> bool
  """Is the word callable or indexable?

  Args:
    node: ExprNode
  """
  # f[1], or f(x)[1], or f[1][1]
  if isinstance(node, arith_expr__ArithVarRef):
    return True
  if isinstance(node, arith_expr__FuncCall):
    return True

  # Hm f[1][1] is not allowed in shell, but might be in Oil.  There are no
  # nested arrays, or mutable strings.
  if isinstance(node, arith_expr__ArithBinary):
    return node.op_id == Id.Arith_LBracket
  return False


def ToLValue(node):
  # type: (arith_expr_t) -> lhs_expr_t
  """Determine if a node is a valid L-value by whitelisting tags.

  Args:
    node: ExprNode (could be VarExprNode or BinaryExprNode)
  """
  # foo = bar, foo[1] = bar
  if isinstance(node, arith_expr__ArithVarRef):
    # For consistency with osh/cmd_parse.py, append a span_id.
    # TODO: (( a[ x ] = 1 )) and a[x]=1 should use different LST nodes.
    n = lhs_expr.LhsName(node.token.val)
    n.spids.append(node.token.span_id)
    return n
  if isinstance(node, arith_expr__ArithBinary):
    # For example, a[0][0] = 1 is NOT valid.
    if (node.op_id == Id.Arith_LBracket and
        isinstance(node.left, arith_expr__ArithVarRef)):
      return lhs_expr.LhsIndexedName(node.left.token.val, node.right)

  return None


#
# Null Denotation
#


def NullError(p, t, bp):
  # type: (TdopParser, word_t, int) -> NoReturn
  # TODO: I need position information
  p_die("Token can't be used in prefix position", word=t)


def NullConstant(p, w, bp):
  # type: (TdopParser, word_t, int) -> arith_expr_t
  var_name_token = word.LooksLikeArithVar(w)
  if var_name_token:
    return arith_expr.ArithVarRef(var_name_token)

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
  return arith_expr.ArithUnary(word.ArithId(w), right)


#
# Left Denotation
#

def LeftError(p, t, left, rbp):
  # type: (TdopParser, word_t, arith_expr_t, int) -> NoReturn
  # Hm is this not called because of binding power?
  p_die("Token can't be used in infix position", word=t)


def LeftBinaryOp(p, w, left, rbp):
  # type: (TdopParser, word_t, arith_expr_t, int) -> arith_expr_t
  """ Normal binary operator like 1+2 or 2*3, etc. """
  # TODO: w shoudl be a TokenWord, and we should extract the token from it.
  return arith_expr.ArithBinary(word.ArithId(w), left, p.ParseUntil(rbp))


def LeftAssign(p, w, left, rbp):
  # type: (TdopParser, word_t, arith_expr_t, int) -> arith_expr_t
  """ Normal binary operator like 1+2 or 2*3, etc. """
  # x += 1, or a[i] += 1
  lhs = ToLValue(left)
  if lhs is None:
    p_die("Can't assign to %r", lhs, word=w)
  return arith_expr.BinaryAssign(word.ArithId(w), lhs, p.ParseUntil(rbp))


#
# Parser definition
#

class LeftInfo(object):
  """Row for operator.

  In C++ this should be a big array.
  """
  def __init__(self, led=None, lbp=0, rbp=0):
    # type: (LeftFunc, int, int) -> None
    self.led = led or LeftError
    self.lbp = lbp
    self.rbp = rbp


class NullInfo(object):
  """Row for operator.

  In C++ this should be a big array.
  """
  def __init__(self, nud=None, bp=0):
    # type: (NullFunc, int) -> None
    self.nud = nud or LeftError
    self.bp = bp


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


#EOF_TOKEN = Token('eof', 'eof')


class TdopParser(object):
  """
  Parser state.  Current token and lookup stack.
  """
  def __init__(self, spec, w_parser):
    # type: (ParserSpec, WordParser) -> None
    self.spec = spec
    self.w_parser = w_parser  # iterable
    self.cur_word = None  # type: word_t  # current token
    self.op_id = Id.Undefined_Tok

  def _Led(self, token):
    # type: (Id_t) -> LeftInfo
    return self.spec.LookupLed(token)

  def AtToken(self, token_type):
    # type: (Id_t) -> bool
    return self.op_id == token_type

  def Eat(self, token_type):
    # type: (Id_t) -> None
    """ Eat()? """
    if not self.AtToken(token_type):
      p_die('Parser expected %s, got %s', token_type, self.cur_word,
            word=self.cur_word)
    self.Next()

  def Next(self):
    # type: () -> bool
    """Preferred over Eat()? """
    self.cur_word = self.w_parser.ReadWord(lex_mode_e.Arith)
    assert self.cur_word is not None
    self.op_id = word.ArithId(self.cur_word)
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
    self.Next()  # skip over the token, e.g. ! ~ + -

    null_info = self.spec.LookupNud(word.ArithId(t))
    node = null_info.nud(self, t, null_info.bp)

    while True:
      t = self.cur_word
      try:
        left_info = self._Led(word.ArithId(t))
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
