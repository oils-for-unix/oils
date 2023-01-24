"""
error.py
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    Token, loc_e, loc_t, loc__Span, loc__WordPart, loc__Word)
from mycpp import mylib
from mycpp.mylib import tagswitch

from typing import Dict, Any, Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:  # avoid circular build deps
  from _devbuild.gen.syntax_asdl import word_part_t, word_t

# Break circular dependency.
#from asdl import runtime
NO_SPID = -1


if mylib.PYTHON:

  def LocationShim(location):
    # type: (Optional[loc_t]) -> Dict[str, Any]
    """ TODO: Remove this and cleanup _ErrorWithLocation constructor. """

    kwargs = {}  # type: Dict[str, Any]

    if location is None:
      kwargs['span_id'] = NO_SPID
    else:
      UP_location = location
      with tagswitch(location) as case:
        if case(loc_e.Missing):
          kwargs['span_id'] = NO_SPID

        elif case(loc_e.Token):
          tok = cast(Token, UP_location)
          kwargs['token'] = tok

        elif case(loc_e.Span):
          location = cast(loc__Span, UP_location)
          kwargs['span_id'] = location.span_id

        elif case(loc_e.WordPart):
          location = cast(loc__WordPart, UP_location)
          kwargs['part'] = location.p

        elif case(loc_e.Word):
          location = cast(loc__Word, UP_location)
          kwargs['word'] = location.w

        else:
          # TODO: fill in other cases
          raise AssertionError()

    return kwargs

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

    def UserErrorString(self):
      # type: () -> str

      if self.args:
        # TODO: this case is obsolete
        return self.msg % self.args
      else:
        return self.msg

    def __repr__(self):
      # type: () -> str
      return '<%s %s %r %r %s>' % (
          self.msg, self.args, self.token, self.word, self.exit_status)

    def __str__(self):
      # type: () -> str
      # The default doesn't work very well?
      return repr(self)


# Need a better constructor
if mylib.PYTHON:
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
      kwargs = LocationShim(location)
      _ErrorWithLocation.__init__(self, msg, **kwargs)


  class FailGlob(_ErrorWithLocation):
    """Raised when a glob matches nothing when failglob is set.

    Meant to be caught.
    """

    def __init__(self, msg, location):
      # type: (str, loc_t) -> None
      kwargs = LocationShim(location)
      _ErrorWithLocation.__init__(self, msg, **kwargs)


  class RedirectEval(_ErrorWithLocation):
    """Used in the CommandEvaluator.

    A bad redirect causes the SimpleCommand to return with status 1.  To make it
    fatal, use set -o errexit.
    """
    def __init__(self, msg, location):
      # type: (str, loc_t) -> None
      kwargs = LocationShim(location)
      _ErrorWithLocation.__init__(self, msg, **kwargs)


  class FatalRuntime(_ErrorWithLocation):
    """An exception that propagates to the top level.

    Used in the evaluators, and also also used in test builtin for invalid
    argument.
    """
    # TODO: Add status, show_code


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
      kwargs = LocationShim(location)
      FatalRuntime.__init__(self, msg, **kwargs)

  class ErrExit(FatalRuntime):
    """For set -e.

    Travels between WordEvaluator and CommandEvaluator.
    """
    # TODO: Add show_code

  class Expr(FatalRuntime):
    """ e.g. KeyError, IndexError, ZeroDivisionError """

    def __init__(self, msg, location):
      # type: (str, loc_t) -> None
      kwargs = LocationShim(location)
      FatalRuntime.__init__(self, msg, **kwargs)

    def ExitStatus(self):
      # type: () -> int
      """For both the caught and uncaught case.
      
      Caught: try sets _status register to 3
      Uncaught: shell exits with status 3
      """
      return 3
