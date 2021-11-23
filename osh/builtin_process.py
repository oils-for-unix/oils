#!/usr/bin/env python2
"""
builtin_process.py - Builtins that deal with processes or modify process state.

This is sort of the opposite of builtin_pure.py.
"""
from __future__ import print_function

import signal  # for calculating numbers

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import (
    cmd_value, cmd_value__Argv,
    wait_status_e, wait_status__Proc, wait_status__Pipeline, wait_status__Cancelled,
    job_state_e,
)
from _devbuild.gen.syntax_asdl import source
from asdl import runtime
from core import alloc
from core import dev
from core import error
from core.pyerror import e_usage
from core import main_loop
from core.pyutil import stderr_line
from core import ui
from core import vm
from core.pyerror import log
from frontend import args
from frontend import flag_spec
from frontend import reader
from frontend import signal_def
from mycpp import mylib
from mycpp.mylib import iteritems, tagswitch

import posix_ as posix

from typing import List, Dict, Optional, Any, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import command_t
  from core.process import ExternalProgram, FdState, JobState, Waiter
  from core.pyos import SignalState
  from core.state import Mem, SearchPath
  from core.ui import ErrorFormatter
  from frontend.parse_lib import ParseContext


if mylib.PYTHON:
  EXEC_SPEC = flag_spec.FlagSpec('exec')


class Exec(vm._Builtin):

  def __init__(self, mem, ext_prog, fd_state, search_path, errfmt):
    # type: (Mem, ExternalProgram, FdState, SearchPath, ErrorFormatter) -> None
    self.mem = mem
    self.ext_prog = ext_prog
    self.fd_state = fd_state
    self.search_path = search_path
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'exec'
    _ = args.Parse(EXEC_SPEC, arg_r)  # no flags now, but accepts --

    # Apply redirects in this shell.  # NOTE: Redirects were processed earlier.
    if arg_r.AtEnd():
      self.fd_state.MakePermanent()
      return 0

    environ = self.mem.GetExported()
    i = arg_r.i
    cmd = cmd_val.argv[i]
    argv0_path = self.search_path.CachedLookup(cmd)
    if argv0_path is None:
      self.errfmt.Print_('exec: %r not found' % cmd,
                         span_id=cmd_val.arg_spids[1])
      raise SystemExit(127)  # exec builtin never returns

    # shift off 'exec'
    c2 = cmd_value.Argv(cmd_val.argv[i:], cmd_val.arg_spids[i:], cmd_val.block)
    self.ext_prog.Exec(argv0_path, c2, environ)  # NEVER RETURNS
    assert False, "This line should never be reached" # makes mypy happy


