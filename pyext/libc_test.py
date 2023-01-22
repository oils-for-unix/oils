#!/usr/bin/env python2
# coding=utf8
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
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

        # What if we also escape extended glob chars?
        # Extra escaping is OK, so we shoudl ALWAYS escape them.
        ('\\(', '(', 1),
        ('\\(', 'x', 0),
        ('\\(', '\\', 0),
        ('\\(', '\\(', 0),

        ('\\|', '|', 1),
        ('\\|', 'x', 0),

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

        ('[a-z]', 'a', 1),
        ('[a-z]', '-', 0),

        # THIS IS INCONSISTENT WITH REGEX!
        # Somehow in regexes (at least ERE) GNU libc  treats [a\-z] as [a-z].
        # See below.
        ('[a\-z]', '-', 1),
        ('[a\-z]', 'b', 0),

        # Need double backslash in character class
        ('[\\\\]', '\\', 1),

        # Can you escape ] with \?  Yes in fnmatch
        ('[\\]]', '\\', 0),
        ('[\\]]', ']', 1),


        None if IS_DARWIN else ('[]', 'a', 0),
        None if IS_DARWIN else ('[]', '[]', 1),

        ('?.c', 'a.c', 1),
        ('?.c', 'aa.c', 0),
        # mu character
        ('?.c', '\xce\xbc.c', 1),
    ]

    for pat, s, expected in filter(None, cases):
      actual = libc.fnmatch(pat, s)
      self.assertEqual(
          expected, actual, '%r %r -> got %d' % (pat, s, actual))

  def testFnmatchExtglob(self):
    # NOTE: We always use FNM_EXTMATCH when available

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

        # escaping *
        ('@(ab\*)', 'ab*', 1),
        ('@(ab\*)', 'abc', 0),
        # escaping ?
        ('@(ab\?)', 'ab?', 1),
        ('@(ab\?)', 'abc', 0),

        # escaping []
        ('@(ab\[\])', 'ab[]', 1),
        ('@(ab\[\])', 'abcd', 0),

        # escaping :
        ('@(ab\:)', 'ab:', 1),
        ('@(ab\:)', 'abc', 0),

        # escaping a is no-op
        (r'@(\ab)', 'ab', 1),
        (r'@(\ab)', r'\ab', 0),

        #('@(ab\|)', 'ab|', 1),  # GNU libc bug?  THIS SHOULD WORK

        # There's no way to escape | in extended glob???  wtf.
        #('@(ab\|)', 'ab', 1),
        #('@(ab\|)', 'ab\\', 1),
        #('@(ab\|)', 'ab\\|', 1),
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
    if not IS_DARWIN:
      self.assertRaises(RuntimeError, libc.regex_parse, '{')

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
      # Invalid regex syntax
      libc.regex_first_group_match("(['+-'])", s, 6)

  def testSpecialCharsInCharClass(self):
    CASES = [
      ("([a-z]+)", '123abc123', (3, 6)),

      # Uh what the heck, \- means the same thing as -?  It's just ignored.  At
      # least in GNU libc.

      # https://stackoverflow.com/questions/28495913/how-do-you-escape-a-hyphen-as-character-range-in-a-posix-regex
      # The <hyphen> character shall be treated as itself if it occurs first (after an initial '^', if any) or last in the list, or as an ending range point in a range expression

      ("([a\-z]+)", '123abc123', (3, 6)),

      # This is an inverted range.  TODO: Need to fix the error message.
      #("([a\-.]+)", '123abc123', None),

      ("([\\\\]+)", 'a\\b', (1, 2)),

      # Can you escape ] with \?  Yes in fnmatch, but NO here!!!
      ('([\\]])', '\\', None),
      ('([\\]])', ']', None),

      # Weird parsing!!!
      ('([\\]])', '\\]', (0, 2)),

    ]

    for pat, s, expected in CASES:
      result = libc.regex_first_group_match(pat, s, 0)
      self.assertEqual(expected, result,
          "FAILED: pat %r  s %r  result %s" % (pat, s, result))

  def testRealpathFailOnNonexistentDirectory(self):
    # This behaviour is actually inconsistent with GNU readlink,
    # but matches behaviour of busybox readlink
    # (https://github.com/jgunthorpe/busybox)
    self.assertEqual(None, libc.realpath('_tmp/nonexistent'))

    # Consistent with GNU
    self.assertEqual(None, libc.realpath('_tmp/nonexistent/supernonexistent'))

  def testPrintTime(self):
    print('', file=sys.stderr)
    libc.print_time(0.1, 0.2, 0.3)
    print('', file=sys.stderr)

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
    if not IS_DARWIN:
      self.assertEqual(1, libc.wcswidth("▶️"))
      self.assertEqual(28, libc.wcswidth("(osh) ~/.../unchanged/oil ▶️ "))

    mu = u"\u03bc".encode('utf-8')
    print(repr(mu))
    print(mu)
    print(len(mu))
    self.assertEqual(1, libc.wcswidth(mu))

    self.assertEqual(2, libc.wcswidth("→ "))

    # mbstowcs fails on invalid utf-8
    try:
      # first byte of mu
      libc.wcswidth("\xce")
    except UnicodeError as e:
      self.assertEqual('mbstowcs() 1', e.message)
    else:
      self.fail('Expected failure')

    # wcswidth fails on unprintable character
    try:
      libc.wcswidth("\x01")
    except UnicodeError as e:
      self.assertEqual('wcswidth()', e.message)
    else:
      self.fail('Expected failure')

    self.assertRaises(UnicodeError, libc.wcswidth, "\xfe")


if __name__ == '__main__':
  # To simulate the OVM_MAIN patch in pythonrun.c
  libc.cpython_reset_locale()
  unittest.main()
