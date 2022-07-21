#!/usr/bin/env python2
"""
builtin_process.py - Builtins that deal with processes or modify process state.

This is sort of the opposite of builtin_pure.py.
"""
from __future__ import print_function

import signal  # for calculating numbers

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import (
    cmd_value__Argv,
    wait_status_e, wait_status__Proc, wait_status__Pipeline,
    wait_status__Cancelled,
)
from core import dev
from core import error
from core.pyerror import e_usage
from core import process  # W1_OK, W1_ECHILD
from core import vm
from core.pyerror import log
from frontend import flag_spec
from frontend import typed_args
from mycpp.mylib import tagswitch

import posix_ as posix

from typing import cast, TYPE_CHECKING
if TYPE_CHECKING:
  from core.process import JobState, Waiter
  from core.state import Mem
  from core.ui import ErrorFormatter


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
      # Loop until there is one fewer process running, there's nothing to wait
      # for, or there's a signal
      n = self.job_state.NumRunning()
      if n == 0:
        status = 127
      else:
        target = n - 1
        status = 0
        while self.job_state.NumRunning() > target:
          result = self.waiter.WaitForOne()
          if result == process.W1_OK:
            status = self.waiter.last_status
          elif result == process.W1_ECHILD:
            # nothing to wait for, or interrupted
            status = 127
            break  
          elif result >= 0:  # signal
            status = 128 + result
            break

      return status

    if len(job_ids) == 0:
      #log('*** wait')

      # BUG: If there is a STOPPED process, this will hang forever, because we
      # don't get ECHILD.  Not sure it matters since you can now Ctrl-C it.
      # But how to fix this?

      status = 0
      while self.job_state.NumRunning() != 0:
        result = self.waiter.WaitForOne()
        if result == process.W1_ECHILD:
          # nothing to wait for, or interrupted.  status is 0
          break  
        elif result >= 0:  # signal
          status = 128 + result
          break

      return status

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
          status = 128 + wait_status.sig_num
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

    if arg.l:
      style = process.STYLE_LONG
    elif arg.p:
      style = process.STYLE_PID_ONLY
    else:
      style = process.STYLE_DEFAULT

    self.job_state.DisplayJobs(style)

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
    return self.job_state.WhenContinued(pid, self.waiter)


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


class Fork(vm._Builtin):

  def __init__(self, shell_ex):
    # type: (vm._Executor) -> None
    self.shell_ex = shell_ex

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    _, arg_r = flag_spec.ParseCmdVal('fork', cmd_val, accept_typed_args=True)

    arg, span_id = arg_r.Peek2()
    if arg is not None:
      e_usage('got unexpected argument %r' % arg, span_id=span_id)

    block = typed_args.GetOneBlock(cmd_val.typed_args)
    if block is None:
      e_usage('expected a block')

    return self.shell_ex.RunBackgroundJob(block)


class ForkWait(vm._Builtin):

  def __init__(self, shell_ex):
    # type: (vm._Executor) -> None
    self.shell_ex = shell_ex

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    _, arg_r = flag_spec.ParseCmdVal('forkwait', cmd_val, accept_typed_args=True)
    arg, span_id = arg_r.Peek2()
    if arg is not None:
      e_usage('got unexpected argument %r' % arg, span_id=span_id)

    block = typed_args.GetOneBlock(cmd_val.typed_args)
    if block is None:
      e_usage('expected a block')

    return self.shell_ex.RunSubshell(block)
