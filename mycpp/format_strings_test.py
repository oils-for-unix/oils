#!/usr/bin/env python3
"""
format_strings_test.py: Tests for format_strings.py
"""
from __future__ import print_function

import json
import unittest

import format_strings  # module under test


class FormatStringsTest(unittest.TestCase):

  def testParse(self):
    parts = format_strings.Parse('foo [%s]')
    self.assertEqual(3, len(parts))
    print(parts)

    # literal %
    parts = format_strings.Parse('%d%%')
    self.assertEqual(2, len(parts))
    print(parts)

    parts = format_strings.Parse('%s %d %s')
    self.assertEqual(5, len(parts))
    print(parts)

    parts = format_strings.Parse('%s\t%s\n')
    self.assertEqual(4, len(parts))
    print(parts)

    parts = format_strings.Parse('%s\tb\n%s\td\n')
    self.assertEqual(4, len(parts))
    print(parts)

    # rjust(), use for 'dirs'
    parts = format_strings.Parse('%2d %s')
    self.assertEqual(3, len(parts))
    print(parts)




if __name__ == '__main__':
  unittest.main()
