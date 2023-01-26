#!/usr/bin/env python2
"""
test_default_args.py
"""
from __future__ import print_function

import os

from mycpp.mylib import log

from typing import List


def f(x, b=False):
  # type: (int, bool) -> None
  log("x = %d", x)
  log("b = %d", b)


def g(x, s=''):
  # type: (int, str) -> None
  log("x = %d", x)
  log("s = %r", s)


class Foo(object):

  def __init__(self, x, y=42):
    # type: (int, int) -> None
    self.x = x
    self.y = y

  def Print(self):
    # type: () -> None
    log("x = %d", self.x)
    log("y = %d", self.y)


def run_tests():
  # type: () -> None

  f(5)
  f(6, True)
  f(7, b = True)

  g(99, s = 'foo')

  f1 = Foo(8)
  f2 = Foo(9, 43)
  f3 = Foo(0, y = 44)

  f1.Print()
  f2.Print()
  f3.Print()

  # TODO: Remove all the extra GLOBAL_STR() instances for log() and % !

  print("const")
  print("print formatted = %d" % True)

  log("const")
  log("log formatted = %d", True)


def run_benchmarks():
  # type: () -> None
  raise NotImplementedError()


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
