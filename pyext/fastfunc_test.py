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

  def testCanOmit(self):
    self.assertEqual(True, fastfunc.CanOmitQuotes('foo'))
    self.assertEqual(False, fastfunc.CanOmitQuotes('foo bar'))
    self.assertEqual(True, fastfunc.CanOmitQuotes('my-dir/my_file.cc'))


if __name__ == '__main__':
  unittest.main()
