#!/usr/bin/python -S
"""
os_path_test.py: Tests for os_path.py
"""
from __future__ import print_function

import unittest

from core import os_path  # module under test


class OsPathTest(unittest.TestCase):

  def testPathExists(self):
    self.assertEqual(True, os_path.exists('/'))
    self.assertEqual(False, os_path.exists('/nonexistent__ZZZZ'))


if __name__ == '__main__':
  unittest.main()
