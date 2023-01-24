#!/usr/bin/env python2
"""
builtin_meta.py - Builtins that call back into the interpreter.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value, CommandStatus
from _devbuild.gen.syntax_asdl import source, loc
from asdl import runtime
from core import alloc
from core import dev
from core import error
from core import main_loop
from core.pyerror import e_die_status, e_usage, log
from core import pyutil  # strerror
from core import state
from core import vm
from frontend import flag_spec
from frontend import consts
from frontend import reader
from frontend import typed_args
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

  def __init__(self, parse_ctx, exec_opts, cmd_ev, tracer, errfmt):
    # type: (ParseContext, optview.Exec, CommandEvaluator, dev.Tracer, ui.ErrorFormatter) -> None
    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena
    self.exec_opts = exec_opts
    self.cmd_ev = cmd_ev
    self.tracer = tracer
    self.errfmt = errfmt

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

    src = source.ArgvWord('eval', eval_spid)
    with dev.ctx_Tracer(self.tracer, 'eval', None):
      with alloc.ctx_Location(self.arena, src):
        return main_loop.Batch(self.cmd_ev, c_parser, self.errfmt,
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
    # TODO: need to close the file!
    try:
      f = self.fd_state.Open(resolved)  # Shell can't use descriptors 3-9
    except (IOError, OSError) as e:
      self.errfmt.Print_('source %r failed: %s' % (path, pyutil.strerror(e)),
                         span_id=cmd_val.arg_spids[1])
      return 1

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
            try:
              status = main_loop.Batch(self.cmd_ev, c_parser, self.errfmt,
                                       cmd_flags=cmd_eval.RaiseControlFlow)
            except vm.ControlFlow as e:
              if e.IsReturn():
                status = e.StatusCode()
              else:
                raise
            finally:
              f.close()

    return status


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

    # accept_typed_args=True because we invoke other builtins
    attrs, arg_r = flag_spec.ParseCmdVal('command', cmd_val,
                                         accept_typed_args=True)
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
                             cmd_val.typed_args)

    # If we respected do_fork here instead of passing True, the case
    # 'command date | wc -l' would take 2 processes instead of 3.  But no other
    # shell does that, and this rare case isn't worth the bookkeeping.
    # See test/syscall
    cmd_st = CommandStatus()
    return self.shell_ex.RunSimpleCommand(cmd_val, cmd_st, True, call_procs=False)


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
                              cmd_val.typed_args)
    return self.shell_ex.RunBuiltin(to_run, cmd_val2)


class RunProc(vm._Builtin):

  def __init__(self, shell_ex, procs, errfmt):
    # type: (vm._Executor, Dict[str, Proc], ui.ErrorFormatter) -> None
    self.shell_ex = shell_ex
    self.procs = procs
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    _, arg_r = flag_spec.ParseCmdVal('runproc', cmd_val,
                                     accept_typed_args=True)
    argv, spids = arg_r.Rest2()

    if len(argv) == 0:
      raise error.Usage('requires arguments', span_id=runtime.NO_SPID)

    name = argv[0]
    if name not in self.procs:
      self.errfmt.PrintMessage('runproc: no proc named %r' % name)
      return 1

    cmd_val2 = cmd_value.Argv(argv, spids, cmd_val.typed_args)
    cmd_st = CommandStatus()
    return self.shell_ex.RunSimpleCommand(cmd_val2, cmd_st, True)


class Try(vm._Builtin):
  """Allows explicit handling of errors.

  Takes command argv, or a block:

  try ls /bad

  try {
    var x = 1 / 0

    ls | wc -l

    diff <(sort left.txt) <(sort right.txt)
  }

  TODO:
  - Set _error_str (e.UserErrorString()) 
  - Set _error_location (span_id)
  - These could be used by a 'raise' builtin?  Or 'reraise'

  try foo
  if (_status != 0) {
    echo 'hello'
    raise  # reads _status, _error_str, and _error_location ?
  }
  """

  def __init__(self, mutable_opts, mem, cmd_ev, shell_ex, errfmt):
    # type: (state.MutableOpts, state.Mem, cmd_eval.CommandEvaluator, vm._Executor, ui.ErrorFormatter) -> None
    self.mutable_opts = mutable_opts
    self.mem = mem
    self.shell_ex = shell_ex
    self.cmd_ev = cmd_ev
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    _, arg_r = flag_spec.ParseCmdVal('try_', cmd_val, accept_typed_args=True)

    block = typed_args.GetOneBlock(cmd_val.typed_args)
    if block:
      status = 0  # success by default
      try:
        with state.ctx_ErrExit(self.mutable_opts, True, runtime.NO_SPID):
          unused = self.cmd_ev.EvalBlock(block)
      except error.Expr as e:
        status = e.ExitStatus()
      except error.ErrExit as e:
        status = e.ExitStatus()

      self.mem.SetTryStatus(status)
      return 0

    if arg_r.Peek() is None:
      e_usage('expects a block or command argv')

    argv, spids = arg_r.Rest2()
    cmd_val2 = cmd_value.Argv(argv, spids, cmd_val.typed_args)

    #failure_spid = runtime.NO_SPID
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
        cmd_st = CommandStatus()  # TODO: take param
        status = self.shell_ex.RunSimpleCommand(cmd_val2, cmd_st, True)
        #log('st %d', status)
    except error.Expr as e:
      status = e.ExitStatus()
    except error.ErrExit as e:
      status = e.ExitStatus()
      #failure_spid = e.span_id

    # special variable
    self.mem.SetTryStatus(status)
    return 0


class BoolStatus(vm._Builtin):
  def __init__(self, shell_ex, errfmt):
    # type: (vm._Executor, ui.ErrorFormatter) -> None
    self.shell_ex = shell_ex
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    _, arg_r = flag_spec.ParseCmdVal('boolstatus', cmd_val)

    if arg_r.Peek() is None:
      e_usage('expected a command to run')

    argv, spids = arg_r.Rest2()
    cmd_val2 = cmd_value.Argv(argv, spids, cmd_val.typed_args)

    cmd_st = CommandStatus()
    status = self.shell_ex.RunSimpleCommand(cmd_val2, cmd_st, True)

    if status not in (0, 1):
      e_die_status(
          status, 'boolstatus expected status 0 or 1, got %d' % status,
          loc.Span(spids[0]))

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
        if not arg.t:  # 'type -t X' is silent in this case
          self.errfmt.PrintMessage('type: %r not found' % name)
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
