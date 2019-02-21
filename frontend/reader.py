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
from core.meta import Id
from frontend.match import HISTORY_LEXER
from osh import word

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
  def __init__(self, arena, prompt_ev, hist_ev, line_input):
    _Reader.__init__(self, arena)
    self.prompt_ev = prompt_ev
    self.hist_ev = hist_ev
    self.line_input = line_input  # may be None!

    self.prev_line = None
    self.prompt_str = ''
    self.Reset()  # initialize self.prompt_str

  def _GetLine(self):
    # NOTE: In bash, the prompt goes to stderr, but this seems to cause drawing
    # problems with readline?  It needs to know about the prompt.

    #sys.stderr.write(self.prompt_str)
    try:
      line = raw_input(self.prompt_str) + '\n'  # newline required
    except EOFError:
      print('^D')  # bash prints 'exit'; mksh prints ^D.
      line = None
    else:
      # NOTE: Like bash, OSH does this on EVERY line in a multi-line command,
      # which is confusing.

      # Also, in bash this is affected by HISTCONTROL=erasedups.  But I
      # realized I don't like that behavior because it changes the numbers!  I
      # can't just remember a number -- I have to type 'hi' again.
      line = self.hist_ev.Eval(line)

    # Add the line if it's not EOL, the same as the previous line, and we have
    # line_input.
    if (line is not None and line != self.prev_line and
        self.line_input is not None):
      self.line_input.add_history(line.rstrip())  # no trailing newlines
      self.prev_line = line

    self.prompt_str = _PS2  # TODO: Do we need $PS2?  Would be easy.
    return line

  def Reset(self):
    """Call this after command execution, to free memory taken up by the lines,
    and reset prompt string back to PS1.
    """
    self.prompt_str = self.prompt_ev.FirstPromptEvaluator()


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


class HistoryEvaluator(object):
  """Expand ! commands within the command line.

  This necessarily happens BEFORE lexing.

  NOTE: This should also be used in completion, and it COULD be used in history
  -p, if we want to support that.
  """

  def __init__(self, readline_mod, parse_ctx, debug_f):
    self.readline_mod = readline_mod
    self.parse_ctx = parse_ctx
    self.debug_f = debug_f

  def Eval(self, line):
    """Returns an expanded line."""

    if not self.readline_mod:
      return line

    tokens = list(HISTORY_LEXER.Tokens(line))
    # Common case: no history expansion.
    if all(id_ == Id.History_Other for (id_, _) in tokens):
      return line

    history_len = self.readline_mod.get_current_history_length()
    if history_len <= 0:  # no commands to expand
      return line

    self.debug_f.log('history length = %d', history_len)

    parts = []
    for id_, val in tokens:
      if id_ == Id.History_Other:
        out = val

      elif id_ == Id.History_Op:
        prev = self.readline_mod.get_history_item(history_len)

        ch = val[1]
        if ch == '!':
          out = prev
        else:
          self.parse_ctx.trail.Clear()  # not strictyl necessary?
          line_reader = StringLineReader(prev, self.parse_ctx.arena)
          c_parser = self.parse_ctx.MakeOshParser(line_reader)
          try:
            c_parser.ParseLogicalLine()
          except util.ParseError as e:
            #from core import ui
            #ui.PrettyPrintError(e, self.parse_ctx.arena)

            # Invalid command in history.  TODO: We should never enter these.
            self.debug_f.log(
                "Couldn't parse historical command %r: %s", prev, e)

          # NOTE: We're using the trail rather than the return value of
          # ParseLogicalLine because it handles cases like 
          # $ for i in 1 2 3; do sleep ${i}; done
          # $ echo !$
          # which should expand to 'echo ${i}'

          words = self.parse_ctx.trail.words
          #self.debug_f.log('TRAIL WORDS: %s', words)

          if ch == '^':
            try:
              w = words[1]
            except IndexError:
              raise util.HistoryError("No first word in %r", prev)
            spid1 = word.LeftMostSpanForWord(w)
            spid2 = word.RightMostSpanForWord(w)

          elif ch == '$':
            try:
              w = words[-1]
            except IndexError:
              raise util.HistoryError("No last word in %r", prev)

            spid1 = word.LeftMostSpanForWord(w)
            spid2 = word.RightMostSpanForWord(w)

          elif ch == '*':
            try:
              w1 = words[1]
              w2 = words[-1]
            except IndexError:
              raise util.HistoryError("Couldn't find words in %r", prev)

            spid1 = word.LeftMostSpanForWord(w1)
            spid2 = word.RightMostSpanForWord(w2)

          else:
            raise AssertionError(ch)

          arena = self.parse_ctx.arena
          span1 = arena.GetLineSpan(spid1)
          span2 = arena.GetLineSpan(spid2)

          begin = span1.col
          end = span2.col + span2.length

          out = prev[begin:end]

      elif id_ == Id.History_Num:
        index = int(val[1:])  # regex ensures this.  Maybe have - on the front.
        if index < 0:
          num = history_len + 1 + index
        else:
          num = index

        out = self.readline_mod.get_history_item(num)
        if out is None:  # out of range
          raise util.HistoryError('%s: not found', val)

      elif id_ == Id.History_Search:
        # Search backward
        prefix = None
        substring = None
        if val[1] == '?':
          substring = val[2:]
        else:
          prefix = val[1:]

        out = None
        for i in xrange(history_len, 1, -1):
          cmd = self.readline_mod.get_history_item(i)
          if prefix and cmd.startswith(prefix):
            out = cmd
          if substring and substring in cmd:
            out = cmd
          if out is not None:
            break

        if out is None:
          raise util.HistoryError('%r found no results', val)

      else:
        raise AssertionError(id_)

      parts.append(out)

    line = ''.join(parts)
    # show what we expanded to
    sys.stdout.write('! %s' % line)
    return line
