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

  class Usage(Exception):
    """Raised by builtins upon flag parsing error."""

    # TODO: Should this be _ErrorWithLocation?  Probably, even though we only use
    # 'span_id'.
    def __init__(self, msg, span_id=NO_SPID):
      # type: (str, int) -> None
      self.msg = msg
      self.span_id = span_id


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
      # TODO: Remove these and create a location type.  I think
      # word_.SpanIdFromError() or LocationFromeError can be called when
      # CREATING this exception, not in core/ui.py.
      self.span_id = kwargs.pop('span_id', NO_SPID)  # type: int
      self.token = kwargs.pop('token', None)  # type: Token
      self.part = kwargs.pop('part', None)  # type: word_part_t
      self.word = kwargs.pop('word', None)  # type: word_t

      # Runtime errors have a default status of 1.  Parse errors return 2
      # explicitly.
      self.exit_status = kwargs.pop('status', 1)  # type: int
      self.show_code = kwargs.pop('show_code', False)  # type: bool
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

  class FailGlob(FatalRuntime):
    """Raised when a glob matches nothing when failglob is set."""


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

  class ErrExit(FatalRuntime):
    """For set -e.

    Travels between WordEvaluator and CommandEvaluator.
    """

  class Expr(FatalRuntime):
    """ e.g. KeyError, IndexError, ZeroDivisionError """

    def ExitStatus(self):
      # type: () -> int
      """For both the caught and uncaught case.
      
      Caught: try sets _status register to 3
      Uncaught: shell exits with status 3
      """
      return 3
