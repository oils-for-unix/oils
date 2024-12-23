#!/usr/bin/env python2
from __future__ import print_function

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
        self.assertEqual(None, lex.GetAttrRaw('novalue'))

        lex = _MakeTagLexer('<a href="double quoted">')
        _PrintTokens(lex)

        self.assertEqual('double quoted', lex.GetAttrRaw('href'))
        self.assertEqual(None, lex.GetAttrRaw('oops'))

        lex = _MakeTagLexer('<a href=foo class="bar">')
        _PrintTokens(lex)

        lex = _MakeTagLexer('<a href=foo class="bar" />')
        _PrintTokens(lex)

        lex = _MakeTagLexer('<a href="?foo=1&amp;bar=2" />')
        self.assertEqual('?foo=1&amp;bar=2', lex.GetAttrRaw('href'))

    def testTagName(self):
        lex = _MakeTagLexer('<a href=foo class="bar" />')
        self.assertEqual('a', lex.TagName())

    def testAllAttrs(self):
        """
        [('key', 'value')] for all
        """
        # closed
        lex = _MakeTagLexer('<a href=foo class="bar" />')
        self.assertEqual([('href', 'foo'), ('class', 'bar')],
                         lex.AllAttrsRaw())

        lex = _MakeTagLexer('<a href="?foo=1&amp;bar=2" />')
        self.assertEqual([('href', '?foo=1&amp;bar=2')], lex.AllAttrsRaw())

    # IndexLinker in devtools/make_help.py
    #  <pre> sections in doc/html_help.py
    # TocExtractor in devtools/cmark.py

    def testPstrip(self):
        """Remove anything like this.

        <p><pstrip> </pstrip></p>
        """
        pass

    def testCommentParse(self):
        n = len(TEST_HTML)
        for tok_id, end_pos in html._Tokens(TEST_HTML, 0, n):
            if tok_id == html.Invalid:
                raise RuntimeError()
            print(tok_id)


if __name__ == '__main__':
    unittest.main()
