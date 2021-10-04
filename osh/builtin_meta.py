#!/usr/bin/env python2
"""
builtin_meta.py - Builtins that call back into the interpreter.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import source
from asdl import runtime
from core import alloc
from core import dev
from core import error
from core import main_loop
from core.pyerror import e_die, e_usage, log
from core import pyutil  # strerror
from core import state
from core import vm
from frontend import flag_spec
from frontend import consts
from frontend import reader
from osh import cmd_eval

_ = log

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv, Proc
  from frontend.parse_lib import ParseContext
  from core import optview
  from core import process
  from core import state
  from core import ui
  from osh.cmd_eval import CommandEvaluator


class Eval(vm._Builtin):

  def __init__(self, parse_ctx, exec_opts, cmd_ev, tracer):
    # type: (ParseContext, optview.Exec, CommandEvaluator, dev.Tracer) -> None
    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena
    self.exec_opts = exec_opts
    self.cmd_ev = cmd_ev
    self.tracer = tracer

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    # There are no flags, but we need it to respect --
    _, arg_r = flag_spec.ParseCmdVal('eval', cmd_val)

    if self.exec_opts.simple_eval_builtin():
      code_str, eval_spid = arg_r.ReadRequired2('requires code string')
      if not arg_r.AtEnd():
        e_usage('requires exactly 1 argument')
    else:
      code_str = ' '.join(arg_r.Rest())
      # code_str could be EMPTY, so just use the first one
      eval_spid = cmd_val.arg_spids[0]

    line_reader = reader.StringLineReader(code_str, self.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader)

    src = source.ArgvWord(eval_spid)
    with dev.ctx_Tracer(self.tracer, 'eval', None):
      with alloc.ctx_Location(self.arena, src):
        return main_loop.Batch(self.cmd_ev, c_parser, self.arena,
                               cmd_flags=cmd_eval.RaiseControlFlow)


class Source(vm._Builtin):

  def __init__(self, parse_ctx, search_path, cmd_ev, fd_state, tracer, errfmt):
    # type: (ParseContext, state.SearchPath, CommandEvaluator, process.FdState, dev.Tracer, ui.ErrorFormatter) -> None
    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena
    self.search_path = search_path
    self.cmd_ev = cmd_ev
    self.fd_state = fd_state
    self.tracer = tracer
    self.errfmt = errfmt

    self.mem = cmd_ev.mem

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    call_spid = cmd_val.arg_spids[0]
    _, arg_r = flag_spec.ParseCmdVal('source', cmd_val)

    path = arg_r.Peek()
    if path is None:
      e_usage('missing required argument')
    arg_r.Next()

    resolved = self.search_path.Lookup(path, exec_required=False)
    if resolved is None:
      resolved = path
    try:
      f = self.fd_state.Open(resolved)  # Shell can't use descriptors 3-9
    except OSError as e:
      self.errfmt.Print_('source %r failed: %s' % (path, pyutil.strerror(e)),
                        span_id=cmd_val.arg_spids[1])
      return 1

    try:
      line_reader = reader.FileLineReader(f, self.arena)
      c_parser = self.parse_ctx.MakeOshParser(line_reader)

      # A sourced module CAN have a new arguments array, but it always shares
      # the same variable scope as the caller.  The caller could be at either a
      # global or a local scope.
      with dev.ctx_Tracer(self.tracer, 'source', cmd_val.argv):
        source_argv = arg_r.Rest()
        with state.ctx_Source(self.mem, path, source_argv):
          with state.ctx_ThisDir(self.mem, path):
            src = source.SourcedFile(path, call_spid)
            with alloc.ctx_Location(self.arena, src):
              status = main_loop.Batch(self.cmd_ev, c_parser, self.arena,
                                       cmd_flags=cmd_eval.RaiseControlFlow)
      return status

    except error._ControlFlow as e:
      if e.IsReturn():
        return e.StatusCode()
      else:
        raise
    finally:
      f.close()


class Command(vm._Builtin):
  """
  'command ls' suppresses function lookup.
  """

  def __init__(self, shell_ex, funcs, aliases, search_path):
    # type: (vm._Executor, Dict[str, Proc], Dict[str, str], state.SearchPath) -> None
    self.shell_ex = shell_ex
    self.funcs = funcs
    self.aliases = aliases
    self.search_path = search_path

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('command', cmd_val)
    arg = arg_types.command(attrs.attrs)
    if arg.v:
      status = 0
      names = arg_r.Rest()
      for kind, argument in _ResolveNames(names, self.funcs, self.aliases,
                                          self.search_path):
        if kind is None:
          status = 1  # nothing printed, but we fail
        else:
          # This is for -v, -V is more detailed.
          print(argument)
      return status

    # shift by one
    cmd_val = cmd_value.Argv(cmd_val.argv[1:], cmd_val.arg_spids[1:],
                             cmd_val.block)

    # If we respected do_fork here instead of passing True, the case
    # 'command date | wc -l' would take 2 processes instead of 3.  But no other
    # shell does that, and this rare case isn't worth the bookkeeping.
    # See test/syscall
    return self.shell_ex.RunSimpleCommand(cmd_val, True, call_procs=False)


class Builtin(vm._Builtin):

  def __init__(self, shell_ex, errfmt):
    # type: (vm._Executor, ui.ErrorFormatter) -> None
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
        self.errfmt.Print_("Can't run assignment builtin recursively",
                          span_id=span_id)
      else:
        self.errfmt.Print_("%r isn't a shell builtin" % name, span_id=span_id)
      return 1

    cmd_val2 = cmd_value.Argv(cmd_val.argv[1:], cmd_val.arg_spids[1:],
                              cmd_val.block)
    return self.shell_ex.RunBuiltin(to_run, cmd_val2)


class RunProc(vm._Builtin):

  def __init__(self, shell_ex, procs, errfmt):
    # type: (vm._Executor, Dict[str, Proc], ui.ErrorFormatter) -> None
    self.shell_ex = shell_ex
    self.procs = procs
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    attrs, arg_r = flag_spec.ParseOilCmdVal('runproc', cmd_val)
    arg = arg_types.runproc(attrs.attrs)

    argv, spids = arg_r.Rest2()

    if len(argv) == 0:
      raise error.Usage('requires arguments', span_id=runtime.NO_SPID)

    name = argv[0]
    if name not in self.procs:
      self.errfmt.StderrLine('runproc: no proc named %r' % name)
      return 1
    cmd_val2 = cmd_value.Argv(argv, spids, cmd_val.block)

    return self.shell_ex.RunSimpleCommand(cmd_val2, True)


class Try(vm._Builtin):
  """For the 'if myfunc' problem with errexit.

  --status-ok
    for SIGPIPE problem
    TODO: I think we want sigpipe_status_ok instead of this
  --allow-status-01
    because 'grep' returns 0, 1, or 2 (true, false, usage error)
  --assign-status
    To check exit codes in a more detailed way rather than relying on errexit
  --push-status
    TODO: for the headless shell to avoid clobbering $! with commands

  if run deploy {
    echo "success"
  }
  if ! run deploy {
    echo "failed"
  }
  """

  def __init__(self, mutable_opts, mem, shell_ex, errfmt):
    # type: (state.MutableOpts, state.Mem, vm._Executor, ui.ErrorFormatter) -> None
    self.mutable_opts = mutable_opts
    self.mem = mem
    self.shell_ex = shell_ex
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    # TODO: Also hard usage error here too?
    attrs, arg_r = flag_spec.ParseOilCmdVal('try_', cmd_val)
    arg = arg_types.try_(attrs.attrs)

    if arg_r.Peek() is None:
      # HARD ERROR, not e_usage(), because errexit is often disabled!
      e_die("'try' expected a command to run", status=2)

    argv, spids = arg_r.Rest2()
    cmd_val2 = cmd_value.Argv(argv, spids, cmd_val.block)

    # Set in the 'except' block, e.g. if 'myfunc' failed
    failure_spid = runtime.NO_SPID
    try:
      # Temporarily turn ON errexit, but don't pass a SPID because we're
      # ENABLING and not disabling.  Note that 'if try myproc' disables it and
      # then enables it!
      with state.ctx_ErrExit(self.mutable_opts, True, runtime.NO_SPID):
        # Pass do_fork=True.  Slight annoyance: the real value is a field of
        # command.Simple().  See _NoForkLast() in CommandEvaluator We have an
        # extra fork (miss out on an optimization) of code like ( status ls )
        # or forkwait { status ls }, but that is NOT idiomatic code.  status is
        # for functions.
        status = self.shell_ex.RunSimpleCommand(cmd_val2, True)
        #log('st %d', status)
    except error.ErrExit as e:  # from function call
      #log('e %d', e.exit_status)
      status = e.exit_status
      failure_spid = e.span_id

    if arg.allow_status_01 and status not in (0, 1):
      if failure_spid != runtime.NO_SPID:
        self.errfmt.Print_('(original failure)', span_id=failure_spid)
        self.errfmt.StderrLine('')

      raise error.ErrExit(
          'fatal: status %d when --allow-status-01' % status,
          span_id=spids[0], status=status)

    if arg.assign is not None:
      var_name = arg.assign
      if var_name.startswith(':'):
        var_name = var_name[1:]

      state.BuiltinSetString(self.mem, var_name, str(status))
      return self.mem.LastStatus()

    return status


def _ResolveNames(names, funcs, aliases, search_path):
  # type: (List[str], Dict[str, Proc], Dict[str, str], state.SearchPath) -> List[Tuple[str, str]]
  results = []  # type: List[Tuple[str, str]]
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
    elif consts.IsControlFlow(name):  # continue, etc.
      kind = ('keyword', name)

    elif consts.IsKeyword(name):
      kind = ('keyword', name)
    else:
      resolved = search_path.Lookup(name)
      if resolved is None:
        no_str = None  # type: Optional[str]
        kind = (no_str, name)
      else:
        kind = ('file', resolved) 
    results.append(kind)

  return results


class Type(vm._Builtin):
  def __init__(self, funcs, aliases, search_path, errfmt):
    # type: (Dict[str, Proc], Dict[str, str], state.SearchPath, ui.ErrorFormatter) -> None
    self.funcs = funcs
    self.aliases = aliases
    self.search_path = search_path
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('type', cmd_val)
    arg = arg_types.type(attrs.attrs)

    if arg.f:
      funcs = {}  # type: Dict[str, Proc]
    else:
      funcs = self.funcs

    status = 0
    r = _ResolveNames(arg_r.Rest(), funcs, self.aliases, self.search_path)
    for kind, name in r:
      if kind is None:
        self.errfmt.StderrLine('type: %r not found' % name)
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
