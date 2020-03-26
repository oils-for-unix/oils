#!/usr/bin/env python2
"""
builtin_meta.py - Builtins that call back into the interpreter.
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import source
from core.error import _ControlFlow
from core import main_loop
from core import pyutil  # strerror_OS
from frontend import args
from frontend import arg_def
from frontend import reader
from osh.builtin_misc import _Builtin
from mycpp import mylib

from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from _devbuild.gen.syntax_asdl import source_t
  from frontend.parse_lib import ParseContext
  from core.alloc import Arena
  from core import optview
  from core import state
  from core import ui
  from osh.cmd_exec import Executor
  from osh.cmd_parse import CommandParser


if mylib.PYTHON:
  EVAL_SPEC = arg_def.Register('eval')


def _EvalHelper(arena, ex, c_parser, src):
  # type: (Arena, Executor, CommandParser, source_t) -> int
  arena.PushSource(src)
  try:
    return main_loop.Batch(ex, c_parser, arena)
  finally:
    arena.PopSource()


class Eval(_Builtin):
  def __init__(self, parse_ctx, exec_opts, ex):
    # type: (ParseContext, optview.Exec, Executor) -> None
    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena
    self.exec_opts = exec_opts
    self.ex = ex

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    # There are no flags, but we need it to respect --
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'eval'
    arg = EVAL_SPEC.Parse(arg_r)

    if self.exec_opts.strict_eval_builtin():
      code_str, eval_spid = arg_r.ReadRequired2('requires code string')
      if not arg_r.AtEnd():
        raise args.UsageError('requires exactly 1 argument')
    else:
      code_str = ' '.join(cmd_val.argv[arg_r.i:])
      # code_str could be EMPTY, so just use the first one
      eval_spid = cmd_val.arg_spids[0]

    line_reader = reader.StringLineReader(code_str, self.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader)

    src = source.EvalArg(eval_spid)
    return _EvalHelper(self.arena, self.ex, c_parser, src)


class Source(_Builtin):
  def __init__(self, parse_ctx, search_path, ex, errfmt):
    # type: (ParseContext, state.SearchPath, Executor, ui.ErrorFormatter) -> None
    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena

    self.search_path = search_path

    self.ex = ex
    self.fd_state = ex.fd_state
    self.mem = ex.mem

    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    argv = cmd_val.argv
    call_spid = cmd_val.arg_spids[0]

    try:
      path = argv[1]
    except IndexError:
      raise args.UsageError('missing required argument')

    resolved = self.search_path.Lookup(path, exec_required=False)
    if resolved is None:
      resolved = path
    try:
      f = self.fd_state.Open(resolved)  # Shell can't use descriptors 3-9
    except OSError as e:
      self.errfmt.Print('source %r failed: %s', path, pyutil.strerror_OS(e),
                        span_id=cmd_val.arg_spids[1])
      return 1

    try:
      line_reader = reader.FileLineReader(f, self.arena)
      c_parser = self.parse_ctx.MakeOshParser(line_reader)

      # A sourced module CAN have a new arguments array, but it always shares
      # the same variable scope as the caller.  The caller could be at either a
      # global or a local scope.
      source_argv = argv[2:]
      src = source.SourcedFile(path, call_spid)
      self.mem.PushSource(path, source_argv)
      try:
        status = _EvalHelper(self.arena, self.ex, c_parser, src)
      finally:
        self.mem.PopSource(source_argv)

      return status

    except _ControlFlow as e:
      if e.IsReturn():
        return e.StatusCode()
      else:
        raise
    finally:
      f.close()
