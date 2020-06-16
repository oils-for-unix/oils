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

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
  from mycpp import mylib


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


class DebugFile(object):
  def __init__(self, f):
    # type: (mylib.Writer) -> None
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
