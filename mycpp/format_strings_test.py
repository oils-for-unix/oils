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
    print(parts)

    # literal %
    parts = format_strings.Parse('%d%%')
    print(parts)

    parts = format_strings.Parse('%s %d %s')
    print(parts)

    parts = format_strings.Parse('%s\t%s\n')
    print(parts)

    parts = format_strings.Parse('%s\tb\n%s\td\n')
    print(parts)



if __name__ == '__main__':
  unittest.main()
