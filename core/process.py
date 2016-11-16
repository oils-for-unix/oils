#!/usr/bin/env python3
"""
process.py - Runtime library for launching processes and manipulating file
descriptors.
"""

import fcntl
import os
import sys

from core import util  # log


class FdState(object):
  """This is for the current process, not child processes?"""

  def __init__(self, base_fd=10):
    self.base_fd = base_fd
    self.next_fd = base_fd
    self.saved = []
    self.need_close = []

  def SaveAndDup(self, fd1, fd2):
    """
    Save fd2 and dup fd1 onto fd2.
    """
    #sys.stdout.write('---- %s %s\n' % (fd1, fd2))

    #print('SaveAndDup %s %s (saving to: %d)' % (fd1, fd2, self.next_fd))
    fcntl.fcntl(fd2, fcntl.F_DUPFD, self.next_fd)
    os.close(fd2)
    fcntl.fcntl(self.next_fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)

    #sys.stdout.write('==== %s %s\n' % (fd1, fd2))

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

    self.saved.append((self.next_fd, fd2))
    self.next_fd += 1
    return True

  def NeedClose(self, fd):
    self.need_close.append(fd)

  def RestoreAll(self):
    for saved, orig in reversed(self.saved):
      os.dup2(saved, orig)
      os.close(saved)
    self.saved = []
    #print('dup2 %s %s' % (fd1, fd2))
    self.next_fd = self.base_fd

    for fd in self.need_close:
      os.close(fd)

  def ForgetAll(self):
    self.saved = []
    self.need_close = []


class Redirect(object):
  def __init__(self, fd):
    self.fd = fd

  def ApplyInParent(self, fd_state):
    """Apply redirect in the main shell process, e.g. for a builtin."""
    raise NotImplementedError

  # In child, we don't need to restore state.  Just do os.dup2().
  def ApplyInChild(self):
    raise NotImplementedError(self.__class__.__name__)

  def BeforeFork(self, fd_state):
    pass

  def AfterForkInParent(self):
    pass


class ReadPipeRedirect(Redirect):
  def __init__(self, fd):
    Redirect.__init__(self, fd)

  def ApplyInChild(self):
    os.dup2(self.fd, 0)
    os.close(self.fd)  # close after dup

  def AfterForkInParent(self):
    os.close(self.fd)


class WritePipeRedirect(Redirect):
  def __init__(self, fd):
    Redirect.__init__(self, fd)

  def ApplyInChild(self):
    os.dup2(self.fd, 1)
    os.close(self.fd)  # close after dup

  def AfterForkInParent(self):
    os.close(self.fd)


class UserRedirect(Redirect):
  def __init__(self, op, fd):
    Redirect.__init__(self, fd)
    self.op = op


class FilenameRedirect(UserRedirect):
  def __init__(self, op, fd, filename):
    UserRedirect.__init__(self, op, fd)
    self.filename = filename

  def ApplyInChild(self):
    target_fd = os.open(self.filename, os.O_CREAT | os.O_RDWR | os.O_TRUNC)
    os.dup2(target_fd, self.fd)
    os.close(target_fd)

  def ApplyInParent(self, fd_state):
    target_fd = os.open(self.filename, os.O_CREAT | os.O_RDWR | os.O_TRUNC)
    fd_state.SaveAndDup(target_fd, self.fd)
    fd_state.NeedClose(target_fd)


class DescriptorRedirect(UserRedirect):
  def __init__(self, op, fd, target_fd):
    UserRedirect.__init__(self, op, fd)
    self.target_fd = target_fd

  def ApplyInChild(self):
    os.dup2(self.target_fd, self.fd)

  def ApplyInParent(self, fd_state):
    fd_state.SaveAndDup(self.target_fd, self.fd)


