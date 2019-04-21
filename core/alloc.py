"""
alloc.py - Sketch of memory management.

This is roughly what you might do in C++, but it's probably overly complicated
for Python.

The idea is to save the LST for functions, but discard it for commands that
have already executed.  Each statement/function can be parsed into a separate
Arena, and the entire Arena can be discarded at once.

Also, we don't want to save comment lines.
"""

from _devbuild.gen.syntax_asdl import line_span, source, source_t
from asdl import const
from core.util import log

from typing import List, Tuple


class Arena(object):
  """A collection line spans and associated debug info.

  Use Cases:
  1. Error reporting
  2. osh-to-oil Translation
  """
  def __init__(self, arena_id):
    # type: (int) -> None
    self.arena_id = arena_id  # an integer stored in tokens

    # TODO: lines should be part of the token, so they get garbage collected
    # when the token goes away.  (For example, a line that's all whitespace
    # will have no tokens put in the LST.)
    self.lines = []  # type: List[str]
    self.next_line_id = 0

    # first real span is 1.  0 means undefined.
    self.spans = []  # type: List[line_span]
    self.next_span_id = 0

    # (src_path, physical line number)
    self.debug_info = []  # type: List[Tuple[str, int]] 
    self.src_paths = []  # type: List[str]
    # reuse these instances in many line_span instances
    self.source_instances = []  # type: List[source_t]

  def PushSource(self, src_path):
    # type: (str) -> None
    self.src_paths.append(src_path)
    self.source_instances.append(source.File(src_path))

  def PopSource(self):
    # type: () -> None
    self.src_paths.pop()
    self.source_instances.pop()

  def AddLine(self, line, line_num):
    # type: (str, int) -> int
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
    self.debug_info.append((self.src_paths[-1], line_num))
    return line_id

  def GetLine(self, line_id):
    # type: (int) -> str
    """
    Given an line ID, return the actual filename, physical line number, and
    line contents.
    """
    assert line_id >= 0, line_id
    return self.lines[line_id]

  def AddLineSpan(self, line_id, col, length):
    # type: (int, int, int) -> int
    """Save a line_span and return a new span ID for later retrieval."""
    span = line_span(line_id, col, length, self.source_instances[-1])
    self.spans.append(span)
    span_id = self.next_span_id
    self.next_span_id += 1
    return span_id

  def GetLineSpan(self, span_id):
    # type: (int) -> line_span
    assert span_id != const.NO_INTEGER, span_id
    try:
      return self.spans[span_id]
    except IndexError:
      log('Span ID out of range: %d is greater than %d', span_id,
          len(self.spans))
      raise

  def LastSpanId(self):
    # type: () -> int
    """Return one past the last span ID."""
    return len(self.spans)

  def GetDebugInfo(self, line_id):
    # type: (int) -> Tuple[str, int]
    """Get the path and physical line number, for parse errors."""
    assert line_id != const.NO_INTEGER, line_id
    path, line_num = self.debug_info[line_id]
    return path, line_num


# TODO: Remove this.  There are many sources of code, and they are hard to
# divide strictly into arenas.
def SideArena(source_name):
  # type: (str) -> Arena
  """A new arena outside the main one.
  
  For completion, $PS1 and $PS4, a[x++]=1, etc.

  Translation takes advantage of the fact that arenas have contiguous span_ids.
  """
  # TODO: Should there only be one pool?  This isn't worked out yet.  Or just
  # get rid of the pool concept?
  pool = Pool()
  arena = pool.NewArena()
  arena.PushSource(source_name)
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
    # type: () -> None
    self.arenas = []  # type: List[Arena]
    self.next_arena_id = 0

  # NOTE: dash uses a similar scheme.  stalloc() / setstackmark() /
  # popstackmark() in memalloc.c.

  # We're not using Push/POp terminology because you never pop twice.  You can
  # only destroy the top/last arena.
  def NewArena(self):
    # type: () -> Arena
    """Call this after parsing anything that you might want to destroy."""
    a = Arena(self.next_arena_id)
    self.next_arena_id += 1
    self.arenas.append(a)
    return a
