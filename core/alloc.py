#!/usr/bin/python
"""
alloc.py - Sketch of memory management, like you would do in C++.

Keep track of which arena, and ALSO the line WITHIN the arena?
So line_span becomes (int arena, int line_index, int col, int length)

Right after executing, you remove the arena from the pool.
Better names?  I think pool is the higher level, and arena is the lower level.
"""

class Arena(object):
  """A collection of lines and line spans.

  For execution, the parse tree doesn't need to represent these.
  For conversion, we.

  In C++ and maybe oil: A block of memory that can be freed at once.

  Two use cases:

  - Reformatting
    - PopLine() is never called
  - Execution
    - PopLine() for lines that are all comments.  The purpose of this is not to
      penalize big comment blocks in .rc files and completion files!

  """
  def __init__(self, arena_id):
    self.arena_id = arena_id  # an integer stored in tokens

    # Could be std::vector<char *> pointing into a std::string.
    # NOTE: lines are required for bootstrapping code within the binary, and
    # also required for interactive or stdin, but optional when code is on
    # disk.  We can go look it up later to save memory.
    self.lines = []
    self.next_line_id = 0

    self.spans = []
    self.next_span_id = 0

    self.debug_info = []  # list of (src_path index, physical line number)
    self.src_paths = []  # list of source paths
    self.src_index = -1  # index of current source file

  def IsComplete(self):
    """Return whether we have a full set of lines -- none of which was cleared.

    Maybe just an assertion error.
    """

  def AddSourcePath(self, src_path):
    # TODO: Should this be part of the pool?
    self.src_paths.append(src_path)
    self.src_index += 1

  def AddLine(self, line, line_num):
    """
    TODO: Add an option of whether to save the line?  You can retrieve it on
    disk in many cases.
    """
    line_id = self.next_line_id
    self.lines.append(line)
    self.next_line_id += 1
    self.debug_info.append((self.src_index, line_num))
    return line_id

  def ClearLastLine(self):
    """Call if it was a comment."""
    pass

  def GetLine(self, line_id):
    """
    Given an line ID, return the actual filename, physical line number, and
    line contents.
    """
    assert line_id >= 0, line_id
    return self.lines[line_id]

  def AddLineSpan(self, line_span):
    """
    TODO: Add an option of whether to save the line?  You can retrieve it on
    disk in many cases.
    """
    span_id = self.next_span_id
    self.spans.append(line_span)
    self.next_span_id += 1
    return span_id

  def GetLineSpan(self, span_id):
    assert span_id >= 0, span_id
    return self.spans[span_id]

  def GetDebugInfo(self, line_id):
    """Get the path and physical line number, for parse errors."""
    assert line_id >= 0
    src_index, line_num = self.debug_info[line_id]
    try:
      path = self.src_paths[src_index]
    except IndexError:
      print('INDEX', src_index)
      raise
    return path, line_num


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


  Two use cases:

  - Reformatting
    - PopArena() is never called
  - Execution
    - PopArena() is called if an arena doesn't have any functions.  If the
      whole thing was executed.
  - At the end of the program, all remaining arenas can be freed, or we just
    let the OS clean up.  Probably in debug/ASAN mode, we will clean it up.
    We also want to clean up in embedded mode.  the oil_Init() and
    oil_Destroy() methods of the API should do this.
  """
  def __init__(self):
    self.arenas = []
    self.next_arena_id = 0

  # NOTE: dash uses a similar scheme.  stalloc() / setstackmark() /
  # popstackmark() in memalloc.c.

  # We're not using Push/POp terminology because you never pop twice.  You can
  # only destroy the top/last arena.
  def NewArena(self):
    """Call this after parsing anything that you might want to destroy."""
    a = Arena(self.next_arena_id)
    self.next_arena_id += 1
    self.arenas.append(a)
    return a

  def DestroyLastArena(self):
    """
    Free everything in the last arena (possibly reusing it).  This is done
    after we executed all of its statements if there were no function
    definitions that need to be executed later.
    """
    a = self.arenas.pop()
    # This removes lines and spans?
    del a

  def IsComplete(self):
    """Return whether we have one arena that was never destroyed?"""


# TODO: Also need arena_id

# NOTE: Not used right now.
def SpanValue(span, arena):
  """Given an line_span and a arena of lines, return the string value.
  """
  line = arena.GetLine(span.line_id)
  c = span.col
  return line[c : c + span.length]
