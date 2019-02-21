#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
ui.py - User interface constructs.
"""
from __future__ import print_function

import sys

from asdl import const
from asdl import format as fmt
from core import dev
from core.meta import syntax_asdl

command = syntax_asdl.command


def Clear():
  sys.stdout.write('\033[2J')  # clear screen
  sys.stdout.write('\033[2;0H')  # Move to 2,0  (below status bar)
  sys.stdout.flush()


class StatusLine(object):
  """For optionally displaying the progress of slow completions."""

  def __init__(self, row_num=3, width=80):
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
    # TODO: Get rid of StatusLine in favor of the new ui.Display() class.
    return

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


class TestStatusLine(object):
  def __init__(self):
    pass

  def Write(self, msg, *args):
    """NOTE: We could use logging?"""
    if args:
      msg = msg % args
    print('\t' + msg)


def PrintFilenameAndLine(span_id, arena, f=sys.stderr):
  line_span = arena.GetLineSpan(span_id)
  line_id = line_span.line_id
  line = arena.GetLine(line_id)
  path, line_num = arena.GetDebugInfo(line_id)
  col = line_span.col
  length = line_span.length

  # TODO: If the line is blank, it would be nice to print the last non-blank
  # line too?
  print('Line %d of %r' % (line_num, path), file=f)
  print('  ' + line.rstrip(), file=f)
  f.write('  ')
  # preserve tabs
  for c in line[:col]:
    f.write('\t' if c == '\t' else ' ')
  f.write('^')
  f.write('~' * (length-1))
  f.write('\n')


def PrettyPrintError(err, arena, prefix='', f=sys.stderr):
  span_id = dev.SpanIdFromError(err)

  # TODO: Should there be a special span_id of 0 for EOF?  const.NO_INTEGER
  # means there is no location info, but 0 could mean that the location is EOF.
  # So then you query the arena for the last line in that case?
  # Eof_Real is the ONLY token with 0 span, because it's invisible!
  # Well Eol_Tok is a sentinel with a span_id of const.NO_INTEGER.  I think
  # that is OK.
  # Problem: the column for Eof could be useful.

  if span_id == const.NO_INTEGER:  # Any clause above might return this.
    # This is usually a bug.
    print('*** Error has no source location info ***', file=f)
  else:
    PrintFilenameAndLine(span_id, arena, f=f)

  f.write(prefix)
  print(err.UserErrorString(), file=f)


def PrintAst(nodes, opts):
  if len(nodes) == 1:
    node = nodes[0]
  else:
    node = command.CommandList(nodes)

  if opts.ast_format == 'none':
    print('AST not printed.', file=sys.stderr)

  else:  # text output
    f = sys.stdout

    if opts.ast_format in ('text', 'abbrev-text'):
      ast_f = fmt.DetectConsoleOutput(f)
    elif opts.ast_format in ('html', 'abbrev-html'):
      ast_f = fmt.HtmlOutput(f)
    else:
      raise AssertionError

    if 'abbrev-' in opts.ast_format:
      tree = node.AbbreviatedTree()
    else:
      tree = node.PrettyTree()

    ast_f.FileHeader()
    fmt.PrintTree(tree, ast_f)
    ast_f.FileFooter()
    ast_f.write('\n')


def usage(msg, *args):
  """For user-facing usage errors."""
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)
