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

from errno import EACCES, EBADF, ECHILD, EINTR, ENOENT, ENOEXEC
import fcntl as fcntl_
from fcntl import F_DUPFD, F_GETFD, F_SETFD, FD_CLOEXEC
from signal import SIG_DFL, SIGINT, SIGPIPE, SIGQUIT, SIGTSTP, SIGTTOU, SIGTTIN

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import (
    job_state_e, job_state_t, job_state_str,
    wait_status, wait_status_t,
    redirect, redirect_arg_e, redirect_arg__Path, redirect_arg__CopyFd,
    redirect_arg__MoveFd, redirect_arg__HereDoc,
    value, value_e, lvalue, value__Str, trace, trace_t
)
from _devbuild.gen.syntax_asdl import (
    redir_loc, redir_loc_e, redir_loc_t, redir_loc__VarName, redir_loc__Fd,
)
from core import dev
from core import pyutil
from core import pyos
from core import state
from core import ui
from core import util
from core.pyerror import log, e_die
from frontend import match
from osh import cmd_eval
from qsn_ import qsn
from mycpp import mylib
from mycpp.mylib import print_stderr, tagswitch, iteritems, StrFromC

import posix_ as posix
from posix_ import (
    # translated by mycpp and directly called!  No wrapper!
    WIFSIGNALED, WIFEXITED, WIFSTOPPED,
    WEXITSTATUS, WTERMSIG,
    O_APPEND, O_CREAT, O_RDONLY, O_RDWR, O_WRONLY, O_TRUNC,
)

from typing import List, Tuple, Dict, Optional, Any, cast, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from _devbuild.gen.syntax_asdl import command_t
  from core import optview
  from core.state import Mem
  from core.ui import ErrorFormatter
  from core.util import _DebugFile
  from osh.cmd_eval import CommandEvaluator
  from osh import builtin_trap


NO_FD = -1

# Minimum file descriptor that the shell can use.  Other descriptors can be
# directly used by user programs, e.g. exec 9>&1
#
# Oil uses 100 because users are allowed TWO digits in frontend/lexer_def.py.
# This is a compromise between bash (unlimited, but requires crazy
# bookkeeping), and dash/zsh (10) and mksh (24)
_SHELL_MIN_FD = 100

# Style for 'jobs' builtin
STYLE_DEFAULT = 0
STYLE_LONG = 1
STYLE_PID_ONLY = 2


def SaveFd(fd):
  # type: (int) -> int
  saved = fcntl_.fcntl(fd, F_DUPFD, _SHELL_MIN_FD)  # type: int
  return saved


class _RedirFrame(object):
  def __init__(self, saved_fd, orig_fd, forget):
    # type: (int, int, bool) -> None
    self.saved_fd = saved_fd
    self.orig_fd = orig_fd
    self.forget = forget


class _FdFrame(object):
  def __init__(self):
    # type: () -> None
    self.saved = []  # type: List[_RedirFrame]
    self.need_wait = []  # type: List[Process]

  def Forget(self):
    # type: () -> None
    """For exec 1>&2."""
    for rf in reversed(self.saved):
      if rf.saved_fd != NO_FD and rf.forget:
        posix.close(rf.saved_fd)

    del self.saved[:]  # like list.clear() in Python 3.3
    del self.need_wait[:]

  def __repr__(self):
    # type: () -> str
    return '<_FdFrame %s>' % self.saved


