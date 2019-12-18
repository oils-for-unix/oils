# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
reader.py - Read lines of input.
"""

from mycpp import mylib

from core.util import p_die

from typing import Optional, Tuple, List, Union, IO, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import Token
  from core.alloc import Arena


class _Reader(object):
  def __init__(self, arena):
    # type: (Arena) -> None
    self.arena = arena
    self.line_num = 1  # physical line numbers start from 1

  def _GetLine(self):
    # type: () -> Optional[str]
    raise NotImplementedError()

  def GetLine(self):
    # type: () -> Tuple[int, Optional[str], int]
    line = self._GetLine()
    if line is None:
      eof_line = None  # type: Optional[str]
      return -1, eof_line, 0

    line_id = self.arena.AddLine(line, self.line_num)
    self.line_num += 1
    return line_id, line, 0

  def Reset(self):
    # type: () -> None
    """Called after command execution in main_loop.py."""
    pass


class DisallowedLineReader(_Reader):
  """For CommandParser in Oil expressions."""

  def __init__(self, arena, blame_token):
    # type: (Arena, Token) -> None
    _Reader.__init__(self, arena)  # TODO: This arena is useless
    self.blame_token = blame_token

  def _GetLine(self):
    # type: () -> Optional[str]
    p_die("Here docs aren't allowed in expressions", token=self.blame_token)


class FileLineReader(_Reader):
  """For -c and stdin?"""

  def __init__(self, f, arena):
    # type: (mylib.LineReader, Arena) -> None
    """
    Args:
      lines: List of (line_id, line) pairs
    """
    _Reader.__init__(self, arena)
    self.f = f

  def _GetLine(self):
    # type: () -> Optional[str]
    line = self.f.readline()
    if len(line) == 0:
      return None

    return line


def StringLineReader(s, arena):
  # type: (str, Arena) -> FileLineReader
  return FileLineReader(mylib.BufLineReader(s), arena)

# TODO: Should be BufLineReader(Str)?
# This doesn't have to copy.  It just has a pointer.


class VirtualLineReader(_Reader):
  """Read from lines we already read from the OS.

  Used for here docs and aliases.
  """

  def __init__(self, lines, arena):
    # type: (List[Tuple[int, str, int]], Arena) -> None
    """
    Args:
      lines: List of (line_id, line) pairs
    """
    _Reader.__init__(self, arena)
    self.lines = lines
    self.num_lines = len(lines)
    self.pos = 0

  def GetLine(self):
    # type: () -> Tuple[int, Optional[str], int]
    if self.pos == self.num_lines:
      eof_line = None  # type: Optional[str]
      return -1, eof_line, 0

    line_id, line, start_offset = self.lines[self.pos]

    self.pos += 1

    # NOTE: we return a partial line, but we also want the lexer to create
    # tokens with the correct line_spans.  So we have to tell it 'start_offset'
    # as well.
    return line_id, line, start_offset
