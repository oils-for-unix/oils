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


class _ControlFlow(Exception):
  """Internal execption for control flow.

  break and continue are caught by loops, return is caught by functions.

  NOTE: I tried representing this in ASDL, but in Python the base class has to
  be BaseException.  Also, 'Token' is in syntax.asdl but not runtime.asdl.

  cflow =
    -- break, continue, return, exit
    Shell(Token keyword, int arg)
    -- break, continue
  | OilLoop(Token keyword)
    -- return
  | OilReturn(Token keyword, value val)
  """

  def __init__(self, token, arg):
    # type: (Token, int) -> None
    """
    Args:
      token: the keyword token
    """
    self.token = token
    self.arg = arg

  def IsReturn(self):
    # type: () -> bool

    from _devbuild.gen.id_kind_asdl import Id  # TODO: fix circular dep
    return self.token.id == Id.ControlFlow_Return

  def IsBreak(self):
    # type: () -> bool

    from _devbuild.gen.id_kind_asdl import Id  # TODO: fix circular dep
    return self.token.id == Id.ControlFlow_Break

  def IsContinue(self):
    # type: () -> bool

    from _devbuild.gen.id_kind_asdl import Id  # TODO: fix circular dep
    return self.token.id == Id.ControlFlow_Continue

  def StatusCode(self):
    # type: () -> int
    assert self.IsReturn()
    return self.arg

  def __repr__(self):
    # type: () -> str
    return '<_ControlFlow %s>' % self.token


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

      # Runtime errors have a default status of 1.  Parse errors return 2
      # explicitly.
      self.exit_status = kwargs.pop('status', 1)  # type: int
      if kwargs:
        raise AssertionError('Invalid keyword args %s' % kwargs)

    def HasLocation(self):
      # type: () -> bool
      return bool(self.span_id != NO_SPID or
                  self.token or self.part or self.word)

    def ExitStatus(self):
      # type: () -> int
      return self.exit_status

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
    """Used in the parsers."""

  class RedirectEval(_ErrorWithLocation):
    """Used in the CommandEvaluator.

    A bad redirect causes the SimpleCommand to return with status 1.  To make it
    fatal, use set -o errexit.
    """

  class Runtime(_ErrorWithLocation):
    """A non-fatal runtime error, e.g. for builtins."""


class FatalRuntime(_ErrorWithLocation):
  """An exception that propagates to the top level.

  Used in the evaluators, and also also used in test builtin for invalid
  argument.
  """


class Strict(FatalRuntime):
  """Depending on shell options, these errors may be caught and ignored.

  For example, if options like these are ON:

    set -o strict_arith
    set -o strict_word_eval

  then we re-raise the error so it's caught by the top level.  Otherwise
  we catch it and return a dummy value like '' or -1 (i.e. what bash commonly
  does.)

  TODO: Have levels, like:

  OIL_STRICT_PRINT=2   # print warnings at level 2 and above
  OIL_STRICT_DIE=1  # abort the program at level 1 and above
  """


if mylib.PYTHON:
  class ErrExit(FatalRuntime):
    """For set -e.

    Travels between WordEvaluator and CommandEvaluator.
    """
