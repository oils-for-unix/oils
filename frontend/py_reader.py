#!/usr/bin/env python2
"""
py_reader.py - Code that won't be translated to C++.
"""
from __future__ import print_function

from frontend.reader import _Reader

from typing import Optional, Any, TYPE_CHECKING
if TYPE_CHECKING:
  from core.alloc import Arena
  # TODO: Hook these up when they have types.
  #from core.process import SignalState
  #from osh.prompt import PromptEvaluator
  #from osh import history


_PS2 = '> '

class InteractiveLineReader(_Reader):
  def __init__(self, arena, prompt_ev, hist_ev, line_input, prompt_state):
    # type: (Arena, Any, Any, Any, Any) -> None
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

