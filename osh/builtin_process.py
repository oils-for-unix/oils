#!/usr/bin/env python2
"""
builtin_process.py - Builtins that deal with processes or modify process state.

This is sort of the opposite of builtin_pure.py.
"""
from __future__ import print_function

import signal  # for calculating numbers

from _devbuild.gen.runtime_asdl import (
    cmd_value, cmd_value__Argv,
    job_status_e, job_status__Proc, job_status__Pipeline,
)
from _devbuild.gen.syntax_asdl import source
from asdl import runtime
from core import error
from core import main_loop
from core import ui
from core.util import log
from frontend import args
from frontend import arg_def
from frontend import reader
from mycpp import mylib
from mycpp.mylib import tagswitch
from osh.builtin_misc import _Builtin

import posix_ as posix

from typing import List, Dict, Any, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import command_t
  from core.ui import ErrorFormatter
  from core.process import (
      ExternalProgram, FdState, JobState, SignalState, Waiter
  )
  from core.state import Mem, SearchPath
  from frontend.parse_lib import ParseContext


if mylib.PYTHON:
  EXEC_SPEC = arg_def.Register('exec')


class Exec(object):

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
    _ = EXEC_SPEC.Parse(arg_r)  # no flags now, but accepts --

    # Apply redirects in this shell.  # NOTE: Redirects were processed earlier.
    if arg_r.AtEnd():
      self.fd_state.MakePermanent()
      return 0

    environ = self.mem.GetExported()
    i = arg_r.i
    cmd = cmd_val.argv[i]
    argv0_path = self.search_path.CachedLookup(cmd)
    if argv0_path is None:
      self.errfmt.Print('exec: %r not found', cmd,
                        span_id=cmd_val.arg_spids[1])
      raise SystemExit(127)  # exec builtin never returns

    # shift off 'exec'
    c2 = cmd_value.Argv(cmd_val.argv[i:], cmd_val.arg_spids[i:], cmd_val.block)
    self.ext_prog.Exec(argv0_path, c2, environ)  # NEVER RETURNS
    assert False, "This line should never be reached" # makes mypy happy



if mylib.PYTHON:
  WAIT_SPEC = arg_def.Register('wait')
  WAIT_SPEC.ShortFlag('-n')


class Wait(object):
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
  def __init__(self, waiter, job_state, mem, errfmt):
    # type: (Waiter, JobState, Mem, ErrorFormatter) -> None
    self.waiter = waiter
    self.job_state = job_state
    self.mem = mem
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    arg, arg_index = WAIT_SPEC.ParseCmdVal(cmd_val)
    job_ids = cmd_val.argv[arg_index:]
    arg_count = len(cmd_val.argv)

    if arg.n:
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

      if self.waiter.WaitForOne():
        return self.waiter.last_status
      else:
        return 127  # nothing to wait for

    if arg_index == arg_count:  # no arguments
      #log('wait all')

      i = 0
      while True:
        # BUG: If there is a STOPPED process, this will hang forever, because
        # we don't get ECHILD.
        # Not sure it matters since you can now Ctrl-C it.

        if not self.waiter.WaitForOne():
          break  # nothing to wait for
        i += 1
        if self.job_state.NoneAreRunning():
          break

      log('Waited for %d processes', i)
      return 0

    # Get list of jobs.  Then we need to check if they are ALL stopped.
    # Returns the exit code of the last one on the COMMAND LINE, not the exit
    # code of last one to FINISH.
    status = 1  # error
    for i in xrange(arg_index, arg_count):
      job_id = cmd_val.argv[i]
      span_id = cmd_val.arg_spids[i]

      # The % syntax is sort of like ! history sub syntax, with various queries.
      # https://stackoverflow.com/questions/35026395/bash-what-is-a-jobspec
      if job_id.startswith('%'):
        raise args.UsageError(
            "doesn't support bash-style jobspecs (got %r)" % job_id,
            span_id=span_id)

      # Does it look like a PID?
      try:
        pid = int(job_id)
      except ValueError:
        raise args.UsageError('expected PID or jobspec, got %r' % job_id,
                              span_id=span_id)

      job = self.job_state.JobFromPid(pid)
      if job is None:
        self.errfmt.Print("%s isn't a child of this shell", pid,
                          span_id=span_id)
        return 127

      # TODO: Does this wait for pipelines?
      job_status = job.JobWait(self.waiter)

      UP_job_status = job_status
      with tagswitch(job_status) as case:
        if case(job_status_e.Proc):
          job_status = cast(job_status__Proc, UP_job_status)
          status = job_status.code
        elif case(job_status_e.Pipeline):
          # TODO: handle PIPESTATUS?
          job_status = cast(job_status__Pipeline, UP_job_status)
          # Is this right?
          status = job_status.codes[-1]
        else:
          raise AssertionError

    return status


