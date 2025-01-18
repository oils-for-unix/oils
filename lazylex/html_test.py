#!/usr/bin/env python2
from __future__ import print_function

import re
import unittest

from lazylex import html  # module under test log = html.log
from doctools.util import log


class RegexTest(unittest.TestCase):

    def testDotAll(self):
        # type: () -> None

        # Note that $ matches end of line, not end of string
        p1 = re.compile(r'.')
        print(p1.match('\n'))

        p2 = re.compile(r'.', re.DOTALL)
        print(p2.match('\n'))

        #p3 = re.compile(r'[.\n]', re.VERBOSE)
        p3 = re.compile(r'[.\n]')
        print(p3.match('\n'))

        print('Negation')

        p4 = re.compile(r'[^>]')
        print(p4.match('\n'))

    def testAttrRe(self):
        # type: () -> None
        _ATTR_RE = html._ATTR_RE
        m = _ATTR_RE.match(' empty= val')
        print(m.groups())


class FunctionsTest(unittest.TestCase):

    def testToText(self):
        # type: () -> None
        t = html.ToText('<b name="&amp;"> three &lt; four && five </b>')
        self.assertEqual(' three < four && five ', t)


def _MakeTagLexer(s):
    # type: (str) -> html.TagLexer
    lex = html.TagLexer(s)
    lex.Reset(0, len(s))
    return lex


def _PrintTokens(lex):
    # type: (html.TagLexer) -> None
    log('')
    log('tag = %r', lex.GetTagName())
    for tok, start, end in lex.Tokens():
        log('%s %r', tok, lex.s[start:end])


class TagLexerTest(unittest.TestCase):

    def testTagName_DEPRECATED(self):
        # type: () -> None
        lex = _MakeTagLexer('<a href=foo class="bar" />')
        self.assertEqual('a', lex.GetTagName())

    def testGetAttrRaw(self):
        # type: () -> None
        lex = _MakeTagLexer('<a>')
        _PrintTokens(lex)
        self.assertEqual(None, lex.GetAttrRaw('oops'))

        # <a novalue> means lex.Get('novalue') == ''
        # https://developer.mozilla.org/en-US/docs/Web/API/Element/hasAttribute
        # We are not distinguishing <a novalue=""> from <a novalue> in this API
        lex = _MakeTagLexer('<a novalue>')
        _PrintTokens(lex)
        self.assertEqual('', lex.GetAttrRaw('novalue'))

        lex = _MakeTagLexer('<a href="double quoted">')
        _PrintTokens(lex)

        self.assertEqual('double quoted', lex.GetAttrRaw('href'))
        self.assertEqual(None, lex.GetAttrRaw('oops'))

        lex = _MakeTagLexer('<a href=foo class="bar">')
        _PrintTokens(lex)
        self.assertEqual('bar', lex.GetAttrRaw('class'))

        lex = _MakeTagLexer('<a href=foo class="bar" />')
        _PrintTokens(lex)
        self.assertEqual('bar', lex.GetAttrRaw('class'))

        lex = _MakeTagLexer('<a href="?foo=1&amp;bar=2" />')
        self.assertEqual('?foo=1&amp;bar=2', lex.GetAttrRaw('href'))

    def testAllAttrs(self):
        # type: () -> None
        """
        [('key', 'value')] for all
        """
        # closed
        lex = _MakeTagLexer('<a href=foo class="bar" />')
        self.assertEqual([('href', 'foo'), ('class', 'bar')],
                         lex.AllAttrsRaw())

        lex = _MakeTagLexer('<a href="?foo=1&amp;bar=2" />')
        self.assertEqual([('href', '?foo=1&amp;bar=2')], lex.AllAttrsRaw())

    def testEmptyMissingValues(self):
        # type: () -> None
        # equivalent to <button disabled="">
        lex = _MakeTagLexer('<button disabled>')
        all_attrs = lex.AllAttrsRaw()
        self.assertEqual([('disabled', '')], all_attrs)

        slices = lex.AllAttrsRawSlice()
        log('slices %s', slices)

        lex = _MakeTagLexer(
            '''<p double="" single='' empty= value missing empty2=>''')
        all_attrs = lex.AllAttrsRaw()
        self.assertEqual([
            ('double', ''),
            ('single', ''),
            ('empty', 'value'),
            ('missing', ''),
            ('empty2', ''),
        ], all_attrs)
        # TODO: should have
        log('all %s', all_attrs)

        slices = lex.AllAttrsRawSlice()
        log('slices %s', slices)

    def testInvalidTag(self):
        # type: () -> None
        try:
            lex = _MakeTagLexer('<a foo=bar !></a>')
            all_attrs = lex.AllAttrsRaw()
        except html.LexError as e:
            print(e)
        else:
            self.fail('Expected LexError')


if __name__ == '__main__':
    unittest.main()