class HereDocRedirect(UserRedirect):
  def __init__(self, op, fd, body_str):
    UserRedirect.__init__(self, op, fd)
    self.body_str = body_str
    self.r = -1
    self.w = -1
    self.here_proc = None

  def _CreatePipeAndMaybeProcess(self, fd_state):
    """
    Create a pipe to write the here doc to.  For big here docs, create a
    separate process to avoid deadlock.
    """
    self.r, self.w = os.pipe()
    thunk = HereDocWriterThunk(self.w, self.body_str)
    start_process = len(self.body_str) > 10  # TODO: Use correct heuristic

    start_process = True
    if start_process:
      #print('starting here doc helper process')
      self.here_proc = Process(thunk)
      self.here_proc.Start()  # who waits for this guy?

      # here proc is not going to read.  Or really you don't have to worry
      # about this?
      #self.here_proc.ChildClose(self.r)
    else:
      #print('writing %s to pipe in %d shell process' % (self.here_lines,)
      #    self.w)
      thunk.RunInParent()
      os.close(self.w)

  def BeforeFork(self, fd_state):  # applying in child
    #print('!!! BeforeFork')
    self._CreatePipeAndMaybeProcess(fd_state)

  def ApplyInChild(self):  # in child
    """When we have an external command."""
    #print('!! ApplyInChild')
    os.dup2(self.r, 0)  # TODO: self.fd

    # NOTE: If we write the short doc to the pipe synchronously, we can't close
    # here!
    #print(os.listdir('/dev/fd'))
    #print('CLOSING', self.w)
    os.close(self.w)  # child is not going to write

  def AfterForkInParent(self):  # applying in child
    os.close(self.r)  # parent isn't going to read or write
    os.close(self.w)

    #print('!! AfterForkInParent')
    if self.here_proc:
      status = self.here_proc.Wait()
      #print('Here doc writer finished with status %d' % status)

  # Separate path: Apply the whole thing in the parent
  def ApplyInParent(self, fd_state):
    """When we have a builtin command."""
    #print('!! ApplyInParent')
    self._CreatePipeAndMaybeProcess(fd_state)
    fd_state.SaveAndDup(self.r, 0)  # dup stdin.  TODO: self.fd


class CommandSubRedirect(Redirect):
  """
- Realization: here docs and command sub are NOT complementary.  There can be
  more than one here doc per command / pipeline, but there can only be one
  command sub!

  cat <<EOF 3<<EOF3
  ...

  cat <<EOF | cat 3<<EOF | cat 5<<EOF
  ...

  Here docs need to always create a process (or temp file, but we're not doing
  that).  CommandSub can use the parent process to read.
  """
  def __init__(self, var):
    fd = 1  # TODO: get rid of DUMMY
    Redirect.__init__(self, fd)
    self.var = var  # list to append to
    self.r = -1
    self.w = -1

  def BeforeFork(self, fd_state):
    self.r, self.w = os.pipe()

  def ApplyInChild(self):  # in child
    os.dup2(self.w, 1)
    os.close(self.r)  # child is not going read

  def AfterForkInParent(self):
    os.close(self.w)  # not going to read
    while True:
      byte_str = os.read(self.r, 4096)
      if not byte_str:
        break
      self.var.append(byte_str.decode('utf-8'))
    os.close(self.r)


class Thunk(object):
  """Abstract base class for things runnable in another process."""

  def RunInParent(self):
    """Returns a status code."""
    raise NotImplementedError

  def RunInChild(self):
    """Never returns."""
    self.RunInParent()

    # TODO: How do we communicate a bad status to the parent process?  It
    # waits?  Signal?
    # The problem is that a subshell cannot fail!
    sys.exit(0)  # This is required

  def IsExternal(self):
    """Test if a thunk represents an external process (ExternalThunk)."""
    return False

  def ShouldRestoreFdState(self):
    """Default is to restore."""
    return True


class ExternalThunk(Thunk):
  """An external executable."""

  def __init__(self, argv, more_env=None):
    self.argv = argv
    self.more_env = more_env or {}

  def IsExternal(self):
    return True

  def RunInParent(self):
    """
    An ExternalThunk is run in parent for the exec builtin.
    """
    # TODO: If there is an error, like the file isn't executable, then we
    # should exit, and the parent will reap it.  Should it capture stderr?

    # NOTE: Do we have to do this?
    env = dict(os.environ)
    env.update(self.more_env)

    try:
      os.execvpe(self.argv[0], self.argv, env)
    except OSError as e:
      util.log('Unexpected error in execvpe(%r, %r, ...): %s', self.argv[0],
               self.argv, e)
      # Command not found means 127.  TODO: Are there other cases?
      sys.exit(127)
    # no return


class SubProgramThunk(Thunk):
  """A subprogram that can be executed in another process."""

  def __init__(self, ex, node):
    self.ex = ex
    self.node = node

  def RunInParent(self):
    return self.ex.Execute(self.node)


# NOTE: We need BuiltinThunk and FuncThunk to maintain the invariant that words
# are evaluated into argv only ONCE.  We don't want to do work in the parent
# process and then do it again in the process.  First word resolution happens
# in the parent no matter what -- but execution may happen in the child.

class BuiltinThunk(Thunk):
  """A resolved builtin.

  We do NOT want to evaluate the node twice, because it can involve side
  effects.
  """
  def __init__(self, ex, builtin_id, argv):
    """
    Args:
      ex: Executor
      builtin_id: integer
      argv: arguuments
    """
    self.ex = ex
    self.builtin_id = builtin_id
    self.argv = argv

  def RunInParent(self):
    return self.ex.RunBuiltin(self.builtin_id, self.argv)

  def ShouldRestoreFdState(self):
    # TODO: exec
    return True