class Jobs(object):
  """List jobs."""
  def __init__(self, job_state):
    # type: (JobState) -> None
    self.job_state = job_state

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    # NOTE: the + and - in the jobs list mean 'current' and 'previous', and are
    # addressed with %+ and %-.

    # [6]   Running                 sleep 5 | sleep 5 &
    # [7]-  Running                 sleep 5 | sleep 5 &
    # [8]+  Running                 sleep 5 | sleep 5 &

    self.job_state.List()
    return 0


class Fg(object):
  """Put a job in the foreground"""
  def __init__(self, job_state, waiter):
    # type: (JobState, Waiter) -> None
    self.job_state = job_state
    self.waiter = waiter

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    # Get job instead of PID, and then do
    #
    # Should we also have job.SendContinueSignal() ?
    # - posix.killpg()
    #
    # job.WaitUntilDone(self.waiter)
    # - waitpid() under the hood

    pid = self.job_state.GetLastStopped()
    if pid is None:
      log('No job to put in the foreground')
      return 1

    # TODO: Print job ID rather than the PID
    log('Continue PID %d', pid)
    posix.kill(pid, signal.SIGCONT)

    job = self.job_state.JobFromPid(pid)
    status = job.Wait(self.waiter)
    #log('status = %d', status)
    return status


class Bg(object):
  """Put a job in the background"""
  def __init__(self, job_state):
    # type: (JobState) -> None
    self.job_state = job_state

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    # How does this differ from 'fg'?  It doesn't wait and it sets controlling
    # terminal?

    raise args.UsageError("isn't implemented")


class _TrapHandler(object):
  """A function that is called by Python's signal module.

  Similar to process.SubProgramThunk."""

  def __init__(self, node, nodes_to_run):
    # type: (command_t, List[command_t]) -> None
    self.node = node
    self.nodes_to_run = nodes_to_run

  def __call__(self, unused_signalnum, unused_frame):
    # type: (int, Any) -> None
    """For Python's signal module."""
    # TODO: set -o xtrace/verbose should enable this.
    #log('*** SETTING TRAP for %d ***', unused_signalnum)
    self.nodes_to_run.append(self.node)

  def __str__(self):
    # type: () -> str
    # Used by trap -p
    # TODO: Abbreviate with fmt.PrettyPrint?
    return '<Trap %s>' % self.node


# TODO: Requires code generation.
def _MakeSignals():
  # type: () -> Dict[str, int]
  """Piggy-back on CPython to get a list of portable signals.

  When Oil is ported to C, we might want to do something like bash/dash.
  """
  names = {}  # type: Dict[str, int]
  for name in dir(signal):
    # don't want SIG_DFL or SIG_IGN
    if name.startswith('SIG') and not name.startswith('SIG_'):
      int_val = getattr(signal, name)
      abbrev = name[3:]
      names[abbrev] = int_val
  return names


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
  return _SIGNAL_NAMES.get(sig_spec)


_SIGNAL_NAMES = _MakeSignals()

_HOOK_NAMES = ('EXIT', 'ERR', 'RETURN', 'DEBUG')


