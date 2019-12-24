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


class _Event(object):
  """
  An event has a type and a (start, end)
  Does it make more sense to store an array of (id, end) pairs?
  And then look back in the array?
  Well the whole event can be returned on the stack here.
  (8, 4, 4) = 16 + tag = 18
  """

  def __init__(self, s, start_pos, end_pos):
    self.s = s
    self.start_pos = start_pos
    self.end_pos = end_pos

    # TODO: Should this have a span ID?

    # Like the Token, except it has a kind
    #
    # Token(id id, int span_id, char* start, int length)

  def Substring(self):
    return self.s[self.start_pos : self.end_pos]

  def __str__(self):
    return '[%s %r]' % (self.__class__.__name__, self.Substring())


class Decl(_Event):
  """
  <!DOCTYPE html>

  Usually this doesn't need to be parsed?
  """
  pass


class Comment(_Event):
  """
  <!-- comment -->
  """
  pass


class Processing(_Event):
  """
  Python's HTML parser has this.

  <? code ?>
  """
  pass


TAG_RE = re.compile(r'\s*([a-zA-Z]+)')

class _AttrEvent(_Event):

  def __init__(self, s, start_pos, end_pos):
    _Event.__init__(self, s, start_pos, end_pos)
    # lazily done
    self.tag = None
    self.attrs = None

  def Tag(self):
    """
    return 'a' for <a href=""> etc.
    """
    # start it after the angle bracket
    if self.tag is None:
      m = TAG_RE.match(self.s, self.start_pos+1)
      if not m:
        raise RuntimeError('Invalid HTML tag: %r' % self.Substring())
      self.tag = m.group(1)
    return self.tag


class StartTag(_AttrEvent):
  pass


class StartEndTag(_AttrEvent):
  pass


class EndTag(_Event):
  pass


class EntityRef(_Event):
  """
  Note: Python has 

  handle_entityref
  handle_charref

  I think those should be the same?  We don't want to force clients to handle
  them?
  """
  def Value(self):
    """
    For use when converting to text.
    """
    pass


class RawData(_Event):
  pass


class Invalid(_Event):
  pass


class EndOfStream(_Event):
  pass


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

  (r'&.*?;', EntityRef),

  # Exclude > for validation
  (r'[^&<>]+', RawData),

  (r'.', Invalid),  # error!
]

LEXER = [
  # DOTALL is for the comment
  (re.compile(pat, re.VERBOSE | re.DOTALL), i) for
  (pat, i) in LEXER
]



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

# for event in p.Events():
#  p.StartPos()
#  p.EndPos()


def Parse(s):
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
        obj = cls(s, pos, end_pos)
        pos = end_pos
        yield obj
        break

  # Zero length sentinel
  yield EndOfStream(s, pos, pos)


def main(argv):
  pass


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
