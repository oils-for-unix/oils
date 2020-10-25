#!/usr/bin/env python2
"""
signal_def.py
"""
from __future__ import print_function

import signal

from typing import List, Dict, Tuple


def _MakeSignals():
  # type: () -> Dict[str, int]
  """Piggy-back on CPython to get a list of portable signals.

  When Oil is ported to C, we might want to do something like bash/dash.
  """
  names = {}  # type: Dict[str, int]
  for name in dir(signal):
    # don't want SIG_DFL or SIG_IGN
    if name.startswith('SIG') and not name.startswith('SIG_'):
      int_val = getattr(signal, name)
      abbrev = name[3:]
      names[abbrev] = int_val
  return names


def GetNumber(sig_spec):
  # type: (str) -> int
  return _SIGNAL_NAMES.get(sig_spec)


_SIGNAL_NAMES = _MakeSignals()


_BY_NUMBER = _SIGNAL_NAMES.items()
_BY_NUMBER.sort(key=lambda x: x[1])


def AllNames():
  # type: () -> List[Tuple[str, int]]
  return _BY_NUMBER

