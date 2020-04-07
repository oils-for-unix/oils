#!/usr/bin/env python2
"""
executor.py
"""
from __future__ import print_function

import sys

#from _devbuild.gen.option_asdl import builtin_i
from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import (value_e, value__Obj, redirect)
from _devbuild.gen.syntax_asdl import (
    command_e, command__Simple, command__Pipeline, command__ControlFlow,
    command_str, Token, compound_word,
)
from asdl import runtime
from core import error
from core import process
from core.util import log, e_die
from frontend import args
from frontend import consts
from oil_lang import objects
from mycpp import mylib
from mycpp.mylib import NewStr

import posix_ as posix

from typing import cast, Dict, List, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.id_kind_asdl import Id_t
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from _devbuild.gen.syntax_asdl import (
    command_t, command__Subshell, command__ShFunction,
  )
  from core import optview
  from core import state
  from core import ui
  from osh.builtin_misc import _Builtin
  from osh import cmd_eval


class ShellExecutor(object):
  """
  This CommandEvaluator is combined with the OSH language evaluators in osh/ to create
  a shell interpreter.
  """
  def __init__(self,
      mem,  # type: state.Mem
      exec_opts,  # type: optview.Exec
      mutable_opts,  # type: state.MutableOpts
      procs,  # type: Dict[str, command__ShFunction]
      builtins,  # type: Dict[int, _Builtin]
      search_path,  # type: state.SearchPath
      ext_prog,  # type: process.ExternalProgram
      waiter,  # type: process.Waiter
      job_state,  # type: process.JobState
      fd_state,  # type: process.FdState
      errfmt  # type: ui.ErrorFormatter
    ):
    # type: (...) -> None
    self.cmd_ev = None  # type: cmd_eval.CommandEvaluator

    self.mem = mem
    self.exec_opts = exec_opts
    # for errexit.SpidIfDisabled.  TODO: try removing it?
    self.mutable_opts = mutable_opts
    self.procs = procs
    self.builtins = builtins
    self.search_path = search_path
    self.ext_prog = ext_prog
    self.waiter = waiter
    # sleep 5 & puts a (PID, job#) entry here.  And then "jobs" displays it.
    self.job_state = job_state
    self.fd_state = fd_state
    self.errfmt = errfmt

  def CheckCircularDeps(self):
    # type: () -> None
    assert self.cmd_ev is not None

  def _MakeProcess(self, node, parent_pipeline=None, inherit_errexit=True):
    # type: (command_t, process.Pipeline, bool) -> process.Process
    """
    Assume we will run the node in another process.  Return a process.
    """
    UP_node = node
    if node.tag_() == command_e.ControlFlow:
      node = cast(command__ControlFlow, UP_node)
      # Pipeline or subshells with control flow are invalid, e.g.:
      # - break | less
      # - continue | less
      # - ( return )
      # NOTE: This could be done at parse time too.
      if node.token.id != Id.ControlFlow_Exit:
        e_die('Invalid control flow %r in pipeline / subshell / background',
              node.token.val, token=node.token)

    # NOTE: If ErrExit(), we could be verbose about subprogram errors?  This
    # only really matters when executing 'exit 42', because the child shell
    # inherits errexit and will be verbose.  Other notes:
    #
    # - We might want errors to fit on a single line so they don't get
    # interleaved.
    # - We could turn the `exit` builtin into a FatalRuntimeError exception and
    # get this check for "free".
    thunk = process.SubProgramThunk(self.cmd_ev, node,
                                    inherit_errexit=inherit_errexit)
    p = process.Process(thunk, self.job_state, parent_pipeline=parent_pipeline)
    return p

  def RunBuiltin(self, builtin_id, cmd_val):
    # type: (int, cmd_value__Argv) -> int
    """Run a builtin.  Also called by the 'builtin' builtin."""

    builtin_func = self.builtins[builtin_id]

    # note: could be second word, like 'builtin read'
    self.errfmt.PushLocation(cmd_val.arg_spids[0])
    try:
      status = builtin_func.Run(cmd_val)
      assert isinstance(status, int)
    except args.UsageError as e:
      arg0 = cmd_val.argv[0]
      # fill in default location.  e.g. osh/state.py raises UsageError without
      # span_id.
      if e.span_id == runtime.NO_SPID:
        e.span_id = self.errfmt.CurrentLocation()
      # e.g. 'type' doesn't accept flag '-x'
      self.errfmt.Print(e.msg, prefix='%r ' % arg0, span_id=e.span_id)
      status = 2  # consistent error code for usage error
    except KeyboardInterrupt:
      if self.exec_opts.interactive():
        print('')  # newline after ^C
        status = 130  # 128 + 2 for SIGINT
      else:
        # Abort a batch script
        raise
    finally:
      # Flush stdout after running ANY builtin.  This is very important!
      # Silence errors like we did from 'echo'.
      try:
        sys.stdout.flush()
      except IOError as e:
        pass

      self.errfmt.PopLocation()

    return status

  def RunSimpleCommand(self, cmd_val, do_fork, call_procs=True):
    # type: (cmd_value__Argv, bool, bool) -> int
    """
    Run builtins, functions, external commands

    Oil and other languages might have different, simpler rules.  No special
    builtins, etc.

    Oil might have OIL_PATH = @( ... ) or something.

    Interpreters might want to define all their own builtins.

    Args:
      procs: whether to look up procs.
    """
    argv = cmd_val.argv
    span_id = cmd_val.arg_spids[0] if cmd_val.arg_spids else runtime.NO_SPID

    # This happens when you write "$@" but have no arguments.
    if len(argv) == 0:
      if self.exec_opts.strict_argv():
        e_die("Command evaluated to an empty argv array", span_id=span_id)
      else:
        return 0  # status 0, or skip it?

    arg0 = argv[0]

    builtin_id = consts.LookupAssignBuiltin(arg0)
    if builtin_id != consts.NO_INDEX:
      # command readonly is disallowed, for technical reasons.  Could relax it
      # later.
      self.errfmt.Print("Can't run assignment builtin recursively",
                        span_id=span_id)
      return 1

    builtin_id = consts.LookupSpecialBuiltin(arg0)
    if builtin_id != consts.NO_INDEX:
      status = self.RunBuiltin(builtin_id, cmd_val)
      # TODO: Enable this and fix spec test failures.
      # Also update _SPECIAL_BUILTINS in osh/builtin.py.
      #if status != 0:
      #  e_die('special builtin failed', status=status)
      return status

    # Builtins like 'true' can be redefined as functions.
    if call_procs:
      # TODO: if shopt -s namespaces, then look up in current namespace FIRST.
      #
      # Then fallback on self.procs, which should be renamed self.procs?
      #
      # honestly there is no real chance of colllision because
      # foo-bar() {} can't be accessed anyway
      # functions can have hyphens, but variables can't

      func_node = self.procs.get(arg0)
      if func_node is not None:
        if (self.exec_opts.strict_errexit() and 
            self.mutable_opts.errexit.SpidIfDisabled() != runtime.NO_SPID):
          # NOTE: This would be checked below, but this gives a better error
          # message.
          e_die("can't disable errexit running a function. "
                "Maybe wrap the function in a process with the at-splice "
                "pattern.", span_id=span_id)

        # NOTE: Functions could call 'exit 42' directly, etc.
        status = self.cmd_ev.RunProc(func_node, argv[1:])
        return status

      # TODO:
      # look up arg0 in global namespace?  And see if the type is value.Obj
      # And it's a proc?
      # isinstance(val.obj, objects.Proc)
      UP_val = self.mem.GetVar(arg0)

      if mylib.PYTHON:  # Not reusing CPython objects
        if UP_val.tag_() == value_e.Obj:
          val = cast(value__Obj, UP_val)
          if isinstance(val.obj, objects.Proc):
            status = self.cmd_ev.RunOilProc(val.obj, argv[1:])
            return status

    builtin_id = consts.LookupNormalBuiltin(arg0)

    if builtin_id != consts.NO_INDEX:
      return self.RunBuiltin(builtin_id, cmd_val)

    environ = self.mem.GetExported()  # Include temporary variables

    if cmd_val.block:
      e_die('Unexpected block passed to external command %r', arg0,
            span_id=cmd_val.block.spids[0])

    # Resolve argv[0] BEFORE forking.
    argv0_path = self.search_path.CachedLookup(arg0)
    if argv0_path is None:
      self.errfmt.Print('%r not found', arg0, span_id=span_id)
      return 127

    # Normal case: ls /
    if do_fork:
      thunk = process.ExternalThunk(self.ext_prog, argv0_path, cmd_val, environ)
      p = process.Process(thunk, self.job_state)
      status = p.Run(self.waiter)
      return status

    # Already forked for pipeline: ls / | wc -l
    # TODO: count subshell?  ( ls / ) vs. ( ls /; ls / )
    self.ext_prog.Exec(argv0_path, cmd_val, environ)  # NEVER RETURNS
    assert False, "This line should never be reached" # makes mypy happy

  def RunBackgroundJob(self, node):
    # type: (command_t) -> int
    """
    for & etc.
    """
    # Special case for pipeline.  There is some evidence here:
    # https://www.gnu.org/software/libc/manual/html_node/Launching-Jobs.html#Launching-Jobs
    #
    #  "You can either make all the processes in the process group be children
    #  of the shell process, or you can make one process in group be the
    #  ancestor of all the other processes in that group. The sample shell
    #  program presented in this chapter uses the first approach because it
    #  makes bookkeeping somewhat simpler."
    UP_node = node

    if UP_node.tag_() == command_e.Pipeline:
      node = cast(command__Pipeline, UP_node)
      pi = process.Pipeline()
      for child in node.children:
        pi.Add(self._MakeProcess(child, parent_pipeline=pi))

      pi.Start(self.waiter)
      last_pid = pi.LastPid()
      self.mem.last_bg_pid = last_pid   # for $!

      job_id = self.job_state.AddJob(pi)  # show in 'jobs' list
      log('[%%%d] Started Pipeline with PID %d', job_id, last_pid)

    else:
      # Problem: to get the 'set -b' behavior of immediate notifications, we
      # have to register SIGCHLD.  But then that introduces race conditions.
      # If we haven't called Register yet, then we won't know who to notify.

      #log('job state %s', self.job_state)
      p = self._MakeProcess(node)
      pid = p.Start()
      self.mem.last_bg_pid = pid  # for $!
      job_id = self.job_state.AddJob(p)  # show in 'jobs' list
      log('[%%%d] Started PID %d', job_id, pid)
    return 0

  def RunPipeline(self, node):
    # type: (command__Pipeline) -> int

    pi = process.Pipeline()

    # First n-1 processes (which is empty when n == 1)
    n = len(node.children)
    for i in xrange(n - 1):
      p = self._MakeProcess(node.children[i], parent_pipeline=pi)
      pi.Add(p)

    # Last piece of code is in THIS PROCESS.  'echo foo | read line; echo $line'
    pi.AddLast((self.cmd_ev, node.children[n-1]))

    pipe_status = pi.Run(self.waiter, self.fd_state)
    self.mem.SetPipeStatus(pipe_status)

    if self.exec_opts.pipefail():
      # The status is that of the last command that is non-zero.
      status = 0
      for st in pipe_status:
        if st != 0:
          status = st
    else:
      status = pipe_status[-1]  # status of last one is pipeline status

    return status

  def RunSubshell(self, node):
    # type: (command__Subshell) -> int

    p = self._MakeProcess(node.child)
    return p.Run(self.waiter)

  def RunCommandSub(self, node):
    # type: (command_t) -> str

    # Hack for weird $(<file) construct
    if node.tag_() == command_e.Simple:
      simple = cast(command__Simple, node)
      # Detect '< file'
      if (len(simple.words) == 0 and
          len(simple.redirects) == 1 and
          simple.redirects[0].op.id == Id.Redir_Less):
        # change it to __cat < file
        tok = Token(Id.Lit_Chars, runtime.NO_SPID, '__cat')
        cat_word = compound_word([tok])
        # MUTATE the command.Simple node.  This will only be done the first
        # time in the parent process.
        simple.words.append(cat_word)

    p = self._MakeProcess(node,
                          inherit_errexit=self.exec_opts.inherit_errexit())

    r, w = posix.pipe()
    p.AddStateChange(process.StdoutToPipe(r, w))
    _ = p.Start()
    #log('Command sub started %d', pid)

    chunks = []  # type: List[str]
    posix.close(w)  # not going to write
    while True:
      byte_str = posix.read(r, 4096)
      if len(byte_str) == 0:
        break
      chunks.append(byte_str)
    posix.close(r)

    status = p.Wait(self.waiter)

    # OSH has the concept of aborting in the middle of a WORD.  We're not
    # waiting until the command is over!
    if self.exec_opts.more_errexit():
      if self.exec_opts.errexit() and status != 0:
        raise error.ErrExit(
            'Command sub exited with status %d (%r)', status,
            NewStr(command_str(node.tag_())))
    else:
      # Set a flag so we check errexit at the same time as bash.  Example:
      #
      # a=$(false)
      # echo foo  # no matter what comes here, the flag is reset
      #
      # Set ONLY until this command node has finished executing.

      # HACK: move this
      self.cmd_ev.check_command_sub_status = True
      self.mem.SetLastStatus(status)

    # Runtime errors test case: # $("echo foo > $@")
    # Why rstrip()?
    # https://unix.stackexchange.com/questions/17747/why-does-shell-command-substitution-gobble-up-a-trailing-newline-char
    return ''.join(chunks).rstrip('\n')

  def RunProcessSub(self, node, op_id):
    # type: (command_t, Id_t) -> str
    """Process sub creates a forks a process connected to a pipe.

    The pipe is typically passed to another process via a /dev/fd/$FD path.

    TODO:

    sane-proc-sub:
    - wait for all the words

    Otherwise, set $!  (mem.last_bg_pid)

    strict-proc-sub:
    - Don't allow it anywhere except SimpleCommand, any redirect, or
    ShAssignment?  And maybe not even assignment?

    Should you put return codes in @PROCESS_SUB_STATUS?  You need two of them.
    """
    p = self._MakeProcess(node)

    r, w = posix.pipe()

    if op_id == Id.Left_ProcSubIn:
      # Example: cat < <(head foo.txt)
      #
      # The head process should write its stdout to a pipe.
      redir = process.StdoutToPipe(r, w) # type: process.ChildStateChange

    elif op_id == Id.Left_ProcSubOut:
      # Example: head foo.txt > >(tac)
      #
      # The tac process should read its stdin from a pipe.
      #
      # NOTE: This appears to hang in bash?  At least when done interactively.
      # It doesn't work at all in osh interactively?
      redir = process.StdinFromPipe(r, w)

    else:
      raise AssertionError()

    p.AddStateChange(redir)

    # Fork, letting the child inherit the pipe file descriptors.
    pid = p.Start()

    # After forking, close the end of the pipe we're not using.
    if op_id == Id.Left_ProcSubIn:
      posix.close(w)
    elif op_id == Id.Left_ProcSubOut:
      posix.close(r)
    else:
      raise AssertionError()

    # NOTE: Like bash, we never actually wait on it!
    # TODO: At least set $! ?

    # Is /dev Linux-specific?
    if op_id == Id.Left_ProcSubIn:
      return '/dev/fd/%d' % r

    elif op_id == Id.Left_ProcSubOut:
      return '/dev/fd/%d' % w

    else:
      raise AssertionError()


  def Time(self):
    # type: () -> None
    pass

  def PushRedirects(self, redirects):
    # type: (List[redirect]) -> bool
    return self.fd_state.Push(redirects, self.waiter)

  def PopRedirects(self):
    # type: () -> None
    self.fd_state.Pop()
