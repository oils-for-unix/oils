#!/usr/bin/env python2
"""
lazylex/html.py - Low-Level HTML Processing.

See lazylex/README.md for details.

TODO: This should be an Oil library eventually.  It's a "lazily-parsed data
structure" like TSV2.
"""
from __future__ import print_function

import re
import sys


def log(msg, *args):
  msg = msg % args
  print(msg, file=sys.stderr)


class LexError(Exception):
  """For bad lexical elements like <> or && """

  def __init__(self, s, pos):
    self.s = s
    self.pos = pos

  def __str__(self):
    return '(LexError %r)' % (self.s[self.pos : self.pos + 20])


class ParseError(Exception):
  """For errors in the tag structure."""

  def __init__(self, msg, *args):
    self.msg = msg
    self.args = args

  def __str__(self):
    return '(ParseError %s)' % (self.msg % self.args)


class Output(object):
  """
  Takes an underlying input buffer and an output file.  Maintains a position in
  the input buffer.

  Print FROM the input or print new text to the output.
  """

  def __init__(self, s, f):
    self.s = s
    self.f = f
    self.pos = 0

  def SkipTo(self, pos):
    """Skip to a position."""
    self.pos = pos

  def PrintUntil(self, pos):
    """Print until a position."""
    piece = self.s[self.pos : pos]
    self.f.write(piece)
    self.pos = pos

  def PrintTheRest(self):
    """Print until the end of the string."""
    self.PrintUntil(len(self.s))

  def Print(self, s):
    """Print text to the underlying buffer."""
    self.f.write(s)


# HTML Tokens
( Decl, Comment, Processing,
  StartTag, StartEndTag, EndTag,
  DecChar, HexChar, CharEntity,
  RawData,
  Invalid, EndOfStream ) = range(12)


def _MakeLexer(rules):
  return [
  # DOTALL is for the comment
    (re.compile(pat, re.VERBOSE | re.DOTALL), i) for
    (pat, i) in rules
  ]

#
# Eggex
#
# Tag      = / ~['>']+ /

# Is this valid?  A single character?
# Tag      = / ~'>'* /

# Maybe better: / [NOT '>']+/
# capital letters not allowed there?
#
# But then this is confusing:
# / [NOT ~digit]+/
#
# / [NOT digit] / is [^\d]
# / ~digit /      is \D
#
# Or maybe:
#
# / [~ digit]+ /
# / [~ '>']+ /
# / [NOT '>']+ /

# End      = / '</' Tag  '>' /
# StartEnd = / '<'  Tag '/>' /
# Start    = / '<'  Tag  '>' /
#
# EntityRef = / '&' dot{* N} ';' /


LEXER = [
  # TODO: instead of nongreedy matches, the loop can just fo .find('-->') and
  # .find('?>')
  (r'<!-- .*? -->', Comment),
  (r'<\? .*? \?>', Processing),

  # NOTE: < is allowed in these.
  (r'<! [^>]+ >', Decl),  # <!DOCTYPE html>

  (r'</ [^>]+ >', EndTag),  # self-closing <br/>  comes FIRST
  (r'< [^>]+ />', StartEndTag),        # end </a>
  (r'< [^>]+  >', StartTag), # start <a>

  (r'&\# [0-9]+ ;', DecChar),
  (r'&\# x[0-9a-fA-F]+ ;', HexChar),
  (r'& [a-zA-Z]+ ;', CharEntity),

  # Note: > is allowed in raw data.
  # https://stackoverflow.com/questions/10462348/right-angle-bracket-in-html
  (r'[^&<]+', RawData),

  (r'.', Invalid),  # error!
]

LEXER = _MakeLexer(LEXER)


def Tokens(s):
  """
  Args:
    s: string to parse
  """
  pos = 0
  n = len(s)

  while pos < n:
    # Find the FIRST pattern that matches.
    for pat, tok_id in LEXER:
      m = pat.match(s, pos)
      if m:
        end_pos = m.end()
        yield tok_id, end_pos
        pos = end_pos
        break

  # Zero length sentinel
  yield EndOfStream, pos


def ValidTokens(s):
  """
  Wrapper around Tokens to prevent callers from having to handle Invalid.

  I'm not combining the two functions because I might want to do a 'yield'
  transformation on Tokens9)?  Exceptions might complicate the issue?
  """
  pos = 0
  for tok_id, end_pos in Tokens(s):
    if tok_id == Invalid:
      raise LexError(s, pos)
    yield tok_id, end_pos
    pos = end_pos


