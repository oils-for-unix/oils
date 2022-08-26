"""
tdop.py
"""

from _devbuild.gen.typed_arith_asdl import arith_expr_t
from typing import (Dict, List, Callable, Optional, Iterator, Tuple, NoReturn)
from typing import TYPE_CHECKING

class ParseError(Exception):
  pass


#
# Default parsing functions give errors
#

def NullError(p, token, bp):
  # type: (Parser, Token, int) -> NoReturn
  raise ParseError("%s can't be used in prefix position" % token)


def LeftError(p, token, left, rbp):
  # type: (Parser, Token, arith_expr_t, int) -> NoReturn
  # Hm is this not called because of binding power?
  raise ParseError("%s can't be used in infix position" % token)


#
# Input
#

class Token(object):
  def __init__(self, type, val, loc=None):
    # type: (str, str, Optional[Tuple[int, int]]) -> None
    self.type = type
    self.val = val

  def __repr__(self):
    # type: () -> str
    return '<Token %s %s>' % (self.type, self.val)


#
# Parser definition
#

class LeftInfo(object):
  """Row for operator.

  In C++ this should be a big array.
  """
  def __init__(self, led=None, lbp=0, rbp=0):
    # type: (Optional[LeftFunc], int, int) -> None
    self.led = led or LeftError
    self.lbp = lbp
    self.rbp = rbp


class NullInfo(object):
  """Row for operator.

  In C++ this should be a big array.
  """
  def __init__(self, nud=None, bp=0):
    # type: (Optional[NullFunc], int) -> None
    self.nud = nud or NullError
    self.bp = bp


class ParserSpec(object):
  """Specification for a TDOP parser."""

  def __init__(self):
    # type: () -> None
    self.null_lookup = {}  # type: Dict[str, NullInfo]
    self.left_lookup = {}  # type: Dict[str, LeftInfo]

  def Null(self, bp, nud, tokens):
    # type: (int, NullFunc, List[str]) -> None
    """Register a token that doesn't take anything on the left.

    Examples: constant, prefix operator, error.
    """
    for token in tokens:
      self.null_lookup[token] = NullInfo(nud=nud, bp=bp)
      if token not in self.left_lookup:
        self.left_lookup[token] = LeftInfo()  # error

  def _RegisterLed(self, lbp, rbp, led, tokens):
    # type: (int, int, LeftFunc, List[str]) -> None
    for token in tokens:
      if token not in self.null_lookup:
        self.null_lookup[token] = NullInfo(NullError)
      self.left_lookup[token] = LeftInfo(lbp=lbp, rbp=rbp, led=led)

  def Left(self, bp, led, tokens):
    # type: (int, LeftFunc, List[str]) -> None
    """Register a token that takes an expression on the left."""
    self._RegisterLed(bp, bp, led, tokens)

  def LeftRightAssoc(self, bp, led, tokens):
    # type: (int, LeftFunc, List[str]) -> None
    """Register a right associative operator."""
    self._RegisterLed(bp, bp-1, led, tokens)

  def LookupNull(self, token):
    # type: (str) -> NullInfo
    """Get the parsing function and precedence for a null position token."""
    try:
      nud = self.null_lookup[token]
    except KeyError:
      raise ParseError('Unexpected token %r' % token)
    return nud

  def LookupLeft(self, token):
    # type: (str) -> LeftInfo
    """Get the parsing function and precedence for a left position token."""
    try:
      led = self.left_lookup[token]
    except KeyError:
      raise ParseError('Unexpected token %r' % token)
    return led


EOF_TOKEN = Token('eof', 'eof')


class Parser(object):
  """Recursive TDOP parser."""

  def __init__(self, spec, lexer):
    # type: (ParserSpec, Iterator[Token]) -> None
    self.spec = spec
    self.lexer = lexer  # iterable
    self.token = Token('undefined', '')  # current token

  def AtToken(self, token_type):
    # type: (str) -> bool
    """Test if we are looking at a token."""
    return self.token.type == token_type

  def Next(self):
    # type: () -> None
    """Move to the next token."""
    try:
      t = self.lexer.next()
    except StopIteration:
      t = EOF_TOKEN
    self.token = t

  def Eat(self, val):
    # type: (str) -> None
    """Assert the value of the current token, then move to the next token."""
    if val and not self.AtToken(val):
      raise ParseError('expected %s, got %s' % (val, self.token))
    self.Next()

  def ParseUntil(self, rbp):
    # type: (int) -> arith_expr_t
    """
    Parse to the right, eating tokens until we encounter a token with binding
    power LESS THAN OR EQUAL TO rbp.
    """
    if self.AtToken('eof'):
      raise ParseError('Unexpected end of input')

    t = self.token
    self.Next()  # skip over the token, e.g. ! ~ + -

    null_info = self.spec.LookupNull(t.type)
    node = null_info.nud(self, t, null_info.bp)

    while True:
      t = self.token
      left_info = self.spec.LookupLeft(t.type)

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
    self.Next()
    return self.ParseUntil(0)


# Must define these aliases AFTER Parser and Token are defined.
if TYPE_CHECKING:
  NullFunc = Callable[[Parser, Token, int], arith_expr_t]
  LeftFunc = Callable[[Parser, Token, arith_expr_t, int], arith_expr_t]


