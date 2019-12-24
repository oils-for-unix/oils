#!/usr/bin/env python2
"""
html_test.py: Tests for html.py
"""
from __future__ import print_function

import sys
import unittest

from lazylex import html  # module under test


with open('lazylex/testdata.html') as f:
  TEST_HTML = f.read()


class PulpTest(unittest.TestCase):

  # IndexLinker in devtools/make_help.py
  #  <pre> sections in doc/html_help.py
  # TocExtractor in devtools/cmark.py

  def testPstrip(self):
    """
    Remove anything like this

    <p><pstrip> </pstrip></p>
    """
    pass

  def testSplit(self):
    """
    doc/help.md and help-index.md have to be split up
    """
    pass

  def testSyntaxHighlight(self):
    """
    <code language="sh">
      ls | wc -l
    </code>

    ->
    <code language="sh">
      <span id="">ls | wc -l</span>
    </code>
    """
    pass

  def testCommentParse(self):
    """
    """
    for event in html.Parse(TEST_HTML):
      if isinstance(event, html.Invalid):
        raise RuntimeError(event)

      print(event)


if __name__ == '__main__':
  unittest.main()
