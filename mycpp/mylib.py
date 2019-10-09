"""
runtime.py
"""
from __future__ import print_function

import sys
import cStringIO

from typing import Any


# C code ignores this!
def log(msg, *args):
  # type: (str, *Any) -> None
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


# TODO: Do we need this?
def p_die(msg, *args):
  # type: (str, *Any) -> None
  raise RuntimeError(msg % args)


Buf = cStringIO.StringIO


def StdOut():
  return sys.stdout
