#!/usr/bin/env python2
"""
os_path_test.py: Tests for os_path.py
"""
from __future__ import print_function

import os
import unittest

from pylib import os_path  # module under test


class OsPathTest(unittest.TestCase):

  def testDirname(self):
    CASES = [
        ('', 'foo'),
        ('dir', 'dir/'),
        ('bin', 'bin/foo'),
        ('bin', 'bin//foo'),  # double slashes
        ('/usr//local//bin', '/usr//local//bin//foo'),
        ('///', '///foo'),  # special case of not stripping slashes
        ]
    for expected, d in CASES:
      self.assertEqual(expected, os_path.dirname(d))

  def testSplit(self):
    CASES = [
        (('bin', 'foo'), 'bin/foo'),
        (('bin', 'foo'), 'bin//foo'),  # double slashes
        (('/usr//local//bin', 'foo'), '/usr//local//bin//foo'),
        (('///', 'foo'), '///foo'),  # special case of not stripping slashes
        ]
    for expected, d in CASES:
      self.assertEqual(expected, os_path.split(d))

  def testBasename(self):
    self.assertEqual('bar', os_path.basename('foo/bar'))

  def testJoin(self):
    CASES = [
        ('foo', 'bar'),
        ('foo/', 'bar'),
        ('foo', '/bar'),
        ('', 'bar'),
        ('foo', ''),
        ('', ''),
        ('/', ''),
        ('', '/'),
    ]
    for s1, s2 in CASES:
      # test against the Python stdlib version
      expected = os.path.join(s1, s2)
      print(expected)
      self.assertEqual(expected, os_path.join(s1, s2))


if __name__ == '__main__':
  unittest.main()
