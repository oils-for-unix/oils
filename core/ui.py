#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
"""
ui.py - User interface constructs.
"""

import sys

from core import word


def Clear():
  sys.stdout.write('\033[2J')  # clear screen
  sys.stdout.write('\033[2;0H')  # Move to 2,0  (below status bar)
  sys.stdout.flush()


class StatusLine(object):

  def __init__(self, row_num=3, width=200):
    # NOTE: '%-80s' % msg doesn't do this, because it doesn't pad at the end
    self.width = width
    self.row_num = row_num

  def _FormatMessage(self, msg):
    max_width = self.width - 4  # two spaces on each side
    # Truncate if necessary.  TODO: could display truncation char?
    msg = msg[:max_width]

    num_end_spaces = max_width - len(msg) + 2  # at least 2 spaces at the end

    to_print = '  %s%s' % (msg, ' ' * num_end_spaces)
    return to_print

  def Write(self, msg, *args):
    if args:
      msg = msg % args

    sys.stdout.write('\033[s')  # save
    # TODO: When there is more than one option for completion, we scroll past
    # this.
    # TODO: Should status line be BELOW, and disappear after readline?
    # Or really it should be at the right margin?  At hit Ctrl-C to cancel?

    sys.stdout.write('\033[%d;0H' % self.row_num)  # Move the cursor

    sys.stdout.write('\033[7m')  # reverse video

    # Make sure you draw the same number of spaces
    # TODO: detect terminal width

    sys.stdout.write(self._FormatMessage(msg))

    sys.stdout.write('\033[0m')  # remove attributes

    sys.stdout.write('\033[u')  # restore
    sys.stdout.flush()


class NullStatusLine(object):

  def __init__(self):
    pass

  def Write(self, msg, *args):
    """NOTE: We could use logging?"""
    pass


class TestStatusLine(object):

  def __init__(self):
    pass

  def Write(self, msg, *args):
    """NOTE: We could use logging?"""
    if args:
      msg = msg % args
    print('\t' + msg)


def MakeStatusLines():
  return [StatusLine(row_num=i) for i in range(3, 10)]


def PrettyPrintError(parse_error, arena, f):
    #print(parse_error)
    if parse_error.token:
      span_id = parse_error.token.span_id
    elif parse_error.word:
      # Can be -1
      span_id = word.LeftMostSpanForWord(parse_error.word)
    else:
      span_id = -1

    if span_id == -1:
      line = '<no position info for token>'
      path = '<unknown>'
      line_num = -1
      col = -1
      length = -1
    else:
      line_span = arena.GetLineSpan(span_id)
      line_id = line_span.line_id
      line = arena.GetLine(line_id)
      path, line_num = arena.GetDebugInfo(line_id)
      col = line_span.col
      length = line_span.length

    print('Line %d of %r' % (line_num+1, path), file=f)
    print('  ' + line.rstrip(), file=f)
    if col != -1:
      f.write('  ')
      # preserve tabs
      for c in line[:col]:
        f.write('\t' if c == '\t' else ' ')
      f.write('^')
      f.write('~' * (length-1))
      f.write('\n')

  #print(error_stack, file=f)


def PrintErrorStack(error_stack, arena, f):
  """
  NOTE:
  - Parse errors always occur within a single arena.  Actually NO, you want to
    show the 'source' stack trace like Python shows the import stack trace.

  - Runtime errors may span arenas (e.g. the function stack).
  """
  # - parse errors happen at runtime because of 'source'
  #   - should there be a distinction then?
  for err in error_stack:
    PrettyPrintError(err, arena, f)
    print(err.UserErrorString(), file=f)
    print('---', file=f)
