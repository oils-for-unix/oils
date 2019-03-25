#!/usr/bin/env python
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
import posix
import pwd
import signal
import sys

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import redirect_e, process_state_e
from core import util
from pylib import os_

from typing import Optional

e_die = util.e_die
log = util.log


def GetHomeDir():
  # type: () -> Optional[str]
  """Get the user's home directory from the /etc/passwd.

  Used by $HOME initialization in osh/state.py.  Tilde expansion and readline
  initialization use mem.GetVar('HOME').
  """
  uid = posix.getuid()
  try:
    e = pwd.getpwuid(uid)
  except KeyError:
    return None
  else:
    return e.pw_dir


class _FdFrame(object):
  def __init__(self):
    self.saved = []
    self.need_close = []
    self.need_wait = []

  def Forget(self):
    """For exec 1>&2."""
    del self.saved[:]  # like list.clear() in Python 3.3
    del self.need_close[:]
    del self.need_wait[:]

  def __repr__(self):
    return '<_FdFrame %s %s>' % (self.saved, self.need_close)


class FdState(object):
  """This is for the current process, as opposed to child processes.

  For example, you can do 'myfunc > out.txt' without forking.
  """
  def __init__(self):
    self.cur_frame = _FdFrame()  # for the top level
    self.stack = [self.cur_frame]

  # TODO: Use fcntl(F_DUPFD) and look at the return value!  I didn't understand
  # the difference.

  def _GetFreeDescriptor(self):
    """Return a free file descriptor above 10 that isn't used."""
    done = False
    fd = 10
    while True:
      try:
        fcntl.fcntl(fd, fcntl.F_GETFD)
      except IOError as e:
        if e.errno == errno.EBADF:
          break
      fd += 1

    return fd

  def Open(self, path, mode='r'):
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
    new_fd = self._GetFreeDescriptor()
    posix.dup2(fd, new_fd)
    posix.close(fd)
    try:
      f = posix.fdopen(new_fd, mode)  # Might raise IOError
    except IOError as e:
      raise OSError(*e.args)  # Consistently raise OSError
    return f

  def _PushDup(self, fd1, fd2):
    """Save fd2, and dup fd1 onto fd2.

    Mutates self.cur_frame.saved.

    Returns:
      success Bool
    """
    new_fd = self._GetFreeDescriptor()
    #log('---- _PushDup %s %s', fd1, fd2)
    need_restore = True
    try:
      fcntl.fcntl(fd2, fcntl.F_DUPFD, new_fd)
    except IOError as e:
      # Example program that causes this error: exec 4>&1.  Descriptor 4 isn't
      # open.
      # This seems to be ignored in dash too in savefd()?
      if e.errno == errno.EBADF:
        #log('ERROR %s', e)
        need_restore = False
      else:
        raise
    else:
      posix.close(fd2)
      fcntl.fcntl(new_fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)

    #log('==== dup %s %s\n' % (fd1, fd2))
    try:
      posix.dup2(fd1, fd2)
    except OSError as e:
      # bash/dash give this error too, e.g. for 'echo hi 1>&3'
      util.error('%d: %s', fd1, posix.strerror(e.errno))
      # Restore and return error
      posix.dup2(new_fd, fd2)
      posix.close(new_fd)
      # Undo it
      return False

    if need_restore:
      self.cur_frame.saved.append((new_fd, fd2))
    return True

  def _PushClose(self, fd):
    self.cur_frame.need_close.append(fd)

  def _PushWait(self, proc, waiter):
    self.cur_frame.need_wait.append((proc, waiter))

  def _ApplyRedirect(self, r, waiter):
    ok = True

    if r.tag == redirect_e.PathRedirect:
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
      else:
        raise NotImplementedError(r.op_id)

      # NOTE: 0666 is affected by umask, all shells use it.
      try:
        target_fd = posix.open(r.filename, mode, 0o666)
      except OSError as e:
        util.error("Can't open %r: %s", r.filename, posix.strerror(e.errno))
        return False

      # Apply redirect
      if not self._PushDup(target_fd, r.fd):
        ok = False

      # Now handle the extra redirects for aliases &> and &>>.
      #
      # We can rewrite
      #   stdout_stderr.py &> out-err.txt
      # as
      #   stdout_stderr.py > out-err.txt 2>&1
      #
      # And rewrite
      #   stdout_stderr.py 3&> out-err.txt
      # as
      #   stdout_stderr.py 3> out-err.txt 2>&3
      if ok:
        if r.op_id == Id.Redir_AndGreat:
          if not self._PushDup(r.fd, 2):
            ok = False
        elif r.op_id == Id.Redir_AndDGreat:
          if not self._PushDup(r.fd, 2):
            ok = False

      posix.close(target_fd)  # We already made a copy of it.
      # I don't think we need to close(0) because it will be restored from its
      # saved position (10), which closes it.
      #self._PushClose(r.fd)

    elif r.tag == redirect_e.DescRedirect:  # e.g. echo hi 1>&2

      if r.op_id == Id.Redir_GreatAnd:  # 1>&2
        if not self._PushDup(r.target_fd, r.fd):
          ok = False
      elif r.op_id == Id.Redir_LessAnd:  # 0<&5
        # The only difference between >& and <& is the default file
        # descriptor argument.
        if not self._PushDup(r.target_fd, r.fd):
          ok = False
      else:
        raise NotImplementedError

    elif r.tag == redirect_e.HereRedirect:
      # NOTE: Do these descriptors have to be moved out of the range 0-9?
      read_fd, write_fd = posix.pipe()

      if not self._PushDup(read_fd, r.fd):  # stdin is now the pipe
        ok = False

      # We can't close like we do in the filename case above?  The writer can
      # get a "broken pipe".
      self._PushClose(read_fd)

      thunk = _HereDocWriterThunk(write_fd, r.body)

      # TODO: Use PIPE_SIZE to save a process in the case of small here docs,
      # which are the common case.  (dash does this.)
      start_process = True
      #start_process = False

      if start_process:
        here_proc = Process(thunk)

        # NOTE: we could close the read pipe here, but it doesn't really
        # matter because we control the code.
        # here_proc.StateChange()
        pid = here_proc.Start()
        # no-op callback
        waiter.Register(pid, here_proc.WhenDone)
        #log('Started %s as %d', here_proc, pid)
        self._PushWait(here_proc, waiter)

        # Now that we've started the child, close it in the parent.
        posix.close(write_fd)

      else:
        posix.write(write_fd, r.body)
        posix.close(write_fd)

    return ok

  def Push(self, redirects, waiter):
    #log('> fd_state.Push %s', redirects)
    new_frame = _FdFrame()
    self.stack.append(new_frame)
    self.cur_frame = new_frame

    for r in redirects:
      #log('apply %s', r)
      if not self._ApplyRedirect(r, waiter):
        return False  # for bad descriptor
    #log('done applying %d redirects', len(redirects))
    return True

  def PushStdinFromPipe(self, r):
    """Save the current stdin and make it come from descriptor 'r'.

    'r' is typically the read-end of a pipe.  For 'lastpipe'/ZSH semantics of

    echo foo | read line; echo $line
    """
    new_frame = _FdFrame()
    self.stack.append(new_frame)
    self.cur_frame = new_frame

    return self._PushDup(r, 0)

  def MakePermanent(self):
    self.cur_frame.Forget()

  def Pop(self):
    frame = self.stack.pop()
    #log('< Pop %s', frame)
    for saved, orig in reversed(frame.saved):
      try:
        posix.dup2(saved, orig)
      except OSError as e:
        log('dup2(%d, %d) error: %s', saved, orig, e)
        #log('fd state:')
        #posix.system('ls -l /proc/%s/fd' % posix.getpid())
        raise
      posix.close(saved)
      #log('dup2 %s %s', saved, orig)

    for fd in frame.need_close:
      #log('Close %d', fd)
      try:
        posix.close(fd)
      except OSError as e:
        log('Error closing descriptor %d: %s', fd, e)
        raise

    # Wait for here doc processes to finish.
    for proc, waiter in frame.need_wait:
      unused_status = proc.WaitUntilDone(waiter)


