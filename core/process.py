# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
process.py - Launch processes and manipulate file descriptors.
"""
from __future__ import print_function

import errno
import fcntl
import signal
import sys

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import (
    job_state_e, job_state_t,
    job_status, job_status_t,
    redirect, redirect_arg_e, redirect_arg__Path, redirect_arg__CopyFd,
    redirect_arg__MoveFd, redirect_arg__HereDoc,
    value, value_e, lvalue, scope_e, value__Str,
)
from _devbuild.gen.syntax_asdl import (
    redir_loc, redir_loc_e, redir_loc_t, redir_loc__VarName, redir_loc__Fd,
)
from qsn_ import qsn
from core import util
from core import ui
from core.util import log
from frontend import match
from mycpp.mylib import tagswitch

import posix_ as posix

from typing import List, Tuple, Dict, Any, cast, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from _devbuild.gen.syntax_asdl import command_t
  from core.ui import ErrorFormatter
  from core.util import NullDebugFile
  from core.comp_ui import _IDisplay
  from core import optview
  from osh.cmd_eval import CommandEvaluator
  from core.state import Mem
  from mycpp import mylib


NO_FD = -1

# Minimum file descriptor that the shell can use.  Other descriptors can be
# directly used by user programs, e.g. exec 9>&1
#
# Oil uses 100 because users are allowed TWO digits in frontend/lexer_def.py.
# This is a compromise between bash (unlimited, but requires crazy
# bookkeeping), and dash/zsh (10) and mksh (24)
_SHELL_MIN_FD = 100


def SignalState_AfterForkingChild():
  # type: () -> None
  """Not a member of SignalState since we didn't do dependency injection."""
  # Respond to Ctrl-\ (core dump)
  signal.signal(signal.SIGQUIT, signal.SIG_DFL)

  # Python sets SIGPIPE handler to SIG_IGN by default.  Child processes
  # shouldn't have this.
  # https://docs.python.org/2/library/signal.html
  # See Python/pythonrun.c.
  signal.signal(signal.SIGPIPE, signal.SIG_DFL)

  # Child processes should get Ctrl-Z.
  signal.signal(signal.SIGTSTP, signal.SIG_DFL)


class SignalState(object):
  """All changes to global signal state go through this object."""

  def __init__(self):
    # type: () -> None
    # Before doing anything else, save the original handler that raises
    # KeyboardInterrupt.
    self.orig_sigint_handler = signal.getsignal(signal.SIGINT)

  def InitShell(self):
    # type: () -> None
    """Always called when initializing the shell process."""
    pass

  def InitInteractiveShell(self, display):
    # type: (_IDisplay) -> None
    """Called when initializing an interactive shell."""
    # The shell itself should ignore Ctrl-\.
    signal.signal(signal.SIGQUIT, signal.SIG_IGN)

    # This prevents Ctrl-Z from suspending OSH in interactive mode.
    signal.signal(signal.SIGTSTP, signal.SIG_IGN)

    # Register a callback to receive terminal width changes.
    # NOTE: In line_input.c, we turned off rl_catch_sigwinch.
    signal.signal(signal.SIGWINCH, lambda x, y: display.OnWindowChange())

  def AddUserTrap(self, sig_num, handler):
    # type: (int, Any) -> None
    """For user-defined handlers registered with the 'trap' builtin."""
    signal.signal(sig_num, handler)

  def RemoveUserTrap(self, sig_num):
    # type: (int) -> None
    """For user-defined handlers registered with the 'trap' builtin."""
    # Restore default
    signal.signal(sig_num, signal.SIG_DFL)


class _FdFrame(object):
  def __init__(self):
    # type: () -> None
    self.saved = []  # type: List[Tuple[int, int, bool]]
    self.need_wait = []  # type: List[Tuple[Process, Waiter]]

  def Forget(self):
    # type: () -> None
    """For exec 1>&2."""
    for saved, orig, forget in reversed(self.saved):
      if saved != NO_FD and forget:
        posix.close(saved)

    del self.saved[:]  # like list.clear() in Python 3.3
    del self.need_wait[:]

  def __repr__(self):
    # type: () -> str
    return '<_FdFrame %s>' % self.saved


