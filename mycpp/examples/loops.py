#!/usr/bin/python
"""
loops.py: Common loops
"""
from __future__ import print_function

import os

from runtime import log


CATS = ['big', 'small', 'hairless']


def run_tests():
  # type: () -> None

  # Tuple unpacking

  mylist = [(1, 'one'), (2, 'two')]
  for i, item in mylist:
    log("- [%d] %s", i, item)

  """
  for i in xrange(3, 10):
    print(i)

  for i, c in enumerate(CATS):
    log('%d %s', i, c)
  """


def run_benchmarks():
  # type: () -> None
  n = 500000

  result = 0

  """
  i = 0
  while i < n:
    for j in xrange(3, 10):
      result += j

    for j, c in enumerate(CATS):
      result += j
      result += len(c)

    i += 1
  log('result = %d', result)
  log('Ran %d iterations of xrange/enumerate', n)
  """


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
