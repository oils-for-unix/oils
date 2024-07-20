#!/usr/bin/env python2
from __future__ import print_function

import unittest

import dynamic_deps  # module under test


class AppDepsTest(unittest.TestCase):

  def testModules(self):
    pairs = [
        ('poly.util', 'poly/util.py'),
        ('core.libc', '/git/oil/core/libc.so'),
        ('simplejson',
         '/home/andy/dev/simplejson-2.1.5/simplejson/__init__.py')
    ]
    for mod_type, x, y in dynamic_deps.FilterModules(pairs):
      print(mod_type, x, y)


if __name__ == '__main__':
  unittest.main()
