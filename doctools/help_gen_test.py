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

    CASES = [
      '  [Overview] hello   there   X not-impl\n',

      # Bug fix: 42 was linkified
      '    int-literal   42  65_536  0xFF  0o755  0b10\n',

      # Bug fix: echo was linkified
      '    expr-splice   echo @[split(x)]  \n',

      # Bug fix: u was linkified
      "    u'line\\n'  b'byte \yff'\n"

      ]

    for line in CASES:
      debug_out = []
      r = help_gen.TopicHtmlRenderer('osh', debug_out)
      html = r.Render(line)
      print(html)
      print(debug_out[0])
      print()
      print()

  def testSplitIntoCards(self):
    contents = """
<h2>YSH Expression Language</h2>

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
