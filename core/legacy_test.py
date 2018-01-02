#!/usr/bin/python -S
"""
legacy_test.py: Tests for legacy.py
"""

import unittest

from core import legacy  # module under test


class SplitTest(unittest.TestCase):

  def testIfsSplitEmpty(self):
    self.assertEqual(
        [''], legacy.IfsSplit('', ' \t\n'))
    self.assertEqual(
        ['', ''], legacy.IfsSplit(' ', ' \t\n'))
    self.assertEqual(
        [''], legacy.IfsSplit('', ' '))

    # No word splitting when no IFS.  Hm.
    self.assertEqual(
        [''], legacy.IfsSplit('', ''))

  def testIfsSplit(self):
    self.assertEqual(
        ['', 'foo', 'bar', ''],
        legacy.IfsSplit('\tfoo bar\n', ' \t\n'))

    self.assertEqual(
        ['\tfoo bar\n'],
        legacy.IfsSplit('\tfoo bar\n', ''))

    self.assertEqual(
        ['a', '', 'd'],
        legacy.IfsSplit('abcd', 'bc'))

  def testIfsSplit_Mixed(self):
    self.assertEqual(
        ['a', 'cd'],
        legacy.IfsSplit('abcd', ' b'))

    # IFS whitespace rule
    self.assertEqual(
        ['a', 'c'],
        legacy.IfsSplit('abc', 'b '))

    self.assertEqual(
        ['a', 'c'],
        legacy.IfsSplit('a c', 'b '))

    self.assertEqual(
        ['a', '', 'c'],
        legacy.IfsSplit('abbc', 'b '))

    self.assertEqual(
        ['', 'a', '', '', 'cd', ''],
        legacy.IfsSplit('\ta b\tb cd\n', 'b \t\n'))

    self.assertEqual(
        ['', 'a', 'cd', ''],
        legacy.IfsSplit('\tabcd\n', 'b \t\n'))

  def testIfsSplit_Mixed2(self):
    # Doesn't work yet
    return
    self.assertEqual(
        ['a', '', '', 'b'],
        legacy.IfsSplit('a _  _ _  b', '_ '))

  def testIfsSplitWhitespaceOnly(self):
    # No non-whitespace IFS
    self.assertEqual(
        ['', 'a', 'c', ''],
        legacy.IfsSplit(' a c ', ' '))

    self.assertEqual(
        ['', 'c'],
        legacy.IfsSplit(' c', ' \t\n'))

  def testIfsSplitNonWhitespaceOnly(self):
    self.assertEqual(
        ['a', 'c'],
        legacy.IfsSplit('a_c', '_'))

    self.assertEqual(
        ['', ''],
        legacy.IfsSplit('_', '_'))


if __name__ == '__main__':
  unittest.main()
