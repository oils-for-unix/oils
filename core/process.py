#!/usr/bin/python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
"""
process.py - Runtime library for launching processes and manipulating file
descriptors.
"""

import errno
import fcntl
import os
import sys

from core import runtime
from core import util
from core.util import log
from core.id_kind import Id, REDIR_DEFAULT_FD

redirect_e = runtime.redirect_e
e_die = util.e_die


class _FdFrame:
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


class FdState:
  """This is for the current process, as opposed to child processes.

  For example, you can do 'myfunc > out.txt' without forking.
  """
  def __init__(self, next_fd=10):
    self.next_fd = next_fd  # where to start saving descriptors
    self.cur_frame = _FdFrame()  # for the top level
    self.stack = [self.cur_frame]

  def _PushDup(self, fd1, fd2):
    """
    Save fd2 and dup fd1 onto fd2.
    """
    #log('---- _PushDup %s %s\n', fd1, fd2)
    try:
      fcntl.fcntl(fd2, fcntl.F_DUPFD, self.next_fd)
    except IOError as e:
      # Example program that causes this error: exec 4>&1.  Descriptor 4 isn't
      # open.
      # This seems to be ignored in dash too in savefd()?
      if e.errno != errno.EBADF:
        raise
    else:
      os.close(fd2)
      fcntl.fcntl(self.next_fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)

    #log('==== dup %s %s\n' % (fd1, fd2))
    try:
      os.dup2(fd1, fd2)
    except OSError as e:
      #print("%s: %s %s" % (e, fd1, fd2))
      print(e, file=sys.stderr)
      # Restore and return error
      os.dup2(self.next_fd, fd2)
      os.close(self.next_fd)
      # Undo it
      return False

    # Oh this is wrong?
    #os.close(fd1)

    self.cur_frame.saved.append((self.next_fd, fd2))
    self.next_fd += 1
    return True

  def _PushClose(self, fd):
    self.cur_frame.need_close.append(fd)

  def _PushWait(self, proc, waiter):
    self.cur_frame.need_wait.append((proc, waiter))

  def _ApplyRedirect(self, r, waiter):
    # NOTE: We only use self for self.waiter.

    # TODO: r.fd needs to be opened?  if it's not stdin or stdout
    # https://stackoverflow.com/questions/3425021/specifying-file-descriptor-number

    if r.tag == redirect_e.PathRedirect:
      if r.op_id == Id.Redir_Great:  # >
        mode = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
      elif r.op_id == Id.Redir_DGreat:  # >>
        mode = os.O_CREAT | os.O_WRONLY | os.O_APPEND
      elif r.op_id == Id.Redir_Less:  # <
        mode = os.O_RDONLY
      else:
        raise NotImplementedError(r.op_id)

      target_fd = os.open(r.filename, mode)

      self._PushDup(target_fd, r.fd)
      self._PushClose(target_fd)

    elif r.tag == redirect_e.DescRedirect:
      if r.op_id == Id.Redir_GreatAnd:  # 1>&
        self._PushDup(r.target_fd, r.fd)
      elif r.op_id == Id.Redir_LessAnd:
        raise NotImplementedError
      else:
        raise NotImplementedError

    elif r.tag == redirect_e.HereRedirect:
      read_fd, write_fd = os.pipe()
      self._PushDup(read_fd, r.fd)  # stdin is now the pipe
      self._PushClose(read_fd)

      thunk = _HereDocWriterThunk(write_fd, r.body)

      # TODO: Use PIPE_SIZE to save a process in the case of small here docs,
      # which are the common case.
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
        os.close(write_fd)

      else:
        os.write(write_fd, r.body)
        os.close(write_fd)

  def Push(self, redirects, waiter):
    #log('> PushFrame')
    new_frame = _FdFrame()
    self.stack.append(new_frame)
    self.cur_frame = new_frame

    for r in redirects:
      self._ApplyRedirect(r, waiter)

  def MakePermanent(self):
    self.cur_frame.Forget()

  def Pop(self):
    frame = self.stack.pop()
    #log('< Pop %s', frame)
    for saved, orig in reversed(frame.saved):
      os.dup2(saved, orig)
      os.close(saved)
      #log('dup2 %s %s', saved, orig)
      self.next_fd -= 1  # Count down

    for fd in frame.need_close:
      #log('Close %d', fd)
      try:
        os.close(fd)
      except OSError as e:
        log('Error closing descriptor %d: %s', fd, e)
        raise

    # Wait for here doc processes to finish.
    for proc, waiter in frame.need_wait:
      unused_status = proc.WaitUntilDone(waiter)


