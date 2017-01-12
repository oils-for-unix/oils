#!/usr/bin/python
"""
fix.py -- Do source transformations.  Somewhat like 'go fix'.
"""

import sys

class Cursor:
  """
  Wrapper for printing/transforming a complete source file stored in a single
  arena.
  """

  def __init__(self, arena):
    self.arena = arena
    self.next_span_id = 0

  def PrintUntil(self, span_id, f):
    for i in xrange(self.next_span_id, span_id):
      span = self.arena.GetSpan(i)
      line = self.arena.GetLine(span.line_id)
      f.write('X')

  def SkipUntil(self, next_span_id):
    """Skip everything before next_span_id.
    Printing will start at next_span_id
    """
    pass

  def PrintTheRest(self, f):
    # Called once at the end.  Trailing comments.
    pass

# Should this just take an arena, which has all three things?

def Print(arena, node):
  #print node
  #print(spans)

  # TODO: 
  # - Attach span_id to every node, with  "attributes" I guess
  #   - or do it manually on arithmetic first

  # - Then do 

  # First pass:
  # - f() {} to proc f {}
  # - $(( )) and $[ ]  to $()
  # - ${foo} to $(foo)
  # - $(echo hi) to $[echo hi]
  #
  # Dispatch on node.type I guess.
  #
  # or just try 'echo $( echo hi )'  -- preserving whitespace

  # c = Cursor(spans)
  # def Fix(node, cursor, f):
  #  cursor.PrintUntil(node._begin_id, f)
  #  print(Reformat(node))
  #  cursor.Skip(node._end_id)

  #  for child in node.children:
  #    Fix(node, cursor, f)
  #
  # "node" is a node tof ix

  c = Cursor(arena)
  for span in arena.spans:
    line = arena.GetLine(span.line_id)
    piece = line[span.col : span.col + span.length]
    print(repr(piece))

