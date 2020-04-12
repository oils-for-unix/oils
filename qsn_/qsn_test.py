#!/usr/bin/env python2
# coding: utf-8
"""
qsn_test.py: Tests for qsn.py
"""
from __future__ import print_function

import re
import unittest

from core.util import log
from qsn_ import qsn  # module under test


class QStrTest(unittest.TestCase):

  def testFlags(self):
    self.assertEqual("a", qsn.maybe_shell_encode('a'))
    self.assertEqual("'a'", qsn.maybe_shell_encode('a', flags=qsn.MUST_QUOTE))

  def testShellEncode(self):
    # We don't want \u{} in shell
    self.assertEqual("$'\\x01'", qsn.maybe_shell_encode('\x01'))

    # We don't want \0 because shell uses \000
    #self.assertEqual("$'\\x00'", qsn.maybe_shell_encode('\0'))

    # backslash handling
    self.assertEqual(r"$'\\'", qsn.maybe_shell_encode('\\'))

  def testErrorRecoveryForInvalidUnicode(self):
    CASES = [
        # Preliminaries
        ('a', "a"),
        ('one two', "'one two'"),

        ('\xce', "$'\\xce'"),
        ('\xce\xce\xbc', "$'\\xceμ'"),  # byte then char
        ('\xce\xbc\xce', "$'μ\\xce'"),
        ('\xcea', "$'\\xcea'"),
        ('a\xce', "$'a\\xce'"),
        ('a\xce\xce', "$'a\\xce\\xce'"),  # two invalid
        ('\xbc', "$'\\xbc'"),
        ('\xbc\xbc', "$'\\xbc\\xbc'"),
        #('\xbc\xbc\x01', "$'\\xbc\\xbc\\x01'"),
        ('\xbca', "$'\\xbca'"),
        ('a\xbc', "$'a\\xbc'"),
        ('\xbcab', "$'\\xbcab'"),
        ('\xbc\x00\x01', "$'\\xbc\\x00\\x01'"),
    ]
    for c, expected in CASES:
      print()
      print('CASE %r' % c)
      print('---')

      actual = qsn.maybe_shell_encode(c)
      print(actual)
      self.assertEqual(expected, actual)

  def testEncodeDecode(self):

    CASES = [
        '',
        '"',
        "'",
        '\\',
        'hello',
        '_my-report.c',
        'a+b',
        '()[]{}',
        'one two',
        'one\ttwo\r\n',
        "'one\0two'",
        '\x00\x01',
        #'\xbc\x00\x01',
        u'[\u03bc]'.encode('utf-8'),
        '\xce\xbc',
        '\xce\xbc\xce',  # char then byte
        '\xce\xce\xbc',  # byte then char

        # two invalid bytes, then restart
        '\xce\xce\xce\xbe',

        # 1 2 3 4
        u'\u007a \u03bb \u4e09 \U0001f618'.encode('utf-8'),
        #        \xce\bb  \xe4\xb8\x89  \xf0\x9f\x98\x98

        '\xe4\xb8\x89',
        '\xe4\xb8a',
        '\xe4a',

        '\xf0\x9f\x98\x98',
        '\xf0\x9f\x98.',
        '\xf0\x9f.',
        '\xf0.',
    ]

    for c in CASES:
      print('-----')
      print('CASE %r' % c)
      print()

      sh = qsn.maybe_shell_encode(c)
      q1 = qsn.maybe_encode(c)
      q2 = qsn.encode(c)
      qu = qsn.encode(c, bit8_display=qsn.BIT8_U_ESCAPE)
      qx = qsn.encode(c, bit8_display=qsn.BIT8_X_ESCAPE)

      print('       sh %s' % sh)
      print('qsn maybe %s' % q1)
      print('qsn UTF-8 %s' % q2)
      print('qsn U     %s' % qu)
      print('qsn X     %s' % qx)

      decoded1 = qsn.decode(q1)
      print('decoded = %r' % decoded1)
      print()
      decoded2 = qsn.decode(q2)
      decoded_u = qsn.decode(qu)
      decoded_x = qsn.decode(qx)

      self.assertEqual(c, decoded1)
      self.assertEqual(c, decoded2)
      self.assertEqual(c, decoded_u)
      self.assertEqual(c, decoded_x)

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

  def testUtf8WithRegex(self):
    """
    This doesn't test any code; it's just a demo of matching UTF-8 with a
    regex.  UTF-8 is a regular language.
    """

    def CountMatches(pat, predicate):

      num_matches = 0
      for i in xrange(256):
        b = chr(i)
        m = pat.match(b)
        left = bool(m)

        right = predicate(i)
        if left != right:
          self.fail('i = %d, b = %r, match: %s, predicate: %s' % (i, b, left, right))

        if m:
          num_matches += 1

      return num_matches

    #
    # Regexes for 4 starting bytes
    #

    start1_pat = re.compile(r'[\x00-\x7f]')
    n = CountMatches(start1_pat, lambda i: (i >> 7) == 0b0)
    log('s1 %d', n)

    # 0b1100_0000 -> 0b1101_1111 is 0xc0 -> 0xdf
    start2_pat = re.compile(r'[\xc0-\xdf]')
    n = CountMatches(start2_pat, lambda i: (i >> 5) == 0b110)
    log('s2 %d', n)

    # 0b1110_0000 -> 0b1110_1111 is 0xe0 -> 0xef
    start3_pat = re.compile(r'[\xe0-\xef]')
    n = CountMatches(start3_pat, lambda i: (i >> 4) == 0b1110)
    log('s3 %d', n)

    # 0b1111_0000 -> 0b1111_0111 is 0xf0 -> 0xf7
    start4_pat = re.compile(r'[\xf0-\xf7]')
    n = CountMatches(start4_pat, lambda i: (i >> 3) == 0b11110)
    log('s4 %d', n)

    #
    # Regex for continuation byte
    #

    # 0b1000_0000 -> 0b1011_1111 is 0x80 -> 0xbf
    cont_pat = re.compile(r'[\x80-\xbf]')
    n = CountMatches(cont_pat, lambda i: (i >> 6) == 0b10)
    log('cont %d', n)

    # TODO: Port this to eggex and test it.
    # cont_byte = [\x80 - \xbf]

    UTF8_LEX = re.compile(r'''
  ( [\x00-\x7f] )
| ( [\xc0-\xdf] [\x80-\xbf] )
| ( [\xe0-\xef] [\x80-\xbf] [\x80-\xbf] )
| ( [\xf0-\xf7] [\x80-\xbf] [\x80-\xbf] [\x80-\xbf] )
| ( . )  # Invalid
''', re.VERBOSE)

    CASES = [
      'a',
      '\xce\xbc',
      '\xce',
      '\xbc',
    ]

    for c in CASES:
      m = UTF8_LEX.match(c)
      print('%r %r' % (c, m.groups()))

    # Tokens
    LEX2 = re.compile(r'''
    [\0\r\n\t\'\"\\]
  ( [\x00-\x7f]+ )
| ( [\xc0-\xdf] [\x80-\xbf] )
| ( [\xe0-\xef] [\x80-\xbf] [\x80-\xbf] )
| ( [\xf0-\xf7] [\x80-\xbf] [\x80-\xbf] [\x80-\xbf] )
| ( . )  # Invalid
''', re.VERBOSE)



if __name__ == '__main__':
  unittest.main()
