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

from mycpp import mylib
from typing import Any


class UserExit(Exception):
  """For explicit 'exit'."""
  def __init__(self, status):
    # type: (int) -> None
    self.status = status


class HistoryError(Exception):

  def __init__(self, msg):
    # type: (str) -> None
    if mylib.PYTHON:
      Exception.__init__(self)

    self.msg = msg

  def UserErrorString(self):
    # type: () -> str
    return 'history: %s' % self.msg


class _DebugFile(object):

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


class NullDebugFile(_DebugFile):

  def __init__(self):
    # type: () -> None
    """Empty constructor for mycpp."""
    _DebugFile.__init__(self)


class DebugFile(_DebugFile):
  def __init__(self, f):
    # type: (mylib.Writer) -> None
    _DebugFile.__init__(self)
    self.f = f

  def log(self, msg, *args):
    # type: (str, *Any) -> None
    if mylib.PYTHON:  # remove dynamic format
      if args:
        msg = msg % args
    self.f.write(msg)
    self.f.write('\n')
    self.f.flush()  # need to see it interactively

  def write(self, s):
    # type: (str) -> None
    """Used by dev::Tracer and ASDL node.PrettyPrint()."""
    self.f.write(s)

  def isatty(self):
    # type: () -> bool
    """Used by node.PrettyPrint()."""
    return self.f.isatty()
