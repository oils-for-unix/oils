#!/usr/bin/env python2
"""
oil_doc_test.py: Tests for oil_doc.py
"""
from __future__ import print_function

import sys
import unittest

from doctools import oil_doc  # module under test
from lazylex import html

with open('lazylex/testdata.html') as f:
  TEST_HTML = f.read()


class OilDoc(unittest.TestCase):

  def testExpandLinks(self):
    """
    <a href=$xref:bash>bash</a>
    ->
    <a href=/cross-ref?tag=bash#bash>

    NOTE: THIs could really be done with a ref like <a.*href="(.*)">
    But we're testing it
    """
    print(oil_doc.ExpandLinks(TEST_HTML))

  def testHighlightCode(self):
    """
    <pre><code language="sh">echo one
    echo two
    </code></pre>
    """
    print(oil_doc.HighlightCode(TEST_HTML))

  def testShPrompt(self):
    r = oil_doc._PROMPT_LINE_RE
    line = 'oil$ ls -l&lt;TAB&gt;  # comment'
    m = r.match(line)
    print(m.groups())
    print(m.group(2))
    print(m.end(2))
    plugin = oil_doc.ShPromptPlugin(line, 0, len(line))
    out = html.Output(line, sys.stdout)
    plugin.PrintHighlighted(out)


if __name__ == '__main__':
  unittest.main()
