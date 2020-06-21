#!/usr/bin/env python2
"""
pyutil_test.py: Tests for pyutil.py
"""
from __future__ import print_function

import unittest

import pyutil  # module under test


class PyUtilTest(unittest.TestCase):

  def testBackslashEscape(self):
    print(pyutil.BackslashEscape('foo', 'o'))


if __name__ == '__main__':
  unittest.main()
