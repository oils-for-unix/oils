#!/usr/bin/env python2
"""
unicode.py
"""
from __future__ import print_function

import re
import sys


def main(argv):
  for line in sys.stdin:
    line = line.rstrip()  # remove newlines and spaces

    if len(line) == 0:  # skip blank lines
      continue

    code_points = line.decode('utf-8')

    n = len(code_points)

    h = n // 2  # floor division

    #print('n = %d, h = %d' % (n, h))

    palindrome = True
    for i in xrange(h):
      if code_points[i] != code_points[n-1-i]:
        palindrome = False
        break

    if palindrome:
      print(line)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
