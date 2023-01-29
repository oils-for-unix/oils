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

from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str
from _devbuild.gen.syntax_asdl import (
    Token, command_t, command_str,
    source_e, source__Stdin, source__MainFile, source__SourcedFile,
    source__Alias, source__Reparsed, source__Variable, source__ArgvWord,
    source__Synthetic
)
from _devbuild.gen.runtime_asdl import value_str, value_t
from asdl import runtime
from asdl import format as fmt
from frontend import location
from mycpp import mylib
from mycpp.mylib import print_stderr, tagswitch, StrFromC
from qsn_ import qsn

from typing import List, Optional, Any, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen import arg_types
  from core.alloc import Arena
  from core import error
  from core.error import _ErrorWithLocation
  from mycpp.mylib import Writer


def ValType(val):
  # type: (value_t) -> str
  """For displaying type errors in the UI."""

  # Displays 'value.MaybeStrArray' for now, maybe change it.
  return StrFromC(value_str(val.tag_()))


def CommandType(cmd):
  # type: (command_t) -> str
  """For displaying commands in the UI."""

  # Displays 'value.MaybeStrArray' for now, maybe change it.
  return StrFromC(command_str(cmd.tag_()))


def PrettyId(id_):
  # type: (Id_t) -> str
  """For displaying type errors in the UI."""

  # Displays 'Id.BoolUnary_v' for now
  return StrFromC(Id_str(id_))


def PrettyToken(tok, arena):
  # type: (Token, Arena) -> str
  """Returns a readable token value for the user.  For syntax errors."""
  if tok.id == Id.Eof_Real:
    return 'EOF'

  span = arena.GetToken(tok.span_id)
  line = arena.GetLine(span.line_id)
  val = line[span.col: span.col + span.length]
  # TODO: Print length 0 as 'EOF'?
  return repr(val)


def PrettyDir(dir_name, home_dir):
  # type: (str, Optional[str]) -> str
  """Maybe replace the home dir with ~.

  Used by the 'dirs' builtin and the prompt evaluator.
  """
  if home_dir is not None:
    if dir_name == home_dir or dir_name.startswith(home_dir + '/'):
      return '~' + dir_name[len(home_dir):]

  return dir_name


def _PrintCodeExcerpt(line, col, length, f):
  # type: (str, int, int, Writer) -> None

  buf = mylib.BufWriter()

  buf.write('  '); buf.write(line.rstrip())
  buf.write('\n  ')
  # preserve tabs
  for c in line[:col]:
    buf.write('\t' if c == '\t' else ' ')
  buf.write('^')
  buf.write('~' * (length-1))
  buf.write('\n')

  # Do this all in a single write() call so it's less likely to be
  # interleaved.  See test/runtime-errors.sh errexit_multiple_processes
  f.write(buf.getvalue())


def GetLineSourceString(arena, line_id, quote_filename=False):
  # type: (Arena, int, bool) -> str
  """Returns a human-readable string for dev tools.

  This function is RECURSIVE because there may be dynamic parsing.
  """
  src = arena.GetLineSource(line_id)
  UP_src = src

  with tagswitch(src) as case:
    if case(source_e.Interactive):
      s = '[ interactive ]'  # This might need some changes
    elif case(source_e.Headless):
      s = '[ headless ]'
    elif case(source_e.CFlag):
      s = '[ -c flag ]'
    elif case(source_e.Stdin):
      src = cast(source__Stdin, UP_src)
      s = '[ stdin%s ]' % src.comment

    elif case(source_e.MainFile):
      src = cast(source__MainFile, UP_src)
      # This will quote a file called '[ -c flag ]' to disambiguate it!
      # also handles characters that are unprintable in a terminal.
      s = src.path
      if quote_filename:
        s = qsn.maybe_encode(s)
    elif case(source_e.SourcedFile):
      src = cast(source__SourcedFile, UP_src)
      # ditto
      s = src.path
      if quote_filename:
        s = qsn.maybe_encode(s)

    elif case(source_e.ArgvWord):
      src = cast(source__ArgvWord, UP_src)
      if src.span_id == runtime.NO_SPID:
        s = '[ %s word at ? ]' % src.what
      else:
        span = arena.GetToken(src.span_id)
        line_num = arena.GetLineNumber(span.line_id)
        outer_source = GetLineSourceString(arena, span.line_id,
                                           quote_filename=quote_filename)
        s = '[ %s word at line %d of %s ]' % (src.what, line_num, outer_source)
      # Note: _PrintCodeExcerpt called above

    elif case(source_e.Variable):
      src = cast(source__Variable, UP_src)

      if src.var_name is None:
        var_name = '?'
      else:
        var_name = repr(src.var_name) 

      if src.span_id == runtime.NO_SPID:
        where = '?'
      else:
        span = arena.GetToken(src.span_id)
        line_num = arena.GetLineNumber(span.line_id)
        outer_source = GetLineSourceString(arena, span.line_id,
                                           quote_filename=quote_filename)
        where = 'line %d of %s' % (line_num, outer_source)

      s = '[ var %s at %s ]' % (var_name, where)

    elif case(source_e.Alias):
      src = cast(source__Alias, UP_src)
      s = '[ expansion of alias %r ]' % src.argv0

    elif case(source_e.Reparsed):
      src = cast(source__Reparsed, UP_src)
      span2 = src.left_token
      outer_source = GetLineSourceString(arena, span2.line_id,
                                         quote_filename=quote_filename)
      s = '[ %s in %s ]' % (src.what, outer_source)

    elif case(source_e.Synthetic):
      src = cast(source__Synthetic, UP_src)
      s = '-- %s' % src.s  # use -- to say it came from a flag

    else:
      raise AssertionError(src)

  return s


