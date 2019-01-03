#!/usr/bin/python -S
"""
pyreadline_test.py: Tests for pyreadline.py
"""
from __future__ import print_function

import unittest

import pyreadline  # module under test


class FooTest(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def testPrintPacked(self):
    matches = ['foo', 'bar', 'spam', 'eggs', 'python', 'perl']
    longest_match_len = max(len(m) for m in matches)
    for width in (10, 20, 30, 40, 50):
      n = pyreadline.PrintPacked(matches, longest_match_len, width)
      print('Wrote %d lines' % n)
      print('')


if __name__ == '__main__':
  unittest.main()
