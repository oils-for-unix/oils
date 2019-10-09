#!/usr/bin/env python2
"""
hoist.py
"""
from __future__ import print_function

import sys


# Note: To fix this,

# - The self.decl pass in assignments can collect every var, and hoist it up.
# - Or it has to detect USES as well as assignments.
# Or maybe it's good enough if it's assigned in two different blogs to hoist it
# up?


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
