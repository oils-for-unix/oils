#!/usr/bin/env python2
"""
passwd.py

Wrapper around the 'pwd' module.  Its API uses large tuples e.g. Tuple7, which
can't be translated directly by mycpp.

"""
from __future__ import print_function

import pwd
import posix_ as posix

from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import Token


def GetMyHomeDir():
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
