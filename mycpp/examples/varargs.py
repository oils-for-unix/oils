#!/usr/bin/env python2
"""
varargs.py
"""
from __future__ import print_function

import os

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


def run_tests():
  # type: () -> None

  log("log %d %s", 42, "LL")

  p_die('hello %d %s', 3, "PP", tok='mytok')


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
