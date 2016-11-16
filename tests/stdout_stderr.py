#!/usr/bin/python3
"""
stdout_stderr.py

Tool for testing redirects.
"""

import sys


def main(argv):
  try:
    stdout = argv[1]
    stderr = argv[2]
  except IndexError:
    stdout = 'STDOUT'
    stderr = 'STDERR'
  print(stdout)
  print(stderr, file=sys.stderr)

if __name__ == '__main__':
  main(sys.argv)