class FuncThunk(Thunk):
  """A resolved user defined function."""
  def __init__(self, ex, func_node, argv):
    self.ex = ex
    self.func_node = func_node
    self.argv = argv

  def RunInParent(self):
    return self.ex.RunFunc(self.func_node, self.argv)


class HereDocWriterThunk(Thunk):
  """Write a here doc to one end of a pipe.
  
  May be be executed in either a child process or the main shell process.
  """
  def __init__(self, w, body_str):
    self.w = w
    self.body_str = body_str

  def RunInParent(self):
    byte_str = self.body_str.encode('utf-8')
    os.write(self.w, byte_str)
    # Don't bother to close, since the process will die
    #os.close(self.w)


# TODO:
# - Do Process and Pipeline need this common interface?
#
# What about SubProgramThunk?    $(echo foo; echo bar)
#
# List node, passed to EvalCommandSub().  Wrap in Process(SubProgramThunk()), and
# then call .AddOutputVar() on it.  That turns it into a pipeline?
#
# What about memory management of that object in C?  I guess Capturable just
# has a virtual destructor.
#
# Pipeline.AddOutputVar() -- return this
#
# When you have both input and output, the output is the one that runs in the
# main thread, and input becomes Process(SubProgramThunk).


class Capturable(object):
  def __init__(self):
    pass

  def CaptureOutput(self, var):
    raise NotImplementedError


class Process(object):
  """A process to run.
  
  It provides an API to manipulate file descriptor state in parent and child.
  """
  def __init__(self, thunk, env=None, fd_state=None, redirects=None):
    """
    Args:
      thunk: Thunk instance
      fd_state: created in parent, but modified in child sometimes (bash does
        this) example: exec 1>&2; ls | wc -l
      redirects: List of EVALUATED redirects (filename, raw string, target
        descriptor)
        Caller should call os.open() or os.pipe() to get file descriptors.
        Sometimes files should be opened in the child.
        Maybe have redirect.ChangeState(fd_state)
        Always in the current process?
    """
    if isinstance(thunk, list):
      self.thunk = ExternalThunk(thunk)
    else:
      self.thunk = thunk 
    self.env = env or {}
    self.fd_state = fd_state
    self.redirects = redirects or []

    self.inputs = []

  def __repr__(self):
    return '<Process %s>' % self.thunk

  def AddRedirect(self, redirect):
    self.redirects.append(redirect)

  def CaptureOutput(self, var):
    self.redirects.append(CommandSubRedirect(var))

  def Start(self):
    """
    Start a process.
    """
    for r in self.redirects:
      r.BeforeFork(self.fd_state)

    pid = os.fork()
    if pid < 0:
      # When does this happen?
      raise RuntimeError('Fatal error in os.fork()')

    elif pid == 0:  # child
      # NOTE: We never call RestoreAll().  It doesn't really matter since
      # the process is torn down.
      for r in self.redirects:
        r.ApplyInChild()

      self.thunk.RunInChild()
      # Never returns

    for r in self.redirects:  # here docs
      r.AfterForkInParent()

  def Wait(self):
    # NOTE: Need to check errors
    wait_pid, status = os.wait()

    # TODO: split up status?
    return status

  def Run(self):
    self.Start()

    # TODO: Can collect garbage here, and record timing stats.  The process
    # will likely take longer than the GC?  Although I guess some processes can
    # only take 1ms, whereas garbage collection can take longer.
    # Maybe you can have a separate GC thread, and only start it after 100ms,
    # and then cancel when done?

    return self.Wait()


class Pipeline(object):
  """A pipeline of processes to run.

  Cases we handle:

  foo | bar
  $(foo | bar)  
  foo | bar | read v
  """
  def __init__(self):
    self.procs = []
    self.pipes = []  # there is a pipe for every pair of procs.

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

    prev.AddRedirect(WritePipeRedirect(w))
    p.AddRedirect(ReadPipeRedirect(r))

    self.procs.append(p)

  def CaptureOutput(self, var):
    """Add output var.

    Args:
      var: A list that is mutated.

    After pi.Run(), you can read the value of 'var'.
    """
    self.procs[-1].CaptureOutput(var)

  def Run(self):
    for p in self.procs:
      #print('start', p)
      p.Start()

    pipe_status = []

    # TODO: Could do some sort of garbage collection here  too.

    for p in self.procs:
      #print('Wait', p)
      pipe_status.append(p.Wait())

    return pipe_status

