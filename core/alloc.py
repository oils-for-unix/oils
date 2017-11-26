"""
alloc.py - Sketch of memory management.

This is roughly what you might do in C++, but it's probably overly complicated
for Python.

The idea is to save the LST for functions, but discard it for commands that
have already executed.  Each statement/function can be parsed into a separate
Arena, and the entire Arena can be discarded at once.

Also, we don't want to save comment lines.
"""

from asdl import const


class Arena(object):
  """A collection of lines and line spans.

  In C++ and maybe Oil: A block of memory that can be freed at once.

  Two use cases:
  1. Reformatting: ClearLastLine() is never called
  2. Execution: ClearLastLine() for lines that are all comments.  The purpose
     of this is not to penalize big comment blocks in .rc files and completion
     files!
  """
  def __init__(self, arena_id):
    self.arena_id = arena_id  # an integer stored in tokens

    # Could be std::vector<char *> pointing into a std::string.
    # NOTE: lines are required for bootstrapping code within the binary, and
    # also required for interactive or stdin, but optional when code is on
    # disk.  We can go look it up later to save memory.
    self.lines = []
    self.next_line_id = 0

    # first real span is 1.  0 means undefined.
    self.spans = []
    self.next_span_id = 0

    # List of (src_path index, physical line number).  This is two integers for
    # every line read.  We could use a clever encoding of this.  (Although the
    # it's probably more important to compact the ASDL representation.)
    self.debug_info = []
    self.src_paths = []  # list of source paths
    self.src_id_stack = []  # stack of src_id integers

  def IsComplete(self):
    """Return whether we have a full set of lines -- none of which was cleared.

    Maybe just an assertion error.
    """

  def PushSource(self, src_path):
    src_id = len(self.src_paths)
    self.src_paths.append(src_path)
    self.src_id_stack.append(src_id)

  def PopSource(self):
    self.src_id_stack.pop()

  def AddLine(self, line, line_num):
    """
    Args:
      line: string
      line_num: physical line number, for printing

    TODO: Add an option of whether to save the line?  You can retrieve it on
    disk in many cases.  (But not in the stdin, '-c', 'eval' case)
    """
    line_id = self.next_line_id
    self.lines.append(line)
    self.next_line_id += 1
    self.debug_info.append((self.src_id_stack[-1], line_num))
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
    assert span_id != const.NO_INTEGER, span_id
    return self.spans[span_id]  # span IDs start from 1

  def GetDebugInfo(self, line_id):
    """Get the path and physical line number, for parse errors."""
    assert line_id != const.NO_INTEGER, line_id
    src_id , line_num = self.debug_info[line_id]
    try:
      path = self.src_paths[src_id]
    except IndexError:
      print('INDEX', src_id)
      raise
    return path, line_num


def CompletionArena(pool):
  """A temporary arena that only exists for a function call?"""
  arena = pool.NewArena()
  arena.PushSource('<completion>')
  return arena


# In C++, InteractiveLineReader and StringLineReader should use the same
# representation: std::string with internal NULs to terminate lines, and then
# std::vector<char*> that points into to it.
# InteractiveLineReader only needs to save a line if it contains a function.
# The parser needs to set a flag if it contains a function!

class Pool(object):
  """Owns source lines plus debug info.

  Two use cases:
  1. Reformatting: PopArena() is never called
  2. Execution: PopArena() is called if an arena doesn't have any functions.
  If the whole thing was executed.

  At the end of the program, all remaining arenas can be freed, or we just let
  the OS clean up.  Probably in debug/ASAN mode, we will clean it up.  We also
  want to clean up in embedded mode.  the oil_Init() and oil_Destroy() methods
  of the API should do this.
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
