#!/usr/bin/env python2
"""
qstr_test.py: Tests for qstr.py
"""
from __future__ import print_function

import unittest

import qstr  # module under test


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
    ]

    for c in CASES:
      sh = qstr.shellstr_encode(c)
      q = qstr.qstr_encode(c)
      print('  sh      %s' % sh)
      print('qstr      %s' % q)

      decoded = qstr.qstr_decode(q)
      print('decoded = %r' % decoded)
      print()

      self.assertEqual(c, decoded)

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

      print('qstr      %s' % q)

      decoded = qstr.qstr_decode(q)
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
      decoded = qstr.qstr_decode(c)
      print('qstr    = %s' % c)
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
        s = qstr.qstr_decode(c)
      except RuntimeError as e:
        print(e)
      else:
        self.fail('Expected %r to be invalid' % c)


if __name__ == '__main__':
  unittest.main()
