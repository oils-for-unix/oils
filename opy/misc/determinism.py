#!/usr/bin/python
"""
determinism.py
"""

import sys


def main(argv):

  s = set()
  #d = {}
  with open(sys.argv[0]) as f:
    for line in f:
      #d[line] = 1
      s.add(line)
      print hash(line)
  #return

  #for line in d:
  #  sys.stdout.write(line)

  print '--'
  for line in s:
    sys.stdout.write(line)
    # NOTE: Detects if set size changed during iteration.
    #s.discard(line)
  print '--'


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