class FdState(object):
  """This is for the current process, as opposed to child processes.

  For example, you can do 'myfunc > out.txt' without forking.
  """
  def __init__(self, errfmt, job_state, mem=None):
    # type: (ErrorFormatter, JobState, Mem) -> None
    """
    Args:
      errfmt: for errors
      job_state: For keeping track of _HereDocWriterThunk
    """
    self.errfmt = errfmt
    self.job_state = job_state
    self.cur_frame = _FdFrame()  # for the top level
    self.stack = [self.cur_frame]
    self.mem = mem

  def Open(self, path, mode='r'):
    # type: (str, str) -> mylib.LineReader
    """Opens a path for read, but moves it out of the reserved 3-9 fd range.

    Returns:
      A Python file object.  The caller is responsible for Close().

    Raises:
      OSError if the path can't be found.
    """
    if mode == 'r':
      fd_mode = posix.O_RDONLY
    elif mode == 'w':
      fd_mode = posix.O_CREAT | posix.O_RDWR
    else:
      raise AssertionError(mode)

    fd = posix.open(path, fd_mode, 0o666)  # may raise OSError

    # Immediately move it to a new location
    new_fd = fcntl.fcntl(fd, fcntl.F_DUPFD, _SHELL_MIN_FD)
    posix.close(fd)

    # Return a Python file handle
    try:
      f = posix.fdopen(new_fd, mode)  # Might raise IOError
    except IOError as e:
      raise OSError(*e.args)  # Consistently raise OSError
    return f

  def _WriteFdToMem(self, fd_name, fd):
    # type: (str, int) -> None
    if self.mem:
      self.mem.SetVar(lvalue.Named(fd_name), value.Str(str(fd)), scope_e.Dynamic)

  def _ReadFdFromMem(self, fd_name):
    # type: (str) -> int
    val = self.mem.GetVar(fd_name)
    if val.tag_() == value_e.Str:
      try:
        return int(cast(value__Str, val).s)
      except ValueError:
        return NO_FD
    return NO_FD

  def _PushSave(self, fd):
    # type: (int) -> bool
    """Save fd to a new location and remember to restore it later."""
    #log('---- _PushSave %s', fd)
    need_restore = True
    try:
      new_fd = fcntl.fcntl(fd, fcntl.F_DUPFD, _SHELL_MIN_FD)
    except IOError as e:
      # Example program that causes this error: exec 4>&1.  Descriptor 4 isn't
      # open.
      # This seems to be ignored in dash too in savefd()?
      if e.errno == errno.EBADF:
        #log('ERROR fd %d: %s', fd, e)
        need_restore = False
      else:
        raise
    else:
      posix.close(fd)
      fcntl.fcntl(new_fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)

    #util.ShowFdState()
    if need_restore:
      self.cur_frame.saved.append((new_fd, fd, True))
    else:
      # if we got EBADF, we still need to close the original on Pop()
      self._PushClose(fd)
      #pass

    return need_restore

  def _PushDup(self, fd1, loc):
    # type: (int, redir_loc_t) -> int
    """Save fd2 in a higher range, and dup fd1 onto fd2.

    Returns whether F_DUPFD/dup2 succeeded, and the new descriptor.
    """
    UP_loc = loc
    if loc.tag_() == redir_loc_e.VarName:
      fd2_name = cast(redir_loc__VarName, UP_loc).name
      try:
        # F_DUPFD: GREATER than range
        new_fd = fcntl.fcntl(fd1, fcntl.F_DUPFD, _SHELL_MIN_FD)  # type: int
      except IOError as e:
        if e.errno == errno.EBADF:
          self.errfmt.Print('%d: %s', fd1, posix.strerror(e.errno))
          return NO_FD
        else:
          raise  # this redirect failed

      self._WriteFdToMem(fd2_name, new_fd)

    elif loc.tag_() == redir_loc_e.Fd:
      fd2 = cast(redir_loc__Fd, UP_loc).fd

      if fd1 == fd2:
        # The user could have asked for it to be open on descrptor 3, but open()
        # already returned 3, e.g. echo 3>out.txt
        return NO_FD

      need_restore = self._PushSave(fd2)

      #log('==== dup2 %s %s\n' % (fd1, fd2))
      try:
        posix.dup2(fd1, fd2)
      except OSError as e:
        # bash/dash give this error too, e.g. for 'echo hi 1>&3'
        self.errfmt.Print('%d: %s', fd1, posix.strerror(e.errno))

        # Restore and return error
        if need_restore:
          new_fd, fd2, _ = self.cur_frame.saved.pop()
          posix.dup2(new_fd, fd2)
          posix.close(new_fd)

        raise  # this redirect failed

      new_fd = fd2

    else:
      raise AssertionError()

    return new_fd

  def _PushCloseFd(self, loc):
    # type: (redir_loc_t) -> bool
    """For 2>&-"""
    # exec {fd}>&- means close the named descriptor

    UP_loc = loc
    if loc.tag_() == redir_loc_e.VarName:
      fd_name = cast(redir_loc__VarName, UP_loc).name
      fd = self._ReadFdFromMem(fd_name)
      if fd == NO_FD:
        return False

    elif loc.tag_() == redir_loc_e.Fd:
      fd = cast(redir_loc__Fd, UP_loc).fd
      self._PushSave(fd)

    else:
      raise AssertionError()

    return True

  def _PushClose(self, fd):
    # type: (int) -> None
    self.cur_frame.saved.append((NO_FD, fd, False))

  def _PushWait(self, proc, waiter):
    # type: (Process, Waiter) -> None
    self.cur_frame.need_wait.append((proc, waiter))

  def _ApplyRedirect(self, r, waiter):
    # type: (redirect, Waiter) -> None
    arg = r.arg
    UP_arg = arg
    with tagswitch(arg) as case:

      if case(redirect_arg_e.Path):
        arg = cast(redirect_arg__Path, UP_arg)

        if r.op_id in (Id.Redir_Great, Id.Redir_AndGreat):  # >   &>
          # NOTE: This is different than >| because it respects noclobber, but
          # that option is almost never used.  See test/wild.sh.
          mode = posix.O_CREAT | posix.O_WRONLY | posix.O_TRUNC
        elif r.op_id == Id.Redir_Clobber:  # >|
          mode = posix.O_CREAT | posix.O_WRONLY | posix.O_TRUNC
        elif r.op_id in (Id.Redir_DGreat, Id.Redir_AndDGreat):  # >>   &>>
          mode = posix.O_CREAT | posix.O_WRONLY | posix.O_APPEND
        elif r.op_id == Id.Redir_Less:  # <
          mode = posix.O_RDONLY
        elif r.op_id == Id.Redir_LessGreat:  # <>
          mode = posix.O_CREAT | posix.O_RDWR
        else:
          raise NotImplementedError(r.op_id)

        # NOTE: 0666 is affected by umask, all shells use it.
        try:
          open_fd = posix.open(arg.filename, mode, 0o666)
        except OSError as e:
          self.errfmt.Print(
              "Can't open %r: %s", arg.filename, posix.strerror(e.errno),
              span_id=r.op_spid)
          raise  # redirect failed

        new_fd = self._PushDup(open_fd, r.loc)
        if new_fd != NO_FD:
          posix.close(open_fd)

        # Now handle &> and &>> and their variants.  These pairs are the same:
        #
        #   stdout_stderr.py &> out-err.txt
        #   stdout_stderr.py > out-err.txt 2>&1
        #
        #   stdout_stderr.py 3&> out-err.txt
        #   stdout_stderr.py 3> out-err.txt 2>&3
        #
        # Ditto for {fd}> and {fd}&>

        if r.op_id in (Id.Redir_AndGreat, Id.Redir_AndDGreat):
          self._PushDup(new_fd, redir_loc.Fd(2))

      elif case(redirect_arg_e.CopyFd):  # e.g. echo hi 1>&2
        arg = cast(redirect_arg__CopyFd, UP_arg)

        if r.op_id == Id.Redir_GreatAnd:  # 1>&2
          self._PushDup(arg.target_fd, r.loc)

        elif r.op_id == Id.Redir_LessAnd:  # 0<&5
          # The only difference between >& and <& is the default file
          # descriptor argument.
          self._PushDup(arg.target_fd, r.loc)

        else:
          raise NotImplementedError()

      elif case(redirect_arg_e.MoveFd):  # e.g. echo hi 5>&6-
        arg = cast(redirect_arg__MoveFd, UP_arg)
        new_fd = self._PushDup(arg.target_fd, r.loc)
        if new_fd != NO_FD:
          posix.close(arg.target_fd)

          UP_loc = r.loc
          if r.loc.tag_() == redir_loc_e.Fd:
            fd = cast(redir_loc__Fd, UP_loc).fd
          else:
            fd = NO_FD

          self.cur_frame.saved.append((new_fd, fd, False))

      elif case(redirect_arg_e.CloseFd):  # e.g. echo hi 5>&-
        self._PushCloseFd(r.loc)

      elif case(redirect_arg_e.HereDoc):
        arg = cast(redirect_arg__HereDoc, UP_arg)

        # NOTE: Do these descriptors have to be moved out of the range 0-9?
        read_fd, write_fd = posix.pipe()

        self._PushDup(read_fd, r.loc)  # stdin is now the pipe

        # We can't close like we do in the filename case above?  The writer can
        # get a "broken pipe".
        self._PushClose(read_fd)

        thunk = _HereDocWriterThunk(write_fd, arg.body)

        # TODO: Use PIPE_SIZE to save a process in the case of small here docs,
        # which are the common case.  (dash does this.)
        start_process = True
        #start_process = False

        if start_process:
          here_proc = Process(thunk, self.job_state)

          # NOTE: we could close the read pipe here, but it doesn't really
          # matter because we control the code.
          _ = here_proc.Start()
          #log('Started %s as %d', here_proc, pid)
          self._PushWait(here_proc, waiter)

          # Now that we've started the child, close it in the parent.
          posix.close(write_fd)

        else:
          posix.write(write_fd, arg.body)
          posix.close(write_fd)

  def Push(self, redirects, waiter):
    # type: (List[redirect], Waiter) -> bool
    """Apply a group of redirects and remember to undo them."""

    #log('> fd_state.Push %s', redirects)
    new_frame = _FdFrame()
    self.stack.append(new_frame)
    self.cur_frame = new_frame

    for r in redirects:
      #log('apply %s', r)
      self.errfmt.PushLocation(r.op_spid)
      try:
        self._ApplyRedirect(r, waiter)
      except (IOError, OSError) as e:
        return False  # for bad descriptor, etc.
      finally:
        self.errfmt.PopLocation()
    #log('done applying %d redirects', len(redirects))
    return True

  def PushStdinFromPipe(self, r):
    # type: (int) -> bool
    """Save the current stdin and make it come from descriptor 'r'.

    'r' is typically the read-end of a pipe.  For 'lastpipe'/ZSH semantics of

    echo foo | read line; echo $line
    """
    new_frame = _FdFrame()
    self.stack.append(new_frame)
    self.cur_frame = new_frame

    self._PushDup(r, redir_loc.Fd(0))
    return True

  def Pop(self):
    # type: () -> None
    frame = self.stack.pop()
    #log('< Pop %s', frame)
    for saved, orig, _ in reversed(frame.saved):
      if saved == NO_FD:
        #log('Close %d', orig)
        try:
          posix.close(orig)
        except OSError as e:
          log('Error closing descriptor %d: %s', orig, e)
          raise
      else:
        try:
          posix.dup2(saved, orig)
        except OSError as e:
          log('dup2(%d, %d) error: %s', saved, orig, e)
          #log('fd state:')
          #posix.system('ls -l /proc/%s/fd' % posix.getpid())
          raise
        posix.close(saved)
        #log('dup2 %s %s', saved, orig)

    # Wait for here doc processes to finish.
    for proc, waiter in frame.need_wait:
      unused_status = proc.Wait(waiter)

  def MakePermanent(self):
    # type: () -> None
    self.cur_frame.Forget()


