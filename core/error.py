"""
error.py
"""
from __future__ import print_function

from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import loc_t


# Break circular dependency.
#from asdl import runtime
NO_SPID = -1

class Usage(Exception):
  """For flag parsing errors in builtins and main()
  
  Called by e_usage().  TODO: Should settle on a single interface that can be
  translated.  Sometimes we use 'raise error.Usage()'
  """
  def __init__(self, msg, span_id=NO_SPID):
    # type: (str, int) -> None
    self.msg = msg
    self.span_id = span_id


class _ErrorWithLocation(Exception):
  """A parse error that can be formatted.

  Formatting is in ui.PrintError.
  """
  def __init__(self, msg, location):
    # type: (str, loc_t) -> None
    #Exception.__init__(self)
    self.msg = msg
    self.location = location

  def HasLocation(self):
    # type: () -> bool
    #print('*** %r', self.location)

    # TODO: move log() to mycpp/mylib.py, and put this at the top
    from _devbuild.gen.syntax_asdl import loc_e

    if self.location:
      return self.location.tag_() != loc_e.Missing
    else:
      return False

  def UserErrorString(self):
    # type: () -> str
    return self.msg

  def __repr__(self):
    # type: () -> str
    return '<%s %r>' % (self.msg, self.location)


class Runtime(Exception):
  """An error that's meant to be caught, i.e. it's non-fatal.
  
  Thrown by core/state.py and caught by builtins
  """

  def __init__(self, msg):
    # type: (str) -> None
    self.msg = msg

  def UserErrorString(self):
    # type: () -> str
    return self.msg


class Parse(_ErrorWithLocation):
  """Used in the parsers."""
  def __init__(self, msg, location):
    # type: (str, loc_t) -> None
    _ErrorWithLocation.__init__(self, msg, location)


class FailGlob(_ErrorWithLocation):
  """Raised when a glob matches nothing when failglob is set.

  Meant to be caught.
  """

  def __init__(self, msg, location):
    # type: (str, loc_t) -> None
    _ErrorWithLocation.__init__(self, msg, location)


class RedirectEval(_ErrorWithLocation):
  """Used in the CommandEvaluator.

  A bad redirect causes the SimpleCommand to return with status 1.  To make it
  fatal, use set -o errexit.
  """
  def __init__(self, msg, location):
    # type: (str, loc_t) -> None
    _ErrorWithLocation.__init__(self, msg, location)


class FatalRuntime(_ErrorWithLocation):
  """An exception that propagates to the top level.

  Used in the evaluators, and also also used in test builtin for invalid
  argument.
  """
  def __init__(self, exit_status, msg, location):
    # type: (int, str, loc_t) -> None
    _ErrorWithLocation.__init__(self, msg, location)
    self.exit_status = exit_status

  def ExitStatus(self):
    # type: () -> int
    return self.exit_status


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
  def __init__(self, msg, location):
    # type: (str, loc_t) -> None
    FatalRuntime.__init__(self, 1, msg, location)


class ErrExit(FatalRuntime):
  """For set -e.

  Travels between WordEvaluator and CommandEvaluator.
  """
  def __init__(self, exit_status, msg, location, show_code=False):
    # type: (int, str, loc_t, bool) -> None
    FatalRuntime.__init__(self, exit_status, msg, location)
    self.show_code = show_code


class Expr(FatalRuntime):
  """ e.g. KeyError, IndexError, ZeroDivisionError """

  def __init__(self, msg, location):
    # type: (str, loc_t) -> None

    # Unique status of 3 for expression errors -- for both the caught and
    # uncaught case.
    #
    # Caught: try sets _status register to 3
    # Uncaught: shell exits with status 3
    FatalRuntime.__init__(self, 3, msg, location)
