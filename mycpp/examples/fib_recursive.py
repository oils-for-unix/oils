#!/usr/bin/python
"""
fib_recursive.py
"""
from __future__ import print_function

import os

from mylib import log


def fib_recursive(n):
  # type: (int) -> int
  if n == 0:
    return 1
  if n == 1:
    return 1
  return fib_recursive(n-1) + fib_recursive(n-2)


def run_tests():
  # type: () -> None
  x = 33

  # NOTE: This is very slow and should be separated
  result = fib_recursive(x)
  log('fib_recursive(%d) = %d', x, result)


def run_benchmarks():
  # type: () -> None
  n = 1  # Just one iteration is enough

  x = 33
  result = -1

  i = 0
  while i < n:
    result = fib_recursive(x)
    i += 1
  log('fib_recursive(%d) = %d', x, result)


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