class ChildStateChange(object):

  def Apply(self):
    # type: () -> None
    raise NotImplementedError()


class StdinFromPipe(ChildStateChange):
  def __init__(self, pipe_read_fd, w):
    # type: (int, int) -> None
    self.r = pipe_read_fd
    self.w = w

  def __repr__(self):
    # type: () -> str
    return '<StdinFromPipe %d %d>' % (self.r, self.w)

  def Apply(self):
    # type: () -> None
    posix.dup2(self.r, 0)
    posix.close(self.r)  # close after dup

    posix.close(self.w)  # we're reading from the pipe, not writing
    #log('child CLOSE w %d pid=%d', self.w, posix.getpid())


class StdoutToPipe(ChildStateChange):
  def __init__(self, r, pipe_write_fd):
    # type: (int, int) -> None
    self.r = r
    self.w = pipe_write_fd

  def __repr__(self):
    # type: () -> str
    return '<StdoutToPipe %d %d>' % (self.r, self.w)

  def Apply(self):
    # type: () -> None
    posix.dup2(self.w, 1)
    posix.close(self.w)  # close after dup

    posix.close(self.r)  # we're writing to the pipe, not reading
    #log('child CLOSE r %d pid=%d', self.r, posix.getpid())


class ExternalProgram(object):
  def __init__(self,
               hijack_shebang,  # type: str
               fd_state,  # type: FdState
               errfmt,  # type: ErrorFormatter
               debug_f,  # type: NullDebugFile
               ):
    # type: (...) -> None
    """
    Args:
      hijack_shebang: The path of an interpreter to run instead of the one
        specified in the shebang line.  May be empty.
    """
    self.hijack_shebang = hijack_shebang
    self.fd_state = fd_state
    self.errfmt = errfmt
    self.debug_f = debug_f

  def Exec(self, argv0_path, cmd_val, environ):
    # type: (str, cmd_value__Argv, Dict[str, str]) -> None
    """Execute a program and exit this process.

    Called by:
      ls /
      exec ls /
      ( ls / )
    """
    self._Exec(argv0_path, cmd_val.argv, cmd_val.arg_spids[0], environ, True)
    assert False, "This line should never execute" # NO RETURN

  def _Exec(self, argv0_path, argv, argv0_spid, environ, should_retry):
    # type: (str, List[str], int, Dict[str, str], bool) -> None
    if self.hijack_shebang:
      try:
        f = self.fd_state.Open(argv0_path)
      except OSError as e:
        pass
      else:
        try:
          # Test if the shebang looks like a shell.  The file might be binary
          # with no newlines, so read 80 bytes instead of readline().
          line = f.read(80)  # type: ignore  # TODO: fix this
          if match.ShouldHijack(line):
            argv = [self.hijack_shebang, argv0_path] + argv[1:]
            argv0_path = self.hijack_shebang
            self.debug_f.log('Hijacked: %s', argv)
          else:
            #self.debug_f.log('Not hijacking %s (%r)', argv, line)
            pass
        finally:
          f.close()

    # TODO: If there is an error, like the file isn't executable, then we should
    # exit, and the parent will reap it.  Should it capture stderr?

    try:
      posix.execve(argv0_path, argv, environ)
    except OSError as e:
      # Run with /bin/sh when ENOEXEC error (no shebang).  All shells do this.
      if e.errno == errno.ENOEXEC and should_retry:
        new_argv = ['/bin/sh', argv0_path]
        new_argv.extend(argv[1:])
        self._Exec('/bin/sh', new_argv, argv0_spid, environ, False)
        # NO RETURN

      # Would be nice: when the path is relative and ENOENT: print PWD and do
      # spelling correction?

      self.errfmt.Print(
          "Can't execute %r: %s", argv0_path, posix.strerror(e.errno),
          span_id=argv0_spid)

      # POSIX mentions 126 and 127 for two specific errors.  The rest are
      # unspecified.
      #
      # http://pubs.opengroup.org/onlinepubs/9699919799.2016edition/utilities/V3_chap02.html#tag_18_08_02
      if e.errno == errno.EACCES:
        status = 126
      elif e.errno == errno.ENOENT:
        # TODO: most shells print 'command not found', rather than strerror()
        # == "No such file or directory".  That's better because it's at the
        # end of the path search, and we're never searching for a directory.
        status = 127
      else:
        # dash uses 2, but we use that for parse errors.  This seems to be
        # consistent with mksh and zsh.
        status = 127

      sys.exit(status)  # raises SystemExit
    # NO RETURN


