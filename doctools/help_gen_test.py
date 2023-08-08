#!/usr/bin/env python2
"""
help_gen_test.py: Tests for help_gen.py
"""
from __future__ import print_function

import os
import unittest
from cStringIO import StringIO

from doctools import help_gen  # module under test


class MakeHelpTest(unittest.TestCase):

  def testTableOfContents(self):
    os.environ['OILS_VERSION'] = '0.7.pre5'

    # Three spaces before
    #
    # ! for deprecated  -- conflicts with ! bang though
    # X for not implemented

    # Do we need markup here?

    line = '  [Overview] hello   there   X not-impl'

    print(help_gen.IndexLineToHtml('osh', line, []))

  def testSplitIntoCards(self):
    contents = """
<h2>Oil Expression Language</h2>

expr

<h3>Literals</h2>

oil literals

<h4>oil-numbers</h4>

42 1e100

<h4>oil-array</h4>

%(a b)
"""
    cards = help_gen.SplitIntoCards(['h2', 'h3', 'h4'], contents)
    print(list(cards))


if __name__ == '__main__':
  unittest.main()
