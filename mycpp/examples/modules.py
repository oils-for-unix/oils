#!/usr/bin/python
"""
modules.py
"""
from __future__ import print_function

import os
from runtime import log

from testpkg import module1
from testpkg.module2 import func2


def run_tests():
  # type: () -> None
  module1.func1()
  func2()


def run_benchmarks():
  # type: () -> None
  i = 0
  n = 2000000
  result = 0
  while i < n:
    result += module1.fortytwo()
    i = i + 1
  log('result = %d', result)


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
