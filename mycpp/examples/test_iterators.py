#!/usr/bin/env python2
"""
iterators.py: Simple iterators
"""
from __future__ import print_function

import os

from mycpp import mylib
from mycpp.mylib import log, iteritems

from typing import Iterator, Tuple


def g(n):
  # type: (int) -> Iterator[Tuple[int, str]]
  for i in f(n):
    yield (i, '2 * %d = %d' % (i, 2*i))


def f(n):
  # type: (int) -> Iterator[int]
  for i in xrange(0, n):
    yield i


class Foo(object):

  def __init__(self):
    # type: () -> None
    pass

  def bar(self, n):
    # type: (int) -> Iterator[int]
    for i in xrange(0, n):
      yield i

  def baz(self, n):
    # type: (int) -> Iterator[Tuple[int, str]]
    it_g = g(n)
    while True:
      try:
        yield it_g.next()
      except StopIteration:
        break


def run_tests():
  # type: () -> None
  log('--- simple iterators')
  for i in f(3):
    log("f() gave %d", i)

  foo = Foo()
  for i in foo.bar(4):
    log("Foo.bar() gave %d", i)

  log('--- nested iterators')
  for i, s in g(3):
    log("g() gave (%d, %r)", i, s)

  for i, s in foo.baz(3):
    log("Foo.baz() gave (%d, %r)", i, s)

  for i in f(3):
    for j in f(3):
      log("f() gave %d, %d", i, j)

  log('--- iterator assignment')
  it_f = f(5)
  while True:
    try:
      log("next(f()) gave %d", it_f.next())
    except StopIteration:
      break

  it_g = g(5)
  while True:
    try:
      i, s = it_g.next()
      log("next(g()) gave (%d, %r)", i, s)
    except StopIteration:
      break

  it = f(5)
  l = list(it)
  for i, x in enumerate(l):
    log("l[%d] = %d", i, x)


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
