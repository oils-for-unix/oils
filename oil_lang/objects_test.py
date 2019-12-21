#!/usr/bin/env python2
"""
objects_test.py: Tests for objects.py
"""
from __future__ import print_function

import unittest

from oil_lang import objects  # module under test


class ObjectsTest(unittest.TestCase):

  def testArrays(self):
    a = objects.IntArray([1, 2, 3])
    print(a)


if __name__ == '__main__':
  unittest.main()
