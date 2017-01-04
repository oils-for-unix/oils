#!/usr/bin/python
"""
pool.py - Sketch of memory management, like you would do in C++.

TODO: I think this should be a pool/arena for EVERY line parsed.
parse/execute/parse/execute.
At least for osh.
So you have to keep track of which arena, and ALSO the line WITHIN the arena?

So line_span becomes (int arena, int line_index, int col, int length)

Right after executing, you remove the arena from the pool.
Better names?  I think pool is the higher level, and arena is the lower level.
"""

import sys


# In C++, InteractiveLineReader and StringLineReader should use the same
# representation: std::string with internal NULs to terminate lines, and then
# std::vector<char*> that points into to it.
# InteractiveLineReader only needs to save a line if it contains a function.
# The parser needs to set a flag if it contains a function!

class Pool(object):
  """Owns source lines plus debug info.

  The Lexer will use the Reader and LineLexer to produce tokens.

  The LinePool has to be passed into both the parser and executor?
  And also parts need to be able to print themselves.. hm.
  """
  def __init__(self):
    # Could be std::vector<char *> pointing into a std::string
    self.lines = []
    self.debug_info = []  # list of (src_path index, line index)
    self.src_paths = []  # list of source paths
    self.src_index = -1  # index of current source file
    #self.mark_index = 0

    # Pools of objects.  Tokens are fixed size value objects?  Or I suppose
    # they could be allocated here.  If they are 16 bytes instead of 8 bytes
    # maybe that's a win on 32 bit?
    self.parts = []  # WordPart
    self.words = []  # Word
    self.nodes = []

  # NOTE: dash uses this same scheme.  stalloc() / setstackmark() /
  # popstackmark() in memalloc.c.

  # Should be NewArena and PopArena though.  But in Python we don't really
  # care?
  def Mark(self):
    """In interactive mode, call this before reading lines."""
    self.mark_index = len(self.lines)
    # TODO: Mark parts, words, nodes too

  def Erase(self):
    """
    Erase last lines from the pool.  This is done if there were no function
    definitions, after we executed everything.
    """
    # Delete the last ones
    del self.lines[self.mark_index : ]
    # TODO: Delete parts, words, nodes too

  def AddSourcePath(self, src_path):
    self.src_paths.append(src_path)
    self.src_index += 1

  def AddLine(self, line, line_num):
    pool_index = len(self.lines)
    self.lines.append(line)
    self.debug_info.append((self.src_index, line_num))
    return pool_index

  def GetLine(self, pool_index):
    """
    Given an line ID, return the actual filename, physical line number, and
    line contents.
    """
    return self.lines[pool_index]

  def GetDebugInfo(self, pool_index):
    src_index, line_num = self.debug_info[pool_index]
    try:
      path = self.src_paths[src_index]
    except IndexError:
      print('INDEX', src_index)
      raise
    return path, line_num


# NOTE: Not used right now.
def SpanValue(span, pool):
  """Given an line_span and a pool of lines, return the string value.
  """
  line = pool.GetLine(span.pool_index)
  c = span.col
  return line[c : c + span.length]
