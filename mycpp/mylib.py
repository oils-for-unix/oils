"""
runtime.py
"""
from __future__ import print_function

import sys
import cStringIO

from typing import Any

# For conditional translation
CPP = False
PYTHON = True


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


BufWriter = cStringIO.StringIO

BufLineReader = cStringIO.StringIO


def Stdout():
  return sys.stdout


def Stdin():
  return sys.stdin

