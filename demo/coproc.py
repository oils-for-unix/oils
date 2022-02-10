#!/usr/bin/env python2
"""
coproc.py
"""

import sys


def main(argv):
  print >>sys.stderr, argv
  try:
    command = argv[1]
  except IndexError:
    command = 'upper'

  if command == 'upper':
    func = lambda x: x.upper()
  else:
    func = lambda x: x.lower()

  while True:
    line = sys.stdin.readline()
    if not line:
      print >>sys.stderr, 'DONE %s' % command
      break
    sys.stdout.write(func(line))
    # If we don't do this, it hangs forever
    sys.stdout.flush()


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
