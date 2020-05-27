#!/usr/bin/env python2
"""
mylib_test.py: Tests for mylib.py
"""
from __future__ import print_function

import unittest

from mycpp import mylib  # module under test


class MycppTest(unittest.TestCase):

  def testSplit(self):
    self.assertEqual(('foo', None), mylib.split_once('foo', '='))
    self.assertEqual(('foo', ''), mylib.split_once('foo=', '='))
    self.assertEqual(('foo', 'bar'), mylib.split_once('foo=bar', '='))


if __name__ == '__main__':
  unittest.main()
