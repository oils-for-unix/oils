"""
alloc.py - Sketch of memory management.

This is roughly what you might do in C++, but it's probably overly complicated
for Python.

The idea is to save the LST for functions, but discard it for commands that
have already executed.  Each statement/function can be parsed into a separate
Arena, and the entire Arena can be discarded at once.

Also, we don't want to save comment lines.
"""

from _devbuild.gen.syntax_asdl import (
    line_span, source_t, source__CFlag, source__MainFile, source__SourcedFile
)
from asdl import const
from core.util import log

from typing import List


class Arena(object):
  """A collection line spans and associated debug info.

  Use Cases:
  1. Error reporting
  2. osh-to-oil Translation
  """
  def __init__(self):
    # type: () -> None

    # Three parallel arrays for line information.  indexed by line_id
    self.line_vals = []  # type: List[str]
    self.line_nums = []  # type: List[int]
    self.line_srcs = []  # type: List[source_t]

    # indexed by span_id
    self.spans = []  # type: List[line_span]

    # reuse these instances in many line_span instances
    self.source_instances = []  # type: List[source_t]

  def PushSource(self, src):
    # type: (source_t) -> None
    self.source_instances.append(src)

  def PopSource(self):
    # type: () -> None
    self.source_instances.pop()

  def AddLine(self, line, line_num):
    # type: (str, int) -> int
    """Save a physical line and return a line_id for later retrieval.

    The line number is 1-based.
    """
    line_id = len(self.line_vals)
    self.line_vals.append(line)
    self.line_nums.append(line_num)
    self.line_srcs.append(self.source_instances[-1])
    return line_id

  def GetLine(self, line_id):
    # type: (int) -> str
    assert line_id >= 0, line_id
    return self.line_vals[line_id]

  def GetLineNumber(self, line_id):
    # type: (int) -> int
    return self.line_nums[line_id]

  def GetLineSource(self, line_id):
    # type: (int) -> source_t
    return self.line_srcs[line_id]

  def GetLineSourceString(self, line_id):
    # type: (int) -> str
    """Returns a human-readable string for dev tools."""
    src = self.line_srcs[line_id]

    # TODO: Make it look nicer, like core/ui.py.
    if isinstance(src, source__CFlag):
      return '-c flag'
    if isinstance(src, source__MainFile):
      return src.path
    if isinstance(src, source__SourcedFile):
      return src.path
    return repr(src)

  def AddLineSpan(self, line_id, col, length):
    # type: (int, int, int) -> int
    """Save a line_span and return a new span ID for later retrieval."""
    span_id = len(self.spans)  # spids are just array indices
    span = line_span(line_id, col, length)
    self.spans.append(span)
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
