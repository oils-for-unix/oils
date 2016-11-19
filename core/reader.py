#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
"""
reader.py - Read lines of input.
"""

class _Reader(object):
  def __init__(self, pool):
    self.pool = pool
    self.line_num = 0  # physical line number

  def GetLine(self):
    line = self._GetLine()
    if self.pool:
      pool_index = self.pool.AddLine(line, self.line_num)
    else:
      pool_index = -1
    self.line_num += 1
    return pool_index, line

  def Reset(self):
    # Should never be called?
    pass


_PS1 = '! '  # distinguish it from bash
_PS2 = '> '

class InteractiveLineReader(_Reader):
  def __init__(self, pool=None):
    _Reader.__init__(self, pool)
    self.prompt_str = _PS1

  def _GetLine(self):
    try:
      ret = input(self.prompt_str) + '\n'
    except EOFError:
      ret = None
    self.prompt_str = _PS2
    return ret

  def Reset(self):
    """Call this after command execution, to free memory taken up by the lines,
    and reset prompt string back to PS1.
    """
    self.prompt_str = _PS1
    # free vector...


class StringLineReader(_Reader):
  """For -c and stdin?"""

  def __init__(self, s, pool=None):
    """
    Args:
      lines: List of (pool_index, line) pairs
    """
    _Reader.__init__(self, pool)
    self.lines = s.splitlines(True)
    self.pos = 0

  def _GetLine(self):
    if self.pos == len(self.lines):
      return None
    line = self.lines[self.pos]

    # The last line should be passed to the Lexer with a '\n', even if it
    # didn't have one.
    if not line.endswith('\n'):
      line += '\n'

    self.pos += 1
    return line


# C++ ownership notes:
# - used for file input (including source)
# - used for -c arg (NUL terminated, likely no newline)
# - used for eval arg
# - for here doc?
#
# Adding \n causes problems for StringPiece.  Maybe we an just copy it
# internally.


class VirtualLineReader(object):
  """Used for here docs."""
  def __init__(self, lines):
    """
    Args:
      lines: List of (pool_index, line) pairs
    """
    self.lines = lines
    self.pos = 0

  def GetLine(self):
    if self.pos == len(self.lines):
      return -1, None
    pool_index, line = self.lines[self.pos]

    self.pos += 1
    return pool_index, line
