#!/usr/bin/env python2
"""
path_stat_test.py: Tests for path_stat.py
"""
from __future__ import print_function

import unittest

from pylib import path_stat  # module under test


class PathStatTest(unittest.TestCase):

  def testPathExists(self):
    self.assertEqual(True, path_stat.exists('.'))
    self.assertEqual(True, path_stat.exists('/'))
    self.assertEqual(True, path_stat.exists('/usr/bin/sh'))
    self.assertEqual(False, path_stat.exists('/nonexistent__ZZZZ'))

  def testIsDir(self):
    self.assertEqual(True, path_stat.isdir('.'))
    self.assertEqual(True, path_stat.isdir('/'))
    self.assertEqual(False, path_stat.isdir('/usr/bin/sh'))
    self.assertEqual(False, path_stat.isdir('/nonexistent__ZZZZ'))

  def testIsFile(self):
    self.assertEqual(False, path_stat.isfile(','))
    self.assertEqual(False, path_stat.isfile('/'))
    self.assertEqual(True, path_stat.isfile('/usr/bin/sh'))
    self.assertEqual(False, path_stat.isfile('/nonexistent__ZZZZ'))


if __name__ == '__main__':
  unittest.main()
