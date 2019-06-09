#!/usr/bin/env python2
"""
posix_test.py: Tests for posix.py
"""
from __future__ import print_function

import unittest

import posix_  # module under test


class FooTest(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def testFoo(self):
    print(posix_.getcwd())


if __name__ == '__main__':
  unittest.main()