class Wait(vm._Builtin):
  """
  wait: wait [-n] [id ...]
      Wait for job completion and return exit status.

      Waits for each process identified by an ID, which may be a process ID or a
      job specification, and reports its termination status.  If ID is not
      given, waits for all currently active child processes, and the return
      status is zero.  If ID is a a job specification, waits for all processes
      in that job's pipeline.

      If the -n option is supplied, waits for the next job to terminate and
      returns its exit status.

      Exit Status:
      Returns the status of the last ID; fails if ID is invalid or an invalid
      option is given.
  """
  def __init__(self, waiter, job_state, mem, tracer, errfmt):
    # type: (Waiter, JobState, Mem, dev.Tracer, ErrorFormatter) -> None
    self.waiter = waiter
    self.job_state = job_state
    self.mem = mem
    self.tracer = tracer
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    with dev.ctx_Tracer(self.tracer, 'wait', cmd_val.argv):
      return self._Run(cmd_val)

  def _Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('wait', cmd_val)
    arg = arg_types.wait(attrs.attrs)

    job_ids, arg_spids = arg_r.Rest2()

    if arg.n:
      #log('*** wait -n')
      # wait -n returns the exit status of the JOB.
      # You don't know WHICH process, which is odd.

      # TODO: this should wait for the next JOB, which may be multiple
      # processes.
      # Bash has a wait_for_any_job() function, which loops until the jobs
      # table changes.
      #
      # target_count = self.job_state.NumRunning() - 1
      # while True:
      #   if not self.waiter.WaitForOne():
      #     break
      #
      #   if self.job_state.NumRunning == target_count:
      #     break
      #    
      #log('wait next')

      result = self.waiter.WaitForOne(False)
      if result == 0:  # OK
        return self.waiter.last_status
      elif result == -1:  # nothing to wait for
        return 127
      else:
        return result  # signal

    if len(job_ids) == 0:
      #log('*** wait')
      i = 0
      while True:
        # BUG: If there is a STOPPED process, this will hang forever, because
        # we don't get ECHILD.
        # Not sure it matters since you can now Ctrl-C it.

        result = self.waiter.WaitForOne(False)
        if result != 0:
          break  # nothing to wait for, or interrupted
        i += 1
        if self.job_state.NoneAreRunning():
          break

      return 0 if result == -1 else result

    # Get list of jobs.  Then we need to check if they are ALL stopped.
    # Returns the exit code of the last one on the COMMAND LINE, not the exit
    # code of last one to FINISH.
    status = 1  # error
    for i, job_id in enumerate(job_ids):
      span_id = arg_spids[i]

      # The % syntax is sort of like ! history sub syntax, with various queries.
      # https://stackoverflow.com/questions/35026395/bash-what-is-a-jobspec
      if job_id.startswith('%'):
        raise error.Usage(
            "doesn't support bash-style jobspecs (got %r)" % job_id,
            span_id=span_id)

      # Does it look like a PID?
      try:
        pid = int(job_id)
      except ValueError:
        raise error.Usage('expected PID or jobspec, got %r' % job_id,
                          span_id=span_id)

      job = self.job_state.JobFromPid(pid)
      if job is None:
        self.errfmt.Print_("%s isn't a child of this shell" % pid,
                           span_id=span_id)
        return 127

      wait_status = job.JobWait(self.waiter)

      UP_wait_status = wait_status
      with tagswitch(wait_status) as case:
        if case(wait_status_e.Proc):
          wait_status = cast(wait_status__Proc, UP_wait_status)
          status = wait_status.code
        elif case(wait_status_e.Pipeline):
          wait_status = cast(wait_status__Pipeline, UP_wait_status)
          # TODO: handle PIPESTATUS?  Is this right?
          status = wait_status.codes[-1]
        elif case(wait_status_e.Cancelled):
          wait_status = cast(wait_status__Cancelled, UP_wait_status)
          status = wait_status.code
        else:
          raise AssertionError()

    return status


class Jobs(vm._Builtin):
  """List jobs."""
  def __init__(self, job_state):
    # type: (JobState) -> None
    self.job_state = job_state

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    attrs, arg_r = flag_spec.ParseCmdVal('jobs', cmd_val)
    arg = arg_types.jobs(attrs.attrs)

    # note: we always use 'jobs -l' format, so -l is a no-op
    self.job_state.DisplayJobs()
    if arg.debug:
      self.job_state.DebugPrint()

    return 0


class Fg(vm._Builtin):
  """Put a job in the foreground"""
  def __init__(self, job_state, waiter):
    # type: (JobState, Waiter) -> None
    self.job_state = job_state
    self.waiter = waiter

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    # Note: 'fg' currently works with processes, but not pipelines.  See issue
    # #360.  Part of it is that we should use posix.killpg().
    pid = self.job_state.GetLastStopped()
    if pid == -1:
      log('No job to put in the foreground')
      return 1

    # TODO: Print job ID rather than the PID
    log('Continue PID %d', pid)
    posix.kill(pid, signal.SIGCONT)

    job = self.job_state.JobFromPid(pid)
    job.state = job_state_e.Running  # needed for Wait() loop to work
    status = job.Wait(self.waiter)
    #log('status = %d', status)
    return status


