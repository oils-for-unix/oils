#!/usr/bin/python -S
"""
libstr_test.py: Tests for libstr.py
"""

import unittest

import libstr  # module under test


class LibStrTest(unittest.TestCase):

  def testUnarySuffixOpDemo(self):
    s = 'abcd'
    n = len(s)

    # All of these loops test exactly 4.
    # NOTE: These are manually copied into DoUnarySuffixOp

    print('## shortest prefix')
    for i in xrange(1, n+1):
      print '%d test %06r return %06r' % (i, s[:i], s[i:])
    print

    print('# longest prefix')
    for i in xrange(n, 0, -1):
      print '%d test %06r return %06r' % (i, s[:i], s[i:])
    print

    print('% shortest suffix')
    for i in xrange(n-1, -1, -1):
      print '%d test %06r return %06r' % (i, s[i:], s[:i])
    print

    print('%% longest suffix')
    for i in xrange(0, n):
      print '%d test %06r return %06r' % (i, s[i:], s[:i])
    print


if __name__ == '__main__':
  unittest.main()
