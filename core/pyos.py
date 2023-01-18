"""
pyos.py -- Wrappers for the operating system.

Like py{error,util}.py, it won't be translated to C++.
"""
from __future__ import print_function

from errno import EINTR
import pwd
import resource
import signal
import select
import sys
import termios  # for read -n
import time

from core import pyutil
from core.pyerror import log

import posix_ as posix
from posix_ import WUNTRACED

from typing import Optional, Tuple, List, Dict, cast, Any


_ = log


EOF_SENTINEL = 256  # bigger than any byte
NEWLINE_CH = 10  # ord('\n')


def FlushStdout():
  # type: () -> None
  """Flush CPython buffers."""
  sys.stdout.flush()


def WaitPid():
  # type: () -> Tuple[int, int]
  try:
    # Notes:
    # - The arg -1 makes it like wait(), which waits for any process.
    # - WUNTRACED is necessary to get stopped jobs.  What about WCONTINUED?
    # - We don't retry on EINTR, because the 'wait' builtin should be
    #   interruptable.
    pid, status = posix.waitpid(-1, WUNTRACED)
  except OSError as e:
    return -1, e.errno

  return pid, status


class ReadError(Exception):
  """Wraps errno returned by read().  Used by 'read' and 'mapfile' builtins.
  """

  def __init__(self, err_num):
    # type: (int) -> None
    self.err_num = err_num


def Read(fd, n, chunks):
  # type: (int, int, List[str]) -> Tuple[int, int]
  """
  C-style wrapper around Python's posix.read() that uses return values instead
  of exceptions for errors.  We will implement this directly in C++ and not use
  exceptions at all.

  It reads n bytes from the given file descriptor and appends it to chunks.

  Returns:
    (-1, errno) on failure
    (number of bytes read, 0) on success.  Where 0 bytes read indicates EOF.
  """
  try:
    chunk = posix.read(fd, n)
  except OSError as e:
    return -1, e.errno
  else:
    length = len(chunk)
    if length:
      chunks.append(chunk)
    return length, 0


def ReadByte(fd):
  # type: (int) -> Tuple[int, int]
  """
  Another low level interface with a return value interface.  Used by
  _ReadUntilDelim() and _ReadLineSlowly().

  Returns:
    failure: (-1, errno) on failure
    success: (ch integer value or EOF_SENTINEL, 0)
  """
  try:
    b = posix.read(fd, 1)
  except OSError as e:
    return -1, e.errno
  else:
    if len(b):
      return ord(b), 0
    else:
      return EOF_SENTINEL, 0


def ReadLine():
  # type: () -> str
  """Read a line from stdin.

  This is a SLOW PYTHON implementation taht calls read(0, 1) too many times.  I
  tried to write libc.stdin_readline() which uses the getline() function, but
  somehow that makes spec/oil-builtins.test.sh fail.  We use Python's
  f.readline() in frontend/reader.py FileLineReader with f == stdin.
  
  So I think the buffers get confused:
  - Python buffers for sys.stdin.readline()
  - libc buffers for getline()
  - no buffers when directly issuing read(0, 1) calls, which ReadByte() does

  TODO: Add keep_newline arg
  """
  ch_array = []  # type: List[int]
  while True:
    ch, err_num = ReadByte(0)

    if ch < 0:
      if err_num == EINTR:
        # Instead of retrying, return EOF, which is what libc.stdin_readline()
        # did.  I think this interface is easier with getline().
        # This causes 'read --line' to return status 1.
        return ''
      else:
        raise ReadError(err_num)

    elif ch == EOF_SENTINEL:
      break

    else:
      ch_array.append(ch)

    # TODO: Add option to omit newline
    if ch == NEWLINE_CH:
      break

  return pyutil.ChArrayToString(ch_array)


def Environ():
  # type: () -> Dict[str, str]
  return posix.environ


def Chdir(dest_dir):
  # type: (str) -> int
  """Returns 0 for success and nonzero errno for error."""
  try:
    posix.chdir(dest_dir)
  except OSError as e:
    return e.errno
  return 0


def GetMyHomeDir():
  # type: () -> Optional[str]
  """Get the user's home directory from the /etc/pyos.

  Used by $HOME initialization in osh/state.py.  Tilde expansion and readline
  initialization use mem.GetValue('HOME').
  """
  uid = posix.getuid()
  try:
    e = pwd.getpwuid(uid)
  except KeyError:
    return None

  return e.pw_dir


def GetHomeDir(user_name):
  # type: (str) -> Optional[str]
  """
  For ~otheruser/src.  TODO: Should this be cached?
  """
  # http://linux.die.net/man/3/getpwnam
  try:
    e = pwd.getpwnam(user_name)
  except KeyError:
    return None

  return e.pw_dir


class PasswdEntry(object):
  def __init__(self, pw_name, uid, gid):
    # type: (str, int, int) -> None
    self.pw_name = pw_name
    self.pw_uid = uid
    self.pw_gid = gid


def GetAllUsers():
  # type: () -> List[PasswdEntry]
  users = [PasswdEntry(u.pw_name, u.pw_uid, u.pw_gid) for u in pwd.getpwall()]
  return users


def GetUserName(uid):
  # type: (int) -> str
  try:
    e = pwd.getpwuid(uid)
  except KeyError:
    return "<ERROR: Couldn't determine user name for uid %d>" % uid
  else:
    return e.pw_name


