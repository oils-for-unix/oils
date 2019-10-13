#!/usr/bin/env python2
"""
format_strings_test.py: Tests for format_strings.py
"""
from __future__ import print_function

import unittest

import format_strings  # module under test


class FooTest(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def testParse(self):
    parts = format_strings.Parse('foo [%s]')
    print(parts)

    # literal %
    parts = format_strings.Parse('%d%%')
    print(parts)

    parts = format_strings.Parse('%s %d %s')
    print(parts)


if __name__ == '__main__':
  unittest.main()
