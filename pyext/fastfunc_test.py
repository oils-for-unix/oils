#!/usr/bin/env python2
from __future__ import print_function
"""
fastfunc_test.py: Tests for fastfunc.c
"""
import unittest

from mycpp.mylib import log

import fastfunc  # module under test


class FastfuncTest(unittest.TestCase):

  def testJ8Encode(self):
    s = 'hello \xff \x01 ' + u'\u03bc " \''.encode('utf-8')
    #print(s)

    x = fastfunc.J8EncodeString(s, 0)
    print(x)

    x = fastfunc.J8EncodeString(s, 1)
    print(x)

  def testShellEncode(self):
    s = 'hello \xff \x01 ' + u'\u03bc " \''.encode('utf-8')
    #print(s)

    x = fastfunc.ShellEncodeString(s, 0)
    print(x)

    x = fastfunc.ShellEncodeString(s, 1)
    print(x)

  def testUtf8(self):
    s = 'hi \xff'
    self.assertEqual(True, fastfunc.PartIsUtf8(s, 0, 3))
    self.assertEqual(False, fastfunc.PartIsUtf8(s, 3, 4))

  def testUtf8Decode(self):
    # interface is:
    #  def Utf8DecodeOne(s: str, start: int) -> (codepoint_or_error: int, bytes_read: int)
    # If codepoint_or_error < 0, then there was a decoding error whose absolute
    # integer value is listed in the Utf8Error enum.

    s = 'h\xE2\xA1\x80\xC5\x81'
    self.assertEqual((ord('h'), 1), fastfunc.Utf8DecodeOne(s, 0))
    self.assertEqual((0x2840, 3), fastfunc.Utf8DecodeOne(s, 1))
    self.assertEqual((0x141, 2), fastfunc.Utf8DecodeOne(s, 4))

    # UTF8_ERR_OVERLONG = 1
    self.assertEqual((-1, 2), fastfunc.Utf8DecodeOne("\xC1\x81", 0))

    # UTF8_ERR_SURROGATE = 2
    self.assertEqual((-2, 3), fastfunc.Utf8DecodeOne("\xED\xBF\x80", 0))

    # UTF8_ERR_TOO_LARGE = 3
    self.assertEqual((-3, 4), fastfunc.Utf8DecodeOne("\xF4\xA0\x80\x80", 0))

    # UTF8_ERR_BAD_ENCODING = 4
    self.assertEqual((-4, 2), fastfunc.Utf8DecodeOne("\xC2\xFF", 0))

    # UTF8_ERR_TRUNCATED_BYTES = 5
    self.assertEqual((-5, 1), fastfunc.Utf8DecodeOne("\xC2", 0))

  def testCanOmit(self):
    self.assertEqual(True, fastfunc.CanOmitQuotes('foo'))
    self.assertEqual(False, fastfunc.CanOmitQuotes('foo bar'))
    self.assertEqual(True, fastfunc.CanOmitQuotes('my-dir/my_file.cc'))
    self.assertEqual(False, fastfunc.CanOmitQuotes(''))

    self.assertEqual(False, fastfunc.CanOmitQuotes('true'))
    self.assertEqual(False, fastfunc.CanOmitQuotes('false'))
    self.assertEqual(False, fastfunc.CanOmitQuotes('null'))

    self.assertEqual(True, fastfunc.CanOmitQuotes('truez'))
    self.assertEqual(True, fastfunc.CanOmitQuotes('nul'))


if __name__ == '__main__':
  unittest.main()
