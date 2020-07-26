#!/usr/bin/env python2
"""
fib.py
"""
from __future__ import print_function

import sys


def main(argv):
  try:
    iters = int(argv[1])
  except IndexError:
    iters = 5

  try:
    n = int(argv[2])
  except IndexError:
    n = 10

  i = 0
  while i < iters:
    j = 0
    a = 1
    b = 1

    while j < n:
      a, b = b, a+b
      j += 1

    print(b)

    i += 1


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