# To match <a  or </a
# <h2 but not <2h ?
_TAG_RE = re.compile(r'/? \s* ([a-zA-Z][a-zA-Z0-9]*)', re.VERBOSE)

# To match href="foo"

_ATTR_RE = re.compile(r'''
\s+                     # Leading whitespace is required
([a-z]+)                # Attribute name
(?:                     # Optional attribute value
  \s* = \s*
  (?:
    " ([^>"]*) "        # double quoted value
  | ([a-zA-Z0-9_\-]+)   # Just allow unquoted "identifiers"
                        # TODO: relax this?  for href=$foo
  )
)?             
''', re.VERBOSE)


TagName, AttrName, UnquotedValue, QuotedValue = range(4)

class TagLexer(object):
  """
  Given a tag like <a href="..."> or <link type="..." />, the TagLexer
  provides a few operations:

  - What is the tag?
  - Iterate through the attributes, giving (name, value_start_pos, value_end_pos)
  """
  def __init__(self, s):
    self.s = s
    self.start_pos = -1  # Invalid
    self.end_pos = -1

  def Reset(self, start_pos, end_pos):
    self.start_pos = start_pos
    self.end_pos = end_pos

  def TagString(self):
    return self.s[self.start_pos : self.end_pos]

  def TagName(self):
    # First event
    tok_id, start, end = next(self.Tokens())
    return self.s[start : end]

  def GetSpanForAttrValue(self, attr_name):
    # Algorithm: search for QuotedValue or UnquotedValue after AttrName
    # TODO: Could also cache these

    events = self.Tokens()
    val = (-1, -1)
    try:
      while True:
        tok_id, start, end = next(events)
        if tok_id == AttrName:
          name = self.s[start:end]
          if name == attr_name:
            # For HasAttr()
            #val = True

            # Now try to get a real value
            tok_id, start, end = next(events)
            if tok_id in (QuotedValue, UnquotedValue):

              # TODO: Unescape this with htmlentitydefs
              # I think we need another lexer!
              #
              # We could make a single pass?
              # Shortcut: 'if '&' in substring'
              # Then we need to unescape it

              val = start, end
              break

    except StopIteration:
      pass
    return val

  def GetAttr(self, attr_name):
    # Algorithm: search for QuotedValue or UnquotedValue after AttrName
    # TODO: Could also cache these
    start, end = self.GetSpanForAttrValue(attr_name)
    if start == -1:
      return None
    return self.s[start : end]

  def Tokens(self):
    """
    Yields a sequence of tokens: Tag (AttrName AttrValue?)*

    Where each Token is (Type, start_pos, end_pos)

    Note that start and end are NOT redundant!  We skip over some unwanted
    characters.
    """
    m = _TAG_RE.match(self.s, self.start_pos+1)
    if not m:
      raise RuntimeError('Invalid HTML tag: %r' % self.TagString())
    yield TagName, m.start(1), m.end(1)

    pos = m.end(0)

    while True:
      # don't search past the end
      m = _ATTR_RE.match(self.s, pos, self.end_pos)
      if not m:
        # A validating parser would check that > or /> is next -- there's no junk
        break

      yield AttrName, m.start(1), m.end(1)

      # Quoted is group 2, unquoted is group 3.
      if m.group(2) is not None:
        yield QuotedValue, m.start(2), m.end(2)
      elif m.group(3) is not None:
        yield UnquotedValue, m.start(3), m.end(3)

      # Skip past the "
      pos = m.end(0)


def ReadUntilStartTag(it, tag_lexer, tag_name):
  """Find the next <foo>.

  tag_lexer is RESET.
  """
  pos = 0
  while True:
    try:
      tok_id, end_pos = next(it)
    except StopIteration:
      break
    tag_lexer.Reset(pos, end_pos)
    if tok_id == StartTag and tag_lexer.TagName() == tag_name:
      return pos, end_pos

    pos = end_pos

  raise ParseError('No start tag %r', tag_name)


def ReadUntilEndTag(it, tag_lexer, tag_name):
  """Find the next </foo>.

  tag_lexer is RESET.
  """
  pos = 0
  while True:
    try:
      tok_id, end_pos = next(it)
    except StopIteration:
      break
    tag_lexer.Reset(pos, end_pos)
    if tok_id == EndTag and tag_lexer.TagName() == tag_name:
      return pos, end_pos

    pos = end_pos

  raise ParseError('No end tag %r', tag_name)
