#!/usr/bin/env python2
"""
qsn_test.py: Tests for qsn.py
"""
from __future__ import print_function

import unittest

import qsn  # module under test


class QStrTest(unittest.TestCase):

  def testEncodeDecode(self):

    CASES = [
        '',
        '"',
        'hello',
        '_my-report.c',
        'a+b',
        '()[]{}',
        'one two',
        'one\ttwo\r\n',
        "'one\0two'",
        '\xbc\x00\x01'
        '\'',
        '\\',
        u'[\u03bc]'.encode('utf-8'),
    ]

    for c in CASES:
      sh = qsn.maybe_shell_encode(c)
      q1 = qsn.maybe_encode(c)
      q2 = qsn.encode(c)
      q3 = qsn.encode(c, bit8_display='x')

      print('       sh %s' % sh)
      print('qsn maybe %s' % q1)
      print('qsn       %s' % q2)
      print('qsn x     %s' % q3)

      decoded1 = qsn.decode(q1)
      print('decoded = %r' % decoded1)
      print()
      decoded2 = qsn.decode(q2)
      decoded3 = qsn.decode(q3)

      self.assertEqual(c, decoded1)
      self.assertEqual(c, decoded2)
      self.assertEqual(c, decoded3)

    # character codes, e.g. U+03bc
    UNICODE_CASES = [
        0x03bc,
        0x0001,
        0x00010000,
    ]
    for c in UNICODE_CASES:
      print(repr(c))
      s = unichr(c).encode('utf-8')  # what it should decode to

      q = '\\u{%0x}' % c  # the QSTR encoding

      print('qsn      %s' % q)

      decoded = qsn.decode(q)
      print('decoded = %r' % decoded)
      print()

      self.assertEqual(s, decoded)

    OTHER_CASES = [
        # '"' and '\"' are the same thing
        "'\\\"'",

        # never encoded, but still legal
        "",

        # Would have quotes
        "%%%", 
    ]
    for c in OTHER_CASES:
      decoded = qsn.decode(c)
      print('qsn    = %s' % c)
      print('decoded = %r' % decoded)
      print()

    # note:
    INVALID = [
        # lone backslash
        "'\\",
        # illegal escape.  Python's JSON library also disallows this, e.g. with
        # ValueError: Invalid \escape: line 1 column 2 (char 1)
        "'\\a'",  
    ]
    for c in INVALID:
      try:
        s = qsn.decode(c)
      except RuntimeError as e:
        print(e)
      else:
        self.fail('Expected %r to be invalid' % c)


if __name__ == '__main__':
  unittest.main()
