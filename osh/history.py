"""
history.py: A LIBRARY for history evaluation.

UI details should go in core/ui.py.
"""
from __future__ import print_function

import sys

from _devbuild.gen.id_kind_asdl import Id
from core import error
from core import util
#from core.util import log
from frontend import match
from frontend import reader
from osh import word_

from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
  from frontend.parse_lib import ParseContext
  from core.util import DebugFile


class Evaluator(object):
  """Expand ! commands within the command line.

  This necessarily happens BEFORE lexing.

  NOTE: This should also be used in completion, and it COULD be used in history
  -p, if we want to support that.
  """

  def __init__(self, readline_mod, parse_ctx, debug_f):
    # type: (Any, ParseContext, DebugFile) -> None
    self.readline_mod = readline_mod
    self.parse_ctx = parse_ctx
    self.debug_f = debug_f

  def Eval(self, line):
    # type: (str) -> str
    """Returns an expanded line."""

    if not self.readline_mod:
      return line

    tokens = match.HistoryTokens(line)
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
          self.parse_ctx.trail.Clear()  # not strictly necessary?
          line_reader = reader.StringLineReader(prev, self.parse_ctx.arena)
          c_parser = self.parse_ctx.MakeOshParser(line_reader)
          try:
            c_parser.ParseLogicalLine()
          except error.Parse as e:
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
            spid1 = word_.LeftMostSpanForWord(w)
            spid2 = word_.RightMostSpanForWord(w)

          elif ch == '$':
            try:
              w = words[-1]
            except IndexError:
              raise util.HistoryError("No last word in %r", prev)

            spid1 = word_.LeftMostSpanForWord(w)
            spid2 = word_.RightMostSpanForWord(w)

          elif ch == '*':
            try:
              w1 = words[1]
              w2 = words[-1]
            except IndexError:
              raise util.HistoryError("Couldn't find words in %r", prev)

            spid1 = word_.LeftMostSpanForWord(w1)
            spid2 = word_.RightMostSpanForWord(w2)

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
        # Remove the required space at the end and save it.  A simple hack than
        # the one bash has.
        last_char = val[-1]
        val = val[:-1]

        # Search backward
        prefix = None
        substring = ''
        if val[1] == '?':
          substring = val[2:]
        else:
          prefix = val[1:]

        out = None
        for i in xrange(history_len, 1, -1):
          cmd = self.readline_mod.get_history_item(i)
          if prefix and cmd.startswith(prefix):
            out = cmd
          if len(substring) and substring in cmd:
            out = cmd
          if out is not None:
            out += last_char  # restore required space
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
