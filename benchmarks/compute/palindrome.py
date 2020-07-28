#!/usr/bin/env python2
"""
unicode.py
"""
from __future__ import print_function

import re
import sys


def main(argv):
  contents = sys.stdin.read()
  code_points = contents.decode('utf-8')

  pat = re.compile('[A-Z]')

  print('len=%d' % len(code_points))

  for i, c in enumerate(code_points):
    #if pat.match(c):
    if True:
      print('%s %s' % (i, c.encode('utf-8')))


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
