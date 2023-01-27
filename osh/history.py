"""
history.py: A LIBRARY for history evaluation.

UI details should go in core/ui.py.
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from core import error
from core import util
#from core.pyerror import log
from frontend import match
from frontend import reader
from osh import word_

from typing import List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
  from frontend.parse_lib import ParseContext
  from frontend.py_readline import Readline
  from core.util import _DebugFile


class Evaluator(object):
  """Expand ! commands within the command line.

  This necessarily happens BEFORE lexing.

  NOTE: This should also be used in completion, and it COULD be used in history
  -p, if we want to support that.
  """

  def __init__(self, readline, parse_ctx, debug_f):
    # type: (Optional[Readline], ParseContext, _DebugFile) -> None
    self.readline = readline
    self.parse_ctx = parse_ctx
    self.debug_f = debug_f

  def Eval(self, line):
    # type: (str) -> str
    """Returns an expanded line."""

    if not self.readline:
      return line

    tokens = match.HistoryTokens(line)
    #self.debug_f.log('tokens %r', tokens)

    # Common case: no history expansion.
    # mycpp: rewrite of all()
    ok = True
    for (id_, _) in tokens:
      if id_ != Id.History_Other:
        ok = False
        break

    if ok:
      return line

    history_len = self.readline.get_current_history_length()
    if history_len <= 0:  # no commands to expand
      return line

    self.debug_f.log('history length = %d', history_len)

    parts = []  # type: List[str]
    for id_, val in tokens:
      if id_ == Id.History_Other:
        out = val

      elif id_ == Id.History_Op:
        # all operations get a part of the previous line
        prev = self.readline.get_history_item(history_len)

        ch = val[1]
        if ch == '!':  # !!
          out = prev
        else:
          self.parse_ctx.trail.Clear()  # not strictly necessary?
          line_reader = reader.StringLineReader(prev, self.parse_ctx.arena)
          c_parser = self.parse_ctx.MakeOshParser(line_reader)
          try:
            c_parser.ParseLogicalLine()
          except error.Parse as e:
            # Invalid command in history.  bash uses a separate, approximate
            # history lexer which allows invalid commands, and will retrieve
            # parts of them.  I guess we should too!
            self.debug_f.log(
                "Couldn't parse historical command %r: %s", prev, e)

          # NOTE: We're using the trail rather than the return value of
          # ParseLogicalLine() because it handles cases like 
          #
          # $ for i in 1 2 3; do sleep ${i}; done
          # $ echo !$
          # which should expand to 'echo ${i}'
          #
          # Although the approximate bash parser returns 'done'.
          # TODO: The trail isn't particularly well-defined, so maybe this
          # isn't a great idea.

          words = self.parse_ctx.trail.words
          self.debug_f.log('TRAIL words: %s', words)

          if ch == '^':
            try:
              w = words[1]
            except IndexError:
              raise util.HistoryError("No first word in %r" % prev)
            spid1 = word_.LeftMostSpanForWord(w)
            spid2 = word_.RightMostSpanForWord(w)

          elif ch == '$':
            try:
              w = words[-1]
            except IndexError:
              raise util.HistoryError("No last word in %r" % prev)

            spid1 = word_.LeftMostSpanForWord(w)
            spid2 = word_.RightMostSpanForWord(w)

          elif ch == '*':
            try:
              w1 = words[1]
              w2 = words[-1]
            except IndexError:
              raise util.HistoryError("Couldn't find words in %r" % prev)

            spid1 = word_.LeftMostSpanForWord(w1)
            spid2 = word_.RightMostSpanForWord(w2)

          else:
            raise AssertionError(ch)

          arena = self.parse_ctx.arena
          span1 = arena.GetToken(spid1)
          span2 = arena.GetToken(spid2)

          begin = span1.col
          end = span2.col + span2.length

          out = prev[begin:end]

      elif id_ == Id.History_Num:
        index = int(val[1:])  # regex ensures this.  Maybe have - on the front.
        if index < 0:
          num = history_len + 1 + index
        else:
          num = index

        out = self.readline.get_history_item(num)
        if out is None:  # out of range
          raise util.HistoryError('%s: not found' % val)

      elif id_ == Id.History_Search:
        # Remove the required space at the end and save it.  A simple hack than
        # the one bash has.
        last_char = val[-1]
        val = val[:-1]

        # Search backward
        prefix = None  # type: Optional[str]
        substring = ''
        if val[1] == '?':
          substring = val[2:]
        else:
          prefix = val[1:]

        out = None
        for i in xrange(history_len, 1, -1):
          cmd = self.readline.get_history_item(i)
          if prefix and cmd.startswith(prefix):
            out = cmd
          if len(substring) and substring in cmd:
            out = cmd
          if out is not None:
            # mycpp: rewrite of +=
            out = out + last_char  # restore required space
            break

        if out is None:
          raise util.HistoryError('%r found no results' % val)

      else:
        raise AssertionError(id_)

      parts.append(out)

    line = ''.join(parts)
    # show what we expanded to
    print('! %s' % line)
    return line
