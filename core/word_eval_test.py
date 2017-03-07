#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
word_eval_test.py: Tests for word_eval.py
"""

import unittest

import word_eval  # module under test


class SplitTest(unittest.TestCase):

  def testIfsSplitEmpty(self):
    self.assertEqual(
        [], word_eval._IfsSplit('', ' \t\n'))
    self.assertEqual(
        [], word_eval._IfsSplit(' ', ' \t\n'))
    self.assertEqual(
        [], word_eval._IfsSplit('', ' '))

    # No word splitting when no IFS.  Hm.
    self.assertEqual(
        [''], word_eval._IfsSplit('', ''))

  def testIfsSplit(self):
    self.assertEqual(
        ['foo', 'bar'],
        word_eval._IfsSplit('\tfoo bar\n', ' \t\n'))

    self.assertEqual(
        ['\tfoo bar\n'],
        word_eval._IfsSplit('\tfoo bar\n', ''))

    self.assertEqual(
        ['a', '', 'd'],
        word_eval._IfsSplit('abcd', 'bc'))

    self.assertEqual(
        ['a', 'cd'],
        word_eval._IfsSplit('abcd', ' b'))

    # IFS whitespace rule
    self.assertEqual(
        ['a', 'c'],
        word_eval._IfsSplit('abc', 'b '))

    self.assertEqual(
        ['a', 'c'],
        word_eval._IfsSplit('a c', 'b '))

    self.assertEqual(
        ['a', '', 'c'],
        word_eval._IfsSplit('abbc', 'b '))

    self.assertEqual(
        ['a', '', '', 'cd'],
        word_eval._IfsSplit('\ta b\tb cd\n', 'b \t\n'))

    self.assertEqual(
        ['a', 'cd'],
        word_eval._IfsSplit('\tabcd\n', 'b \t\n'))

    # No non-whitespace IFS
    self.assertEqual(
        ['a', 'c'],
        word_eval._IfsSplit(' a c ', ' '))


if __name__ == '__main__':
  unittest.main()
