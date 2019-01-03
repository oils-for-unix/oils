#!/usr/bin/python -S
"""
pyreadline_test.py: Tests for pyreadline.py
"""
from __future__ import print_function

import unittest

import pyreadline  # module under test


# TODO: Unit tests should test some properties of the output!
# How many lines are there, and did it overflow?

class PyReadlineTest(unittest.TestCase):

  def testPrintPacked(self):
    matches = ['foo', 'bar', 'spam', 'eggs', 'python', 'perl']
    longest_match_len = max(len(m) for m in matches)
    for width in (10, 20, 30, 40, 50):
      n = pyreadline.PrintPacked(matches, longest_match_len, width, 10)
      print('Wrote %d lines' % n)
      print('')

  def testTooMany(self):
    matches = ['--flag%d' % i for i in xrange(100)]
    longest_match_len = max(len(m) for m in matches)
    for width in (10, 20, 30, 40, 50, 60):
      n = pyreadline.PrintPacked(matches, longest_match_len, width, 10)
      print('Wrote %d lines' % n)
      print('')


if __name__ == '__main__':
  unittest.main()