class ChildStateChange(object):

  def Apply(self):
    raise NotImplementedError


class StdinFromPipe(ChildStateChange):
  def __init__(self, pipe_read_fd, w):
    self.r = pipe_read_fd
    self.w = w

  def __repr__(self):
    return '<StdinFromPipe %d %d>' % (self.r, self.w)

  def Apply(self):
    posix.dup2(self.r, 0)
    posix.close(self.r)  # close after dup

    posix.close(self.w)  # we're reading from the pipe, not writing
    #log('child CLOSE w %d pid=%d', self.w, posix.getpid())


class StdoutToPipe(ChildStateChange):
  def __init__(self, r, pipe_write_fd):
    self.r = r
    self.w = pipe_write_fd

  def __repr__(self):
    return '<StdoutToPipe %d %d>' % (self.r, self.w)

  def Apply(self):
    posix.dup2(self.w, 1)
    posix.close(self.w)  # close after dup

    posix.close(self.r)  # we're writing to the pipe, not reading
    #log('child CLOSE r %d pid=%d', self.r, posix.getpid())


class Thunk(object):
  """Abstract base class for things runnable in another process."""

  def Run(self):
    """Returns a status code."""
    raise NotImplementedError


class ExternalProgram(object):
  def __init__(self, hijack_shebang, fd_state, debug_f):
    """
    Args:
      hijack_shebang: The path of an interpreter to run instead of the one
        specified in the shebang line.  May be empty.
    """
    self.hijack_shebang = hijack_shebang
    self.fd_state = fd_state
    self.debug_f = debug_f

  def Exec(self, argv, environ):
    """Execute a program and exit this process.

    Called by:
    ls /
    exec ls /
    ( ls / )
    """
    if self.hijack_shebang:
      try:
        f = self.fd_state.Open(argv[0])
      except OSError as e:
        pass
      else:
        try:
          line = f.read(40)
          if (line.startswith('#!/bin/sh') or
              line.startswith('#!/bin/bash') or
              line.startswith('#!/usr/bin/env bash')):
            self.debug_f.log('Hijacked: %s with %s', argv, self.hijack_shebang)
            argv = [self.hijack_shebang] + argv
          else:
            #self.debug_f.log('Not hijacking %s (%r)', argv, line)
            pass
        finally:
          f.close()

    # TODO: If there is an error, like the file isn't executable, then we should
    # exit, and the parent will reap it.  Should it capture stderr?
    try:
      os_.execvpe(argv[0], argv, environ)
    except OSError as e:
      # TODO: Run with /bin/sh when ENOEXEC error (noshebang).  Because all
      # shells do it.

      util.error('%r: %s', argv[0], posix.strerror(e.errno))
      # POSIX mentions 126 and 127 for two specific errors.  The rest are
      # unspecified.
      #
      # http://pubs.opengroup.org/onlinepubs/9699919799.2016edition/utilities/V3_chap02.html#tag_18_08_02

      if e.errno == errno.EACCES:
        status = 126
      elif e.errno == errno.ENOENT:
        status = 127  # e.g. command not found should be 127.
      else:
        # dash uses 2, but we use that for parse errors.  This seems to be
        # consistent with mksh and zsh.
        status = 127

      sys.exit(status)  # raises SystemExit
    # NO RETURN


