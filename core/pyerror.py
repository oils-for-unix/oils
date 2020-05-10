#!/usr/bin/env python2
"""
pyerror.py -- Wrappers for raising exceptions.

These functions have different implementations in C++.
"""
from __future__ import print_function

from typing import NoReturn, Any


# TODO: Move log, p_die, and e_die here too.

def e_usage(msg, *pos_args, **kwargs):
  # type: (str, *Any, **Any) -> NoReturn
  """Convenience wrapper for arg parsing / validation errors.

  Usually causes a builtin to fail with status 2, but the script can continue
  if 'set +o errexit'.  Main programs like bin/oil also use this.
  """
  from core import error
  raise error.Usage(msg, *pos_args, **kwargs)
