#!/usr/bin/env python2
"""
varargs.py
"""
from __future__ import print_function

import os
import sys

from mycpp import mylib
from mycpp.mylib import log, print_stderr

from typing import Any


CONST = "myconst"

def run_tests():
  # type: () -> None

  log('constant string')

  print_stderr('stderr_line')

  # Positional args
  log("log %d %s", 42, "LL")

  # Escaped %%
  log("[%%] %d %s", 42, "LL")

  log(CONST)


def run_benchmarks():
  # type: () -> None

  # Test the interpreted format strings vs. the compiler!
  # This might not be enough to get over startup time
  for i in xrange(1000):
    log("[%%] %d %s", 42, "LL")


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
