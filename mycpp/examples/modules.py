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
  n = 100000
  while i < n:
    run_tests()
    i = i + 1


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
