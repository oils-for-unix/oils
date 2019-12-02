#!/usr/bin/env python2
"""
error.py
"""
from __future__ import print_function

from mycpp import mylib

from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:  # avoid circular build deps
  from _devbuild.gen.syntax_asdl import Token, word_part_t, word_t

# Break circular dependency.
#from asdl import runtime
NO_SPID = -1


if mylib.PYTHON:
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
      self.span_id = kwargs.pop('span_id', NO_SPID)  # type: int
      self.token = kwargs.pop('token', None)  # type: Token
      self.part = kwargs.pop('part', None)  # type: word_part_t
      self.word = kwargs.pop('word', None)  # type: word_t
      self.exit_status = kwargs.pop('status', None)  # type: int
      if kwargs:
        raise AssertionError('Invalid keyword args %s' % kwargs)

    def HasLocation(self):
      # type: () -> bool
      return bool(self.span_id != NO_SPID or
                  self.token or self.part or self.word)

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


# Need a better constructor
if mylib.PYTHON:
  class Parse(_ErrorWithLocation):
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


class RedirectEval(_ErrorWithLocation):
  """Used in the Executor.

  A bad redirect causes the SimpleCommand to return with status 1.  To make it
  fatal, use set -o errexit.
  """


class FatalRuntime(_ErrorWithLocation):
  """An exception that propagates to the top level.

  Used in the evaluators, and also also used in test builtin for invalid
  argument.
  """


class InvalidSlice(FatalRuntime):
  """Whether this is fatal depends on set -o strict-word-eval.
  """


class InvalidUtf8(FatalRuntime):
  """Whether this is fatal depends on set -o strict-word-eval.
  """


class ErrExit(FatalRuntime):
  """For set -e.

  Travels between WordEvaluator and Executor.
  """
