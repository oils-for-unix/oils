#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
reader.py - Read lines of input.
"""

import cStringIO
import sys

from core import util
log = util.log


class _Reader(object):
  def __init__(self, arena):
    self.arena = arena
    self.line_num = 1  # physical line numbers start from 1

  def GetLine(self):
    line = self._GetLine()
    if line is None:
      return -1, None, 0

    if self.arena:
      line_id = self.arena.AddLine(line, self.line_num)
    else:
      line_id = -1
    self.line_num += 1
    return line_id, line, 0

  def Reset(self):
    # Should never be called?
    pass


_PS2 = '> '

class InteractiveLineReader(_Reader):
  def __init__(self, arena, prompt):
    _Reader.__init__(self, arena)
    self.prompt = prompt
    self.prompt_str = ''
    self.Reset()  # initialize self.prompt_str

  def _GetLine(self):
    # NOTE: In bash, the prompt goes to stderr, but this seems to cause drawing
    # problems with readline?  It needs to know about the prompt.

    #sys.stderr.write(self.prompt_str)
    try:
      ret = raw_input(self.prompt_str) + '\n'  # newline required
    except EOFError:
      print('^D')  # bash prints 'exit'; mksh prints ^D.
      ret = None
    self.prompt_str = _PS2  # TODO: Do we need $PS2?  Would be easy.
    return ret

  def Reset(self):
    """Call this after command execution, to free memory taken up by the lines,
    and reset prompt string back to PS1.
    """
    self.prompt_str = self.prompt.FirstPrompt()


class FileLineReader(_Reader):
  """For -c and stdin?"""

  def __init__(self, f, arena):
    """
    Args:
      lines: List of (line_id, line) pairs
    """
    _Reader.__init__(self, arena)
    self.f = f

  def _GetLine(self):
    line = self.f.readline()
    if not line:
      return None

    return line


def StringLineReader(s, arena):
  return FileLineReader(cStringIO.StringIO(s), arena)


# C++ ownership notes:
# - used for file input (including source)
# - used for -c arg (NUL terminated, likely no newline)
# - used for eval arg
# - for here doc?
#
# Adding \n causes problems for StringPiece.  Maybe we an just copy it
# internally.


class VirtualLineReader(_Reader):
  """Read from lines we already read from the OS.

  Used for here docs and aliases.
  """

  def __init__(self, lines, arena):
    """
    Args:
      lines: List of (line_id, line) pairs
    """
    _Reader.__init__(self, arena)
    self.lines = lines
    self.num_lines = len(lines)
    self.pos = 0

  def GetLine(self):
    if self.pos == self.num_lines:
      return -1, None, 0
    line_id, line, start_offset = self.lines[self.pos]

    self.pos += 1

    # NOTE: we return a partial line, but we also want the lexer to create
    # tokens with the correct line_spans.  So we have to tell it 'start_offset'
    # as well.
    return line_id, line, start_offset
