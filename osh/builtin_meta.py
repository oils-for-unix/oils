#!/usr/bin/env python2
"""
builtin_meta.py - Builtins that call back into the interpreter.
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import source
from core import main_loop
from frontend import args
from frontend import arg_def
from frontend import reader
from osh.builtin_misc import _Builtin
from mycpp import mylib

from typing import List, Dict, Tuple, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from frontend.parse_lib import ParseContext
  from core.alloc import Arena
  from core import optview
  from osh.cmd_exec import Executor


if mylib.PYTHON:
  EVAL_SPEC = arg_def.Register('eval')


def _EvalHelper(arena, ex, c_parser, src):
  # type: (Arena, Executor, CommandParser, source_t) -> int
  arena.PushSource(src)
  try:
    return main_loop.Batch(ex, c_parser, arena)
  finally:
    arena.PopSource()


class Eval(object):
  def __init__(self, parse_ctx, exec_opts, ex):
    # type: (ParseContext, optview.Exec, cmd_exec.Executor) -> None
    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena
    self.exec_opts = exec_opts
    self.ex = ex
    #self.errfmt = errfmt

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
