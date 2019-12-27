#!/usr/bin/env python2
"""
pulp.py - Low-Level HTML Processing.

TODO: This should be an Oil library eventually.  It's a "lazily-parsed data
structure" like TSV2.

In theory JSON could do use this?

Features:

1. Syntax errors with locations
2. Lazy Parsing
   note: how does the Oil language support that?  Maybe at the C API level?
3. Lossless Syntax Tree
   - enables 'sed' like behavior

"""
from __future__ import print_function

import re
import sys


def log(msg, *args):
  msg = msg % args
  print(msg, file=sys.stderr)


class Output(object):

  def __init__(self, s, f):
    self.s = s
    self.f = f
    self.pos = 0

  def Skip(self, pos):
    self.pos = pos

  def PrintUntil(self, pos):
    piece = self.s[self.pos : pos]
    self.f.write(piece)
    self.pos = pos


( Decl, Comment, Processing,
  StartTag, StartEndTag, EndTag,
  EntityRef, RawData,
  Invalid, EndOfStream ) = range(10)


def _MakeLexer(rules):
  return [
  # DOTALL is for the comment
    (re.compile(pat, re.VERBOSE | re.DOTALL), i) for
    (pat, i) in rules
  ]

#
# Eggex
#
# Tag      = / ~['>']* /

# Is this valid?  A single character?
# Tag      = / ~'>'* /

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

  (r'<! [^>]* >', Decl),

  (r'</ [^>]* >', EndTag),  # self-closing <br/>  comes FIRST
  (r'< [^>]* />', StartEndTag),        # end </a>
  (r'< [^>]*  >', StartTag), # start <a>

  # TODO: MAke this more precise
  (r'&.*?;', EntityRef),

  # Exclude > for validation
  (r'[^&<>]+', RawData),

  (r'.', Invalid),  # error!
]

LEXER = _MakeLexer(LEXER)

# Another design:
#
# out = pulp.Printer(TEST_HTML, sys.stdout)
#
# p = html.Parser(TEST_HTML)
# p.Next()

# p.EventType()
# p.StartPos() or p.Pos()
# p.EndPos()
#
# out.PrintTo(p.StartPos())
# out.SkipTo(p.EndPos())

# for event in p.Tokens():
#  p.StartPos()
#  p.EndPos()


def Tokens(s):
  """
  Args:
    s: string to parse
  """
  pos = 0
  n = len(s)

  while pos < n:
    for pat, cls in LEXER:
      m = pat.match(s, pos)
      if m:
        end_pos = m.end()
        yield cls, end_pos
        pos = end_pos
        break

  # Zero length sentinel
  yield EndOfStream, pos


# To match <a
_TAG_RE = re.compile(r'\s*([a-zA-Z]+)')

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
  def __init__(self):
    pass

  def Reset(self, s, start_pos, end_pos):
    self.s = s
    self.start_pos = start_pos
    self.end_pos = end_pos

  def TagString(self):
    return self.s[self.start_pos : self.end_pos]

  def Tag(self):
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