class Bg(vm._Builtin):
  """Put a job in the background"""
  def __init__(self, job_state):
    # type: (JobState) -> None
    self.job_state = job_state

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    # How does this differ from 'fg'?  It doesn't wait and it sets controlling
    # terminal?

    raise error.Usage("isn't implemented")


class _TrapHandler(object):
  """A function that is called by Python's signal module.

  Similar to process.SubProgramThunk."""

  def __init__(self, node, nodes_to_run, sig_state, tracer):
    # type: (command_t, List[command_t], SignalState, dev.Tracer) -> None
    self.node = node
    self.nodes_to_run = nodes_to_run
    self.sig_state = sig_state
    self.tracer = tracer

  def __call__(self, sig_num, unused_frame):
    # type: (int, Any) -> None
    """For Python's signal module."""
    self.tracer.PrintMessage(
        'Received signal %d.  Will run handler in main loop' % sig_num)

    self.sig_state.last_sig_num = sig_num  # for interrupted 'wait'
    self.nodes_to_run.append(self.node)

  def __str__(self):
    # type: () -> str
    # Used by trap -p
    # TODO: Abbreviate with fmt.PrettyPrint?
    return '<Trap %s>' % self.node


def _GetSignalNumber(sig_spec):
  # type: (str) -> int

  # POSIX lists the numbers that are required.
  # http://pubs.opengroup.org/onlinepubs/9699919799/
  #
  # Added 13 for SIGPIPE because autoconf's 'configure' uses it!
  if sig_spec.strip() in ('1', '2', '3', '6', '9', '13', '14', '15'):
    return int(sig_spec)

  # INT is an alias for SIGINT
  if sig_spec.startswith('SIG'):
    sig_spec = sig_spec[3:]
  return signal_def.GetNumber(sig_spec)


_HOOK_NAMES = ['EXIT', 'ERR', 'RETURN', 'DEBUG']


# TODO:
#
# bash's default -p looks like this:
# trap -- '' SIGTSTP
# trap -- '' SIGTTIN
# trap -- '' SIGTTOU
#
# CPython registers different default handlers.  The C++ rewrite should make
# OVM match sh/bash more closely.

