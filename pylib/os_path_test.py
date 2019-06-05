#!/usr/bin/env python2
"""
os_path_test.py: Tests for os_path.py
"""
from __future__ import print_function

import unittest

from pylib import os_path  # module under test


class OsPathTest(unittest.TestCase):

  def testBasename(self):
    self.assertEqual('bar', os_path.basename('foo/bar'))


if __name__ == '__main__':
  unittest.main()