class ExternalThunk(object):
  """An external executable."""

  def __init__(self, ext_prog, argv, environ):
    self.ext_prog = ext_prog
    self.argv = argv
    self.environ = environ

  def Run(self):
    """
    An ExternalThunk is run in parent for the exec builtin.
    """
    self.ext_prog.Exec(self.argv, self.environ)


class SubProgramThunk(object):
  """A subprogram that can be executed in another process."""

  def __init__(self, ex, node, disable_errexit=False):
    self.ex = ex
    self.node = node
    self.disable_errexit = disable_errexit  # for bash errexit compatibility

  def Run(self):
    # NOTE: may NOT return due to exec().
    if self.disable_errexit:
      self.ex.exec_opts.errexit.Disable()
    self.ex.ExecuteAndCatch(self.node, fork_external=False)

    # Raises SystemExit, so we still have time to write a crash dump.
    sys.exit(self.ex.LastStatus())


class _HereDocWriterThunk(Thunk):
  """Write a here doc to one end of a pipe.

  May be be executed in either a child process or the main shell process.
  """
  def __init__(self, w, body_str):
    self.w = w
    self.body_str = body_str

  def Run(self):
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
  def __init__(self):
    self.state = process_state_e.Init

  def State(self):
    return self.state

  def WaitUntilDone(self, waiter):
    """
    Returns:
      An int for a process
      A list of ints for a pipeline
    """
    raise NotImplementedError


