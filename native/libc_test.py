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
    #print(dir(libc))
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

  def testFnmatchExtglob(self):
    return

    # With GNU extension.
    cases = [
        # One of these
        ('--@(help|verbose)', '--verbose', 1),
        ('--@(help|verbose)', '--foo', 0),

        ('--*(help|verbose)', '--verbose', 1),
        ('--*(help|verbose)', '--', 1),
        ('--*(help|verbose)', '--helpverbose', 1),  # Not what we want

        ('--+(help|verbose)', '--verbose', 1),
        ('--+(help|verbose)', '--', 0),
        ('--+(help|verbose)', '--helpverbose', 1),  # Not what we want

        ('--?(help|verbose)', '--verbose', 1),
        ('--?(help|verbose)', '--helpverbose', 0),

        # Neither of these
        ('--!(help|verbose)', '--verbose', 0),
    ]
    for pat, s, expected in cases:
      actual = libc.fnmatch(pat, s)
      self.assertEqual(expected, actual,
          "Matching %s against %s: got %s but expected %s" %
          (pat, s, actual, expected))

  def testGlob(self):
    print(libc.glob('*.py'))

    # This will not match anything!
    print(libc.glob('\\'))
    # This one will match a file named \
    print(libc.glob('\\\\'))

  def testRegexParse(self):
    self.assertEqual(True, libc.regex_parse(r'.*\.py'))

    # Syntax errors
    self.assertRaises(RuntimeError, libc.regex_parse, r'*')
    self.assertRaises(RuntimeError, libc.regex_parse, '\\')
    self.assertRaises(RuntimeError, libc.regex_parse, '{')

    cases = [
        ('([a-z]+)([0-9]+)', 'foo123', ['foo123', 'foo', '123']),
        (r'.*\.py', 'foo.py', ['foo.py']),
        (r'.*\.py', 'abcd', None),
        # The match is unanchored
        (r'bc', 'abcd', ['bc']),
        # The match is unanchored
        (r'.c', 'abcd', ['bc'])
    ]

    for pat, s, expected in cases:
      #print('CASE %s' % pat)
      actual = libc.regex_match(pat, s)
      self.assertEqual(expected, actual)

  def testRegexMatch(self):
    self.assertRaises(RuntimeError, libc.regex_match, r'*', 'abcd')

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

    # Syntax Error
    self.assertRaises(
        RuntimeError, libc.regex_first_group_match, r'*', 'abcd', 0)

  def testRealpathFailOnNonexistentDirectory(self):
    # This behaviour is actually inconsistent with GNU readlink,
    # but matches behaviour of busybox readlink
    # (https://github.com/jgunthorpe/busybox)
    self.assertEqual(None, libc.realpath('_tmp/nonexistent'))

    # Consistent with GNU
    self.assertEqual(None, libc.realpath('_tmp/nonexistent/supernonexistent'))


if __name__ == '__main__':
  unittest.main()
