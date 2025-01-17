#!/usr/bin/env python2
from __future__ import print_function

import unittest

from lazylex import html  # module under test log = html.log
from doctools.util import log


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


class LexerTest(unittest.TestCase):

    def testInvalid(self):
        # type: () -> None
        from data_lang.htm8_test import ValidTokenList
        for s in INVALID_LEX:
            try:
                tokens = ValidTokenList(s)
            except html.LexError as e:
                print(e)
            else:
                self.fail('Expected LexError %r' % s)

    def testValid(self):
        # type: () -> None

        from data_lang.htm8_test import Lex

        for s, _ in VALID_LEX:
            tokens = Lex(s)
            print()


INVALID_LEX = [
    '< >',
    '<a><',
    '&amp<',
    '&<',
    # Hm > is allowed?
    #'a > b',
    'a < b',
    '<!-- unfinished comment',
    '<? unfinished processing',
    '</div bad=attr> <a> <b>',

    # not allowed, but 3 > 4 is allowed
    '<a> 3 < 4 </a>',
    # Not a CDATA tag
    '<STYLEz><</STYLEz>',
]

SKIP = 0
UNCHANGED = 1

VALID_LEX = [
    # TODO: convert these to XML
    ('<foo></foo>', UNCHANGED),
    ('<foo x=y></foo>', ''),
    #('<foo x="&"></foo>', '<foo x="&amp;"></foo>'),
    ('<foo x="&"></foo>', ''),

    # Allowed with BadAmpersand
    ('<p> x & y </p>', '<p> x &amp; y </p>'),

    # No ambiguity
    ('<img src=/ >', ''),
    ('<img src="/">', ''),
    ('<img src=foo/ >', ''),
]

INVALID_PARSE = [
    '<a></b>',
    '<a>',  # missing closing tag
    '<meta></meta>',  # this is a self-closing tag
]

INVALID_ATTR_LEX = [
    # Ambiguous, should be ""
    '<img src=/>',
    '<img src= />',
    '<img src=foo/>',
    '<img src= foo/>',

    # Quoting
    '<img src=x"y">',
    "<img src=j''>",
]

VALID_PARSE = [
    ('<!DOCTYPE html>\n', ''),
    ('<!DOCTYPE>', ''),

    # empty strings
    ('<p x=""></p>', UNCHANGED),
    ("<p x=''></p>", UNCHANGED),
    ('<self-closing a="b" />', UNCHANGED),

    # We could also normalize CDATA?
    # Note that CDATA has an escaping problem: you need to handle it ]]> with
    # concatenation.  It just "pushes the problem around".
    # So I think it's better to use ONE kind of escaping, which is &lt;
    ('<script><![CDATA[ <wtf> >< ]]></script>', UNCHANGED),

    # allowed, but 3 < 4 is not allowed
    ('<a> 3 > 4 </a>', '<a> 3 &gt; 4 </a>'),
    # allowed, but 3 > 4 is not allowed
    ('<p x="3 < 4"></p>', ''),
    ('<b><a href="foo">link</a></b>', UNCHANGED),

    # TODO: should be self-closing
    #('<meta><a></a>', '<meta/><a></a>'),
    ('<meta><a></a>', ''),

    # no attribute
    ('<button disabled></button>', ''),
    ('<button disabled=></button>', ''),
    ('<button disabled= ></button>', ''),

    # single quoted is pretty common
    ("<a href='single'></a>", ''),

    # Conceding to reality - I used these myself
    ('<a href=ble.sh></a>', ''),
    ('<a href=foo.html></a>', ''),
    ('<foo x="&"></foo>', ''),

    # caps
    ('<foo></FOO>', ''),
    ('<Foo></fOO>', ''),

    # capital VOID tag
    ('<META><a></a>', ''),
    ('<script><</script>', ''),
    # matching
    ('<SCRipt><</SCRipt>', ''),
    ('<SCRIPT><</SCRIPT>', ''),
    ('<STYLE><</STYLE>', ''),
    #'<SCRipt><</script>',

    # Regression test from blog
    ('<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>',
     '')

    # Note: Python HTMLParser.py does DYNAMIC compilation of regex with re.I
    # flag to handle this!  Gah I want something faster.
    #'<script><</SCRIPT>',

    # TODO: Test <svg> and <math> ?
]

VALID_XML = [
    '<meta></meta>',
]

INVALID_TAG_LEX = [
    # not allowed, but 3 < 4 is allowed
    '<p x="3 > 4"></p>',
    # same thing
    '<a href=">"></a>',
    '<a foo=bar !></a>',  # bad attr
]


class ValidateTest(unittest.TestCase):

    def testInvalid(self):
        # type: () -> None
        counters = html.Counters()
        for s in INVALID_LEX + INVALID_TAG_LEX + INVALID_ATTR_LEX:
            try:
                html.Validate(s, html.BALANCED_TAGS, counters)
            except html.LexError as e:
                print(e)
            else:
                self.fail('Expected LexError %r' % s)

        for s in INVALID_PARSE:
            try:
                html.Validate(s, html.BALANCED_TAGS, counters)
            except html.ParseError as e:
                print(e)
            else:
                self.fail('Expected ParseError')

    def testValid(self):
        # type: () -> None
        counters = html.Counters()
        for s, _ in VALID_PARSE:
            print('HTML5 %r' % s)
            html.Validate(s, html.BALANCED_TAGS, counters)
            #print('HTML5 attrs %r' % counters.debug_attrs)

    def testValidXml(self):
        # type: () -> None
        counters = html.Counters()
        for s in VALID_XML:
            print('XML %r' % s)
            html.Validate(s, html.BALANCED_TAGS | html.NO_SPECIAL_TAGS,
                          counters)
            #print('XML attrs %r' % counters.debug_attrs)


class XmlTest(unittest.TestCase):

    def testValid(self):
        # type: () -> None
        counters = html.Counters()
        for h, expected_xml in VALID_LEX + VALID_PARSE:
            actual = html.ToXml(h)
            if expected_xml == UNCHANGED:  # Unchanged
                self.assertEqual(h, actual)
            elif expected_xml == '':  # Skip
                pass
            else:
                self.assertEqual(expected_xml, actual)


if __name__ == '__main__':
    unittest.main()