class Process(Job):
  """A process to run.

  TODO: Should we make it clear that this is a FOREGROUND process?  A
  background process is wrapped in a "job".  It is unevaluated.

  It provides an API to manipulate file descriptor state in parent and child.
  """
  def __init__(self, thunk, job_state=None):
    """
    Args:
      thunk: Thunk instance
      job_state: notify upon completion
    """
    Job.__init__(self)
    assert not isinstance(thunk, list), thunk
    self.thunk = thunk
    self.job_state = job_state

    # For pipelines
    self.state_changes = []
    self.close_r = -1
    self.close_w = -1

    self.pid = -1
    self.status = -1

  def __repr__(self):
    return '<Process %s>' % self.thunk

  def AddStateChange(self, s):
    self.state_changes.append(s)

  def AddPipeToClose(self, r, w):
    self.close_r = r
    self.close_w = w

  def ClosePipe(self):
    if self.close_r != -1:
      posix.close(self.close_r)
      posix.close(self.close_w)

  def Start(self):
    """Start this process with fork(), haandling redirects."""
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
      # Respond to Ctrl-\ (core dump)
      signal.signal(signal.SIGQUIT, signal.SIG_DFL)
      # Respond to Ctrl-C
      signal.signal(signal.SIGINT, signal.SIG_DFL)

      # This doesn't make the child respond to Ctrl-Z?  Why not?  Is there
      # something at the Python level?  signalmodule.c has PyOS_AfterFork but
      # it seems OK.
      # If we add it then somehow the process stop responding to Ctrl-C too.
      #signal.signal(signal.SIGTSTP, signal.SIG_DFL)

      for st in self.state_changes:
        st.Apply()

      self.thunk.Run()
      # Never returns

    #log('STARTED process %s, pid = %d', self, pid)

    # Invariant, after the process is started, it stores its PID.
    self.pid = pid
    return pid

  def WaitUntilDone(self, waiter):
    while True:
      #log('WAITING')
      if not waiter.Wait():
        break
      if self.state == process_state_e.Done:
        break
    return self.status

  def WhenDone(self, pid, status):
    #log('WhenDone %d %d', pid, status)
    assert pid == self.pid, 'Expected %d, got %d' % (self.pid, pid)
    self.status = status
    self.state = process_state_e.Done
    if self.job_state:
      self.job_state.WhenDone(pid)

  def Run(self, waiter):
    """Run this process synchronously."""
    self.Start()
    # NOTE: No race condition between start and Register, because the shell is
    # single-threaded and nothing else can call Wait() before we do!

    waiter.Register(self.pid, self.WhenDone)

    # TODO: Can collect garbage here, and record timing stats.  The process
    # will likely take longer than the GC?  Although I guess some processes can
    # only take 1ms, whereas garbage collection can take longer.
    # Maybe you can have a separate GC thread, and only start it after 100ms,
    # and then cancel when done?

    return self.WaitUntilDone(waiter)


