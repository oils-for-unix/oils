#!/usr/bin/env python2
"""
mycpp/examples/arith_ops.py
"""
from __future__ import print_function

import os
from mycpp.mylib import log


def run_tests():
  # type: () -> None

  for i in xrange(8):
    log("%d // 3 = %d", i, i // 3)

  log('');

  # SEMANTIC DIFFERENCE with negative numbers:
  #
  # - Python: -1 / 3 == -1 and
  #           -4 / 3 == -2
  #           it rounds toward negative infinity
  # - C++:    -1 / 3 == 0
  #           -4 / 3 == -1
  #           it rounds toward zero

  # TODO: We could create a function like python_div() to make them identical?

  if 0:
    for i in xrange(8):
      log("%d // 3 = %d", -i, -i // 3)


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
