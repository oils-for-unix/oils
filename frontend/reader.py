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

from core.util import p_die

from typing import Optional, Tuple, List, IO, Any, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import token
  from core.alloc import Arena
  # TODO: Hook these up when they have types.
  #from core.process import SignalState
  #from osh.prompt import PromptEvaluator
  #from osh import history


class _Reader(object):
  def __init__(self, arena):
    # type: (Arena) -> None
    self.arena = arena
    self.line_num = 1  # physical line numbers start from 1

  def _GetLine(self):
    # type: () -> Optional[str]
    raise NotImplementedError

  def GetLine(self):
    # type: () -> Tuple[int, Optional[str], int]
    line = self._GetLine()
    if line is None:
      return -1, None, 0

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
    # type: (Arena, token) -> None
    _Reader.__init__(self, arena)  # TODO: This arena is useless
    self.blame_token = blame_token

  def _GetLine(self):
    # type: () -> Optional[str]
    p_die("Here docs aren't allowed in expressions", token=self.blame_token)


_PS2 = '> '

class InteractiveLineReader(_Reader):
  def __init__(self, arena, prompt_ev, hist_ev, line_input, prompt_state,
               sig_state):
    # type: (Arena, Any, Any, Any, Any, Any) -> None
    # TODO: Hook up PromptEvaluator and history.Evaluator when they have types.
    """
    Args:
      prompt_state: Current prompt is PUBLISHED here.
    """
    _Reader.__init__(self, arena)
    self.prompt_ev = prompt_ev
    self.hist_ev = hist_ev
    self.line_input = line_input  # may be None!
    self.prompt_state = prompt_state
    self.sig_state = sig_state

    self.prev_line = None  # type: str
    self.prompt_str = ''

    self.Reset()

  def Reset(self):
    # type: () -> None
    """Called after command execution."""
    self.render_ps1 = True

  def _GetLine(self):
    # type: () -> Optional[str]

    # NOTE: In bash, the prompt goes to stderr, but this seems to cause drawing
    # problems with readline?  It needs to know about the prompt.
    #sys.stderr.write(self.prompt_str)

    if self.render_ps1:
      self.prompt_str = self.prompt_ev.EvalFirstPrompt()
      self.prompt_state.SetLastPrompt(self.prompt_str)

    try:
      line = raw_input(self.prompt_str) + '\n'  # newline required
    except EOFError:
      print('^D')  # bash prints 'exit'; mksh prints ^D.
      line = None

    if line is not None:
      # NOTE: Like bash, OSH does this on EVERY line in a multi-line command,
      # which is confusing.

      # Also, in bash this is affected by HISTCONTROL=erasedups.  But I
      # realized I don't like that behavior because it changes the numbers!  I
      # can't just remember a number -- I have to type 'hi' again.
      line = self.hist_ev.Eval(line)

      # Add the line if it's not EOL, not whitespace-only, not the same as the
      # previous line, and we have line_input.
      if (line.strip() and line != self.prev_line and
          self.line_input is not None):
        self.line_input.add_history(line.rstrip())  # no trailing newlines
        self.prev_line = line

    self.prompt_str = _PS2  # TODO: Do we need $PS2?  Would be easy.
    self.prompt_state.SetLastPrompt(self.prompt_str)
    self.render_ps1 = False
    return line


class FileLineReader(_Reader):
  """For -c and stdin?"""

  def __init__(self, f, arena):
    # type: (IO[str], Arena) -> None
    """
    Args:
      lines: List of (line_id, line) pairs
    """
    _Reader.__init__(self, arena)
    self.f = f

  def _GetLine(self):
    # type: () -> Optional[str]
    line = self.f.readline()
    if not line:
      return None

    return line


def StringLineReader(s, arena):
  # type: (str, Arena) -> FileLineReader
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
      return -1, None, 0
    line_id, line, start_offset = self.lines[self.pos]

    self.pos += 1

    # NOTE: we return a partial line, but we also want the lexer to create
    # tokens with the correct line_spans.  So we have to tell it 'start_offset'
    # as well.
    return line_id, line, start_offset
