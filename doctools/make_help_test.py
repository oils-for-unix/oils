#!/usr/bin/env python2
"""
make_help_test.py: Tests for make_help.py
"""
from __future__ import print_function

import os
import unittest
from cStringIO import StringIO

import make_help  # module under test


class MakeHelpTest(unittest.TestCase):

  def testTableOfContents(self):
    os.environ['OILS_VERSION'] = '0.7.pre5'

    # Three spaces before
    #
    # ! for deprecated  -- conflicts with ! bang though
    # X for not implemented

    # Do we need markup here?

    line = '  [Overview] hello   there   X not-impl'

    print(make_help.HighlightLine('osh', line))

  def testSplitIntoCards(self):
    contents = """
<h2>Oil Expression Langauge</h2>

expr

<h3>Literals</h2>

oil literals

<h4>oil-numbers</h4>

42 1e100

<h4>oil-array</h4>

%(a b)
"""
    cards = make_help.SplitIntoCards(['h2', 'h3', 'h4'], contents)
    print(list(cards))


if __name__ == '__main__':
  unittest.main()
