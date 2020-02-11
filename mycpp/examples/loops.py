#!/usr/bin/python
"""
loops.py: Common loops
"""
from __future__ import print_function

import os

import mylib
from mylib import log, iteritems

from typing import Dict


def TestListComp():
  # type: () -> None
  log('--- list comprehension')

  x = [1, 2, 3, 4]

  y = [i*5 for i in x[1:]]

  log("len = %d", len(y))
  log("y[0] = %d", y[0])
  log("y[-1] = %d", y[-1])

  log('--- list comprehension changing type')

  z = ['[%d]' % i for i in x[1:-1]]
  if mylib.PYTHON:
    #log("z = %s", z)
    pass

  log("len = %d", len(z))
  log("z[0] = %s", z[0])
  log("z[-1] = %s", z[-1])

  pairs = [('one', 1), ('two', 2)]
  first = [s for s, _ in pairs]
  for s2 in first:
    log('first = %s', s2)


def TestDict():
  # type: () -> None
  log('--- Dict')
  d = {}  # type: Dict[str, int]
  d['a'] = 99
  d['c'] = 42
  d['b'] = 0

  log('a = %d', d['a'])
  log('b = %d', d['b'])
  log('c = %d', d['c'])

  for k in d:
    log("k = %s", k)

  for k, v in iteritems(d):
    log("k = %s, v = %d", k, v)


CATS = ['big', 'small', 'hairless']


def run_tests():
  # type: () -> None

  log('--- iterate over bytes in string')
  for ch in 'abc':
    log('ch = %s', ch)

  log('--- iterate over items in list')
  for item in ['xx', 'yy']:
    log('item = %s', item)

  # TODO: iterate over items in dict
  # DictIter gives pairs?  Just do .Key() and .Value()?  Hm that makes sense.

  log('--- tuple unpacking')

  list_of_tuples = [(5, 'five'), (6, 'six')]
  for i, item in list_of_tuples:
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

  for i, pair in enumerate(list_of_tuples):
    index, s = pair
    log('%d %d %s', i, index, s)

  # TODO: Note: might want to combine with enumerate?  But we're not using
  # that.  We can specialize it for a list.  ReverseListIter().
  log('--- reversed() list')

  list_of_strings = ['spam', 'eggs']
  for item in reversed(list_of_strings):
    log("- %s", item)

  log('--- reversed() list with tuple unpacking')
  for i, item in reversed(list_of_tuples):
    log("- [%d] %s", i, item)

  TestListComp()

  TestDict()



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
