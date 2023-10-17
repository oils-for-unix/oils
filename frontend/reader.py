# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
reader.py - Read lines of input.
"""
from __future__ import print_function

from mycpp import mylib

from core.error import p_die

from typing import Optional, Tuple, List, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import Token, SourceLine
    from core.alloc import Arena
    from core.comp_ui import PromptState
    from osh import history
    from osh import prompt
    from frontend.py_readline import Readline

_PS2 = '> '


class _Reader(object):

    def __init__(self, arena):
        # type: (Arena) -> None
        self.arena = arena
        self.line_num = 1  # physical line numbers start from 1

    def SetLineOffset(self, n):
        # type: (int) -> None
        """For --location-line-offset."""
        self.line_num = n

    def _GetLine(self):
        # type: () -> Optional[str]
        raise NotImplementedError()

    def GetLine(self):
        # type: () -> Tuple[SourceLine, int]
        line_str = self._GetLine()
        if line_str is None:
            eof_line = None  # type: Optional[SourceLine]
            return eof_line, 0

        src_line = self.arena.AddLine(line_str, self.line_num)
        self.line_num += 1
        return src_line, 0

    def Reset(self):
        # type: () -> None
        """Called after command execution in main_loop.py."""
        pass

    def LastLineHint(self):
        # type: () -> bool
        """A hint if we're on the last line, for optimization.

        This is only for performance, not correctness.
        """
        return False


class DisallowedLineReader(_Reader):
    """For CommandParser in YSH expressions."""

    def __init__(self, arena, blame_token):
        # type: (Arena, Token) -> None
        _Reader.__init__(self, arena)  # TODO: This arena is useless
        self.blame_token = blame_token

    def _GetLine(self):
        # type: () -> Optional[str]
        p_die("Here docs aren't allowed in expressions", self.blame_token)


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
        self.last_line_hint = False

    def _GetLine(self):
        # type: () -> Optional[str]
        line = self.f.readline()
        if len(line) == 0:
            return None

        if not line.endswith('\n'):
            self.last_line_hint = True

        #from mycpp.mylib import log
        #log('LINE %r', line)
        return line

    def LastLineHint(self):
        # type: () -> bool
        return self.last_line_hint


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
        # type: (List[Tuple[SourceLine, int]], Arena) -> None
        """
    Args:
      lines: List of (line_id, line) pairs
    """
        _Reader.__init__(self, arena)
        self.lines = lines
        self.num_lines = len(lines)
        self.pos = 0

    def GetLine(self):
        # type: () -> Tuple[SourceLine, int]
        if self.pos == self.num_lines:
            eof_line = None  # type: Optional[SourceLine]
            return eof_line, 0

        src_line, start_offset = self.lines[self.pos]

        self.pos += 1

        # NOTE: we return a partial line, but we also want the lexer to create
        # tokens with the correct line_spans.  So we have to tell it 'start_offset'
        # as well.
        return src_line, start_offset


def _readline_no_tty(prompt):
    # type: (str) -> str
    w = mylib.Stderr()
    w.write(prompt)
    w.flush()

    line = mylib.Stdin().readline()
    if line is None or len(line) == 0:
        # empty string == EOF
        raise EOFError()

    return line


class InteractiveLineReader(_Reader):

    def __init__(
            self,
            arena,  # type: Arena
            prompt_ev,  # type: prompt.Evaluator
            hist_ev,  # type:history.Evaluator
            line_input,  # type: Readline
            prompt_state,  # type:PromptState
    ):
        # type: (...) -> None
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

        line = None  # type: Optional[str]
        try:
            if not mylib.Stdout().isatty() or not mylib.Stdin().isatty():
                line = _readline_no_tty(
                    self.prompt_str) + '\n'  # newline required
            else:
                line = raw_input(self.prompt_str) + '\n'  # newline required
        except EOFError:
            print('^D')  # bash prints 'exit'; mksh prints ^D.

        if line is not None:
            # NOTE: Like bash, OSH does this on EVERY line in a multi-line command,
            # which is confusing.

            # Also, in bash this is affected by HISTCONTROL=erasedups.  But I
            # realized I don't like that behavior because it changes the numbers!  I
            # can't just remember a number -- I have to type 'hi' again.
            line = self.hist_ev.Eval(line)

            # Add the line if it's not EOL, not whitespace-only, not the same as the
            # previous line, and we have line_input.
            if (len(line.strip()) and line != self.prev_line and
                    self.line_input is not None):
                self.line_input.add_history(
                    line.rstrip())  # no trailing newlines
                self.prev_line = line

        self.prompt_str = _PS2  # TODO: Do we need $PS2?  Would be easy.
        self.prompt_state.SetLastPrompt(self.prompt_str)
        self.render_ps1 = False
        return line
