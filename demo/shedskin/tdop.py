"""
tdop.py
"""

import re


class ParseError(Exception):
  pass


#
# Default parsing functions give errors
#

def NullError(p, token, bp):
  raise ParseError("%s can't be used in prefix position" % token)


def LeftError(p, token, left, rbp):
  # Hm is this not called because of binding power?
  raise ParseError("%s can't be used in infix position" % token)


#
# Input
#

class Token:
  def __init__(self, type, val, loc=None):
    self.type = type
    self.val = val

  def __repr__(self):
    return '<Token %s %s>' % (self.type, self.val)


#
# Using the pattern here: http://effbot.org/zone/xml-scanner.htm
#

# NOTE: () and [] need to be on their own so (-1+2) works
TOKEN_RE = re.compile("""
\s* (?: (\d+) | (\w+) | ( [\-\+\*/%!~<>=&^|?:,]+ ) | ([\(\)\[\]]) )
""", re.VERBOSE)

def Tokenize(s):
  for item in TOKEN_RE.findall(s):
    if item[0]:
      typ = 'number'
      val = int(item[0])
    elif item[1]:
      typ = 'name'
      val = item[1]
    elif item[2]:
      typ = item[2]
      val = item[2]
    elif item[3]:
      typ = item[3]
      val = item[3]
    yield Token(typ, val, loc=(0, 0))


#
# Simple and Composite AST nodes
#

class Node(object):
  def __init__(self, token):
    """
    Args:
      type: token type (operator, etc.)
      val: token val, only important for number and string
    """
    self.token = token

  def __repr__(self):
    return str(self.token.val)


class CompositeNode(Node):
  def __init__(self, token, children):
    """
    Args:
      type: token type (operator, etc.)
    """
    Node.__init__(self, token)
    self.children = children

  def __repr__(self):
    args = ''.join([" " + repr(c) for c in self.children])
    return "(" + self.token.type + args + ")"


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
    self.nud = nud or NullError
    self.bp = bp


class ParserSpec(object):
  """Specification for a TDOP parser."""

  def __init__(self):
    self.null_lookup = {}
    self.left_lookup = {}

  def Null(self, bp, nud, tokens):
    """Register a token that doesn't take anything on the left.

    Examples: constant, prefix operator, error.
    """
    for token in tokens:
      self.null_lookup[token] = NullInfo(nud=nud, bp=bp)
      if token not in self.left_lookup:
        self.left_lookup[token] = LeftInfo()  # error

  def _RegisterLed(self, lbp, rbp, led, tokens):
    for token in tokens:
      if token not in self.null_lookup:
        self.null_lookup[token] = NullInfo(NullError)
      self.left_lookup[token] = LeftInfo(lbp=lbp, rbp=rbp, led=led)

  def Left(self, bp, led, tokens):
    """Register a token that takes an expression on the left."""
    self._RegisterLed(bp, bp, led, tokens)

  def LeftRightAssoc(self, bp, led, tokens):
    """Register a right associative operator."""
    self._RegisterLed(bp, bp-1, led, tokens)

  def LookupNull(self, token):
    """Get the parsing function and precedence for a null position token."""
    try:
      nud = self.null_lookup[token]
    except KeyError:
      raise ParseError('Unexpected token %r' % token)
    return nud

  def LookupLeft(self, token):
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
    self.spec = spec
    self.lexer = lexer  # iterable
    self.token = None  # current token

  def AtToken(self, token_type):
    """Test if we are looking at a token."""
    return self.token.type == token_type

  def Next(self):
    """Move to the next token."""
    try:
      t = self.lexer.next()
    except StopIteration:
      t = EOF_TOKEN
    self.token = t

  def Eat(self, val):
    """Assert the value of the current token, then move to the next token."""
    if val and not self.AtToken(val):
      raise ParseError('expected %s, got %s' % (val, self.token))
    self.Next()

  def ParseUntil(self, rbp):
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
    self.Next()
    return self.ParseUntil(0)
