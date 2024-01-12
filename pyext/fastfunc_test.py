#!/usr/bin/env python2
from __future__ import print_function
"""
fastfunc_test.py: Tests for fastfunc.c
"""
import unittest

from mycpp.mylib import log

import fastfunc  # module under test


class FastfuncTest(unittest.TestCase):

  def testEncode(self):
    """Send with Python; received our fanos library"""

    s = 'hello \xff \x01 ' + u'\u03bc " \''.encode('utf-8')
    #print(s)

    x = fastfunc.J8EncodeString(s, 0)
    print(x)

    x = fastfunc.J8EncodeString(s, 1)
    print(x)



if __name__ == '__main__':
  unittest.main()
