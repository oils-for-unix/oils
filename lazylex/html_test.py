#!/usr/bin/env python2
"""
html_test.py: Tests for html.py
"""
from __future__ import print_function

import sys
import unittest

from lazylex import html  # module under test log = html.log 

log = html.log

with open('lazylex/testdata.html') as f:
  TEST_HTML = f.read()


def _MakeTagLexer(s):
  lex = html.TagLexer(s)
  lex.Reset(0, len(s))
  return lex


def _PrintTokens(lex):
  log('')
  log('tag = %r', lex.TagName())
  for tok, start, end in lex.Tokens():
    log('%s %r', tok, lex.s[start:end])


class HtmlTest(unittest.TestCase):

  def testTagLexer(self):
    # Invalid!
    #lex = _MakeTagLexer('< >')
    #print(lex.Tag())

    lex = _MakeTagLexer('<a>')
    _PrintTokens(lex)

    lex = _MakeTagLexer('<a novalue>')
    _PrintTokens(lex)

    # Note: we could have a different HasAttr() method
    # <a novalue> means lex.Get('novalue') == None
    # https://developer.mozilla.org/en-US/docs/Web/API/Element/hasAttribute
    self.assertEqual(None, lex.GetAttr('novalue'))

    lex = _MakeTagLexer('<a href="double quoted">')
    _PrintTokens(lex)

    self.assertEqual('double quoted', lex.GetAttr('href'))
    self.assertEqual(None, lex.GetAttr('oops'))

    lex = _MakeTagLexer('<a href=foo class="bar">')
    _PrintTokens(lex)

    lex = _MakeTagLexer('<a href=foo class="bar" />')
    _PrintTokens(lex)

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

  def testCommentParse(self):
    """
    """
    for tok_id, end_pos in html.Tokens(TEST_HTML):
      if tok_id == html.Invalid:
        raise RuntimeError(event)
      print(tok_id)


if __name__ == '__main__':
  unittest.main()
