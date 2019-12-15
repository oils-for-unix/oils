#!/usr/bin/env python2
"""
tuple_return_value.py
"""
from __future__ import print_function

import os

from mylib import log

from typing import Tuple, List


def f(x):
  # type: (int) -> Tuple[int, str]

  i = x + 42
  s = 'foo'

  return i, s


def run_tests():
  # type: () -> None

  i, s = f(0)
  log("i = %d", i)
  log("s = %s", s)

  items = []  # type: List[Tuple[int, str]]
  items.append((43, 'bar'))
  log('length = %d', len(items))


  mytuple = (44, 'spam')
  myint, mystr = mytuple


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
