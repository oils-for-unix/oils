#!/usr/bin/env python2
"""
pyos.py -- Wrappers for the operating system.

Like py{error,util}.py, it won't be translated to C++.
"""
from __future__ import print_function

import pwd
import resource
import termios  # for read -n
import time

import posix_ as posix

from typing import Optional, Tuple, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import Token


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
  else:
    return e.pw_dir


def GetHomeDir(token):
  # type: (Token) -> str

  # For ~otheruser/src.  TODO: Should this be cached?
  # http://linux.die.net/man/3/getpwnam
  name = token.val[1:]
  try:
    e = pwd.getpwnam(name)
  except KeyError:
    # If not found, it's ~nonexistent.  TODO: In strict mode, this should be
    # an error, kind of like failglob and nounset.  Perhaps strict-tilde or
    # even strict-word-eval.
    result = token.val
  else:
    result = e.pw_dir

  return result


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


def ReadBytesFromTerminal(fd, n):
  # type: (int, int) -> str

  # silly way to make a copy
  # https://docs.python.org/2/library/termios.html
  orig_attrs = termios.tcgetattr(fd)
  term_attrs = termios.tcgetattr(fd)

  # cast for MyPy.  Each element in termios doesn't have a static type!
  #reveal_type(term_attrs[3])

  a3 = cast(int, term_attrs[3])
  # Disable canonical (buffered) mode.  See `man termios` for an extended
  # discussion.
  term_attrs[3] = a3 & ~termios.ICANON

  chunks = []
  try:
    termios.tcsetattr(fd, termios.TCSANOW, term_attrs)
    # posix.read always returns a single character in unbuffered mode
    while n > 0:
      chunks.append(posix.read(fd, 1))
      n -= 1
  finally:
    termios.tcsetattr(fd, termios.TCSANOW, orig_attrs)

  return ''.join(chunks)


def OsType():
  # type: () -> str
  """ Compute $OSTYPE variable """
  return posix.uname()[0].lower()


