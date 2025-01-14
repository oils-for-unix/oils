#!/usr/bin/env python2
from __future__ import print_function

import unittest

from lazylex import html  # module under test log = html.log
from typing import List
from typing import Tuple

log = html.log

with open('data_lang/testdata/hello.htm8') as f:
    TEST_HTML = f.read()


class RegexTest(unittest.TestCase):

    def testDotAll(self):
        # type: () -> None
        import re

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

    def testFindLineNum(self):
        # type: () -> None
        s = 'foo\n' * 3
        for pos in [1, 5, 10, 50]:  # out of bounds
            line_num = html.FindLineNum(s, pos)
            print(line_num)

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
    log('tag = %r', lex.TagName())
    for tok, start, end in lex.Tokens():
        log('%s %r', tok, lex.s[start:end])


class TagLexerTest(unittest.TestCase):

    def testTagLexer(self):
        # type: () -> None
        # Invalid!
        #lex = _MakeTagLexer('< >')
        #print(lex.Tag())

        lex = _MakeTagLexer('<a>')
        _PrintTokens(lex)

        lex = _MakeTagLexer('<a novalue>')
        _PrintTokens(lex)

        # Note: we could have a different HasAttr() method
        # <a novalue> means lex.Get('novalue') == ''
        # https://developer.mozilla.org/en-US/docs/Web/API/Element/hasAttribute
        self.assertEqual('', lex.GetAttrRaw('novalue'))

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
        # type: () -> None
        lex = _MakeTagLexer('<a href=foo class="bar" />')
        self.assertEqual('a', lex.TagName())

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


def _MakeAttrValueLexer(s):
    # type: (str) -> html.AttrValueLexer
    lex = html.AttrValueLexer(s)
    lex.Reset(0, len(s))
    return lex


class AttrValueLexerTest(unittest.TestCase):

    def testGood(self):
        # type: () -> None
        lex = _MakeAttrValueLexer('?foo=42&amp;bar=99')
        n = lex.NumTokens()
        self.assertEqual(3, n)


def Lex(h, no_special_tags=False):
    # type: (str, bool) -> List[Tuple[int, int]]
    print(repr(h))
    tokens = html.ValidTokenList(h, no_special_tags=no_special_tags)
    start_pos = 0
    for tok_id, end_pos in tokens:
        frag = h[start_pos:end_pos]
        log('%d %s %r', end_pos, html.TokenName(tok_id), frag)
        start_pos = end_pos
    return tokens


