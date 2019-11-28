#!/usr/bin/env python2
"""
oheap2_test.py: Tests for oheap2.py
"""
from __future__ import print_function

import unittest

from ovm2 import oheap2  # module under test


class Oheap2Test(unittest.TestCase):

  def testAlign4(self):
    self.assertEqual(0, oheap2.Align4(0))
    self.assertEqual(4, oheap2.Align4(1))
    self.assertEqual(4, oheap2.Align4(3))
    self.assertEqual(4, oheap2.Align4(4))
    self.assertEqual(8, oheap2.Align4(5))

  def testAlign16(self):
    self.assertEqual(0, oheap2.Align16(0))
    self.assertEqual(16, oheap2.Align16(1))
    self.assertEqual(16, oheap2.Align16(15))
    self.assertEqual(16, oheap2.Align16(16))
    self.assertEqual(32, oheap2.Align16(17))


if __name__ == '__main__':
  unittest.main()