def _PrintWithSpanId(prefix, msg, span_id, arena, show_code):
  # type: (str, str, int, Arena, bool) -> None
  """
  Should we have multiple error formats:
  - single line and verbose?
  - and turn on "stack" tracing?  For 'source' and more?
  """
  f = mylib.Stderr()
  if span_id == runtime.NO_SPID:  # When does this happen?
    f.write('[??? no location ???] %s%s\n' % (prefix, msg))
    return

  line_span = arena.GetToken(span_id)
  orig_col = line_span.col
  line_id = line_span.line_id

  src = arena.GetLineSource(line_id)
  line = arena.GetLine(line_id)
  line_num = arena.GetLineNumber(line_id)  # overwritten by source__LValue case

  if show_code:
    UP_src = src
    # LValue/backticks is the only case where we don't print this
    if src.tag_() == source_e.Reparsed:
      src = cast(source__Reparsed, UP_src)
      span2 = src.left_token
      line_num = arena.GetLineNumber(span2.line_id)

      # We want the excerpt to look like this:
      #   a[x+]=1
      #       ^
      # Rather than quoting the internal buffer:
      #   x+
      #     ^
      line2 = arena.GetLine(span2.line_id)
      lbracket_col = span2.col + span2.length
      # NOTE: The inner line number is always 1 because of reparsing.  We
      # overwrite it with the original span.
      _PrintCodeExcerpt(line2, orig_col + lbracket_col, 1, f)

    else:
      _PrintCodeExcerpt(line, line_span.col, line_span.length, f)

  source_str = GetLineSourceString(arena, line_id, quote_filename=True)

  # TODO: If the line is blank, it would be nice to print the last non-blank
  # line too?
  f.write('%s:%d: %s%s\n' % (source_str, line_num, prefix, msg))


class ctx_Location(object):

  def __init__(self, errfmt, spid):
    # type: (ErrorFormatter, int) -> None
    errfmt.spid_stack.append(spid)
    self.errfmt = errfmt

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.errfmt.spid_stack.pop()


# TODO:
# - ColorErrorFormatter
# - BareErrorFormatter?  Could just display the foo.sh:37:8: and not quotation.
#
# Are these controlled by a flag?  It's sort of like --comp-ui.  Maybe
# --error-ui.

