#!/usr/bin/env python2
"""
word_freq.py
"""
from __future__ import print_function

import sys


def main(argv):
  try:
    iters = int(argv[1])
  except IndexError:
    iters = 1000

  text = sys.stdin.read()

  words = {}

  for i in xrange(iters):
    for word in text.split():
      if word in words:
        words[word] += 1
      else:
        words[word] = 1

  for word in words:
    print("%d %s" % (words[word], word))


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