class Thunk(object):
  """Abstract base class for things runnable in another process."""

  def Run(self):
    # type: () -> None
    """Returns a status code."""
    raise NotImplementedError()

  def DisplayLine(self):
    # type: () -> str
    """Display for the 'jobs' list."""
    raise NotImplementedError()

  def __str__(self):
    # type: () -> str
    # For debugging
    return self.DisplayLine()


class ExternalThunk(Thunk):
  """An external executable."""

  def __init__(self, ext_prog, argv0_path, cmd_val, environ):
    # type: (ExternalProgram, str, cmd_value__Argv, Dict[str, str]) -> None
    self.ext_prog = ext_prog
    self.argv0_path = argv0_path
    self.cmd_val = cmd_val
    self.environ = environ

  def DisplayLine(self):
    # type: () -> str

    # NOTE: This is the format the Tracer uses.
    # bash displays        sleep $n & (code)
    # but OSH displays     sleep 1 &  (argv array)
    # We could switch the former but I'm not sure it's necessary.
    tmp = [qsn.maybe_shell_encode(a) for a in self.cmd_val.argv]
    return '[process] %s' % ' '.join(tmp)

  def Run(self):
    # type: () -> None
    """
    An ExternalThunk is run in parent for the exec builtin.
    """
    self.ext_prog.Exec(self.argv0_path, self.cmd_val, self.environ)