class FdState(object):
  """File descriptor state for the current process.
  
  For example, you can do 'myfunc > out.txt' without forking.  Child processes
  inherit our state.
  """
  def __init__(self, errfmt, job_state, mem, tracer, waiter):
    # type: (ErrorFormatter, JobState, Mem, Optional[dev.Tracer], Optional[Waiter]) -> None
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
    self.tracer = tracer
    self.waiter = waiter

  def Open(self, path):
    # type: (str) -> mylib.LineReader
    """Opens a path for read, but moves it out of the reserved 3-9 fd range.

    Returns:
      A Python file object.  The caller is responsible for Close().

    Raises:
      IOError or OSError if the path can't be found.  (This is Python-induced wart)
    """
    fd_mode = O_RDONLY
    return self._Open(path, 'r', fd_mode)

  # used for util.DebugFile
  def OpenForWrite(self, path):
    # type: (str) -> mylib.Writer
    fd_mode = O_CREAT | O_RDWR
    f = self._Open(path, 'w', fd_mode)
    # Hack to change mylib.LineReader into mylib.Writer.  In reality the file
    # object supports both interfaces.
    return cast('mylib.Writer', f)

  def _Open(self, path, c_mode, fd_mode):
    # type: (str, str, int) -> mylib.LineReader
    fd = posix.open(path, fd_mode, 0o666)  # may raise OSError

    # Immediately move it to a new location
    new_fd = SaveFd(fd)
    posix.close(fd)

    # Return a Python file handle
    f = posix.fdopen(new_fd, c_mode)  # may raise IOError
    return f

  def _WriteFdToMem(self, fd_name, fd):
    # type: (str, int) -> None
    if self.mem:
      # setvar, not setref
      state.OshLanguageSetValue(self.mem, lvalue.Named(fd_name), value.Str(str(fd)))

  def _ReadFdFromMem(self, fd_name):
    # type: (str) -> int
    val = self.mem.GetValue(fd_name)
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
    ok = True
    try:
      new_fd = SaveFd(fd)
    except IOError as e:
      ok = False
      # Example program that causes this error: exec 4>&1.  Descriptor 4 isn't
      # open.
      # This seems to be ignored in dash too in savefd()?
      if e.errno != EBADF:
        raise
    if ok:
      posix.close(fd)
      fcntl_.fcntl(new_fd, F_SETFD, FD_CLOEXEC)
      self.cur_frame.saved.append(_RedirFrame(new_fd, fd, True))
    else:
      # if we got EBADF, we still need to close the original on Pop()
      self._PushClose(fd)

    return ok

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
        new_fd = fcntl_.fcntl(fd1, F_DUPFD, _SHELL_MIN_FD)  # type: int
      except IOError as e:
        if e.errno == EBADF:
          self.errfmt.Print_('%d: %s' % (fd1, pyutil.strerror(e)))
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

      # Check the validity of fd1 before _PushSave(fd2)
      try:
        fcntl_.fcntl(fd1, F_GETFD)
      except IOError as e:
        self.errfmt.Print_('%d: %s' % (fd1, pyutil.strerror(e)))
        raise

      need_restore = self._PushSave(fd2)

      #log('==== dup2 %s %s\n' % (fd1, fd2))
      try:
        posix.dup2(fd1, fd2)
      except OSError as e:
        # bash/dash give this error too, e.g. for 'echo hi 1>&3'
        self.errfmt.Print_('%d: %s' % (fd1, pyutil.strerror(e)))

        # Restore and return error
        if need_restore:
          rf = self.cur_frame.saved.pop()
          posix.dup2(rf.saved_fd, rf.orig_fd)
          posix.close(rf.saved_fd)

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

    else:
      raise AssertionError()

    self._PushSave(fd)

    return True

  def _PushClose(self, fd):
    # type: (int) -> None
    self.cur_frame.saved.append(_RedirFrame(NO_FD, fd, False))

  def _PushWait(self, proc):
    # type: (Process) -> None
    self.cur_frame.need_wait.append(proc)

  def _ApplyRedirect(self, r):
    # type: (redirect) -> None
    arg = r.arg
    UP_arg = arg
    with tagswitch(arg) as case:

      if case(redirect_arg_e.Path):
        arg = cast(redirect_arg__Path, UP_arg)

        if r.op_id in (Id.Redir_Great, Id.Redir_AndGreat):  # >   &>
          # NOTE: This is different than >| because it respects noclobber, but
          # that option is almost never used.  See test/wild.sh.
          mode = O_CREAT | O_WRONLY | O_TRUNC
        elif r.op_id == Id.Redir_Clobber:  # >|
          mode = O_CREAT | O_WRONLY | O_TRUNC
        elif r.op_id in (Id.Redir_DGreat, Id.Redir_AndDGreat):  # >>   &>>
          mode = O_CREAT | O_WRONLY | O_APPEND
        elif r.op_id == Id.Redir_Less:  # <
          mode = O_RDONLY
        elif r.op_id == Id.Redir_LessGreat:  # <>
          mode = O_CREAT | O_RDWR
        else:
          raise NotImplementedError(r.op_id)

        # NOTE: 0666 is affected by umask, all shells use it.
        try:
          open_fd = posix.open(arg.filename, mode, 0o666)
        except OSError as e:
          self.errfmt.Print_(
              "Can't open %r: %s" % (arg.filename, pyutil.strerror(e)),
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

          self.cur_frame.saved.append(_RedirFrame(new_fd, fd, False))

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
          here_proc = Process(thunk, self.job_state, self.tracer)

          # NOTE: we could close the read pipe here, but it doesn't really
          # matter because we control the code.
          here_proc.Start(trace.HereDoc())
          #log('Started %s as %d', here_proc, pid)
          self._PushWait(here_proc)

          # Now that we've started the child, close it in the parent.
          posix.close(write_fd)

        else:
          posix.write(write_fd, arg.body)
          posix.close(write_fd)

  def Push(self, redirects):
    # type: (List[redirect]) -> bool
    """Apply a group of redirects and remember to undo them."""

    #log('> fd_state.Push %s', redirects)
    new_frame = _FdFrame()
    self.stack.append(new_frame)
    self.cur_frame = new_frame

    for r in redirects:
      #log('apply %s', r)
      with ui.ctx_Location(self.errfmt, r.op_spid):
        try:
          self._ApplyRedirect(r)
        except (IOError, OSError) as e:
          self.Pop()
          return False  # for bad descriptor, etc.
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
    for rf in reversed(frame.saved):
      if rf.saved_fd == NO_FD:
        #log('Close %d', orig)
        try:
          posix.close(rf.orig_fd)
        except OSError as e:
          log('Error closing descriptor %d: %s', rf.orig_fd, pyutil.strerror(e))
          raise
      else:
        try:
          posix.dup2(rf.saved_fd, rf.orig_fd)
        except OSError as e:
          log('dup2(%d, %d) error: %s', rf.saved_fd, rf.orig_fd, pyutil.strerror(e))
          #log('fd state:')
          #posix.system('ls -l /proc/%s/fd' % posix.getpid())
          raise
        posix.close(rf.saved_fd)
        #log('dup2 %s %s', saved, orig)

    # Wait for here doc processes to finish.
    for proc in frame.need_wait:
      unused_status = proc.Wait(self.waiter)

  def MakePermanent(self):
    # type: () -> None
    self.cur_frame.Forget()


class ChildStateChange(object):
  def __init__(self):
    # type: () -> None
    """Empty constructor for mycpp."""
    pass

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
  """The capability to execute an external program like 'ls'. """

  def __init__(self,
               hijack_shebang,  # type: str
               fd_state,  # type: FdState
               errfmt,  # type: ErrorFormatter
               debug_f,  # type: _DebugFile
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
    if len(self.hijack_shebang):
      ok = True
      try:
        f = self.fd_state.Open(argv0_path)
      except (IOError, OSError) as e:
        ok = False
      if ok:
        try:
          # Test if the shebang looks like a shell.  TODO: The file might be
          # binary with no newlines, so read 80 bytes instead of readline().

          #line = f.read(80)  # type: ignore  # TODO: fix this
          line = f.readline()

          if match.ShouldHijack(line):
            h_argv = [self.hijack_shebang, argv0_path]
            h_argv.extend(argv[1:])
            argv = h_argv
            argv0_path = self.hijack_shebang
            self.debug_f.log('Hijacked: %s', argv0_path)
          else:
            #self.debug_f.log('Not hijacking %s (%r)', argv, line)
            pass
        finally:  # TODO: use context manager
          f.close()

    try:
      posix.execve(argv0_path, argv, environ)
    except OSError as e:
      # Run with /bin/sh when ENOEXEC error (no shebang).  All shells do this.
      if e.errno == ENOEXEC and should_retry:
        new_argv = ['/bin/sh', argv0_path]
        new_argv.extend(argv[1:])
        self._Exec('/bin/sh', new_argv, argv0_spid, environ, False)
        # NO RETURN

      # Would be nice: when the path is relative and ENOENT: print PWD and do
      # spelling correction?

      self.errfmt.Print_(
          "Can't execute %r: %s" % (argv0_path, pyutil.strerror(e)),
          span_id=argv0_spid)

      # POSIX mentions 126 and 127 for two specific errors.  The rest are
      # unspecified.
      #
      # http://pubs.opengroup.org/onlinepubs/9699919799.2016edition/utilities/V3_chap02.html#tag_18_08_02
      if e.errno == EACCES:
        status = 126
      elif e.errno == ENOENT:
        # TODO: most shells print 'command not found', rather than strerror()
        # == "No such file or directory".  That's better because it's at the
        # end of the path search, and we're never searching for a directory.
        status = 127
      else:
        # dash uses 2, but we use that for parse errors.  This seems to be
        # consistent with mksh and zsh.
        status = 127

      posix._exit(status)
    # NO RETURN


class Thunk(object):
  """Abstract base class for things runnable in another process."""

  def __init__(self):
    # type: () -> None
    """Empty constructor for mycpp."""
    pass

  def Run(self):
    # type: () -> None
    """Returns a status code."""
    raise NotImplementedError()

  def UserString(self):
    # type: () -> str
    """Display for the 'jobs' list."""
    raise NotImplementedError()

  def __repr__(self):
    # type: () -> str
    return self.UserString()


class ExternalThunk(Thunk):
  """An external executable."""

  def __init__(self, ext_prog, argv0_path, cmd_val, environ):
    # type: (ExternalProgram, str, cmd_value__Argv, Dict[str, str]) -> None
    self.ext_prog = ext_prog
    self.argv0_path = argv0_path
    self.cmd_val = cmd_val
    self.environ = environ

  def UserString(self):
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

  def UserString(self):
    # type: () -> str

    # NOTE: These can be pieces of a pipeline, so they're arbitrary nodes.
    # TODO: Extract SPIDS from node to display source?  Note that
    #   CompoundStatus also has locations of each pipeline component; see
    #   Executor.RunPipeline()
    thunk_str = ui.CommandType(self.node)
    return '[subprog] %s' % thunk_str

  def Run(self):
    # type: () -> None

    #self.errfmt.OneLineErrExit()  # don't quote code in child processes

    # NOTE: may NOT return due to exec().
    if not self.inherit_errexit:
      self.cmd_ev.mutable_opts.DisableErrExit()
    try:
      # optimize to eliminate redundant subshells like ( echo hi ) | wc -l etc.
      self.cmd_ev.ExecuteAndCatch(self.node, cmd_flags=cmd_eval.Optimize)
      status = self.cmd_ev.LastStatus()
      # NOTE: We ignore the is_fatal return value.  The user should set -o
      # errexit so failures in subprocesses cause failures in the parent.
    except util.UserExit as e:
      status = e.status

    # Handle errors in a subshell.  These two cases are repeated from main()
    # and the core/completion.py hook.
    except KeyboardInterrupt:
      print('')
      status = 130  # 128 + 2
    except (IOError, OSError) as e:
      print_stderr('osh I/O error: %s' % pyutil.strerror(e))
      status = 2

    # If ProcessInit() doesn't turn off buffering, this is needed before
    # _exit()
    pyos.FlushStdout()

    # We do NOT want to raise SystemExit here.  Otherwise dev.Tracer::Pop()
    # gets called in BOTH processes.
    # The crash dump seems to be unaffected.
    posix._exit(status)


class _HereDocWriterThunk(Thunk):
  """Write a here doc to one end of a pipe.

  May be be executed in either a child process or the main shell process.
  """
  def __init__(self, w, body_str):
    # type: (int, str) -> None
    self.w = w
    self.body_str = body_str

  def UserString(self):
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

    posix._exit(0)


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

  def DisplayJob(self, job_id, f, style):
    # type: (int, mylib.Writer, int) -> None
    raise NotImplementedError()

  def State(self):
    # type: () -> job_state_t
    return self.state

  def JobWait(self, waiter):
    # type: (Waiter) -> wait_status_t
    """Wait for this process/pipeline to be stopped or finished."""
    raise NotImplementedError()


class Process(Job):
  """A process to run.

  TODO: Should we make it clear that this is a FOREGROUND process?  A
  background process is wrapped in a "job".  It is unevaluated.

  It provides an API to manipulate file descriptor state in parent and child.
  """
  def __init__(self, thunk, job_state, tracer):
    # type: (Thunk, JobState, dev.Tracer) -> None
    """
    Args:
      thunk: Thunk instance
      job_state: for process bookkeeping
    """
    Job.__init__(self)
    assert isinstance(thunk, Thunk), thunk
    self.thunk = thunk
    self.job_state = job_state
    self.tracer = tracer

    # For pipelines
    self.parent_pipeline = None  # type: Pipeline
    self.state_changes = []  # type: List[ChildStateChange]
    self.close_r = -1
    self.close_w = -1

    self.pid = -1
    self.status = -1

  def Init_ParentPipeline(self, pi):
    # type: (Pipeline) -> None
    """For updating PIPESTATUS."""
    self.parent_pipeline = pi

  def __repr__(self):
    # type: () -> str

    # note: be wary of infinite mutual recursion
    #s = ' %s' % self.parent_pipeline if self.parent_pipeline else ''
    #return '<Process %s%s>' % (self.thunk, s)
    return '<Process %s %s>' % (_JobStateStr(self.state), self.thunk)

  def DisplayJob(self, job_id, f, style):
    # type: (int, mylib.Writer, int) -> None
    if job_id == -1:
      job_id_str = '  '
    else:
      job_id_str = '%%%d' % job_id
    if style == STYLE_PID_ONLY:
      f.write('%d\n' % self.pid)
    else:
      f.write('%s %d %7s ' % (job_id_str, self.pid, _JobStateStr(self.state)))
      f.write(self.thunk.UserString())
      f.write('\n')

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

  def Start(self, why):
    # type: (trace_t) -> int
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
      e_die('Fatal error in posix.fork()')

    elif pid == 0:  # child
      # Note: this happens in BOTH interactive and non-interactive shells.
      # We technically don't need to do most of it in non-interactive, since we
      # did not change state in InitInteractiveShell().

      # Python sets SIGPIPE handler to SIG_IGN by default.  Child processes
      # shouldn't have this.
      # https://docs.python.org/2/library/signal.html
      # See Python/pythonrun.c.
      pyos.Sigaction(SIGPIPE, SIG_DFL)

      # Respond to Ctrl-\ (core dump)
      pyos.Sigaction(SIGQUIT, SIG_DFL)

      # Child processes should get Ctrl-Z.
      pyos.Sigaction(SIGTSTP, SIG_DFL)

      # More signals from
      # https://www.gnu.org/software/libc/manual/html_node/Launching-Jobs.html
      # (but not SIGCHLD)
      pyos.Sigaction(SIGTTOU, SIG_DFL)
      pyos.Sigaction(SIGTTIN, SIG_DFL)

      for st in self.state_changes:
        st.Apply()

      self.tracer.SetProcess(posix.getpid())
      self.thunk.Run()
      # Never returns

    #log('STARTED process %s, pid = %d', self, pid)
    self.tracer.OnProcessStart(pid, why)

    # Class invariant: after the process is started, it stores its PID.
    self.pid = pid
    # Program invariant: We keep track of every child process!
    self.job_state.AddChildProcess(pid, self)

    return pid

  def Wait(self, waiter):
    # type: (Waiter) -> int
    """Wait for this process to finish."""
    while self.state == job_state_e.Running:
      # signals are ignored
      if waiter.WaitForOne() == W1_ECHILD:
        break

    return self.status

  def JobWait(self, waiter):
    # type: (Waiter) -> wait_status_t
    # wait builtin can be interrupted
    while self.state == job_state_e.Running:
      result = waiter.WaitForOne()

      if result >= 0:  # signal
        return wait_status.Cancelled(result)

      if result == W1_ECHILD:
        break

    return wait_status.Proc(self.status)

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

  def RunWait(self, waiter, why):
    # type: (Waiter, trace_t) -> int
    """Run this process synchronously."""
    self.Start(why)
    return self.Wait(waiter)


class ctx_Pipe(object):

  def __init__(self, fd_state, fd):
    # type: (FdState, int) -> None
    fd_state.PushStdinFromPipe(fd)
    self.fd_state = fd_state

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.fd_state.Pop()


class Pipeline(Job):
  """A pipeline of processes to run.

  Cases we handle:

  foo | bar
  $(foo | bar)
  foo | bar | read v
  """
  def __init__(self, sigpipe_status_ok):
    # type: (bool) -> None
    Job.__init__(self)
    self.procs = []  # type: List[Process]
    self.pids = []  # type: List[int]  # pids in order
    self.pipe_status = []  # type: List[int]  # status in order
    self.status = -1  # for 'wait' jobs

    # Optional for foreground
    self.last_thunk = None  # type: Tuple[CommandEvaluator, command_t]
    self.last_pipe = None  # type: Tuple[int, int]

    self.sigpipe_status_ok = sigpipe_status_ok

  def DisplayJob(self, job_id, f, style):
    # type: (int, mylib.Writer, int) -> None
    if style == STYLE_PID_ONLY:
      f.write('%d\n' % self.procs[0].pid)
    else:
      # Note: this is STYLE_LONG.
      for i, proc in enumerate(self.procs):
        if i == 0:  # show job ID for first element in pipeline
          job_id_str = '%%%d' % job_id
        else:
          job_id_str = '  '  # 2 spaces

          f.write('%s %d %7s ' % (job_id_str, proc.pid, _JobStateStr(proc.state)))
          f.write(proc.thunk.UserString())
          f.write('\n')

  def DebugPrint(self):
    # type: () -> None
    print('Pipeline in state %s' % _JobStateStr(self.state))
    if mylib.PYTHON:  # %s for Process not allowed in C++
      for proc in self.procs:
        print('  proc %s' % proc)
      _, last_node = self.last_thunk
      print('  last %s' % last_node)
      print('  pipe_status %s' % self.pipe_status)

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
      pid = proc.Start(trace.PipelinePart())
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
    """Wait for this pipeline to finish."""

    assert self.procs, "no procs for Wait()"
    # waitpid(-1) zero or more times
    while self.state == job_state_e.Running:
      # signals are ignored
      if waiter.WaitForOne() == W1_ECHILD:
        break

    return self.pipe_status

  def JobWait(self, waiter):
    # type: (Waiter) -> wait_status_t
    """Called by 'wait' builtin, e.g. 'wait %1'
    """
    # wait builtin can be interrupted
    assert self.procs, "no procs for Wait()"
    while self.state == job_state_e.Running:
      result = waiter.WaitForOne()

      if result >= 0:  # signal
        return wait_status.Cancelled(result)

      if result == W1_ECHILD:
        break

    return wait_status.Pipeline(self.pipe_status)

  def Run(self, waiter, fd_state):
    # type: (Waiter, FdState) -> List[int]
    """Run this pipeline synchronously (foreground pipeline).

    Returns:
      pipe_status (list of integers).
    """
    self.Start(waiter)

    # Run the last part of the pipeline IN PARALLEL with other processes.  It
    # may or may not fork:
    #   echo foo | read line  # no fork, the builtin runs in THIS shell process
    #   ls | wc -l            # fork for 'wc'

    cmd_ev, last_node = self.last_thunk

    #log('thunk %s', self.last_thunk)
    if self.last_pipe is not None:
      r, w = self.last_pipe  # set in AddLast()
      posix.close(w)  # we will not write here

      with ctx_Pipe(fd_state, r):
        cmd_ev.ExecuteAndCatch(last_node)

      # We won't read anymore.  If we don't do this, then 'cat' in 'cat
      # /dev/urandom | sleep 1' will never get SIGPIPE.
      posix.close(r)

    else:
      if len(self.procs):
        cmd_ev.ExecuteAndCatch(last_node)  # Background pipeline without last_pipe
      else:
        cmd_ev._Execute(last_node)  # singleton foreground pipeline, e.g. '! func'

    self.pipe_status[-1] = cmd_ev.LastStatus()
    if self.AllDone():
      self.state = job_state_e.Done

    #log('pipestatus before all have finished = %s', self.pipe_status)

    if len(self.procs):
      return self.Wait(waiter)
    else:
      return self.pipe_status  # singleton foreground pipeline, e.g. '! func'

  def AllDone(self):
    # type: () -> bool

    # mycpp rewrite: all(status != -1 for status in self.pipe_status)
    for status in self.pipe_status:
      if status == -1:
        return False
    return True

  def WhenDone(self, pid, status):
    # type: (int, int) -> None
    """Called by Process.WhenDone. """
    #log('Pipeline WhenDone %d %d', pid, status)
    i = self.pids.index(pid)
    assert i != -1, 'Unexpected PID %d' % pid

    if status == 141 and self.sigpipe_status_ok:
      status = 0

    self.pipe_status[i] = status
    if self.AllDone():
      # status of pipeline is status of last process
      self.status = self.pipe_status[-1]
      self.state = job_state_e.Done


def _JobStateStr(i):
  # type: (job_state_t) -> str
  return StrFromC(job_state_str(i))[10:]  # remove 'job_state.'


class JobState(object):
  """Global list of jobs, used by a few builtins."""

  def __init__(self):
    # type: () -> None

    # pid -> Job instance
    # ERROR: This implication is incorrect, jobs are numbered from 1, 2, ... in the dict! 
    # This is for display in 'jobs' builtin and for %+ %1 lookup.
    self.jobs = {}  # type: Dict[int, Job]

    # pid -> Process.  This is for STOP notification.
    self.child_procs = {}  # type: Dict[int, Process]
    self.debug_pipelines = []  # type: List[Pipeline]

    self.last_stopped_pid = -1  # type: int  # for basic 'fg' implementation
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

  def WhenStopped(self, pid):
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

  def WhenContinued(self, pid, waiter):
    # type: (int, Waiter) -> int
    if pid == self.last_stopped_pid:
        self.last_stopped_pid = -1
    job = self.JobFromPid(pid)
    # needed for Wait() loop to work
    job.state = job_state_e.Running
    return job.Wait(waiter)

  def WhenDone(self, pid):
    # type: (int) -> None
    """Process and Pipeline can call this."""
    # Problem: This only happens after an explicit wait().
    # I think the main_loop in bash waits without blocking?
    if pid == self.last_stopped_pid:
      self.last_stopped_pid = -1

    mylib.dict_erase(self.jobs, pid)

  def AddJob(self, job):
    # type: (Job) -> int
    """Add a background job to the list.

    A job is either a Process or Pipeline.  You can resume a job with 'fg',
    kill it with 'kill', etc.

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

  def AddPipeline(self, pi):
    # type: (Pipeline) -> None
    """For debugging only."""
    if mylib.PYTHON:
      self.debug_pipelines.append(pi)

  def JobFromPid(self, pid):
    # type: (int) -> Process
    """For wait $PID.

    There's no way to wait for a pipeline with a PID.  That uses job syntax, e.g. 
    %1.  Not a great interface.
    """
    return self.child_procs.get(pid)

  def DisplayJobs(self, style):
    # type: (int) -> None
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
    # 'jobs -l' GROUPS the PIDs by job.  It has the job number, + - indicators
    # for %% and %-, PID, status, and "command".
    #
    # Every component of a pipeline is on the same line with 'jobs', but
    # they're separated into different lines with 'jobs -l'.
    #
    # See demo/jobs-builtin.sh

    # $ jobs -l
    # [1]+ 24414 Stopped                 sleep 5
    #      24415                       | sleep 5
    # [2]  24502 Running                 sleep 6
    #      24503                       | sleep 6
    #      24504                       | sleep 5 &
    # [3]- 24508 Running                 sleep 6
    #      24509                       | sleep 6
    #      24510                       | sleep 5 &

    f = mylib.Stdout()
    for job_id, job in iteritems(self.jobs):
      # Use the %1 syntax
      job.DisplayJob(job_id, f, style)

  def DebugPrint(self):
    # type: () -> None

    f = mylib.Stdout()
    f.write('\n')
    f.write('[process debug info]\n')

    for pid, proc in iteritems(self.child_procs):
      proc.DisplayJob(-1, f, STYLE_DEFAULT)
      #p = ' |' if proc.parent_pipeline else ''
      #print('%d %7s %s%s' % (pid, _JobStateStr(proc.state), proc.thunk.UserString(), p))

    if len(self.debug_pipelines):
      f.write('\n')
      f.write('[pipeline debug info]\n')
      for pi in self.debug_pipelines:
        pi.DebugPrint()

  def ListRecent(self):
    # type: () -> None
    """For jobs -n, which I think is also used in the interactive prompt."""
    pass

  def NumRunning(self):
    # type: () -> int
    """Return the number of running jobs.  Used by 'wait' and 'wait -n'."""
    count = 0
    for _, job in iteritems(self.jobs):  # mycpp rewite: from itervalues()
      if job.State() == job_state_e.Running:
        count += 1
    return count


# WaitForOne() return values

# -1: pyos.UNTRAPPED_SIGWINCH
W1_OK = -2      # waitpid(-1) returned
W1_ECHILD = -3  # no processes to wait for
# result > 0:   # a signal number that we exited with!
                # ignoring untrapped SIGWINCH


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
  def __init__(self, job_state, exec_opts, trap_state, tracer):
    # type: (JobState, optview.Exec, builtin_trap.TrapState, dev.Tracer) -> None
    self.job_state = job_state
    self.exec_opts = exec_opts
    self.trap_state = trap_state
    self.tracer = tracer
    self.last_status = 127  # wait -n error code

  def WaitForOne(self):
    # type: () -> int
    """Wait until the next process returns (or maybe Ctrl-C).

    Returns:
      W1_ECHILD     Nothing to wait for
      W1_OK         Caller should keep waiting
      result > 0    Signal interrupted with

      In the interactive shell, we return 0 if we get a Ctrl-C, so the caller
      will try again.

    Callers:
      wait -n          -- loop until there is one fewer process (TODO)
      wait             -- loop until there are no processes
      wait $!          -- loop until job state is Done (process or pipeline)
      Process::Wait()  -- loop until Process state is done
      Pipeline::Wait() -- loop until Pipeline state is done

    Comparisons:
      bash: jobs.c waitchld() Has a special case macro(!) CHECK_WAIT_INTR for
      the wait builtin

      dash: jobs.c waitproc() uses sigfillset(), sigprocmask(), etc.  Runs in a
      loop while (gotsigchld), but that might be a hack for System V!

    Should we have a cleaner API like named posix::wait_for_one() ?

    wait_result =
      ECHILD                     -- nothing to wait for
    | Done(int pid, int status)  -- process done
    | EINTR(bool sigint)         -- may or may not retry
    """
    pid, status = pyos.WaitPid()
    if pid < 0:  # error case
      err_num = status
      #log('waitpid() error => %d %s', e.errno, pyutil.strerror(e))
      if err_num == ECHILD:
        return W1_ECHILD  # nothing to wait for caller should stop
      elif err_num == EINTR:  # Bug #858 fix
        #log('WaitForOne() => %d', self.trap_state.GetLastSignal())
        return self.trap_state.GetLastSignal()  # e.g. 1 for SIGHUP
      else:
        # The signature of waitpid() means this shouldn't happen
        raise AssertionError()

    # All child processes are supposed to be in this dict.  But this may
    # legitimately happen if a grandchild outlives the child (its parent).
    # Then it is reparented under this process, so we might receive
    # notification of its exit, even though we didn't start it.  We can't have
    # any knowledge of such processes, so print a warning.
    if pid not in self.job_state.child_procs:
      print_stderr("osh: PID %d stopped, but osh didn't start it" % pid)
      return W1_OK

    proc = self.job_state.child_procs[pid]
    if 0:
      self.job_state.DebugPrint()

    if WIFSIGNALED(status):
      term_sig = WTERMSIG(status)
      status = 128 + term_sig

      # Print newline after Ctrl-C.
      if term_sig == SIGINT:
        print('')

      self.job_state.WhenDone(pid)
      proc.WhenDone(pid, status)

    elif WIFEXITED(status):
      status = WEXITSTATUS(status)
      #log('exit status: %s', status)
      self.job_state.WhenDone(pid)
      proc.WhenDone(pid, status)

    elif WIFSTOPPED(status):
      #sig = posix.WSTOPSIG(status)

      # BUG: Stopping pipelines doesn't work!
      # sleep 5 | wc -l then Ctrl-Z and fg
      log('')
      log('[PID %d] Stopped', pid)
      self.job_state.WhenStopped(pid)  # show in 'jobs' list, enable 'fg'
      proc.WhenStopped()

    else:
      raise AssertionError(status)

    self.last_status = status  # for wait -n
    self.tracer.OnProcessEnd(pid, status)
    return W1_OK
