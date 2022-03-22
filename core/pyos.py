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
import termios  # for read -n
import time

from core import pyutil
from core.pyerror import log

import posix_ as posix
from posix_ import WUNTRACED

from typing import Optional, Tuple, List, Dict, cast, Any, TYPE_CHECKING

if TYPE_CHECKING:
  from core.comp_ui import _IDisplay
  from osh.builtin_process import _TrapHandler

_ = log


EOF_SENTINEL = 256  # bigger than any byte
NEWLINE_CH = 10  # ord('\n')


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


def Read(fd, n, buf):
  # type: (int, int, List[str]) -> Tuple[int, int]
  """
  C-style wrapper around Python's posix.read() that uses return values instead
  of exceptions for errors.  We will implement this directly in C++ and not use
  exceptions at all.

  It reads n bytes from the given file descriptor and appends it to buf.

  Returns:
    (-1, errno) on failure
    (number of bytes read, 0) on success.  Where 0 bytes read indicates EOF.
  """
  try:
    chunk = posix.read(fd, n)
  except OSError as e:
    return -1, e.errno
  else:
    buf.append(chunk)
    return len(chunk), 0


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
  print("%dm%1.3fs %dm%1.3fs" % (utime / 60, utime % 60, stime / 60, stime % 60))
  print("%dm%1.3fs %dm%1.3fs" % (cutime / 60, cutime % 60, cstime / 60, cstime % 60))


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

class SigwinchHandler(object):
  """Wrapper to call user handler."""

  def __init__(self, display, sig_state):
    # type: (_IDisplay, SignalState) -> None
    self.display = display
    self.sig_state = sig_state
    self.user_handler = None  # type: _TrapHandler

  def __call__(self, sig_num, unused_frame):
    # type: (int, Any) -> None
    """For Python's signal module."""

    # SENTINEL for UNTRAPPED SIGWINCH.  If it's trapped, self.user_handler
    # will overwrite it with signal.SIGWINCH.
    self.sig_state.last_sig_num = UNTRAPPED_SIGWINCH

    self.display.OnWindowChange()
    if self.user_handler:
      self.user_handler(sig_num, unused_frame)


def SignalState_AfterForkingChild():
  # type: () -> None
  """Not a member of SignalState since we didn't do dependency injection."""

  # Note: this happens in BOTH interactive and non-interactive shells.
  # We technically don't need to do most of it in non-interactive, since we
  # did not change state in InitInteractiveShell().

  # Python sets SIGPIPE handler to SIG_IGN by default.  Child processes
  # shouldn't have this.
  # https://docs.python.org/2/library/signal.html
  # See Python/pythonrun.c.
  signal.signal(signal.SIGPIPE, signal.SIG_DFL)

  # Respond to Ctrl-\ (core dump)
  signal.signal(signal.SIGQUIT, signal.SIG_DFL)

  # Child processes should get Ctrl-Z.
  signal.signal(signal.SIGTSTP, signal.SIG_DFL)

  # More signals from
  # https://www.gnu.org/software/libc/manual/html_node/Launching-Jobs.html
  # (but not SIGCHLD)
  signal.signal(signal.SIGTTOU, signal.SIG_DFL)
  signal.signal(signal.SIGTTIN, signal.SIG_DFL)


class SignalState(object):
  """All changes to global signal state go through this object."""

  def __init__(self):
    # type: () -> None
    self.sigwinch_handler = None  # type: SigwinchHandler
    self.last_sig_num = 0  # MUTABLE GLOBAL, for interrupted 'wait'

  def InitShell(self):
    # type: () -> None
    """Always called when initializing the shell process."""
    pass

  def InitInteractiveShell(self, display, my_pid):
    # type: (_IDisplay, int) -> None
    """Called when initializing an interactive shell."""
    # The shell itself should ignore Ctrl-\.
    signal.signal(signal.SIGQUIT, signal.SIG_IGN)

    # This prevents Ctrl-Z from suspending OSH in interactive mode.
    signal.signal(signal.SIGTSTP, signal.SIG_IGN)

    # More signals from
    # https://www.gnu.org/software/libc/manual/html_node/Initializing-the-Shell.html
    # (but not SIGCHLD)
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    signal.signal(signal.SIGTTIN, signal.SIG_IGN)

    # Register a callback to receive terminal width changes.
    # NOTE: In line_input.c, we turned off rl_catch_sigwinch.

    # This is ALWAYS on, which means that it can cause EINTR, and wait() and
    # read() have to handle it
    self.sigwinch_handler = SigwinchHandler(display, self)
    signal.signal(signal.SIGWINCH, self.sigwinch_handler)

    # This doesn't make any tests pass, and we might punt on job control
    if 0:
      try:
        # Put the interactive shell in its own process group, named by its PID
        posix.setpgid(my_pid, my_pid)
        # Attach the terminal (stdin) to the progress group
        posix.tcsetpgrp(0, my_pid)

      except (IOError, OSError) as e:
        # For some reason setpgid() fails with Operation Not Permitted (EPERM) under pexpect?
        pass

  def AddUserTrap(self, sig_num, handler):
    # type: (int, Any) -> None
    """For user-defined handlers registered with the 'trap' builtin."""

    if sig_num == signal.SIGWINCH:
      assert self.sigwinch_handler is not None
      self.sigwinch_handler.user_handler = handler
    else:
      signal.signal(sig_num, handler)
    # TODO: SIGINT is similar: set a flag, then optionally call user _TrapHandler

  def RemoveUserTrap(self, sig_num):
    # type: (int) -> None
    """For user-defined handlers registered with the 'trap' builtin."""
    # Restore default
    if sig_num == signal.SIGWINCH:
      assert self.sigwinch_handler is not None
      self.sigwinch_handler.user_handler = None
    else:
      signal.signal(sig_num, signal.SIG_DFL)
    # TODO: SIGINT is similar: set a flag, then optionally call user _TrapHandler