if mylib.PYTHON:
  TRAP_SPEC = arg_def.Register('trap')
  TRAP_SPEC.ShortFlag('-p')
  TRAP_SPEC.ShortFlag('-l')

# TODO:
#
# bash's default -p looks like this:
# trap -- '' SIGTSTP
# trap -- '' SIGTTIN
# trap -- '' SIGTTOU
#
# CPython registers different default handlers.  The C++ rewrite should make
# OVM match sh/bash more closely.

class Trap(object):
  def __init__(self, sig_state, traps, nodes_to_run, parse_ctx, errfmt):
    # type: (SignalState, Dict[str, _TrapHandler], List[command_t], ParseContext, ErrorFormatter) -> None
    self.sig_state = sig_state
    self.traps = traps
    self.nodes_to_run = nodes_to_run
    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena
    self.errfmt = errfmt

  def _ParseTrapCode(self, code_str):
    # type: (str) -> command_t
    """
    Returns:
      A node, or None if the code is invalid.
    """
    line_reader = reader.StringLineReader(code_str, self.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader)

    # TODO: the SPID should be passed through argv
    self.arena.PushSource(source.Trap(runtime.NO_SPID))
    try:
      try:
        node = main_loop.ParseWholeFile(c_parser)
      except error.Parse as e:
        ui.PrettyPrintError(e, self.arena)
        return None

    finally:
      self.arena.PopSource()

    return node

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'trap'
    arg, _ = TRAP_SPEC.Parse(arg_r)

    if arg.p:  # Print registered handlers
      for name, value in self.traps.iteritems():
        # The unit tests rely on this being one line.
        # bash prints a line that can be re-parsed.
        print('%s %s' % (name, value.__class__.__name__))

      return 0

    if arg.l:  # List valid signals and hooks
      ordered = _SIGNAL_NAMES.items()
      ordered.sort(key=lambda x: x[1])

      for name in _HOOK_NAMES:
        print('   %s' % name)
      for name, int_val in ordered:
        print('%2d %s' % (int_val, name))

      return 0

    code_str = arg_r.ReadRequired('requires a code string')
    sig_spec, sig_spid = arg_r.ReadRequired2('requires a signal or hook name')

    # sig_key is NORMALIZED sig_spec: and integer signal number or string hook
    # name.
    sig_key = None
    sig_num = None
    if sig_spec in _HOOK_NAMES:
      sig_key = sig_spec
    elif sig_spec == '0':  # Special case
      sig_key = 'EXIT'
    else:
      sig_num = _GetSignalNumber(sig_spec)
      if sig_num is not None:
        sig_key = sig_num  # TODO: fix dynamic typing here

    if sig_key is None:
      self.errfmt.Print("Invalid signal or hook %r", sig_spec,
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
    node = self._ParseTrapCode(code_str)
    if node is None:
      return 1  # ParseTrapCode() prints an error for us.

    # Register a hook.
    if sig_key in _HOOK_NAMES:
      if sig_key in ('ERR', 'RETURN', 'DEBUG'):
        ui.Stderr("osh warning: The %r hook isn't yet implemented ",
                  sig_spec)
      self.traps[sig_key] = _TrapHandler(node, self.nodes_to_run)
      return 0

    # Register a signal.
    sig_num = _GetSignalNumber(sig_spec)
    if sig_num is not None:
      handler = _TrapHandler(node, self.nodes_to_run)
      # For signal handlers, the traps dictionary is used only for debugging.
      self.traps[sig_key] = handler
      if sig_num in (signal.SIGKILL, signal.SIGSTOP):
        self.errfmt.Print("Signal %r can't be handled", sig_spec,
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


class Umask(_Builtin):

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
        ui.Stderr("osh warning: umask with symbolic input isn't implemented")
        return 1
      else:
        posix.umask(new_mask)
        return 0

    raise args.UsageError('umask: unexpected arguments')