class LexerTest(unittest.TestCase):

    # IndexLinker in devtools/make_help.py
    #  <pre> sections in doc/html_help.py
    # TocExtractor in devtools/cmark.py

    def testPstrip(self):
        # type: () -> None
        """Remove anything like this.

        <p><pstrip> </pstrip></p>
        """
        pass

    def testCommentParse(self):
        # type: () -> None
        n = len(TEST_HTML)
        tokens = Lex(TEST_HTML)

    def testCommentParse2(self):
        # type: () -> None

        Tok = html.Tok
        h = '''
        hi <!-- line 1
                line 2 --><br/>'''
        tokens = Lex(h)

        self.assertEqual(
            [
                (Tok.RawData, 12),
                (Tok.Comment, 50),  # <? err ?>
                (Tok.StartEndTag, 55),
                (Tok.EndOfStream, 55),
            ],
            tokens)

    def testProcessingInstruction(self):
        # type: () -> None
        # <?xml ?> header
        Tok = html.Tok
        h = 'hi <? err ?>'
        tokens = Lex(h)

        self.assertEqual(
            [
                (Tok.RawData, 3),
                (Tok.Processing, 12),  # <? err ?>
                (Tok.EndOfStream, 12),
            ],
            tokens)

    def testScriptStyle(self):
        # type: () -> None
        Tok = html.Tok
        h = '''
        hi <script src=""> if (x < 1 && y > 2 ) { console.log(""); }
        </script>
        '''
        tokens = Lex(h)

        expected = [
            (Tok.RawData, 12),
            (Tok.StartTag, 27),  # <script>
            (Tok.HtmlCData, 78),  # JavaScript code is HTML CData
            (Tok.EndTag, 87),  # </script>
            (Tok.RawData, 96),  # \n
            (Tok.EndOfStream, 96),  # \n
        ]
        self.assertEqual(expected, tokens)

        # Test case matching
        tokens = Lex(h.replace('script', 'scrIPT'))
        self.assertEqual(expected, tokens)

    def testScriptStyleXml(self):
        # type: () -> None
        Tok = html.Tok
        h = 'hi <script src=""> &lt; </script>'
        # XML mode
        tokens = Lex(h, no_special_tags=True)

        self.assertEqual(
            [
                (Tok.RawData, 3),
                (Tok.StartTag, 18),  # <script>
                (Tok.RawData, 19),  # space
                (Tok.CharEntity, 23),  # </script>
                (Tok.RawData, 24),  # \n
                (Tok.EndTag, 33),  # \n
                (Tok.EndOfStream, 33),  # \n
            ],
            tokens)

    def testCData(self):
        # type: () -> None
        Tok = html.Tok

        # from
        # /home/andy/src/languages/Python-3.11.5/Lib/test/xmltestdata/c14n-20/inC14N4.xml
        h = '<compute><![CDATA[value>"0" && value<"10" ?"valid":"error"]]></compute>'
        tokens = Lex(h)

        self.assertEqual([
            (Tok.StartTag, 9),
            (Tok.CData, 61),
            (Tok.EndTag, 71),
            (Tok.EndOfStream, 71),
        ], tokens)

    def testEntity(self):
        # type: () -> None
        Tok = html.Tok

        # from
        # /home/andy/src/Python-3.12.4/Lib/test/xmltestdata/c14n-20/inC14N5.xml
        h = '&ent1;, &ent2;!'

        tokens = Lex(h)

        self.assertEqual([
            (Tok.CharEntity, 6),
            (Tok.RawData, 8),
            (Tok.CharEntity, 14),
            (Tok.RawData, 15),
            (Tok.EndOfStream, 15),
        ], tokens)

    def testStartTag(self):
        # type: () -> None
        Tok = html.Tok

        h = '<a>hi</a>'
        tokens = Lex(h)

        self.assertEqual([
            (Tok.StartTag, 3),
            (Tok.RawData, 5),
            (Tok.EndTag, 9),
            (Tok.EndOfStream, 9),
        ], tokens)

        # Make sure we don't consume too much
        h = '<a><source>1.7</source></a>'

        tokens = Lex(h)

        self.assertEqual([
            (Tok.StartTag, 3),
            (Tok.StartTag, 11),
            (Tok.RawData, 14),
            (Tok.EndTag, 23),
            (Tok.EndTag, 27),
            (Tok.EndOfStream, 27),
        ], tokens)

        return

        h = '''
        <configuration>
          <source>1.7</source>
        </configuration>'''

        tokens = Lex(h)

        self.assertEqual([
            (Tok.RawData, 9),
            (Tok.StartTag, 24),
            (Tok.RawData, 9),
            (Tok.EndOfStream, 9),
        ], tokens)

    def testBad(self):
        # type: () -> None
        Tok = html.Tok

        h = '&'
        tokens = Lex(h)

        self.assertEqual([
            (Tok.BadAmpersand, 1),
            (Tok.EndOfStream, 1),
        ], tokens)

        h = '>'
        tokens = Lex(h)

        self.assertEqual([
            (Tok.BadGreaterThan, 1),
            (Tok.EndOfStream, 1),
        ], tokens)

    def testInvalid(self):
        # type: () -> None
        Tok = html.Tok

        for s in INVALID_LEX:
            try:
                tokens = html.ValidTokenList(s)
            except html.LexError as e:
                print(e)
            else:
                self.fail('Expected LexError %r' % s)

    def testValid(self):
        # type: () -> None
        for s, _ in VALID_LEX:
            tokens = Lex(s)
            print()


INVALID_LEX = [
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
]

INVALID_PARSE = [
    '<a></b>',
    '<a>',  # missing closing tag
    '<meta></meta>',  # this is a self-closing tag
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
        for s in INVALID_LEX + INVALID_TAG_LEX:
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
            html.Validate(s, html.BALANCED_TAGS, counters)
            print('HTML5 %r' % s)
            print('HTML5 attrs %r' % counters.debug_attrs)

    def testValidXml(self):
        # type: () -> None
        counters = html.Counters()
        for s in VALID_XML:
            html.Validate(s, html.BALANCED_TAGS | html.NO_SPECIAL_TAGS,
                          counters)
            print('XML %r' % s)
            print('XML attrs %r' % counters.debug_attrs)


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
