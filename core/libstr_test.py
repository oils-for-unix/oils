#!/usr/bin/python -S
from __future__ import print_function
"""
libstr_test.py: Tests for libstr.py
"""

import unittest

from core import libstr  # module under test


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
      self.assertEqual(expected, libstr.Utf8Encode(code_point))

  def testUnarySuffixOpDemo(self):
    print(libstr)

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
        libstr._AllMatchPositions(s, '(X.)'))

    # No match
    self.assertEqual(
        [],
        libstr._AllMatchPositions(s, '(z)'))

    # Replacement
    self.assertEqual(
        'o_o_ooX',
        libstr._PatSubAll(s, '(X.)', '_'))

    # Replacement with no match
    self.assertEqual(
        s,
        libstr._PatSubAll(s, '(z)', '_'))


if __name__ == '__main__':
  unittest.main()
