#!/usr/bin/env python2
"""
quick_ref_test.py: Tests for quick_ref.py
"""
from __future__ import print_function

import os
import unittest
from cStringIO import StringIO

import quick_ref  # module under test


class QuickRefTest(unittest.TestCase):

  def testTableOfContents(self):
    os.environ['OIL_VERSION'] = '0.7.pre5'

    # Three spaces before
    #
    # ! for deprecated  -- conflicts with ! bang though
    # X for not implemented

    # Do we need markup here?


    f = StringIO('''\
INTRO
  [Overview] hello   there   X not-impl
''')

    quick_ref.TableOfContents(f)


if __name__ == '__main__':
  unittest.main()
