#!/usr/bin/python3
"""
tdop.py - Library for expression parsing.
"""

#from parse_util import Node, CompositeNode
#from tokenize import Token
from core import base

from core import tokens
from core.tokens import Id

from core.arith_node import AtomANode, UnaryANode, BinaryANode
from osh.lex import LexMode


class ParseError(Exception):
  pass


def Assert(s, expected, tree):
  """Used for tests."""
  print(s)
  if expected is not None:
    sexpr = repr(tree)
    assert sexpr == expected, '%r != %r' % (sexpr, expected)


# Hm everything gets collapsed into Id.Node_Arith_WORD
LVALUE_TYPES = (Id.Node_ArithWord, Id.Arith_LBracket)
CALL_INDEX_TYPES = (Id.Node_ArithWord,)


#
# Null Denotation
#


def NullError(p, t, bp):
  # TODO: I need position information
  raise ParseError("Token %s can't be used in prefix position" % t)


def NullConstant(p, t, bp):
  # TODO: if word.HasQuotedParts:
  # - Id.Node_Arith_STRING
  # - Id.Node_Arith_WORD
  return AtomANode(t)


def NullParen(p, t, bp):
  """ Arithmetic grouping """
  r = p.ParseUntil(bp)
  p.Eat(Id.Arith_RParen)
  return r


def NullPrefixOp(p, t, bp):
  """Prefix operator.

  Low precedence:  return, raise, etc.
    return x+y is return (x+y), not (return x) + y

  High precedence: logical negation, bitwise complement, etc.
    !x && y is (!x) && y, not !(x && y)
  """
  right = p.ParseUntil(bp)
  return UnaryANode(t.ArithId(), right)


#
# Left Denotation
#

def LeftError(p, t, left, rbp):
  # Hm is this not called because of binding power?
  raise ParseError("Token %s can't be used in infix position" % t)


def LeftBinaryOp(p, t, left, rbp):
  """ Normal binary operator like 1+2 or 2*3, etc. """
  return BinaryANode(t.ArithId(), left, p.ParseUntil(rbp))


def LeftAssign(p, t, left, rbp):
  """ Normal binary operator like 1+2 or 2*3, etc. """
  # x += 1, or a[i] += 1
  if left.atype not in LVALUE_TYPES:
    raise ParseError("Can't assign to %r (%s)" % (left, left.atype))
  return BinaryANode(t.ArithId(), left, p.ParseUntil(rbp))


#
# Parser definition
#

class LeftInfo(object):
  """Row for operator.

  In C++ this should be a big array.
  """
  def __init__(self, led=None, lbp=0, rbp=0):
    self.led = led or LeftError
    self.lbp = lbp
    self.rbp = rbp


class NullInfo(object):
  """Row for operator.

  In C++ this should be a big array.
  """
  def __init__(self, nud=None, bp=0):
    self.nud = nud or LeftError
    self.bp = bp


class ParserSpec(object):
  """Specification for a TDOP parser.

  This can be compiled to a table in C++.
  """
  def __init__(self):
    self.nud_lookup = {}
    self.led_lookup = {}

  def Null(self, bp, nud, tokens):
    """Register a token that doesn't take anything on the left.

    Examples: constant, prefix operator, error.
    """
    for token in tokens:
      self.nud_lookup[token] = NullInfo(nud=nud, bp=bp)
      if token not in self.led_lookup:
        self.led_lookup[token] = LeftInfo()  # error

  def _RegisterLed(self, lbp, rbp, led, tokens):
    for token in tokens:
      if token not in self.nud_lookup:
        self.nud_lookup[token] = NullInfo(NullError)
      self.led_lookup[token] = LeftInfo(lbp=lbp, rbp=rbp, led=led)

  def Left(self, bp, led, tokens):
    """Register a token that takes an expression on the left."""
    self._RegisterLed(bp, bp, led, tokens)

  def LeftRightAssoc(self, bp, led, tokens):
    """Register a right associative operator."""
    self._RegisterLed(bp, bp - 1, led, tokens)

  def LookupNud(self, token):
    try:
      nud = self.nud_lookup[token]
    except KeyError:
      raise ParseError('No nud for token %r' % token)
    return nud

  def LookupLed(self, token):
    """Get a left_info for the token."""
    return self.led_lookup[token]