class Pipeline(Job):
  """A pipeline of processes to run.

  Cases we handle:

  foo | bar
  $(foo | bar)
  foo | bar | read v
  """
  def __init__(self):
    Job.__init__(self)
    self.procs = []
    self.pids = []  # pids in order
    self.pipe_status = []  # status in order
    self.status = -1  # for 'wait' jobs

    # optional for background
    self.job_state = None

    # Optional for foregroud
    self.last_thunk = None
    self.last_pipe = None

  def __repr__(self):
    return '<Pipeline %s>' % ' '.join(repr(p) for p in self.procs)

  def Add(self, p):
    """Append a process to the pipeline."""
    if len(self.procs) == 0:
      self.procs.append(p)
      return

    r, w = posix.pipe()
    #log('pipe for %s: %d %d', p, r, w)
    prev = self.procs[-1]

    prev.AddStateChange(StdoutToPipe(r, w))  # applied on Start()
    p.AddStateChange(StdinFromPipe(r, w))  # applied on Start()

    p.AddPipeToClose(r, w)  # ClosePipe() on Start()

    self.procs.append(p)

  def AddLast(self, thunk):
    """Append the last node to the pipeline.

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
    # TODO: pipelines should be put in their own process group with setpgid().
    # I tried 'cat | cat' and Ctrl-C, and it works without this, probably
    # because of SIGPIPE?  I think you will need that for Ctrl-Z, to suspend a
    # whole pipeline.

    for i, proc in enumerate(self.procs):
      pid = proc.Start()
      self.pids.append(pid)
      self.pipe_status.append(-1)  # uninitialized
      waiter.Register(pid, self.WhenDone)

      # NOTE: This has to be done after every fork() call.  Otherwise processes
      # will have descriptors from non-adjacent pipes.
      proc.ClosePipe()

    if self.last_thunk:
      self.pipe_status.append(-1)  # for self.last_thunk

  def StartInBackground(self, waiter, job_state):
    """Returns a job ID."""
    self.job_state = job_state
    self.Start(waiter)
    return self.pids[-1]  # the last PID is the job ID

  def WaitUntilDone(self, waiter):
    while True:
      #log('WAIT pipeline')
      if not waiter.Wait():
        break
      if self.state == process_state_e.Done:
        #log('Pipeline DONE')
        break

    return self.pipe_status

  def Run(self, waiter, fd_state):
    """Run this pipeline synchronously."""
    self.Start(waiter)

    # Run our portion IN PARALLEL with other processes.  This may or may not
    # fork:
    # ls | wc -l
    # echo foo | read line  # no need to fork

    ex, node = self.last_thunk

    #log('thunk %s', self.last_thunk)
    if self.last_pipe is not None:
      r, w = self.last_pipe  # set in AddLast()
      posix.close(w)  # we will not write here
      fd_state.PushStdinFromPipe(r)
      try:
        ex.ExecuteAndCatch(node)
      finally:
        fd_state.Pop()
    else:
      ex.ExecuteAndCatch(node)

    self.pipe_status[-1] = ex.LastStatus()
    #log('pipestatus before all have finished = %s', self.pipe_status)

    return self.WaitUntilDone(waiter)  # returns pipe_status

  def WhenDone(self, pid, status):
    #log('Pipeline WhenDone %d %d', pid, status)
    i = self.pids.index(pid)
    assert i != -1, 'Unexpected PID %d' % pid
    self.pipe_status[i] = status
    if all(status != -1 for status in self.pipe_status):
      self.status = self.pipe_status[-1]  # last one
      self.state = process_state_e.Done
      if self.job_state:
        self.job_state.WhenDone(self.pipe_status[-1])


class JobState(object):
  """Global list of jobs, used by a few builtins."""

  def __init__(self):
    # pid -> Job instance
    # A pipeline that is backgrounded is always run in a SubProgramThunk?  So
    # you can wait for it once?
    self.jobs = {}

  def Register(self, pid, job):
    """ Used by 'sleep 1 &' """
    self.jobs[pid] = job

  def List(self):
    """Used by the 'jobs' builtin."""
    # NOTE: A job is a background process.
    #
    # echo hi | wc -l    -- this starts two processes.  Wait for TWO
    # echo hi | wc -l &   -- this starts a process which starts two processes
    #                        Wait for ONE.

    #self.callbacks[pid]
    for pid, job in self.jobs.iteritems():
      print(pid, job.State(), job)

  def IsDone(self, jid):
    """Test if a specific job is done."""
    if jid not in self.jobs:
      return False, False
    job = self.jobs[jid]
    return True, job.State() == process_state_e.Done

  def AllDone(self):
    """Test if all jobs are done.  Used by 'wait' builtin."""
    for job in self.jobs.itervalues():
      if job.State() != process_state_e.Done:
        return False
    return True

  def WhenDone(self, pid):
    """Process and Pipeline can call this."""
    log('JobState WhenDone %d', pid)
    # TODO: Update the list


class Waiter(object):
  """A capability to wait for processes.

  This must be a singleton (and is because Executor is a singleton).

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

  NOTE: strace reveals that all shells call wait4(-1), which waits for ANY
  process.  posix.wait() ends up calling that too.  This is the only way to
  support the processes we need.
  """
  def __init__(self):
    self.callbacks = {}  # pid -> callback
    self.last_status = 127  # wait -n error code

  def Register(self, pid, callback):
    self.callbacks[pid] = callback

  def Wait(self):
    # This is a list of async jobs
    while True:
      try:
        pid, status = posix.wait()
      except OSError as e:
        #log('wait() error: %s', e)
        if e.errno == errno.ECHILD:
          return False  # nothing to wait for caller should stop
        elif e.errno == errno.EINTR:
          # This happens when we register a handler for SIGINT, and thus never
          # get the KeyboardInterrupt exception?  Not sure why.
          # Try
          # $ cat   # Now hit Ctrl-C
          #log('Continuing')
          continue  # try again
        else:
          # An error we don't know about.
          raise
      else:
        break  # no exception thrown, so no need to retry

    #log('WAIT got %s %s', pid, status)

    # TODO: change status in more cases.
    if posix.WIFSIGNALED(status):
      if posix.WTERMSIG(status) == signal.SIGINT:
        print()
    elif posix.WIFEXITED(status):
      status = posix.WEXITSTATUS(status)
      #log('exit status: %s', status)

    # This could happen via coding error.  But this may legitimately happen
    # if a grandchild outlives the child (its parent).  Then it is reparented
    # under this process, so we might receive notification of its exit, even
    # though we didn't start it.  We can't have any knowledge of such
    # processes, so print a warning.
    if pid not in self.callbacks:
      util.warn("PID %d stopped, but osh didn't start it", pid)
      return True  # caller should keep waiting

    callback = self.callbacks.pop(pid)
    callback(pid, status)
    self.last_status = status  # for wait -n

    return True  # caller should keep waiting
