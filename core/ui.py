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
    source__Interactive, source__CFlag, source__Stdin, source__MainFile,
    source__SourcedFile, source__EvalArg, source__Trap,
    source__Alias, source__Backticks, source__LValue

)
from _devbuild.gen.runtime_asdl import value_t, value, value__Str
from asdl import runtime
from asdl import format as fmt
from osh import word_
from mycpp import mylib

from typing import List, Any, IO, TYPE_CHECKING
if TYPE_CHECKING:
  from core.alloc import Arena
  from core.util import _ErrorWithLocation
  #from frontend.args import UsageError


def PrettyDir(dir_name, home_dir):
  # type: (str, value_t) -> str
  """Maybe replace the home dir with ~.

  Used by the 'dirs' builtin and the prompt evaluator.
  """
  if (home_dir and
      isinstance(home_dir, value__Str) and
      (dir_name == home_dir.s or dir_name.startswith(home_dir.s + '/'))):
    return '~' + dir_name[len(home_dir.s):]

  return dir_name


def _PrintCodeExcerpt(line, col, length, f):
  # type: (str, int, int, IO[str]) -> None
  print('  ' + line.rstrip(), file=f)
  f.write('  ')
  # preserve tabs
  for c in line[:col]:
    f.write('\t' if c == '\t' else ' ')
  f.write('^')
  f.write('~' * (length-1))
  f.write('\n')


def _PrintWithSpanId(prefix, msg, span_id, arena, f=sys.stderr):
  # type: (str, str, int, Arena, IO[str]) -> None
  line_span = arena.GetLineSpan(span_id)
  orig_col = line_span.col
  line_id = line_span.line_id

  src = arena.GetLineSource(line_id)
  line = arena.GetLine(line_id)
  line_num = arena.GetLineNumber(line_id)  # overwritten by source__LValue case

  if not isinstance(src, source__LValue):  # This is printed specially
    _PrintCodeExcerpt(line, line_span.col, line_span.length, f)

  # TODO: Use color instead of [ ]
  if isinstance(src, source__Interactive):
    source_str = '[ interactive ]'  # This might need some changes
  elif isinstance(src, source__CFlag):
    source_str = '[ -c flag ]'

  elif isinstance(src, source__Stdin):
    source_str = '[ stdin%s ]' % src.comment
  elif isinstance(src, source__MainFile):
    source_str = src.path

  elif isinstance(src, source__SourcedFile):
    # TODO: could chain of 'source' with the spid
    source_str = src.path

  elif isinstance(src, source__Alias):
    source_str = '[ expansion of alias %r ]' % src.argv0
  elif isinstance(src, source__Backticks):
    source_str = '[ backticks at ... ]'
  elif isinstance(src, source__LValue):
    span2 = arena.GetLineSpan(src.left_spid)
    line2 = arena.GetLine(span2.line_id)
    outer_source = arena.GetLineSourceString(span2.line_id)
    source_str = '[ array LValue in %s ]' % outer_source
    # NOTE: The inner line number is always 1 because of reparsing.  We
    # overwrite it with the original span.
    line_num = arena.GetLineNumber(span2.line_id)

    # We want the excerpt to look like this:
    #   a[x+]=1
    #       ^
    # Rather than quoting the internal buffer:
    #   x+
    #     ^
    lbracket_col = span2.col + span2.length
    _PrintCodeExcerpt(line2, orig_col + lbracket_col, 1, f)

  elif isinstance(src, source__EvalArg):
    span = arena.GetLineSpan(src.eval_spid)
    line_num = arena.GetLineNumber(span.line_id)
    outer_source = arena.GetLineSourceString(span.line_id)
    source_str = '[ eval at line %d of %s ]' % (line_num, outer_source)

  elif isinstance(src, source__Trap):
    # TODO: Look at word_spid
    source_str = '[ trap ]'

  else:
    source_str = repr(src)

  # TODO: If the line is blank, it would be nice to print the last non-blank
  # line too?
  print('%s:%d: %s%s' % (source_str, line_num, prefix, msg), file=f)


def _PrintWithOptionalSpanId(prefix, msg, span_id, arena, f):
  # type: (str, str, int, Arena, IO[str]) -> None
  if span_id == runtime.NO_SPID:  # When does this happen?
    print('[??? no location ???] %s%s' % (prefix, msg), file=f)
  else:
    _PrintWithSpanId(prefix, msg, span_id, arena)


def PrettyPrintError(err, arena, prefix='', f=sys.stderr):
  # type: (_ErrorWithLocation, Arena, str, IO[str]) -> None
  """
  Args:
    prefix: in osh/cmd_exec.py we want to print 'fatal'
  """
  msg = err.UserErrorString()
  span_id = word_.SpanIdFromError(err)

  # TODO: Should there be a special span_id of 0 for EOF?  runtime.NO_SPID
  # means there is no location info, but 0 could mean that the location is EOF.
  # So then you query the arena for the last line in that case?
  # Eof_Real is the ONLY token with 0 span, because it's invisible!
  # Well Eol_Tok is a sentinel with a span_id of runtime.NO_SPID.  I think
  # that is OK.
  # Problem: the column for Eof could be useful.

  _PrintWithOptionalSpanId(prefix, msg, span_id, arena, f)


# TODO:
# - ColorErrorFormatter
# - BareErrorFormatter?  Could just display the foo.sh:37:8: and not quotation.
#
# Are these controlled by a flag?  It's sort of like --comp-ui.  Maybe
# --error-ui.

class ErrorFormatter(object):

  def __init__(self, arena):
    # type: (Arena) -> None
    self.arena = arena
    self.last_spid = runtime.NO_SPID  # last resort for location info
    self.spid_stack = []  # type: List[int]

  # A stack used for the current builtin.  A fallback for UsageError.
  # TODO: Should we have PushBuiltinName?  Then we can have a consistent style
  # like foo.sh:1: (compopt) Not currently executing.

  def PushLocation(self, spid):
    # type: (int) -> None
    #log('%sPushLocation(%d)', '  ' * len(self.spid_stack), spid)
    self.spid_stack.append(spid)

  def PopLocation(self):
    # type: () -> None
    self.spid_stack.pop()
    #log('%sPopLocation -> %d', '  ' * len(self.spid_stack), self.last_spid)

  def CurrentLocation(self):
    # type: () -> int
    if self.spid_stack:
      return self.spid_stack[-1]
    else:
      return runtime.NO_SPID

  def Print(self, msg, *args, **kwargs):
    # type: (str, *Any, **Any) -> None
    """Print a message with a code quotation based on the given span_id."""
    span_id = kwargs.pop('span_id', self.CurrentLocation())
    prefix = kwargs.pop('prefix', '')
    if args:
      msg = msg % args
    _PrintWithOptionalSpanId(prefix, msg, span_id, self.arena, sys.stderr)

  def PrettyPrintError(self, err, prefix=''):
    # type: (_ErrorWithLocation, str) -> None
    """Print an exception that was caught."""
    PrettyPrintError(err, self.arena, prefix=prefix)


def Stderr(msg, *args):
  # type: (str, *Any) -> None
  """Print a message to stderr for the user.

  This should be used sparingly, since it doesn't have any location info.
  Right now we use it to print fatal I/O errors that were only caught at the
  top level.
  """
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def PrintAst(nodes, opts):
  # type: (List[command_t], Any) -> None
  if len(nodes) == 1:
    node = nodes[0]
  else:
    node = command.CommandList(nodes)

  if opts.ast_format == 'none':
    print('AST not printed.', file=sys.stderr)

  else:  # text output
    f = mylib.Stdout()

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
