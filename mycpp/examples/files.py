#!/usr/bin/python
"""
files.py: Write to filesj
"""
from __future__ import print_function

import os
import sys

from runtime import log, Buf


def run_tests():
  # type: () -> None

  f = Buf()
  for i in xrange(30):
    f.write(chr(i + 65))

  contents = f.getvalue()
  log('Wrote %d bytes to StringIO', len(contents))
  log('contents = %s ... %s', contents[:10], contents[-10:])

  # TODO:
  #f = sys.stdout
  #f.write('stdout\n')


def run_benchmarks():
  # type: () -> None
  n = 10000

  result = 0

  i = 0
  while i < n:
    f = Buf()
    for j in xrange(30):
      f.write(chr(i + 65))

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
