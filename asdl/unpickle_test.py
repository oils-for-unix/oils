#!/usr/bin/python -S
"""
unpickle_test.py: Tests for unpickle.py
"""
from __future__ import print_function

import unittest

from asdl import unpickle  # module under test


class UnpickleTest(unittest.TestCase):

  def testFoo(self):
    with open('_devbuild/osh_asdl.pickle') as f:
      root = unpickle.load_v2_subset(f)
    # TODO: Make some assertions.
    print(root)


if __name__ == '__main__':
  unittest.main()
