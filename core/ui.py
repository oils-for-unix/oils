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

from _devbuild.gen.syntax_asdl import (
    command_t, command,
    source__Interactive, source__CFlag, source__Stdin, source__File,
    source__Alias, source__Backticks, source__LValue

)
from _devbuild.gen.runtime_asdl import value_t, value
from asdl import const
from asdl import format as fmt
from osh import word

from typing import List, Any, IO, TYPE_CHECKING
if TYPE_CHECKING:
  from core.alloc import Arena
  from core.util import ParseError


def PrettyDir(dir_name, home_dir):
  # type: (str, value_t) -> str
  """Maybe replace the home dir with ~.

  Used by the 'dirs' builtin and the prompt evaluator.
  """
  if (home_dir and
      isinstance(home_dir, value.Str) and
      (dir_name == home_dir.s or dir_name.startswith(home_dir.s + '/'))):
    return '~' + dir_name[len(home_dir.s):]

  return dir_name


def _PrintWithLocation(prefix, msg, span_id, arena, f=sys.stderr):
  # type: (int, Arena, IO[str]) -> None
  line_span = arena.GetLineSpan(span_id)
  col = line_span.col
  line_id = line_span.line_id
  line = arena.GetLine(line_id)

  print('  ' + line.rstrip(), file=f)
  f.write('  ')
  # preserve tabs
  for c in line[:col]:
    f.write('\t' if c == '\t' else ' ')
  f.write('^')
  f.write('~' * (line_span.length-1))
  f.write('\n')

  # TODO: Use color instead of [ ]
  src = arena.GetLineSource(line_id)
  if isinstance(src, source__Interactive):
    source_str = '[ interactive ]'  # This might need some changes
  elif isinstance(src, source__CFlag):
    source_str = '[ -c flag ]'

  elif isinstance(src, source__Stdin):
    source_str = '[ stdin%s ]' % src.comment
  elif isinstance(src, source__File):
    source_str = src.path

  # TODO: These three cases have to recurse into the source of the extent!
  elif isinstance(src, source__Alias):
    source_str = '[ expansion of alias %r ]' % src.argv0
  elif isinstance(src, source__Backticks):
    source_str = '[ backticks at ... ]'
  elif isinstance(src, source__LValue):
    source_str = '[ array index LValue at ... ]'

  else:
    source_str = repr(src)

  # TODO: If the line is blank, it would be nice to print the last non-blank
  # line too?
  line_num = arena.GetLineNumber(line_id)
  print('%s:%d: %s%s' % (source_str, line_num, prefix, msg), file=f)


def PrettyPrintError(err, arena, prefix='', f=sys.stderr):
  # type: (ParseError, Arena, str, IO[str]) -> None
  """
  Args:
    prefix: in osh/cmd_exec.py we want to print 'fatal'
  """
  msg = err.UserErrorString()
  span_id = word.SpanIdFromError(err)

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
    print('%s%s' % (prefix, msg), file=f)
  else:
    _PrintWithLocation(prefix, msg, span_id, arena, f=f)


def PrintWarning(msg, span_id, arena, f=sys.stderr):
  prefix = 'warning: '
  if span_id == const.NO_INTEGER:  # When does this happen?
    print('*** Warning has no source location info ***', file=f)
    print('%s%s' % (prefix, msg), file=f)
  else:
    _PrintWithLocation(prefix, msg, span_id, arena)


def PrintAst(nodes, opts):
  # type: (List[command_t], Any) -> None
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
  # type: (str, *Any) -> None
  """For user-facing usage errors."""
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)