class ChildStateChange:

  def Apply(self):
    raise NotImplementedError


class StdinFromPipe(ChildStateChange):
  def __init__(self, pipe_read_fd, w):
    self.r = pipe_read_fd
    self.w = w

  def __repr__(self):
    return '<StdinFromPipe %d %d>' % (self.r, self.w)

  def Apply(self):
    os.dup2(self.r, 0)
    os.close(self.r)  # close after dup

    os.close(self.w)  # we're reading from the pipe, not writing
    #log('child CLOSE w %d pid=%d', self.w, os.getpid())


class StdoutToPipe(ChildStateChange):
  def __init__(self, r, pipe_write_fd):
    self.r = r
    self.w = pipe_write_fd

  def __repr__(self):
    return '<StdoutToPipe %d %d>' % (self.r, self.w)

  def Apply(self):
    os.dup2(self.w, 1)
    os.close(self.w)  # close after dup

    os.close(self.r)  # we're writing to the pipe, not reading
    #log('child CLOSE r %d pid=%d', self.r, os.getpid())


class Thunk(object):
  """Abstract base class for things runnable in another process."""

  def Run(self):
    """Returns a status code."""
    raise NotImplementedError


def ExecExternalProgram(argv, more_env):
  """
  """
  # TODO: If there is an error, like the file isn't executable, then we
  # should exit, and the parent will reap it.  Should it capture stderr?

  # NOTE: Do we have to do this?
  env = dict(os.environ)
  env.update(more_env)

  try:
    os.execvpe(argv[0], argv, env)
  except OSError as e:
    log('Unexpected error in execvpe(%r, %r, ...): %s', argv[0], argv, e)
    # Command not found means 127.  TODO: Are there other cases?
    sys.exit(127)
  # no return


class ExternalThunk:
  """An external executable."""

  def __init__(self, argv, more_env=None):
    self.argv = argv
    self.more_env = more_env or {}

  def Run(self):
    """
    An ExternalThunk is run in parent for the exec builtin.
    """
    ExecExternalProgram(self.argv, self.more_env)


class SubProgramThunk:
  """A subprogram that can be executed in another process."""

  def __init__(self, ex, node):
    self.ex = ex
    self.node = node

  def Run(self):
    # NOTE: may NOT return due to exec().
    status = self.ex.Execute(self.node, fork_external=False)
    sys.exit(status)  # Must exit!


class _HereDocWriterThunk(Thunk):
  """Write a here doc to one end of a pipe.

  May be be executed in either a child process or the main shell process.
  """
  def __init__(self, w, body_str):
    self.w = w
    self.body_str = body_str

  #def RunInParent(self):
  #  byte_str = self.body_str.encode('utf-8')
  #  os.write(self.w, byte_str)
  #  # Don't bother to close, since the process will die
  #  #os.close(self.w)

  def Run(self):
    """
    do_exit: For small pipelines
    """
    #log('Writing %r', self.body_str)
    os.write(self.w, self.body_str)
    #log('Wrote %r', self.body_str)
    os.close(self.w)
    #log('Closed %d', self.w)

    sys.exit(0)  # Could this fail?


ProcessState = util.Enum('ProcessState', """Init Done""".split())


