#!/usr/bin/python
"""
loops.py: Common loops
"""
from __future__ import print_function

import os

from mylib import log


CATS = ['big', 'small', 'hairless']


def run_tests():
  # type: () -> None

  log('--- tuple unpacking')

  mylist = [(5, 'five'), (6, 'six')]
  for i, item in mylist:
    log("- [%d] %s", i, item)

  log('--- one arg xrange()')

  m = 2
  n = 3

  for j in xrange(m*2):
    log("%d", j)

  log('--- two arg xrange()')

  # TODO: reuse index variable j
  for k in xrange(m+2, n+5):
    log("%d", k)

  log('--- enumerate()')

  for i, c in enumerate(CATS):
    log('%d %s', i, c)

  for i, pair in enumerate(mylist):
    index, s = pair
    log('%d %d %s', i, index, s)


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
