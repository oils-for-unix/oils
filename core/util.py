#t!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
util.py - Common infrastructure.
"""
from __future__ import print_function

import sys
from core import error
from typing import IO, NoReturn, Any


class UserExit(Exception):
  """For explicit 'exit'."""
  def __init__(self, status):
    # type: (int) -> None
    self.status = status


class HistoryError(Exception):

  def __init__(self, msg, *args):
    # type: (str, *Any) -> None
    Exception.__init__(self)
    self.msg = msg
    self.args = args

  def UserErrorString(self):
    # type: () -> str
    out = 'history: '
    if self.args:
      out += self.msg % self.args
    else:
      out += self.msg
    return out


def p_die(msg, *args, **kwargs):
  # type: (str, *Any, **Any) -> NoReturn
  """Convenience wrapper for parse errors."""
  raise error.Parse(msg, *args, **kwargs)


def e_die(msg, *args, **kwargs):
  # type: (str, *Any, **Any) -> NoReturn
  """Convenience wrapper for runtime errors."""
  raise error.FatalRuntime(msg, *args, **kwargs)


def log(msg, *args):
  # type: (str, *Any) -> None
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def BackslashEscape(s, meta_chars):
  # type: (str, str) -> str
  """Escaped certain characters with backslashes.

  Used for shell syntax (i.e. quoting completed filenames), globs, and EREs.
  """
  escaped = []
  for c in s:
    if c in meta_chars:
      escaped.append('\\')
    escaped.append(c)
  return ''.join(escaped)


# This was useful for debugging.
def ShowFdState():
  # type: () -> None
  import subprocess
  import posix_ as posix
  subprocess.call(['ls', '-l', '/proc/%d/fd' % posix.getpid()])


class DebugFile(object):
  def __init__(self, f):
    # type: (IO[str]) -> None
    self.f = f

  def log(self, msg, *args):
    # type: (str, *Any) -> None
    if args:
      msg = msg % args
    self.f.write(msg)
    self.f.write('\n')
    self.f.flush()  # need to see it interacitvely

  # These two methods are for node.PrettyPrint()
  def write(self, s):
    # type: (str) -> None
    self.f.write(s)

  def isatty(self):
    # type: () -> bool
    return self.f.isatty()


class NullDebugFile(DebugFile):

  def __init__(self):
    # type: () -> None
    pass

  def log(self, msg, *args):
    # type: (str, *Any) -> None
    pass

  def write(self, s):
    # type: (str) -> None
    pass

  def isatty(self):
    # type: () -> bool
    return False
