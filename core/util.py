#!/usr/bin/env python
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

import posix
import sys

from asdl import const

from typing import IO, NoReturn, Any, TYPE_CHECKING
if TYPE_CHECKING:  # avoid circular build deps
  from _devbuild.gen.syntax_asdl import token, word_part_t, word_t


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


class _ErrorWithLocation(Exception):
  """A parse error that can be formatted.

  Formatting is in ui.PrintError.
  """
  def __init__(self, msg, *args, **kwargs):
    # type: (str, *Any, **Any) -> None
    Exception.__init__(self)
    self.msg = msg
    self.args = args
    # NOTE: We use a kwargs dict because Python 2 doesn't have keyword-only
    # args.
    self.span_id = kwargs.pop('span_id', const.NO_INTEGER)  # type: int
    self.token = kwargs.pop('token', None)  # type: token
    self.part = kwargs.pop('part', None)  # type: word_part_t
    self.word = kwargs.pop('word', None)  # type: word_t
    self.exit_status = kwargs.pop('status', None)  # type: int
    if kwargs:
      raise AssertionError('Invalid keyword args %s' % kwargs)

  def __repr__(self):
    # type: () -> str
    return '<%s %s %r %r %s>' % (
        self.msg, self.args, self.token, self.word, self.exit_status)

  def __str__(self):
    # type: () -> str
    # The default doesn't work very well?
    return repr(self)

  def UserErrorString(self):
    # type: () -> str
    return self.msg % self.args


class ParseError(_ErrorWithLocation):
  """Used in the parsers.

  TODO:
  - This could just be FatalError?
  - You might want to catch this and add multiple locations?
    try:
      foo
    except ParseError as e:
      e.AddErrorInfo('hi', token=t)
      raise
  """
  pass


class FatalRuntimeError(_ErrorWithLocation):
  """Used in the evaluators.

  Also used in test builtin for invalid argument.
  """
  pass


class InvalidSlice(FatalRuntimeError):
  """Whether this is fatal depends on set -o strict-word-eval.
  """
  pass


class InvalidUtf8(FatalRuntimeError):
  """Whether this is fatal depends on set -o strict-word-eval.
  """
  pass


class ErrExitFailure(FatalRuntimeError):
  """For set -e.

  Travels between WordEvaluator and Executor.
  """
  pass


def p_die(msg, *args, **kwargs):
  # type: (str, *Any, **Any) -> NoReturn
  """Convenience wrapper for parse errors."""
  raise ParseError(msg, *args, **kwargs)


def e_die(msg, *args, **kwargs):
  # type: (str, *Any, **Any) -> NoReturn
  """Convenience wrapper for runtime errors."""
  raise FatalRuntimeError(msg, *args, **kwargs)


def log(msg, *args):
  # type: (str, *Any) -> None
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def warn(msg, *args):
  # type: (str, *Any) -> None
  if args:
    msg = msg % args
  print('osh warning: ' + msg, file=sys.stderr)


# NOTE: This should say 'oilc error' or 'oil error', instead of 'osh error' in
# some cases.
def error(msg, *args):
  # type: (str, *Any) -> None
  if args:
    msg = msg % args
  print('osh error: ' + msg, file=sys.stderr)


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
