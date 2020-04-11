#!/usr/bin/env python2
"""
utf8_test.py: Tests for utf8.py
"""
from __future__ import print_function

import unittest

from qsn_ import utf8  # module under test


class Utf8Test(unittest.TestCase):

  def testDecode(self):

    CASES = [
      '\xce\xbc',
      '\xce\xce\xbc',
      '\xce\xbc\xce',
    ]

    for s in CASES:
      print('---')
      print(repr(s))
      codepoint = 0
      state = 0
      args = [state, codepoint]
      for c in s:
        byte = ord(c)
        utf8.decode(args, byte)

        state, codepoint = args
        print('state: %d' % state)
        print('code point: %02x' % codepoint)
      print()


if __name__ == '__main__':
  unittest.main()
