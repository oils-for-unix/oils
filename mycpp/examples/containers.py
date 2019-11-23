#!/usr/bin/python
"""
container_types.py
"""
from __future__ import print_function

import os
from mylib import log

from typing import List, Tuple, Dict


def ListDemo():
  # type: () -> None
  intlist = []  # type: List[int]
               # NOTE: this annotation is required, or MyPy has a partial type.
               # I thoguht it would be able to infer it from expressions below.

  intlist.append(1)
  intlist.append(2)
  intlist.append(3)
  log("len(intlist) = %d", len(intlist))
  for i in intlist:
    log("i = %d", i)

  log('1? %d', 1 in intlist)
  log('42? %d', 42 in intlist)

  del intlist[:]
  log("len() after del = %d", len(intlist))

  strlist = []  # type: List[str]

  strlist.append('a')
  strlist.append('b')
  log("len(strlist) = %d", len(strlist))
  for s in strlist:
    log("s = %s", s)

  log('a? %d', 'a' in strlist)
  log('foo? %d', 'foo' in strlist)

  #strlist.pop()
  #strlist.pop()
  x = strlist.pop()
  log("len(strlist) = %d", len(strlist))
  # seg fault
  #log("x = %s", x)



class Point(object):
  def __init__(self, x, y):
    # type: (int, int) -> None
    self.x = x
    self.y = y


def TupleDemo():
  # type: () -> None

  t2 = (3, 'hello')  # type: Tuple[int, str]

  # Destructuring
  myint, mystr = t2
  log('myint = %d', myint)
  log('mystr = %s', mystr)

  # Does this ever happen?  Or do we always use destructring?
  #log('t2[0] = %d', t2[0])
  #log('t2[1] = %s', t2[1])

  x = 3
  if x in (3, 4, 5):
    print('yes')
  else:
    print('no')

  p = Point(3, 4)
  if p.x in (3, 4, 5):
    print('yes')
  else:
    print('no')


def DictDemo():
  # type: () -> None

  d = {}  # type: Dict[str, int]
  d['foo'] = 42

  # TODO: implement len(Dict) and Dict::remove() and enable this
  if 0:
    log('len(d) = %d', len(d))

    del d['foo']
    log('len(d) = %d', len(d))


def run_tests():
  # type: () -> None

  ListDemo()
  log('')
  TupleDemo()
  log('')
  DictDemo()


def run_benchmarks():
  # type: () -> None
  n = 1000000
  i = 0
  intlist = []  # type: List[int]
  strlist = []  # type: List[str]
  while i < n:
    intlist.append(i)
    strlist.append("foo")
    i += 1

  log('Appended %d items to 2 lists', n)


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
