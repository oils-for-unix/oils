#!/usr/bin/env python2
"""
typeswitch.py
"""
from __future__ import print_function

import os

from mylib import switch, log


def run_tests():
  # type: () -> None

  x = 5
  with switch(x) as case:
    if case(0):
      print('zero')
      print('zero')

    elif case(1, 2):
      print('one or two')

    elif case(3, 4):
      print('three or four')

    else:
      print('default')
      print('another')


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