def Time():
  # type: () -> Tuple[float, float, float]
  t = time.time()  # calls gettimeofday() under the hood
  u = resource.getrusage(resource.RUSAGE_SELF)
  return t, u.ru_utime, u.ru_stime


def PrintTimes():
  # type: () -> None
  utime, stime, cutime, cstime, elapsed = posix.times()
  print("%dm%.3fs %dm%.3fs" % (utime / 60, utime % 60, stime / 60, stime % 60))
  print("%dm%.3fs %dm%.3fs" % (cutime / 60, cutime % 60, cstime / 60, cstime % 60))


# So builtin_misc.py doesn't depend on termios, which makes C++ translation
# easier
TERM_ICANON = termios.ICANON
TERM_ECHO = termios.ECHO


class TermState(object):
  """
  TODO: Make this into a context manager which is a C++ destructor?
  """
  def __init__(self, fd, mask):
    # type: (int, int) -> None
    self.fd = fd

    # silly way to make a copy
    # https://docs.python.org/2/library/termios.html
    self.orig_attrs = termios.tcgetattr(fd)
    term_attrs = termios.tcgetattr(fd)

    a3 = cast(int, term_attrs[3])
    # Disable canonical (buffered) mode.  See `man termios` for an extended
    # discussion.
    term_attrs[3] = a3 & mask
    termios.tcsetattr(self.fd, termios.TCSANOW, term_attrs)

  def Restore(self):
    # type: () -> None
    try:
      termios.tcsetattr(self.fd, termios.TCSANOW, self.orig_attrs)
    except termios.error as e:
      # Superficial fix for issue #1001.  I'm not sure why we get errno.EIO,
      # but we can't really handle it here.  In C++ I guess we ignore the
      # error.
      pass


def OsType():
  # type: () -> str
  """ Compute $OSTYPE variable """
  return posix.uname()[0].lower()


def InputAvailable(fd):
  # type: (int) -> bool
  # similar to lib/sh/input_avail.c in bash
  # read, write, except
  r, w, exc = select.select([fd], [], [fd], 0)
  return len(r) != 0


UNTRAPPED_SIGWINCH = -1


class SignalHandler(object):
  """
  A basic signal handler that enqueues signals for asynchrnous processing as
  they are fired.
  """
  def __init__(self):
    # type: () -> None
    self.signal_queue = []  # type: List[int]
    self.last_sig_num = 0  # type: int
    self.sigwinch_num = UNTRAPPED_SIGWINCH

  def __call__(self, sig_num, unused_frame):
    # type: (int, Any) -> None
    if sig_num == signal.SIGWINCH:
      self.last_sig_num = self.sigwinch_num
    else:
      self.last_sig_num = sig_num

    self.signal_queue.append(sig_num)

  def TakeSignalQueue(self):
    # type: () -> List[int]
    # A note on signal-safety here. The main loop might be calling this function
    # at the same time a signal is firing and appending to
    # `self.signal_queue`. We can forgoe using a lock here
    # (which would be problematic for the signal handler) because mutual
    # exclusivity should be maintained by the atomic nature of pointer
    # assignment (i.e. word-sized writes) on most modern platforms.
    # The replacement run list is allocated before the swap, so it can be
    # interuppted at any point without consequence.
    # This means the signal handler always has exclusive access to
    # `self.signal_queue`. In the worst case the signal handler might write to
    # `new_queue` and the corresponding trap handler won't get executed
    # until the main loop calls this function again.
    # NOTE: It's important to distinguish between signal-saftey an
    # thread-saftey here. Signals run in the same process context as the main
    # loop, while concurrent threads do not and would have to worry about
    # cache-coherence and instruction reordering.
    new_queue = []  #  type: List[int]
    ret = self.signal_queue
    self.signal_queue = new_queue
    return ret


gSignalHandler = None  #  type: SignalHandler


def Sigaction(sig_num, handler):
  # type: (int, Any) -> None
  """Register a signal handler"""
  signal.signal(sig_num, handler)


def RegisterSignalInterest(sig_num):
  # type: (int) -> None
  """Have the kernel notify the main loop about the given signal"""
  assert gSignalHandler is not None
  signal.signal(sig_num, gSignalHandler)


def TakeSignalQueue():
  # type: () -> List[int]
  """Transfer ownership of the current queue of pending signals to the caller."""
  global gSignalHandler
  assert gSignalHandler is not None
  return gSignalHandler.TakeSignalQueue()


def LastSignal():
  # type: () -> int
  """Returns the number of the last signal that fired"""
  assert gSignalHandler is not None
  return gSignalHandler.last_sig_num


def SetSigwinchCode(code):
  # type: (int) -> None
  """
  Depending on whether or not SIGWINCH is trapped by a user, it is expected to
  report a different code to `wait`. SetSigwinchCode() lets us set which code is
  reported.
  """
  global gSignalHandler
  assert gSignalHandler is not None
  gSignalHandler.sigwinch_num = code


def InitShell():
  # type: () -> None
  global gSignalHandler
  gSignalHandler = SignalHandler()


def MakeDirCacheKey(path):
  # type: (str) -> Tuple[str, int]
  """
  Returns a pair (path with last modified time) that can be used to cache directory accesses.
  """
  st = posix.stat(path)
  return (path, int(st.st_mtime))