class SubProgramThunk(Thunk):
  """A subprogram that can be executed in another process."""

  def __init__(self, cmd_ev, node, inherit_errexit=True):
    # type: (CommandEvaluator, command_t, bool) -> None
    self.cmd_ev = cmd_ev
    self.node = node
    self.inherit_errexit = inherit_errexit  # for bash errexit compatibility

  def DisplayLine(self):
    # type: () -> str

    # NOTE: These can be pieces of a pipeline, so they're arbitrary nodes.
    # TODO: We should extract the SPIDS from each node!
    return '[subprog] %s' % self.node.__class__.__name__

  def Run(self):
    # type: () -> None

    # NOTE: may NOT return due to exec().
    if not self.inherit_errexit:
      self.cmd_ev.mutable_opts.errexit.Disable()

    try:
      # optimize to eliminate redundant subshells like ( echo hi ) | wc -l etc.
      self.cmd_ev.ExecuteAndCatch(self.node, optimize=True)
      status = self.cmd_ev.LastStatus()
      # NOTE: We ignore the is_fatal return value.  The user should set -o
      # errexit so failures in subprocesses cause failures in the parent.
    except util.UserExit as e:
      status = e.status

    # Handle errors in a subshell.  These two cases are repeated from main()
    # and the core/completion.py hook.
    except KeyboardInterrupt:
      print()
      status = 130  # 128 + 2
    except (IOError, OSError) as e:
      ui.Stderr('osh I/O error: %s', posix.strerror(e.errno))
      status = 2

    # Raises SystemExit, so we still have time to write a crash dump.
    sys.exit(status)


class _HereDocWriterThunk(Thunk):
  """Write a here doc to one end of a pipe.

  May be be executed in either a child process or the main shell process.
  """
  def __init__(self, w, body_str):
    # type: (int, str) -> None
    self.w = w
    self.body_str = body_str

  def DisplayLine(self):
    # type: () -> str

    # You can hit Ctrl-Z and the here doc writer will be suspended!  Other
    # shells don't have this problem because they use temp files!  That's a bit
    # unfortunate.
    return '[here doc writer]'

  def Run(self):
    # type: () -> None
    """
    do_exit: For small pipelines
    """
    #log('Writing %r', self.body_str)
    posix.write(self.w, self.body_str)
    #log('Wrote %r', self.body_str)
    posix.close(self.w)
    #log('Closed %d', self.w)

    sys.exit(0)  # Could this fail?


class Job(object):
  """Interface for both Process and Pipeline.

  They both can be put in the background and waited on.

  Confusing thing about pipelines in the background: They have TOO MANY NAMES.

  sleep 1 | sleep 2 &

  - The LAST PID is what's printed at the prompt.  This is $!, a PROCESS ID and
    not a JOB ID.
    # https://www.gnu.org/software/bash/manual/html_node/Special-Parameters.html#Special-Parameters
  - The process group leader (setpgid) is the FIRST PID.
  - It's also %1 or %+.  The last job started.
  """

  def __init__(self):
    # type: () -> None
    # Initial state with & or Ctrl-Z is Running.
    self.state = job_state_e.Running

  def State(self):
    # type: () -> job_state_t
    return self.state

  def Send_SIGCONT(self, waiter):
    # type: (Waiter) -> None
    """Resume the job -- for 'fg' and 'bg' builtins.

    We need to know the process group.
    """
    pass

  def JobWait(self, waiter):
    # type: (Waiter) -> job_status_t
    """Wait for this process/pipeline to be stopped or finished."""
    raise NotImplementedError()


