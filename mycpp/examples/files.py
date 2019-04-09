#!/usr/bin/python
"""
files.py: Write to filesj
"""
from __future__ import print_function

import os
import sys
import cStringIO

from runtime import log


def run_tests():
  # type: () -> None

  f = cStringIO.StringIO()
  for i in xrange(100):
    f.write(str(i))

  contents = f.getvalue()
  log('Wrote %d bytes to StringIO', len(contents))
  log('contents = %s ... %s', contents[:10], contents[-10:])

  f = sys.stdout
  f.write('stdout\n')


def run_benchmarks():
  # type: () -> None
  n = 10000

  result = 0

  i = 0
  while i < n:
    f = cStringIO.StringIO()
    for j in xrange(100):
      f.write(str(j))

    result += len(f.getvalue())

    i += 1
  log('Ran %d iterations', n)
  log('result = %d', result)


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
