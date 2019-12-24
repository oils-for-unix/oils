#!/usr/bin/env python2
"""
oil_doc_test.py: Tests for oil_doc.py
"""
from __future__ import print_function

import unittest

from lazylex import oil_doc  # module under test


with open('lazylex/testdata.html') as f:
  TEST_HTML = f.read()


class OilDoc(unittest.TestCase):

  def testReplaceLink(self):
    """
    <a href=$xref:bash>bash</a>
    ->
    <a href=/cross-ref?tag=bash#bash>

    NOTE: THIs could really be done with a ref like <a.*href="(.*)">
    But we're testing it
    """
    print(oil_doc.ExpandLinks(TEST_HTML))

if __name__ == '__main__':
  unittest.main()