class Process(Job):
  """A process to run.

  TODO: Should we make it clear that this is a FOREGROUND process?  A
  background process is wrapped in a "job".  It is unevaluated.

  It provides an API to manipulate file descriptor state in parent and child.
  """
  def __init__(self, thunk, job_state, parent_pipeline=None):
    # type: (Thunk, JobState, Pipeline) -> None
    """
    Args:
      thunk: Thunk instance
      job_state: for process bookkeeping
      parent_pipeline: For updating PIPESTATUS
    """
    Job.__init__(self)
    assert isinstance(thunk, Thunk), thunk
    self.thunk = thunk
    self.job_state = job_state
    self.parent_pipeline = parent_pipeline

    # For pipelines
    self.state_changes = []  # type: List[ChildStateChange]
    self.close_r = -1
    self.close_w = -1

    self.pid = -1
    self.status = -1

  def __repr__(self):
    # type: () -> str
    return '<Process %s>' % self.thunk

  def AddStateChange(self, s):
    # type: (ChildStateChange) -> None
    self.state_changes.append(s)

  def AddPipeToClose(self, r, w):
    # type: (int, int) -> None
    self.close_r = r
    self.close_w = w

  def MaybeClosePipe(self):
    # type: () -> None
    if self.close_r != -1:
      posix.close(self.close_r)
      posix.close(self.close_w)

  def Start(self):
    # type: () -> int
    """Start this process with fork(), handling redirects."""
    # TODO: If OSH were a job control shell, we might need to call some of
    # these here.  They control the distribution of signals, some of which
    # originate from a terminal.  All the processes in a pipeline should be in
    # a single process group.
    #
    # - posix.setpgid()
    # - posix.setpgrp() 
    # - posix.tcsetpgrp()
    #
    # NOTE: posix.setsid() isn't called by the shell; it's should be called by the
    # login program that starts the shell.
    #
    # The whole job control mechanism is complicated and hacky.

    pid = posix.fork()
    if pid < 0:
      # When does this happen?
      raise RuntimeError('Fatal error in posix.fork()')

    elif pid == 0:  # child
      SignalState_AfterForkingChild()

      for st in self.state_changes:
        st.Apply()

      self.thunk.Run()
      # Never returns

    #log('STARTED process %s, pid = %d', self, pid)

    # Class invariant: after the process is started, it stores its PID.
    self.pid = pid
    # Program invariant: We keep track of every child process!
    self.job_state.AddChildProcess(pid, self)

    return pid

  def Wait(self, waiter):
    # type: (Waiter) -> int
    """Wait for this process to finish."""
    while True:
      #log('WAITING')
      if not waiter.WaitForOne():
        break
      if self.state != job_state_e.Running:
        break
    return self.status

  def JobWait(self, waiter):
    # type: (Waiter) -> job_status_t
    exit_code = self.Wait(waiter)
    return job_status.Proc(exit_code)

  def WhenStopped(self):
    # type: () -> None
    self.state = job_state_e.Stopped

  def WhenDone(self, pid, status):
    # type: (int, int) -> None
    """Called by the Waiter when this Process finishes."""

    #log('WhenDone %d %d', pid, status)
    assert pid == self.pid, 'Expected %d, got %d' % (self.pid, pid)
    self.status = status
    self.state = job_state_e.Done
    if self.parent_pipeline:
      self.parent_pipeline.WhenDone(pid, status)

  def Run(self, waiter):
    # type: (Waiter) -> int
    """Run this process synchronously."""
    self.Start()

    # TODO: Can collect garbage here, and record timing stats.  The process
    # will likely take longer than the GC?  Although I guess some processes can
    # only take 1ms, whereas garbage collection can take longer.
    # Maybe you can have a separate GC thread, and only start it after 100ms,
    # and then cancel when done?

    return self.Wait(waiter)


class Pipeline(Job):
  """A pipeline of processes to run.

  Cases we handle:

  foo | bar
  $(foo | bar)
  foo | bar | read v
  """
  def __init__(self):
    # type: () -> None
    Job.__init__(self)
    self.procs = []  # type: List[Process]
    self.pids = []  # type: List[int]  # pids in order
    self.pipe_status = []  # type: List[int]  # status in order
    self.status = -1  # for 'wait' jobs

    # Optional for foregroud
    self.last_thunk = None  # type: Tuple[CommandEvaluator, command_t]
    self.last_pipe = None  # type: Tuple[int, int]

  def __repr__(self):
    # type: () -> str
    return '<Pipeline %s>' % ' '.join(repr(p) for p in self.procs)

  def Add(self, p):
    # type: (Process) -> None
    """Append a process to the pipeline."""
    if len(self.procs) == 0:
      self.procs.append(p)
      return

    r, w = posix.pipe()
    #log('pipe for %s: %d %d', p, r, w)
    prev = self.procs[-1]

    prev.AddStateChange(StdoutToPipe(r, w))  # applied on Start()
    p.AddStateChange(StdinFromPipe(r, w))  # applied on Start()

    p.AddPipeToClose(r, w)  # MaybeClosePipe() on Start()

    self.procs.append(p)

  def AddLast(self, thunk):
    # type: (Tuple[CommandEvaluator, command_t]) -> None
    """Append the last noden to the pipeline.

    This is run in the CURRENT process.  It is OPTIONAL, because pipelines in
    the background are run uniformly.
    """
    self.last_thunk = thunk

    if len(self.procs) == 0:   # No pipe: if ! foo
      return

    r, w = posix.pipe()
    #log('last pipe %d %d', r, w)

    prev = self.procs[-1]
    prev.AddStateChange(StdoutToPipe(r, w))

    self.last_pipe = (r, w)  # So we can connect it to last_thunk

  def Start(self, waiter):
    # type: (Waiter) -> None
    # TODO: pipelines should be put in their own process group with setpgid().
    # I tried 'cat | cat' and Ctrl-C, and it works without this, probably
    # because of SIGPIPE?  I think you will need that for Ctrl-Z, to suspend a
    # whole pipeline.

    for i, proc in enumerate(self.procs):
      pid = proc.Start()
      self.pids.append(pid)
      self.pipe_status.append(-1)  # uninitialized

      # NOTE: This is done in the SHELL PROCESS after every fork() call.
      # It can't be done at the end; otherwise processes will have descriptors
      # from non-adjacent pipes.
      proc.MaybeClosePipe()

    if self.last_thunk:
      self.pipe_status.append(-1)  # for self.last_thunk

  def LastPid(self):
    # type: () -> int
    """For the odd $! variable.

    It would be better if job IDs or PGIDs were used consistently.
    """
    return self.pids[-1]

  def Wait(self, waiter):
    # type: (Waiter) -> List[int]
    """Wait for this pipeline to finish.

    Called by the 'wait' builtin.
    """
    # This is ONLY for background pipelines.  Foreground pipelines use Run(),
    # and must account for lastpipe!
    assert self.procs, "no procs for Wait()"
    while True:
      #log('WAIT pipeline')
      if not waiter.WaitForOne():
        break
      if self.state != job_state_e.Running:
        #log('Pipeline DONE')
        break

    return self.pipe_status

  def JobWait(self, waiter):
    # type: (Waiter) -> job_status_t
    pipe_status = self.Wait(waiter)
    return job_status.Pipeline(pipe_status)

  def Run(self, waiter, fd_state):
    # type: (Waiter, FdState) -> List[int]
    """Run this pipeline synchronously (foreground pipeline).

    Returns:
      pipe_status (list of integers).
    """
    self.Start(waiter)

    # Run our portion IN PARALLEL with other processes.  This may or may not
    # fork:
    # ls | wc -l
    # echo foo | read line  # no need to fork

    cmd_ev, node = self.last_thunk

    #log('thunk %s', self.last_thunk)
    if self.last_pipe is not None:
      r, w = self.last_pipe  # set in AddLast()
      posix.close(w)  # we will not write here
      fd_state.PushStdinFromPipe(r)

      # TODO: determine fork_external here, so we can go BEYOND lastpipe.  Not
      # only do we run builtins in the same process.  External processes will
      # exec() rather than fork/exec().

      try:
        cmd_ev.ExecuteAndCatch(node)
      finally:
        fd_state.Pop()
      # We won't read anymore.  If we don't do this, then 'cat' in 'cat
      # /dev/urandom | sleep 1' will never get SIGPIPE.
      posix.close(r)

    else:
      if self.procs:
        cmd_ev.ExecuteAndCatch(node)  # Background pipeline without last_pipe
      else:
        cmd_ev._Execute(node)  # singleton foreground pipeline, e.g. '! func'

    self.pipe_status[-1] = cmd_ev.LastStatus()
    #log('pipestatus before all have finished = %s', self.pipe_status)

    if self.procs:
      return self.Wait(waiter)
    else:
      return self.pipe_status  # singleton foreground pipeline, e.g. '! func'

  def WhenDone(self, pid, status):
    # type: (int, int) -> None
    """Called by Process.WhenDone. """
    #log('Pipeline WhenDone %d %d', pid, status)
    i = self.pids.index(pid)
    assert i != -1, 'Unexpected PID %d' % pid
    self.pipe_status[i] = status
    if all(status != -1 for status in self.pipe_status):
      # status of pipeline is status of last process
      self.status = self.pipe_status[-1]
      self.state = job_state_e.Done


