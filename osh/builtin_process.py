#!/usr/bin/env python2
"""
builtin_process.py - Builtins that deal with processes or modify process state.

This is sort of the opposite of builtin_pure.py.
"""
from __future__ import print_function

import signal  # for calculating numbers

from core import ui
from core.util import log
from frontend import args
from osh.builtin import _Register  # TODO: Remove this

import posix_ as posix

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import command_t

WAIT_SPEC = _Register('wait')
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
    self.waiter = waiter
    self.job_state = job_state
    self.mem = mem
    self.errfmt = errfmt

  def __call__(self, cmd_val):
    arg, arg_index = WAIT_SPEC.ParseVec(cmd_val)
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

      # TODO: Wait for pipelines, and handle PIPESTATUS from Pipeline.Wait().
      status = job.Wait(self.waiter)

    return status


class Jobs(object):
  """List jobs."""
  def __init__(self, job_state):
    self.job_state = job_state

  def __call__(self, cmd_val):
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
    self.job_state = job_state
    self.waiter = waiter

  def __call__(self, cmd_val):
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
    self.job_state = job_state

  def __call__(self, cmd_val):
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
    """For Python's signal module."""
    # TODO: set -o xtrace/verbose should enable this.
    #log('*** SETTING TRAP for %d ***', unused_signalnum)
    self.nodes_to_run.append(self.node)

  def __str__(self):
    # Used by trap -p
    # TODO: Abbreviate with fmt.PrettyPrint?
    return '<Trap %s>' % self.node


def _MakeSignals():
  """Piggy-back on CPython to get a list of portable signals.

  When Oil is ported to C, we might want to do something like bash/dash.
  """
  names = {}
  for name in dir(signal):
    # don't want SIG_DFL or SIG_IGN
    if name.startswith('SIG') and not name.startswith('SIG_'):
      int_val = getattr(signal, name)
      abbrev = name[3:]
      names[abbrev] = int_val
  return names


def _GetSignalNumber(sig_spec):
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


TRAP_SPEC = _Register('trap')
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
  def __init__(self, sig_state, traps, nodes_to_run, ex, errfmt):
    self.sig_state = sig_state
    self.traps = traps
    self.nodes_to_run = nodes_to_run
    self.ex = ex  # TODO: ParseTrapCode could be inlined below
    self.errfmt = errfmt

  def __call__(self, cmd_val):
    arg, _ = TRAP_SPEC.ParseVec(cmd_val)

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

    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip argv[0]
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
        sig_key = sig_num

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
    node = self.ex.ParseTrapCode(code_str)
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


def Umask(cmd_val):
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
