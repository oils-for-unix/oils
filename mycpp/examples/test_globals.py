#!/usr/bin/env python2
"""
test_globals.py
"""
from __future__ import print_function

import os

from mycpp import mylib
from mycpp.mylib import log

_ = log  # this assignment is ignored
unused = log  # this too

from typing import List


class MyClass(object):

  def __init__(self, x):
    # type: (int) -> None
    self.x = x

  def Print(self):
    # type: () -> None
    log("x = %d", self.x)


# Note: the C++ code for this object uses GC_CLASS_SCANNED / HeapTag::Scanned,
# but HeapTag::Global would make more sense.
#
# So it gets put in the mark set, but it doesn't cause a crash because it's
# never in the live_objs_ list, and thus not considered for sweeping.

gFoo = MyClass(5)


def f():
  # type: () -> None
  gFoo.Print()


def g(x):
  # type: (int) -> int
  print("g %d" % x)
  return x


def run_tests():
  # type: () -> None

  for i in xrange(10):
    f()
    mylib.MaybeCollect()

    new_obj = MyClass(42)
    new_obj.Print()

  for j in xrange(3):
    # _ = g(j)  # hm doesn't work

    # This satisfies lint, the type checker, and is translated correctly by
    # mycpp
    unused = g(j)


def run_benchmarks():
  # type: () -> None
  raise NotImplementedError()


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