class Job(object):
  def __init__(self):
    self.state = ProcessState.Init

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
      os.close(self.close_r)
      os.close(self.close_w)

  def Start(self):
    """Start this process with fork(), haandling redirects."""
    pid = os.fork()
    if pid < 0:
      # When does this happen?
      raise RuntimeError('Fatal error in os.fork()')

    elif pid == 0:  # child
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
      if self.state == ProcessState.Done:
        break
    return self.status

  def WhenDone(self, pid, status):
    #log('WhenDone %d %d', pid, status)
    assert pid == self.pid, 'Expected %d, got %d' % (self.pid, pid)
    self.status = status
    self.state = ProcessState.Done
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
  def __init__(self, job_state=None):
    Job.__init__(self)
    self.job_state = job_state
    self.procs = []
    self.pids = []  # pids in order
    self.pipe_status = []  # status in order
    self.status = -1  # for 'wait' jobs

  def __repr__(self):
    return '<Pipeline %s>' % ' '.join(repr(p) for p in self.procs)

  def Add(self, p):
    """Append a process to the pipeline.

    NOTE: Are its descriptors already set up?
    """
    if len(self.procs) == 0:
      self.procs.append(p)
      return

    r, w = os.pipe()
    prev = self.procs[-1]

    #prev.AddRedirect(WritePipeRedirect(w))
    #p.AddRedirect(ReadPipeRedirect(r))
    prev.AddStateChange(StdoutToPipe(r, w))
    p.AddStateChange(StdinFromPipe(r, w))

    p.AddPipeToClose(r, w)

    self.procs.append(p)

  def Start(self, waiter):
    for i, proc in enumerate(self.procs):
      pid = proc.Start()
      self.pids.append(pid)
      self.pipe_status.append(-1)  # uninitialized
      waiter.Register(pid, self.WhenDone)

      # NOTE: This has to be done after every fork() call.  Otherwise processes
      # will have descriptors from non-adjacent pipes.
      proc.ClosePipe()
    return self.pids[-1]  # the last PID is the job ID

  def WaitUntilDone(self, waiter):
    while True:
      #log('WAIT pipeline')
      if not waiter.Wait():
        break
      if self.state == ProcessState.Done:
        #log('Pipeline DONE')
        break

    return self.pipe_status

  def Run(self, waiter):
    """Run this pipeline synchronously."""
    self.Start(waiter)
    return self.WaitUntilDone(waiter)

  def WhenDone(self, pid, status):
    #log('Pipeline WhenDone %d %d', pid, status)
    i = self.pids.index(pid)
    assert i != -1, 'Unexpected PID %d' % pid
    self.pipe_status[i] = status
    if all(status != -1 for status in self.pipe_status):
      self.status = self.pipe_status[-1]  # last one
      self.state = ProcessState.Done
      if self.job_state:
        self.job_state.WhenDone(self.pipe_status[-1])


class JobState:
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
    return True, job.State() == ProcessState.Done

  def AllDone(self):
    """Test if all jobs are done.  Used by 'wait' builtin."""
    for job in self.jobs.itervalues():
      if job.State() != ProcessState.Done:
        return False
    return True

  def WhenDone(self, pid):
    """Process and Pipeline can call this."""
    log('JobState WhenDone %d', pid)
    # TODO: Update the list


class Waiter:
  """A capability to wait for processes.

  This must be a singleton (and is because Executor is a singleton).

  Invariants:
  - Every child process is registered once
  - Every child process is waited for

  Canonical example of why we need a GLBOAL waiter:

  { sleep 3; echo 'done 3'; } &
  { sleep 4; echo 'done 4'; } &

  # ... do arbitrary stuff ...

  { sleep 1; exit 1; } | { sleep 2; exit 2; }

  Now when you do wait() after starting the pipeline, you might get a pipeline
  process OR a background process!  So you have to distinguish between them.

  NOTE: strace reveals that all shells call wait4(-1), which waits for ANY
  process.  os.wait() ends up calling that too.  This is the only way to
  support the processes we need.
  """
  def __init__(self):
    self.callbacks = {}  # pid -> callback
    self.last_status = 127  # wait -n error code

  def Register(self, pid, callback):
    self.callbacks[pid] = callback

  def Wait(self):
    # This is a list of async jobs
    try:
      pid, status = os.wait()
    except OSError as e:
      if e.errno == errno.ECHILD:
        #log('WAIT ECHILD')
        return False  # nothing to wait for caller should stop
      else:
        # What else can go wrong?
        raise

    #log('WAIT got %s %s', pid, status)

    # TODO: change status in more cases.
    if os.WIFSIGNALED(status):
      pass
    elif os.WIFEXITED(status):
      status = os.WEXITSTATUS(status)
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
