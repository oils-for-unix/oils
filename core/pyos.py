#!/usr/bin/env python2
"""
pyos.py -- Wrappers for the operating system.

Like py{error,util}.py, it won't be translated to C++.
"""
from __future__ import print_function

import pwd
import resource
import select
import termios  # for read -n
import time

import posix_ as posix

from typing import Optional, Tuple, cast


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
