"""
pyerror.py -- Wrappers for raising exceptions.

Like pyutil.py, this code is only needed in Python.  In C++ they have different
implementations.  This file has fewer deps than pyutil.py.
"""
from __future__ import print_function

import sys

from core import error
from mycpp import mylib

from typing import NoReturn, Any, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import loc_t


if mylib.PYTHON:
  def log(msg, *args):
    # type: (str, *Any) -> None
    if args:
      msg = msg % args
    print(msg, file=sys.stderr)


NO_SPID = -1

def e_usage(msg, span_id=NO_SPID):
  # type: (str, int) -> NoReturn
  """Convenience wrapper for arg parsing / validation errors.

  Usually causes a builtin to fail with status 2, but the script can continue
  if 'set +o errexit'.  Main programs like bin/oil also use this.

  Caught by

  - RunAssignBuiltin and RunBuiltin, with optional LOCATION INFO
  - various main() programs, without location info

  Probably should separate these two cases?

  - builtins pass Token() or loc::Missing()
  - tool interfaces don't pass any location info
  """
  raise error.Usage(msg, span_id)


def e_strict(msg, location):
  # type: (str, loc_t) -> NoReturn
  """Convenience wrapper for strictness errors.

  Like e_die(), except the script MAY continue executing after these errors.

  TODO: This could have a level too?
  """
  raise error.Strict(msg, location)


def p_die(msg, location):
  # type: (str, loc_t) -> NoReturn
  """Convenience wrapper for parse errors.

  Exits with status 2.  See core/main_loop.py.
  """
  raise error.Parse(msg, location)


def e_die(msg, location=None):
  # type: (str, loc_t) -> NoReturn
  """Convenience wrapper for fatal runtime errors.

  Usually exits with status 1.  See osh/cmd_eval.py.
  """
  raise error.FatalRuntime(1, msg, location)


def e_die_status(status, msg, location=None):
  # type: (int, str, loc_t) -> NoReturn
  """Wrapper for C++ semantics
  
  To avoid confusing e_die(int span_id) and e_die(int status)!

  Note that it doesn't take positional args, so you should use % formatting.
  """
  raise error.FatalRuntime(status, msg, location)
