#!/usr/bin/env python2
"""
bubble_sort.py
"""
from __future__ import print_function

import sys


# https://rosettacode.org/wiki/Sorting_algorithms/Bubble_sort#Python
def bubble_sort(seq):
    """Inefficiently sort the mutable sequence (list) in place.
       seq MUST BE A MUTABLE SEQUENCE.
 
       As with list.sort() and random.shuffle this does NOT return 
    """
    changed = True
    while changed:
        changed = False
        for i in xrange(len(seq) - 1):
            #if seq[i] > seq[i+1]:

            # fairer comparison against shell, which doesn't have integers
            if int(seq[i]) > int(seq[i+1]):
                seq[i], seq[i+1] = seq[i+1], seq[i]
                changed = True
    return seq


def main():
  lines = sys.stdin.readlines()
  bubble_sort(lines)
  for line in lines:
    sys.stdout.write(line)


if __name__ == '__main__':
  try:
    main()
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
