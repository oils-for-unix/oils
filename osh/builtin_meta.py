#!/usr/bin/env python2
"""
builtin_meta.py - Builtins that call back into the interpreter.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import source
from core import error
from core.error import _ControlFlow
from core import main_loop
from core import pyutil  # strerror_OS
from core.vm import _Builtin
from frontend import args
from frontend import arg_def
from frontend import consts
from frontend import lexer_def
from frontend import reader

from typing import Dict, List, Tuple, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from _devbuild.gen.syntax_asdl import command__ShFunction
  from frontend.parse_lib import ParseContext
  from core import optview
  from core import process
  from core import state
  from core import ui
  from core.executor import ShellExecutor
  from osh.cmd_eval import CommandEvaluator


class Eval(_Builtin):

  def __init__(self, parse_ctx, exec_opts, cmd_ev):
    # type: (ParseContext, optview.Exec, CommandEvaluator) -> None
    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena
    self.exec_opts = exec_opts
    self.cmd_ev = cmd_ev

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    # There are no flags, but we need it to respect --
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'eval'
    _ = arg_def.Parse('eval', arg_r)

    if self.exec_opts.strict_eval_builtin():
      code_str, eval_spid = arg_r.ReadRequired2('requires code string')
      if not arg_r.AtEnd():
        raise error.Usage('requires exactly 1 argument')
    else:
      code_str = ' '.join(cmd_val.argv[arg_r.i:])
      # code_str could be EMPTY, so just use the first one
      eval_spid = cmd_val.arg_spids[0]

    line_reader = reader.StringLineReader(code_str, self.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader)

    src = source.EvalArg(eval_spid)
    self.arena.PushSource(src)
    try:
      return main_loop.Batch(self.cmd_ev, c_parser, self.arena)
    finally:
      self.arena.PopSource()


class Source(_Builtin):

  def __init__(self, parse_ctx, search_path, cmd_ev, fd_state, errfmt):
    # type: (ParseContext, state.SearchPath, CommandEvaluator, process.FdState, ui.ErrorFormatter) -> None
    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena

    self.search_path = search_path

    self.cmd_ev = cmd_ev
    self.fd_state = fd_state
    self.mem = cmd_ev.mem

    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    argv = cmd_val.argv
    call_spid = cmd_val.arg_spids[0]

    try:
      path = argv[1]
    except IndexError:
      raise error.Usage('missing required argument')

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
      self.mem.PushSource(path, source_argv)

      src = source.SourcedFile(path, call_spid)
      self.arena.PushSource(src)
      try:
        status = main_loop.Batch(self.cmd_ev, c_parser, self.arena)
      finally:
        self.arena.PopSource()
        self.mem.PopSource(source_argv)

      return status

    except _ControlFlow as e:
      if e.IsReturn():
        return e.StatusCode()
      else:
        raise
    finally:
      f.close()



class Command(_Builtin):
  """
  'command ls' suppresses function lookup.
  """

  def __init__(self, shell_ex, funcs, aliases, search_path):
    # type: (ShellExecutor, Dict[str, command__ShFunction], Dict[str, str], state.SearchPath) -> None
    self.shell_ex = shell_ex
    self.funcs = funcs
    self.aliases = aliases
    self.search_path = search_path

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_index = arg_def.ParseCmdVal('command', cmd_val)
    arg = arg_types.command(attrs.attrs)
    if arg.v:
      status = 0
      names = cmd_val.argv[arg_index:]
      for kind, argument in ResolveNames(names, self.funcs, self.aliases,
                                         self.search_path):
        if kind is None:
          status = 1  # nothing printed, but we fail
        else:
          # This is for -v, -V is more detailed.
          print(argument)
      return status

    # shift by one
    cmd_val = cmd_value.Argv(cmd_val.argv[1:], cmd_val.arg_spids[1:])

    # If we respected do_fork here instead of passing True, the case
    # 'command date | wc -l' would take 2 processes instead of 3.  But no other
    # shell does that, and this rare case isn't worth the bookkeeping.
    # See test/syscall
    return self.shell_ex.RunSimpleCommand(cmd_val, True, call_procs=False)


class Builtin(_Builtin):

  def __init__(self, shell_ex, errfmt):
    # type: (ShellExecutor, ui.ErrorFormatter) -> None
    self.shell_ex = shell_ex
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    if len(cmd_val.argv) == 1:
      return 0  # this could be an error in strict mode?

    name = cmd_val.argv[1]

    # Run regular builtin or special builtin
    to_run = consts.LookupNormalBuiltin(name)
    if to_run == consts.NO_INDEX:
      to_run = consts.LookupSpecialBuiltin(name)
    if to_run == consts.NO_INDEX:
      span_id = cmd_val.arg_spids[1]
      if consts.LookupAssignBuiltin(name) != consts.NO_INDEX:
        # NOTE: There's a similar restriction for 'command'
        self.errfmt.Print("Can't run assignment builtin recursively",
                          span_id=span_id)
      else:
        self.errfmt.Print("%r isn't a shell builtin", name, span_id=span_id)
      return 1

    cmd_val2 = cmd_value.Argv(cmd_val.argv[1:], cmd_val.arg_spids[1:],
                              cmd_val.block)
    return self.shell_ex.RunBuiltin(to_run, cmd_val2)


def ResolveNames(names, funcs, aliases, search_path):
  # type: (List[str], Dict[str, command__ShFunction], Dict[str, str], state.SearchPath) -> List[Tuple[str, str]]
  results = []
  for name in names:
    if name in funcs:
      kind = ('function', name)
    elif name in aliases:
      kind = ('alias', name)

    # TODO: Use match instead?
    elif consts.LookupNormalBuiltin(name) != 0:
      kind = ('builtin', name)
    elif consts.LookupSpecialBuiltin(name) != 0:
      kind = ('builtin', name)
    elif consts.LookupAssignBuiltin(name) != 0:
      kind = ('builtin', name)
    elif lexer_def.IsControlFlow(name):  # continue, etc.
      kind = ('keyword', name)

    elif lexer_def.IsKeyword(name):
      kind = ('keyword', name)
    else:
      resolved = search_path.Lookup(name)
      if resolved is None:
        kind = (None, None)
      else:
        kind = ('file', resolved) 
    results.append(kind)

  return results


class Type(object):
  def __init__(self, funcs, aliases, search_path):
    # type: (Dict[str, command__ShFunction], Dict[str, str], state.SearchPath) -> None
    self.funcs = funcs
    self.aliases = aliases
    self.search_path = search_path

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, i = arg_def.ParseCmdVal('type', cmd_val)
    arg = arg_types.type(attrs.attrs)

    if arg.f:
      funcs = {}  # type: Dict[str, command__ShFunction]
    else:
      funcs = self.funcs

    status = 0
    r = ResolveNames(cmd_val.argv[i:], funcs, self.aliases, self.search_path)
    for kind, name in r:
      if kind is None:
        status = 1  # nothing printed, but we fail
      else:
        if arg.t:
          print(kind)
        elif arg.p:
          if kind == 'file':
            print(name)
        elif arg.P:
          if kind == 'file':
            print(name)
          else:
            resolved = self.search_path.Lookup(name)
            if resolved is None:
              status = 1
            else:
              print(resolved)

        else:
          # Alpine's abuild relies on this text because busybox ash doesn't have
          # -t!
          # ash prints "is a shell function" instead of "is a function", but the
          # regex accouts for that.
          print('%s is a %s' % (name, kind))
          if kind == 'function':
            # bash prints the function body, busybox ash doesn't.
            pass

    return status
