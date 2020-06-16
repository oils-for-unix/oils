#!/usr/bin/env python2
"""
pyerror.py -- Wrappers for raising exceptions.

These functions have different implementations in C++.
"""
from __future__ import print_function

import sys

from core import error
from typing import NoReturn, Any


def log(msg, *args):
  # type: (str, *Any) -> None
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def e_usage(msg, *pos_args, **kwargs):
  # type: (str, *Any, **Any) -> NoReturn
  """Convenience wrapper for arg parsing / validation errors.

  Usually causes a builtin to fail with status 2, but the script can continue
  if 'set +o errexit'.  Main programs like bin/oil also use this.
  """
  raise error.Usage(msg, *pos_args, **kwargs)


def e_strict(msg, *args, **kwargs):
  # type: (str, *Any, **Any) -> NoReturn
  """Convenience wrapper for strictness errors.

  Like e_die(), except the script MAY continue executing after these errors.

  TODO: This could have a level too?
  """
  raise error.Strict(msg, *args, **kwargs)


def p_die(msg, *args, **kwargs):
  # type: (str, *Any, **Any) -> NoReturn
  """Convenience wrapper for parse errors.

  Exits with status 2.  See core/main_loop.py.
  """
  raise error.Parse(msg, *args, **kwargs)


def e_die(msg, *args, **kwargs):
  # type: (str, *Any, **Any) -> NoReturn
  """Convenience wrapper for fatal runtime errors.

  Usually exits with status 1.  See osh/cmd_eval.py.
  """
  raise error.FatalRuntime(msg, *args, **kwargs)
