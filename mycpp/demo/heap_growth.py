#!/usr/bin/env python2
"""
heap_growth.py
"""
from __future__ import print_function

import sys


class Space(object):
  def __init__(self, space_size):
    self.filled_size = 0
    self.space_size = space_size


def Simulate(spaces, alloc_sizes):
  # TODO:
  # - how to simulate garbage too
  # - simulate semi-spaces
  # - eventually we could TIGHTEN the heap?  Actually we might get that for
  #   free?

  # Input:
  # - Stream of Allocation Sizes
  # Output:
  # - Whether we should collect now
  #   - this happens as rarely as possible, only when we have no space
  # - Whether we should grow, and HOW MUCH (2x, 4x)
  #   - this happens AFTER a collection, if we don't have much space left
  #   - And we try to keep the sizes even

  space = spaces[0]

  for i, a in enumerate(alloc_sizes):
    if space.filled_size + a > space.space_size:
      do_collect = True
    else:
      do_collect = False

    # Assume we didn't collect anything
    while float(space.filled_size) / space.space_size >= 0.8:
      space.space_size *= 2

    space.filled_size += a

    yield a, space.filled_size, space.space_size, do_collect


def main(argv):
  initial_size = 256
  spaces = [Space(initial_size), Space(initial_size)]

  fmt = '%10s %10s %10s %10s'
  print(fmt % ('alloc', 'filled', 'space max', 'collect'))

  #alloc_sizes = range(50, 100)
  alloc_sizes = range(0, 10000, 400)  # big allocations
  for row in Simulate(spaces, alloc_sizes):
    print(fmt % row)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
