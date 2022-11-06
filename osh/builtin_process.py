#!/usr/bin/env python2
"""
builtin_process.py - Builtins that deal with processes or modify process state.

This is sort of the opposite of builtin_pure.py.
"""
from __future__ import print_function

from signal import SIGCONT

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value__Argv
from core import error
from core.pyerror import e_usage
from core import process  # W1_OK, W1_ECHILD
from core import vm
from core.pyerror import log
from frontend import flag_spec
from frontend import typed_args

import posix_ as posix

from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from core.process import JobState, Waiter


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
    posix.kill(pid, SIGCONT)
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