class ErrorFormatter(object):
  """Print errors with code excerpts.

  Philosophy:
  - There should be zero or one code quotation when a shell exits non-zero.
    Showing the same line twice is noisy.
  - When running parallel processes, avoid interleaving multi-line code
    quotations.  (TODO: turn off in child processes?)
  """

  def __init__(self, arena):
    # type: (Arena) -> None
    self.arena = arena
    self.last_spid = runtime.NO_SPID  # last resort for location info
    self.spid_stack = []  # type: List[int]

    self.one_line_errexit = False  # root process

  def OneLineErrExit(self):
    # type: () -> None
    """Used by SubprogramThunk."""
    self.one_line_errexit = True

  # A stack used for the current builtin.  A fallback for UsageError.
  # TODO: Should we have PushBuiltinName?  Then we can have a consistent style
  # like foo.sh:1: (compopt) Not currently executing.

  def CurrentLocation(self):
    # type: () -> int
    if len(self.spid_stack):
      return self.spid_stack[-1]
    else:
      return runtime.NO_SPID

  def PrefixPrint(self, msg, prefix, span_id=runtime.NO_SPID):
    # type: (str, str, int) -> None
    """Print a hard-coded message with a prefix, and quote code."""
    _PrintWithSpanId(prefix, msg, span_id, self.arena, show_code=True)

  def Print_(self, msg, span_id=runtime.NO_SPID):
    # type: (str, int) -> None
    """Print a hard-coded message, and quote code."""
    if span_id == runtime.NO_SPID:
      span_id = self.CurrentLocation()
    _PrintWithSpanId('', msg, span_id, self.arena, show_code=True)

  def PrintMessage(self, msg, span_id=runtime.NO_SPID):
    # type: (str, int) -> None
    """Print a message WITHOUT quoting code."""
    if span_id == runtime.NO_SPID:
      span_id = self.CurrentLocation()
    _PrintWithSpanId('', msg, span_id, self.arena, show_code=False)

  def StderrLine(self, msg):
    # type: (str) -> None
    """Just print to stderr."""
    print_stderr(msg)

  def PrettyPrintError(self, err, prefix=''):
    # type: (_ErrorWithLocation, str) -> None
    """Print an exception that was caught, with a code quotation.

    Unlike other methods, this doesn't use the CurrentLocation() fallback.
    That only applies to builtins; instead we check e.HasLocation() at a higher
    level, in CommandEvaluator.
    """
    msg = err.UserErrorString()
    span_id = location.GetSpanId(err.location)

    # TODO: Should there be a special span_id of 0 for EOF?  runtime.NO_SPID
    # means there is no location info, but 0 could mean that the location is EOF.
    # So then you query the arena for the last line in that case?
    # Eof_Real is the ONLY token with 0 span, because it's invisible!
    # Well Eol_Tok is a sentinel with a span_id of runtime.NO_SPID.  I think
    # that is OK.
    # Problem: the column for Eof could be useful.

    _PrintWithSpanId(prefix, msg, span_id, self.arena, True)

  def PrintErrExit(self, err, pid):
    # type: (error.ErrExit, int) -> None

    # TODO:
    # - Don't quote code if you already quoted something on the same line?
    #   - _PrintWithSpanId calculates the line_id.  So you need to remember that?
    #   - return it here?
    prefix = 'errexit PID %d: ' % pid
    #self.PrettyPrintError(err, prefix=prefix)

    msg = err.UserErrorString()
    span_id = location.GetSpanId(err.location)
    _PrintWithSpanId(prefix, msg, span_id, self.arena, err.show_code)


def PrintAst(node, flag):
  # type: (command_t, arg_types.main) -> None

  if flag.ast_format == 'none':
    print_stderr('AST not printed.')
    if 0:
      from _devbuild.gen.id_kind_asdl import Id_str
      from frontend.lexer import ID_HIST
      for id_, count in ID_HIST.most_common(10):
        print('%8d %s' % (count, Id_str(id_)))
      print()
      total = sum(ID_HIST.values())
      print('%8d total tokens returned' % total)

  else:  # text output
    f = mylib.Stdout()

    afmt = flag.ast_format  # note: mycpp rewrite to avoid 'in'
    if afmt in ('text', 'abbrev-text'):
      ast_f = fmt.DetectConsoleOutput(f)
    elif afmt in ('html', 'abbrev-html'):
      ast_f = fmt.HtmlOutput(f)
    else:
      raise AssertionError()

    if 'abbrev-' in afmt:
      # ASDL "abbreviations" are only supported by asdl/gen_python.py
      if mylib.PYTHON:
        tree = node.AbbreviatedTree()
      else:
        tree = node.PrettyTree()
    else:
      tree = node.PrettyTree()

    ast_f.FileHeader()
    fmt.PrintTree(tree, ast_f)
    ast_f.FileFooter()
    ast_f.write('\n')