class JobState(object):
  """Global list of jobs, used by a few builtins."""

  def __init__(self):
    # type: () -> None

    # pid -> Job instance
    # This is for display in 'jobs' builtin and for %+ %1 lookup.
    self.jobs = {}  # type: Dict[int, Job]

    # pid -> Process.  This is for STOP notification.
    self.child_procs = {}  # type: Dict[int, Process]

    self.last_stopped_pid = None  # type: int  # for basic 'fg' implementation
    self.job_id = 1  # Strictly increasing

  # TODO: This isn't a PID.  This is a process group ID?
  #
  # What should the table look like?
  #
  # Do we need the last PID?  I don't know why bash prints that.  Probably so
  # you can do wait $!
  # wait -n waits for any node to go from job_state.Running to job_state.Done?
  #
  # And it needs a flag for CURRENT, for the implicit arg to 'fg'.
  # job_id is just an integer.  This is sort of lame.
  #
  # [job_id, flag, pgid, job_state, node]

  def NotifyStopped(self, pid):
    # type: (int) -> None

    # TODO: Look up the PID.
    # And display it in the table?
    # What if it's not here?
    # We need a table of processes state.
    # Every time we do Process.Start() we need to record it, in case we get a
    # notification that it stopped?  Then we look up what process it was.
    # And we can find what part of the pipeline it's in.

    self.last_stopped_pid = pid

  def GetLastStopped(self):
    # type: () -> int

    # This be GetCurrent()?  %+ in bash?  That's what 'fg' takes.
    return self.last_stopped_pid

  def AddJob(self, job):
    # type: (Job) -> int
    """Add a job to the list, so it can be listed and possibly resumed.

    A job is either a process or pipeline.

    Two cases:
    
    1. async jobs: sleep 5 | sleep 4 &
    2. stopped jobs: sleep 5; then Ctrl-Z
    """
    job_id = self.job_id
    self.jobs[job_id] = job
    self.job_id += 1  # For now, the ID is ever-increasing.
    return job_id

  def AddChildProcess(self, pid, proc):
    # type: (int, Process) -> None
    """Every child process should be added here as soon as we know its PID.

    When the Waiter gets an EXITED or STOPPED notification, we need to know
    about it so 'jobs' can work.
    """
    self.child_procs[pid] = proc

  def JobFromPid(self, pid):
    # type: (int) -> Process
    """For wait $PID.

    There's no way to wait for a pipeline with a PID.  That uses job syntax, e.g. 
    %1.  Not a great interface.
    """
    return self.child_procs.get(pid)

  def List(self):
    # type: () -> None
    """Used by the 'jobs' builtin.

    https://pubs.opengroup.org/onlinepubs/9699919799/utilities/jobs.html

    "By default, the jobs utility shall display the status of all stopped jobs,
    running background jobs and all jobs whose status has changed and have not
    been reported by the shell."
    """
    # NOTE: A job is a background process or pipeline.
    #
    # echo hi | wc -l    -- this starts two processes.  Wait for TWO
    # echo hi | wc -l &   -- this starts a process which starts two processes
    #                        Wait for ONE.
    #
    # bash GROUPS the PIDs by job.  And it has their state and code.

    # $ jobs -l
    # [1]+ 24414 Stopped                 sleep 5
    #      24415                       | sleep 5
    # [2]  24502 Running                 sleep 6
    #      24503                       | sleep 6
    #      24504                       | sleep 5 &
    # [3]- 24508 Running                 sleep 6
    #      24509                       | sleep 6
    #      24510                       | sleep 5 &
    #
    # zsh has VERY similar UI.

    # NOTE: Jobs don't need to show state?  Because pipelines are never stopped
    # -- only the jobs within them are.
    print('Jobs:')
    for pid, job in self.jobs.iteritems():
      # Use the %1 syntax
      print('%%%d %s %s' % (pid, job.State(), job))

    print('')
    print('Processes:')
    for pid, proc in self.child_procs.iteritems():
      print('%d %s %s' % (pid, proc.state, proc.thunk.DisplayLine()))

  def ListRecent(self):
    # type: () -> None
    """For jobs -n, which I think is also used in the interactive prompt."""
    pass

  def NoneAreRunning(self):
    # type: () -> bool
    """Test if all jobs are done.  Used by 'wait' builtin."""
    for job in self.jobs.itervalues():
      if job.State() == job_state_e.Running:
        return False
    return True

  def MaybeRemove(self, pid):
    # type: (int) -> None
    """Process and Pipeline can call this."""
    # Problem: This only happens after an explicit wait()?
    # I think the main_loop in bash waits without blocking?
    log('JobState MaybeRemove %d', pid)

    # TODO: Enabling this causes a failure in spec/background.
    return
    try:
      del self.jobs[pid]
    except KeyError:
      # This should never happen?
      log("AssertionError: PID %d should have never been in the job list", pid)


