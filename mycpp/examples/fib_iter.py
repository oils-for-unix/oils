#!/usr/bin/python
"""
fib.py: Simple Python 2 program to translate to C++.
"""
from __future__ import print_function

import os

from mylib import log


def fib_iter(n):
  # type: (int) -> int
  a = 0
  b = 1
  i = 0 
  while i < n:
    tmp = a + b
    a = b
    b = tmp
    i += 1
  return b


def run_tests():
  # type: () -> None
  x = 33

  result = fib_iter(x)
  log('fib_iter(%d) = %d', x, result)



def run_benchmarks():
  # type: () -> None
  n = 500000

  x = 33
  result = -1

  i = 0
  while i < n:
    result = fib_iter(x)
    i += 1
  log('fib_iter(%d) = %d', x, result)
  log('Ran %d iterations of fib_iter', n)


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
