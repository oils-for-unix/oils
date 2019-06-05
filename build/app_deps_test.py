#!/usr/bin/env python2
from __future__ import print_function
"""
app_deps_test.py: Tests for app_deps.py
"""

import sys
import unittest

import app_deps  # module under test


class AppDepsTest(unittest.TestCase):

  def testModules(self):
    pairs = [
        ('poly.util', 'poly/util.py'),
        ('core.libc', '/git/oil/core/libc.so'),
        ('simplejson',
         '/home/andy/dev/simplejson-2.1.5/simplejson/__init__.py')
    ]
    for mod_type, x, y in app_deps.FilterModules(pairs):
      print(mod_type, x, y)


if __name__ == '__main__':
  unittest.main()
