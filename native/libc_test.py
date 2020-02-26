#!/usr/bin/env python2
# coding=utf8
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
import sys

import libc  # module under test

# guard some tests that fail on Darwin
IS_DARWIN = sys.platform == 'darwin'

class LibcTest(unittest.TestCase):

  def testFnmatch(self):

    cases = [
    #   (pattern, string, result)

        ('', '', 1),  # no pattern is valid
        ('a', 'a', 1),
        ('?', 'a', 1),

        # Test escaping of glob operator chars
        ('\\?', '-', 0),
        ('\\?', '?', 1),

        ('\\*', '-', 0),
        ('\\*', '*', 1),

        ('\\[', '-', 0),
        ('\\[', '[', 1),

        ('\\!', '-', 0),
        ('\\!', '!', 1),

        ('\\\\', '\\', 1),
        ('\\\\', 'x', 0),
        ('\\\\', '\\extra', 0),

        ('\\f', '\\', 0),  # no match

        # Hm this is weird, c is not a special character
        ('\\c', 'c', 1),
        ('\\c', '\\c', 0),
        ('\\\\c', '\\c', 1),  # the proper way to match

        ('c:\\foo', 'c:\\foo', 0),
        ('c:\\foo', 'c:foo', 1),

        ('strange]one', 'strange]one', 1),

        # What is another error?  Invalid escape is OK?
        None if IS_DARWIN else ('\\', '\\', 0),  # no pattern is valid

        ('[[:alpha:]]', 'a', 1),
        ('[^[:alpha:]]', 'a', 0),  # negate
        ('[[:alpha:]]', 'aa', 0),  # exact match fails

        # Combining char class and a literal character
        ('[[:alpha:]7]', '7', 1),
        ('[[:alpha:]][[:alpha:]]', 'az', 1),

        ('[a]', 'a', 1),
        # Hm [] is treated as a constant string, not an empty char class.
        # Should we change LooksLikeGlob?
        ('[]', '', 0),
        None if IS_DARWIN else ('[]', 'a', 0),
        None if IS_DARWIN else ('[]', '[]', 1),
    ]

    for pat, s, expected in filter(None, cases):
      actual = libc.fnmatch(pat, s)
      self.assertEqual(
          expected, actual, '%r %r -> got %d' % (pat, s, actual))

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
    print(libc.glob('[[:punct:]]'))

  def testRegexParse(self):
    self.assertEqual(True, libc.regex_parse(r'.*\.py'))

    # Syntax errors
    self.assertRaises(RuntimeError, libc.regex_parse, r'*')
    self.assertRaises(RuntimeError, libc.regex_parse, '\\')
    IS_DARWIN or self.assertRaises(RuntimeError, libc.regex_parse, '{')

    cases = [
        ('([a-z]+)([0-9]+)', 'foo123', ['foo123', 'foo', '123']),
        (r'.*\.py', 'foo.py', ['foo.py']),
        (r'.*\.py', 'abcd', None),
        # The match is unanchored
        (r'bc', 'abcd', ['bc']),
        # The match is unanchored
        (r'.c', 'abcd', ['bc']),
        # Empty matches empty
        None if IS_DARWIN else (r'', '', ['']),
        (r'^$', '', ['']),
        (r'^.$', '', None),
    ]

    for pat, s, expected in filter(None, cases):
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

  def testRegexFirstGroupMatchError(self):
    # Helping to debug issue #291
    s = ''
    if 0:
      libc.regex_first_group_match("(['+-'])", s, 6)

  def testRealpathFailOnNonexistentDirectory(self):
    # This behaviour is actually inconsistent with GNU readlink,
    # but matches behaviour of busybox readlink
    # (https://github.com/jgunthorpe/busybox)
    self.assertEqual(None, libc.realpath('_tmp/nonexistent'))

    # Consistent with GNU
    self.assertEqual(None, libc.realpath('_tmp/nonexistent/supernonexistent'))

  def testPrintTime(self):
    libc.print_time(0.1, 0.2, 0.3)

  def testGethostname(self):
    print(libc.gethostname())

  def testGetTerminalWidth(self):
    try:
      width = libc.get_terminal_width()
    except IOError as e:
      print('error getting terminal width: %s' % e)
    else:
      print('width % d' % width)

  def testWcsWidth(self):
    IS_DARWIN or self.assertEqual(1, libc.wcswidth("▶️"))
    IS_DARWIN or self.assertEqual(28, libc.wcswidth("(osh) ~/.../unchanged/oil ▶️ "))
    self.assertEqual(2, libc.wcswidth("→ "))
    self.assertRaises(UnicodeError, libc.wcswidth, "\xfe")

if __name__ == '__main__':
  unittest.main()
