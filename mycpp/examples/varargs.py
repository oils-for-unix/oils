#!/usr/bin/env python2
"""
varargs.py
"""
from __future__ import print_function

import os
import sys

import mylib
from mylib import log

from typing import Any


if mylib.PYTHON:
  # This is the Python version.  The C++ version is void p_die(Str *s, token*
  # tok)
  def p_die(msg, *args, **kwargs):
    # type: (str, Any, Any) -> None
    tok = kwargs.get('tok')
    print(tok)

  def e_die(msg, *args, **kwargs):
    # type: (str, Any, Any) -> None
    tok = kwargs.get('tok')
    print(tok)

  def stderr_line(msg, *args):
    # type: (str, Any) -> None
    if args:
      msg = msg % args
    print(msg, file=sys.stderr)


CONST = "myconst"

def run_tests():
  # type: () -> None

  log('constant string')

  stderr_line('stderr_line')

  # Positional args
  log("log %d %s", 42, "LL")

  log(CONST)
  p_die(CONST, span_id=-1)

  # Keyword args give location info for X_die()
  span_id = 123
  p_die('hello %d %s', 3, "PP", span_id=span_id)

  # No keyword arguments
  e_die('hello %d', 42)
  e_die('hello')


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
