#!/usr/bin/python -S
"""
word_compile_test.py: Tests for word_compile.py
"""

import unittest

from core import word_compile  # module under test


class WordCompileTest(unittest.TestCase):

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
      self.assertEqual(expected, word_compile.Utf8Encode(code_point))

if __name__ == '__main__':
  unittest.main()
