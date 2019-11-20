#!/usr/bin/env python2
"""
string_ops_test.py: Tests for string_ops.py
"""
from __future__ import print_function

import unittest

from core import error
from osh import string_ops  # module under test


class LibStrTest(unittest.TestCase):

  def testUtf8Encode(self):
    CASES = [
        (u'\u0065'.encode('utf-8'), 0x0065),
        (u'\u0100'.encode('utf-8'), 0x0100),
        (u'\u1234'.encode('utf-8'), 0x1234),
        (u'\U00020000'.encode('utf-8'), 0x00020000),
        # Out of range gives Unicode replacement character.
        ('\xef\xbf\xbd', 0x10020000),
        ]

    for expected, code_point in CASES:
      print('')
      print('Utf8Encode case %r %r' % (expected, code_point))
      self.assertEqual(expected, string_ops.Utf8Encode(code_point))

  def test_NextUtf8Char(self):
    CASES = [
        ([1, 3, 6, 10], '\x24\xC2\xA2\xE0\xA4\xB9\xF0\x90\x8D\x88'),
        ([1, 3, 'Invalid UTF-8 continuation byte'], '\x24\xC2\xA2\xE0\xE0\xA4'),
        ([1, 3, 6, 'Invalid start of UTF-8 character'], '\x24\xC2\xA2\xE0\xA4\xA4\xB9'),
        ([1, 3, 'Invalid start of UTF-8 character'], '\x24\xC2\xA2\xFF'),
        ([1, 'Incomplete UTF-8 character'], '\x24\xF0\x90\x8D'),
    ]
    for expected_indexes, input_str in CASES:
      print()
      print('_NextUtf8Char case %r %r' % (expected_indexes, input_str))
      i = 0
      actual_indexes = []
      while True:
        try:
          i = string_ops._NextUtf8Char(input_str, i)
          actual_indexes.append(i)
          if i >= len(input_str):
            break
        except error.InvalidUtf8 as e:
          actual_indexes.append(e.msg)
          break
      self.assertEqual(expected_indexes, actual_indexes)

  def test_PreviousUtf8Char(self):
    # The error messages could probably be improved for more consistency
    # with NextUtf8Char, at the expense of more complexity.
    CASES = [
        ([6, 3, 1, 0], '\x24\xC2\xA2\xE0\xA4\xB9\xF0\x90\x8D\x88'),
        ([6, 3, 1, 'Invalid start of UTF-8 character'], '\xA2\xC2\xA2\xE0\xA4\xB9\xF0\x90\x8D\x88'),
        ([10, 'Invalid start of UTF-8 character'], '\xF0\x90\x8D\x88\x90\x8D\x88\x90\x8D\x88\x24'),
        ([3, 'Invalid start of UTF-8 character'], '\xF0\x90\x8D\x24'),
    ]
    for expected_indexes, input_str in CASES:
      print()
      print('_PreviousUtf8Char case %r %r' % (expected_indexes, input_str))
      i = len(input_str)
      actual_indexes = []
      while True:
        try:
          i = string_ops._PreviousUtf8Char(input_str, i)
          actual_indexes.append(i)
          if i == 0:
            break
        except error.InvalidUtf8 as e:
          actual_indexes.append(e.msg)
          break
      self.assertEqual(expected_indexes, actual_indexes)

  def testUnarySuffixOpDemo(self):
    print(string_ops)

    s = 'abcd'
    n = len(s)

    # All of these loops test exactly 4.
    # NOTE: These are manually copied into DoUnarySuffixOp

    print('## shortest prefix')
    for i in xrange(1, n+1):
      print('%d test %06r return %06r' % (i, s[:i], s[i:]))
    print()

    print('# longest prefix')
    for i in xrange(n, 0, -1):
      print('%d test %06r return %06r' % (i, s[:i], s[i:]))
    print()

    print('% shortest suffix')
    for i in xrange(n-1, -1, -1):
      print('%d test %06r return %06r' % (i, s[i:], s[:i]))
    print()

    print('%% longest suffix')
    for i in xrange(0, n):
      print('%d test %06r return %06r' % (i, s[i:], s[:i]))
    print()

  def testPatSubAllMatches(self):
    s = 'oXooXoooX'

    # Match positions
    self.assertEqual(
        [(1, 3), (4, 6)],
        string_ops._AllMatchPositions(s, '(X.)'))

    # No match
    self.assertEqual(
        [],
        string_ops._AllMatchPositions(s, '(z)'))

    # Replacement
    self.assertEqual(
        'o_o_ooX',
        string_ops._PatSubAll(s, '(X.)', '_'))

    # Replacement with no match
    self.assertEqual(
        s,
        string_ops._PatSubAll(s, '(z)', '_'))

  def testShellQuote(self):
    CASES = [
        'x y',
        'one\ntwo\n',
        "'",
        '"',
    ]
    for case in CASES:
      print(string_ops.ShellQuoteOneLine(case))


if __name__ == '__main__':
  unittest.main()
