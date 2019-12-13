#!/usr/bin/env python2
"""
sizelog.py
"""
from __future__ import print_function

import sys

import collections


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def main(argv):
  d = collections.defaultdict(list)
  for i, line in enumerate(sys.stdin):
    address, length = line.split()
    count = int(length)
    d[address].append(count)

  log('Read %d items', i)

  # Find the ones with the most
  longest = sorted(d, key=lambda addr: len(d[addr]))

  for addr in longest:
    lengths = d[addr]
    #print('%s %s' % (addr, lengths))
    print('%s %d %d' % (addr, len(lengths), max(lengths)))


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