#EOF_TOKEN = Token('eof', 'eof')


class TdopParser(object):
  """
  Parser state.  Current token and lookup stack.
  """
  def __init__(self, spec, w_parser):
    self.spec = spec
    self.w_parser = w_parser  # iterable
    self.cur_word = None  # current token
    self.a_id = Id.Undefined_Tok

    self.error_stack = []

  def AddErrorContext(self, msg, *args, token=None, word=None):
    err = base.MakeError(msg, *args, token=token, word=word)
    self.error_stack.append(err)

  def Error(self):
    return self.error_stack

  def _Led(self, token):
    return self.spec.LookupLed(token)

  def AtAnyOf(self, *args):
    return self.a_id in args

  def AtToken(self, token_type):
    return self.a_id == token_type

  def Eat(self, token_type):
    """ Eat()? """
    if not self.AtToken(token_type):
      t = tokens.TokenTypeToName(token_type)
      raise ParseError('TDOP expected %s, got %s' % (t, self.cur_word))

    self.Next()

  def Next(self):
    """Preferred over Eat()? """
    self.cur_word = self.w_parser.ReadWord(LexMode.ARITH)
    if self.cur_word is None:
      error_stack = self.w_parser.Error()
      self.error_stack.extend(error_stack)
      self.AddErrorContext('Error reading arith word in ArithParser',
          word=self.cur_word)
      #return False
      raise ParseError()  # use exceptions for now
    self.a_id = self.cur_word.ArithId()
    return True

  def ParseUntil(self, rbp):
    """
    Parse to the right, eating tokens until we encounter a token with binding
    power LESS THAN OR EQUAL TO rbp.
    """
    # TODO: use TokenKind.Eof
    if self.a_id in (Id.Eof_Real, Id.Eof_RParen, Id.Eof_Backtick):
      raise ParseError('Unexpected end of input')

    t = self.cur_word
    self.Next()  # skip over the token, e.g. ! ~ + -

    null_info = self.spec.LookupNud(t.ArithId())
    node = null_info.nud(self, t, null_info.bp)

    while True:
      t = self.cur_word
      try:
        left_info = self._Led(t.ArithId())
      except KeyError:
        raise ParseError('Invalid token %s' % t)

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
    try:
      self.Next()  # can raise ParseError
      node = self.ParseUntil(0)
    except ParseError as e:
      self.error_stack.append((None, str(e)))  # TODO: token
      return None
    return node


class DynamicTdopParser(TdopParser):
  def __init__(self, *args):
    TdopParser.__init__(self, *args)

    # for precedence tweakins
    # TODO: Don't peek inside the member?  How to represent this in C++?
    self.dynamic_led = dict(self.spec.led_lookup)
    self.stack = []  # saved dynamic_led entries

  def Push(self, token, v):
    """
    Temporarily adjust precedence of a token, or insert a new token.

    In Python, this is used for commas, because sometimes it has greater
    precedence than =, and sometimes less.  For example:

    x, y = x, y
    (x, y) = (x, y)

    vs.

    f(x = 1, y = 1)

    This is NOT:
    f(x = (1, y )= 1)

    So inside f(x,y), (t1, t2), [i, j], {i:1, i:2} we tweak it.

    Why is it used for "in"?

    for x in y: pass
    # NOT VALID
    for (x in y) in y:

    [ x for x+1 in y ]
    [ x for x in y ]

    I think INSTEAD of tweak, we need something that's not an expression?  Do
    this later.
    """
    self.stack.append((token, self.dynamic_led[token]))  # save old value
    if v:
      self.dynamic_led[token] = self.spec.LookupLed(token)
    else:
      self.dynamic_led[token] = LeftInfo()

  def Pop(self):
    """ Restore dynamic_led after p.Push(). """
    k, v = self.stack.pop()
    self.dynamic_led[k] = v

  def _Led(self, token):
    return self.dynamic_led[token]