class Trap(vm._Builtin):
  def __init__(self, sig_state, traps, nodes_to_run, parse_ctx, tracer, errfmt):
    # type: (SignalState, Dict[str, _TrapHandler], List[command_t], ParseContext, dev.Tracer, ErrorFormatter) -> None
    self.sig_state = sig_state
    self.traps = traps
    self.nodes_to_run = nodes_to_run
    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena
    self.tracer = tracer
    self.errfmt = errfmt

  def _ParseTrapCode(self, code_str):
    # type: (str) -> command_t
    """
    Returns:
      A node, or None if the code is invalid.
    """
    line_reader = reader.StringLineReader(code_str, self.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader)

    # TODO: the SPID should be passed through argv.
    src = source.ArgvWord('trap', runtime.NO_SPID)
    with alloc.ctx_Location(self.arena, src):
      try:
        node = main_loop.ParseWholeFile(c_parser)
      except error.Parse as e:
        ui.PrettyPrintError(e, self.arena)
        return None

    return node

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('trap', cmd_val)
    arg = arg_types.trap(attrs.attrs)

    if arg.p:  # Print registered handlers
      for name, value in iteritems(self.traps):
        # The unit tests rely on this being one line.
        # bash prints a line that can be re-parsed.
        print('%s %s' % (name, value.__class__.__name__))

      return 0

    if arg.l:  # List valid signals and hooks
      for name in _HOOK_NAMES:
        print('   %s' % name)
      for name, int_val in signal_def.AllNames():
        print('%2d %s' % (int_val, name))

      return 0

    code_str = arg_r.ReadRequired('requires a code string')
    sig_spec, sig_spid = arg_r.ReadRequired2('requires a signal or hook name')

    # sig_key is NORMALIZED sig_spec: a signal number string or string hook
    # name.
    sig_key = None  # type: Optional[str]
    sig_num = None
    if sig_spec in _HOOK_NAMES:
      sig_key = sig_spec
    elif sig_spec == '0':  # Special case
      sig_key = 'EXIT'
    else:
      sig_num = _GetSignalNumber(sig_spec)
      if sig_num is not None:
        sig_key = str(sig_num)

    if sig_key is None:
      self.errfmt.Print_("Invalid signal or hook %r" % sig_spec,
                         span_id=cmd_val.arg_spids[2])
      return 1

    # NOTE: sig_spec isn't validated when removing handlers.
    if code_str == '-':
      if sig_key in _HOOK_NAMES:
        try:
          del self.traps[sig_key]
        except KeyError:
          pass
        return 0

      if sig_num is not None:
        try:
          del self.traps[sig_key]
        except KeyError:
          pass

        self.sig_state.RemoveUserTrap(sig_num)
        return 0

      raise AssertionError('Signal or trap')

    # Try parsing the code first.

    # TODO: If simple_trap is on (for oil:basic), then it must be a function
    # name?  And then you wrap it in 'try'?

    node = self._ParseTrapCode(code_str)
    if node is None:
      return 1  # ParseTrapCode() prints an error for us.

    # Register a hook.
    if sig_key in _HOOK_NAMES:
      if sig_key in ('ERR', 'RETURN', 'DEBUG'):
        stderr_line("osh warning: The %r hook isn't implemented", sig_spec)
      self.traps[sig_key] = _TrapHandler(node, self.nodes_to_run,
                                         self.sig_state, self.tracer)
      return 0

    # Register a signal.
    if sig_num is not None:
      handler = _TrapHandler(node, self.nodes_to_run, self.sig_state,
                             self.tracer)
      # For signal handlers, the traps dictionary is used only for debugging.
      self.traps[sig_key] = handler
      if sig_num in (signal.SIGKILL, signal.SIGSTOP):
        self.errfmt.Print_("Signal %r can't be handled" % sig_spec,
                           span_id=sig_spid)
        # Other shells return 0, but this seems like an obvious error
        return 1
      self.sig_state.AddUserTrap(sig_num, handler)
      return 0

    raise AssertionError('Signal or trap')

  # Example:
  # trap -- 'echo "hi  there" | wc ' SIGINT
  #
  # Then hit Ctrl-C.


class Umask(vm._Builtin):

  def __init__(self):
    # type: () -> None
    """Dummy constructor for mycpp."""
    pass

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    argv = cmd_val.argv[1:]
    if len(argv) == 0:
      # umask() has a dumb API: you can't get it without modifying it first!
      # NOTE: dash disables interrupts around the two umask() calls, but that
      # shouldn't be a concern for us.  Signal handlers won't call umask().
      mask = posix.umask(0)
      posix.umask(mask)  #
      print('0%03o' % mask)  # octal format
      return 0

    if len(argv) == 1:
      a = argv[0]
      try:
        new_mask = int(a, 8)
      except ValueError:
        # NOTE: This happens if we have '8' or '9' in the input too.
        stderr_line("osh warning: umask with symbolic input isn't implemented")
        return 1
      else:
        posix.umask(new_mask)
        return 0

    e_usage('umask: unexpected arguments')


class Fork(vm._Builtin):

  def __init__(self, shell_ex):
    # type: (vm._Executor) -> None
    self.shell_ex = shell_ex

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('fork', cmd_val)
    arg, span_id = arg_r.Peek2()
    if arg is not None:
      e_usage('got unexpected argument %r' % arg, span_id=span_id)

    if cmd_val.block is None:
      e_usage('expected a block')

    return self.shell_ex.RunBackgroundJob(cmd_val.block)


class ForkWait(vm._Builtin):

  def __init__(self, shell_ex):
    # type: (vm._Executor) -> None
    self.shell_ex = shell_ex

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('forkwait', cmd_val)
    arg, span_id = arg_r.Peek2()
    if arg is not None:
      e_usage('got unexpected argument %r' % arg, span_id=span_id)

    if cmd_val.block is None:
      e_usage('expected a block')

    return self.shell_ex.RunSubshell(cmd_val.block)