class Waiter(object):
  """A capability to wait for processes.

  This must be a singleton (and is because CommandEvaluator is a singleton).

  Invariants:
  - Every child process is registered once
  - Every child process is waited for

  Canonical example of why we need a GLOBAL waiter:

  { sleep 3; echo 'done 3'; } &
  { sleep 4; echo 'done 4'; } &

  # ... do arbitrary stuff ...

  { sleep 1; exit 1; } | { sleep 2; exit 2; }

  Now when you do wait() after starting the pipeline, you might get a pipeline
  process OR a background process!  So you have to distinguish between them.
  """
  def __init__(self, job_state, exec_opts):
    # type: (JobState, optview.Exec) -> None
    self.job_state = job_state
    self.exec_opts = exec_opts
    self.last_status = 127  # wait -n error code

  def WaitForOne(self):
    # type: () -> bool
    """Wait until the next process returns (or maybe Ctrl-C).

    Returns:
      True if we got a notification, or False if there was nothing to wait for.

      In the interactive shell, we return True if we get a Ctrl-C, so the
      caller will try again.
    """
    # This is a list of async jobs
    try:
      # -1 makes it like wait(), which waits for any process.
      # NOTE: WUNTRACED is necessary to get stopped jobs.  What about
      # WCONTINUED?
      pid, status = posix.waitpid(-1, posix.WUNTRACED)
    except OSError as e:
      #log('wait() error: %s', e)
      if e.errno == errno.ECHILD:
        return False  # nothing to wait for caller should stop
      else:
        # We should never get here.  EINTR was handled by the 'posix'
        # module.  The only other error is EINVAL, which doesn't apply to
        # this call.
        raise
    except KeyboardInterrupt:
      # NOTE: Another way to handle this is to disable SIGINT when a process is
      # running.  Not sure if there's any real difference.  bash and dash
      # handle SIGINT pretty differently.
      if self.exec_opts.interactive():
        # Caller should keep waiting.  If we run 'sleep 3' and hit Ctrl-C, both
        # processes will get SIGINT, but the shell has to wait again to get the
        # exit code.
        return True
      else:
        raise  # abort a batch script

    #log('WAIT got %s %s', pid, status)

    # All child processes are suppoed to be in this doc.  But this may
    # legitimately happen if a grandchild outlives the child (its parent).
    # Then it is reparented under this process, so we might receive
    # notification of its exit, even though we didn't start it.  We can't have
    # any knowledge of such processes, so print a warning.
    if pid not in self.job_state.child_procs:
      ui.Stderr("osh: PID %d stopped, but osh didn't start it", pid)
      return True  # caller should keep waiting

    proc = self.job_state.child_procs[pid]

    if posix.WIFSIGNALED(status):
      status = 128 + posix.WTERMSIG(status)

      # Print newline after Ctrl-C.
      if posix.WTERMSIG(status) == signal.SIGINT:
        print()

      proc.WhenDone(pid, status)

    elif posix.WIFEXITED(status):
      status = posix.WEXITSTATUS(status)
      #log('exit status: %s', status)
      proc.WhenDone(pid, status)

    elif posix.WIFSTOPPED(status):
      #sig = posix.WSTOPSIG(status)

      # TODO: Do something nicer here.  Implement 'fg' command.
      # Show in jobs list.
      log('')
      log('[PID %d] Stopped', pid)
      self.job_state.NotifyStopped(pid)  # show in 'jobs' list, enable 'fg'
      proc.WhenStopped()

    self.last_status = status  # for wait -n

    return True  # caller should keep waiting
