#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
libc_test.py: Tests for libc.py
"""

import unittest

import libc  # module under test


class LibcTest(unittest.TestCase):

  def testFnmatch(self):
    print(dir(libc))
    # pattern, string, result

    cases = [
        ('', '', 1),  # no pattern is valid
        ('a', 'a', 1),
        ('?', 'a', 1),
        ('\?', 'a', 0),
        ('\?', '?', 1),
        ('\\\\', '\\', 1),
        # What is another error?  Invalid escape is OK?
        ('\\', '\\', 0),  # no pattern is valid

        ('[[:alpha:]]', 'a', 1),
        ('[^[:alpha:]]', 'a', 0),  # negate
        ('[[:alpha:]]', 'aa', 0),  # exact match fails

        # Combining char class and a literal character
        ('[[:alpha:]7]', '7', 1),
        ('[[:alpha:]][[:alpha:]]', 'az', 1),
    ]

    for pat, s, expected in cases:
      actual = libc.fnmatch(pat, s)
      self.assertEqual(expected, actual)

  def testGlob(self):
    print('GLOB')
    print(libc.glob('*.py'))

    # This will not match anything!
    print(libc.glob('\\'))
    # This one will match a file named \
    print(libc.glob('\\\\'))

  def testRegex(self):
    #print(libc.regcomp(r'.*\.py'))
    self.assertEqual(True, libc.regex_parse(r'.*\.py'))
    self.assertEqual(False, libc.regex_parse(r'*'))
    self.assertEqual(False, libc.regex_parse('\\'))
    self.assertEqual(False, libc.regex_parse('{'))

    cases = [
        (r'.*\.py', 'foo.py', True),
        (r'.*\.py', 'abcd', False),
        # The match is unanchored
        (r'bc', 'abcd', True),
        # The match is unanchored
        (r'.c', 'abcd', True),
        ]

    for pat, s, expected in cases:
      actual = libc.regex_match(pat, s)
      self.assertEqual(expected, actual)

    # Error.
    print(libc.regex_match(r'*', 'abcd'))

  def testRegexFirstGroupMatch(self):
    s='oXooXoooXoX'
    self.assertEqual(
        (1, 3),
        libc.regex_first_group_match('(X.)', s, 0))

    # Match from position 3
    self.assertEqual(
        (4, 6),
        libc.regex_first_group_match('(X.)', s, 3))

    # Match from position 3
    self.assertEqual(
        (8, 10),
        libc.regex_first_group_match('(X.)', s, 6))


if __name__ == '__main__':
  unittest.main()
