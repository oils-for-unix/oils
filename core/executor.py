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
    command_sub, compound_word, Token,
)
from asdl import runtime
from core import error
from core import process
from core.pyerror import log, e_die
from core.pyutil import stderr_line
from core import ui
from core import vm
from frontend import consts
from oil_lang import objects
from mycpp import mylib

import posix_ as posix

from typing import cast, Dict, List, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from _devbuild.gen.syntax_asdl import (
    command_t, command__Subshell, command__ShFunction,
  )
  from core import optview
  from core import state
  from core.vm import _Builtin


class _ProcessSubFrame(object):
  def __init__(self):
    # type: () -> None
    self.to_close = []  # type: List[int]  # file descriptors
    self.to_wait = []  # type: List[process.Process]


class ShellExecutor(vm._Executor):
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
    vm._Executor.__init__(self)
    self.mem = mem
    self.exec_opts = exec_opts
    self.mutable_opts = mutable_opts  # for IsDisabled(), not mutating
    self.procs = procs
    self.builtins = builtins
    self.search_path = search_path
    self.ext_prog = ext_prog
    self.waiter = waiter
    # sleep 5 & puts a (PID, job#) entry here.  And then "jobs" displays it.
    self.job_state = job_state
    self.fd_state = fd_state
    self.errfmt = errfmt
    self.process_sub_stack = []  # type: List[_ProcessSubFrame]

  def CheckCircularDeps(self):
    # type: () -> None
    assert self.cmd_ev is not None

  def _MakeProcess(self, node, inherit_errexit=True):
    # type: (command_t, bool) -> process.Process
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
    p = process.Process(thunk, self.job_state)
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
    except error.Usage as e:
      arg0 = cmd_val.argv[0]
      # fill in default location.  e.g. osh/state.py raises UsageError without
      # span_id.
      if e.span_id == runtime.NO_SPID:
        e.span_id = self.errfmt.CurrentLocation()
      # e.g. 'type' doesn't accept flag '-x'
      self.errfmt.PrefixPrint(e.msg, prefix='%r ' % arg0, span_id=e.span_id)
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
    span_id = cmd_val.arg_spids[0] if len(cmd_val.arg_spids) else runtime.NO_SPID

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
      self.errfmt.Print_("Can't run assignment builtin recursively",
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

    # TODO: if shopt -s namespaces, then look up in current namespace FIRST.
    #
    # Then fallback on self.procs, which should be renamed self.procs?
    #
    # honestly there is no real chance of colllision because
    # foo-bar() {} can't be accessed anyway
    # functions can have hyphens, but variables can't

    # Builtins like 'true' can be redefined as functions.
    if call_procs:
      proc_node = self.procs.get(arg0)
      if proc_node is not None:
        if (self.exec_opts.strict_errexit() and 
            self.mutable_opts.ErrExitIsDisabled()):
          self.errfmt.Print_('errexit was disabled for this construct',
                             span_id=self.mutable_opts.ErrExitSpanId())
          stderr_line('')
          e_die("Can't run a proc while errexit is disabled. "
                "Use 'catch' or wrap it in a process with $0 myproc",
                span_id=span_id)

        # NOTE: Functions could call 'exit 42' directly, etc.
        status = self.cmd_ev.RunProc(proc_node, argv[1:])
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
      self.errfmt.Print_('%r not found' % arg0, span_id=span_id)
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
        p = self._MakeProcess(child)
        p.Init_ParentPipeline(pi)
        pi.Add(p)

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
      p = self._MakeProcess(node.children[i])
      p.Init_ParentPipeline(pi)
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

  def RunCommandSub(self, cs_part):
    # type: (command_sub) -> str

    if not self.exec_opts.allow_command_sub():
      # TODO: Add spid of $(
      e_die("Command subs not allowed when errexit disabled (strict_errexit)")

    node = cs_part.child

    # Hack for weird $(<file) construct
    if node.tag_() == command_e.Simple:
      simple = cast(command__Simple, node)
      # Detect '< file'
      if (len(simple.words) == 0 and
          len(simple.redirects) == 1 and
          simple.redirects[0].op.id == Id.Redir_Less):
        # change it to __cat < file
        # note: cmd_eval.py _Dispatch works around lack of spid
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
    if self.exec_opts.command_sub_errexit():
      if status != 0:
        raise error.ErrExit(
            'Command sub exited with status %d (%s)' %
            (status, ui.CommandType(node)), span_id=cs_part.left_token.span_id,
            status=status)

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

  def RunProcessSub(self, cs_part):
    # type: (command_sub) -> str
    """Process sub creates a forks a process connected to a pipe.

    The pipe is typically passed to another process via a /dev/fd/$FD path.

    Life cycle of a process substitution:

    1. Start with this code

      diff <(seq 3) <(seq 4)

    2. To evaluate the command line, we evaluate every word.  The
    NormalWordEvaluator this method, RunProcessSub(), which does 3 things:

      a. Create a pipe(), getting r and w
      b. Starts the seq process, which inherits r and w
         It has a StdoutToPipe() redirect, which means that it dup2(w, 1)
         and close(r)
      c. Close the w FD, because neither the shell or 'diff' will write to it.
         However we must retain 'r', because 'diff' hasn't opened /dev/fd yet!
      d. We evaluate <(seq 3) to /dev/fd/$r, so "diff" can read from it

    3. Now we're done evaluating every word, so we know the command line of
       diff, which looks like

      diff /dev/fd/64 /dev/fd/65

    Those are the FDs for the read ends of the pipes we created.

    4. diff inherits a copy of the read end of bot pipes.  But it actually
    calls open() both files passed as argv.  (I think this is fine.)

    5. wait() for the diff process.

    6. The shell closes both the read ends of both pipes.  Neither us or
    'diffd' will read again.

    7. The shell waits for both 'seq' processes.

    Related:
      shopt -s process_sub_fail
      _process_sub_status
    """
    p = self._MakeProcess(cs_part.child)

    r, w = posix.pipe()
    #log('pipe = %d, %d', r, w)

    op_id = cs_part.left_token.id
    if op_id == Id.Left_ProcSubIn:
      # Example: cat < <(head foo.txt)
      #
      # The head process should write its stdout to a pipe.
      redir = process.StdoutToPipe(r, w)  # type: process.ChildStateChange

    elif op_id == Id.Left_ProcSubOut:
      # Example: head foo.txt > >(tac)
      #
      # The tac process should read its stdin from a pipe.

      # Note: this example sometimes requires you to hit "enter" in bash and
      # zsh.  WHy?
      redir = process.StdinFromPipe(r, w)

    else:
      raise AssertionError()

    p.AddStateChange(redir)

    # Fork, letting the child inherit the pipe file descriptors.
    pid = p.Start()

    ps_frame = self.process_sub_stack[-1]

    # Note: bash never waits() on the process, but zsh does.  The calling
    # program needs to read() before we can wait, e.g.
    #   diff <(sort left.txt) <(sort right.txt)
    ps_frame.to_wait.append(p)

    # After forking, close the end of the pipe we're not using.
    if op_id == Id.Left_ProcSubIn:
      posix.close(w)  # cat < <(head foo.txt)
      ps_frame.to_close.append(r)  # close later
    elif op_id == Id.Left_ProcSubOut:
      posix.close(r)
      #log('Left_ProcSubOut closed %d', r)
      ps_frame.to_close.append(w)  # close later
    else:
      raise AssertionError()

    # Is /dev Linux-specific?
    if op_id == Id.Left_ProcSubIn:
      return '/dev/fd/%d' % r

    elif op_id == Id.Left_ProcSubOut:
      return '/dev/fd/%d' % w

    else:
      raise AssertionError()

  def MaybeWaitOnProcessSubs(self, frame):
    # type: (_ProcessSubFrame) -> List[int]

    # Wait in the same order that they were evaluated.  That seems fine.

    #if self.to_close:
    #  log('to_close %s', self.to_close)
    for fd in frame.to_close:
      #log('close %d', fd)
      posix.close(fd)

    #if self.to_wait:
    #  log('to_wait %s', self.to_wait)

    statuses = []  # type: List[int]
    for p in frame.to_wait:
      #log('waiting for %s', p)
      st = p.Wait(self.waiter)
      statuses.append(st)

    # TODO: Return spid of <( or >( as well.  Thread it into _CheckStatus
    return statuses

  def Time(self):
    # type: () -> None
    pass

  def PushRedirects(self, redirects):
    # type: (List[redirect]) -> bool
    return self.fd_state.Push(redirects, self.waiter)

  def PopRedirects(self):
    # type: () -> None
    self.fd_state.Pop()

  def PushProcessSub(self):
    # type: () -> None
    self.process_sub_stack.append(_ProcessSubFrame())

  def PopProcessSub(self):
    # type: () -> List[int]
    """
    This method is called by a context manager, which means we always wait() on
    the way out, which I think is the right thing.  We don't always set
    _process_sub_status, e.g. if some fatal error occurs first, but we always
    wait.
    """
    frame = self.process_sub_stack.pop()
    st = self.MaybeWaitOnProcessSubs(frame)
    return st
