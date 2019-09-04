#!/usr/bin/env python2
from __future__ import print_function
"""
stdout_stderr.py

Tool for testing redirects.
"""

import sys


def main(argv):
  try:
    stdout = argv[1]
    stderr = argv[2]
    status = int(argv[3])
  except IndexError:
    stdout = 'STDOUT'
    stderr = 'STDERR'
    status = 0
  print(stdout)
  print(stderr, file=sys.stderr)
  return status


if __name__ == '__main__':
  sys.exit(main(sys.argv))
