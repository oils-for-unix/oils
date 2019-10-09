#!/usr/bin/env python2
"""
hoist.py
"""
from __future__ import print_function

import sys


def run_tests():
  # type: () -> None

  x = 1
  if x > 0:
    s = 'greater'
  else:
    s = 'less'
  print(s)
  return s


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
