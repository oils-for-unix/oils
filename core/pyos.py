#!/usr/bin/env python2
"""
pyos.py -- Wrappers for the operating system.

Like py{error,util}.py, it won't be translated to C++.
"""
from __future__ import print_function

import pwd
import resource
import signal
import select
import termios  # for read -n
import time

import posix_ as posix

from typing import Optional, Tuple, cast, Any, TYPE_CHECKING

if TYPE_CHECKING:
  from core.comp_ui import _IDisplay


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
  initialization use mem.GetVar('HOME').
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
    termios.tcsetattr(self.fd, termios.TCSANOW, self.orig_attrs)


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
