#!/usr/bin/env python2
from __future__ import print_function

import unittest

from lazylex import html  # module under test log = html.log

log = html.log

with open('lazylex/testdata.html') as f:
    TEST_HTML = f.read()


class RegexTest(unittest.TestCase):

    def testDotAll(self):
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


class FunctionsTest(unittest.TestCase):

    def testFindLineNum(self):
        s = 'foo\n' * 3
        for pos in [1, 5, 10, 50]:  # out of bounds
            line_num = html.FindLineNum(s, pos)
            print(line_num)


def _MakeTagLexer(s):
    lex = html.TagLexer(s)
    lex.Reset(0, len(s))
    return lex


def _PrintTokens(lex):
    log('')
    log('tag = %r', lex.TagName())
    for tok, start, end in lex.Tokens():
        log('%s %r', tok, lex.s[start:end])


class TagLexerTest(unittest.TestCase):

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

    def testAttrWithoutValue(self):
        # equivalent to <button disabled="">
        lex = _MakeTagLexer('<button disabled>')
        all_attrs = lex.AllAttrsRaw()
        log('all %s', all_attrs)

        try:
            lex = _MakeTagLexer('<a foo=bar !></a>')
            all_attrs = lex.AllAttrsRaw()
        except html.LexError as e:
            print(e)
        else:
            self.fail('Expected LexError')


def _MakeAttrValueLexer(s):
    lex = html.AttrValueLexer(s)
    lex.Reset(0, len(s))
    return lex


class AttrValueLexerTest(unittest.TestCase):

    def testGood(self):
        lex = _MakeAttrValueLexer('?foo=42&amp;bar=99')
        n = lex.NumTokens()
        self.assertEqual(3, n)


def Lex(h, no_special_tags=False):
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
        """Remove anything like this.

        <p><pstrip> </pstrip></p>
        """
        pass

    def testCommentParse(self):
        n = len(TEST_HTML)
        tokens = Lex(TEST_HTML)

    def testCommentParse2(self):

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
        Tok = html.Tok
        h = '''
        hi <script src=""> if (x < 1 && y > 2 ) { console.log(""); }
        </script>
        '''
        tokens = Lex(h)

        self.assertEqual(
            [
                (Tok.RawData, 12),
                (Tok.StartTag, 27),  # <script>
                (Tok.HtmlCData, 78),  # JavaScript code is HTML CData
                (Tok.EndTag, 87),  # </script>
                (Tok.RawData, 96),  # \n
                (Tok.EndOfStream, 96),  # \n
            ],
            tokens)

    def testScriptStyleXml(self):
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

    def testInvalid(self):
        Tok = html.Tok

        for s in INVALID_LEX:
            try:
                tokens = html.ValidTokenList(s)
            except html.LexError as e:
                print(e)
            else:
                self.fail('Expected LexError %r' % s)


INVALID_LEX = [
    # Should be &amp;
    '<a>&',
    '&amp',  # not finished
    '&#',  # not finished
    # Hm > is allowed?
    #'a > b',
    'a < b',
    '<!-- unfinished comment',
    '<? unfinished processing',
    '</div bad=attr> <a> <b>',

    # not allowed, but 3 > 4 is allowed
    '<a> 3 < 4 </a>',
]

INVALID_PARSE = [
    '<a></b>',
    '<a>',  # missing closing tag
    '<meta></meta>',  # this is a self-closing tag
]

VALID_PARSE = [
    '<!DOCTYPE html>\n',
    '<!DOCTYPE>',

    # empty strings
    '<p x=""></p>',
    "<p x=''></p>",

    # allowed, but 3 < 4 is not allowed
    '<a> 3 > 4 </a>',
    # allowed, but 3 > 4 is not allowed
    '<p x="3 < 4"></p>',
    '<b><a href="foo">link</a></b>',
    '<meta><a></a>',
    # no attribute
    '<button disabled></button>',
    '<button disabled=></button>',
    '<button disabled= ></button>',

    # single quoted is pretty common
    "<a href='single'></a>",

    # Conceding to reality - I used these myself
    '<a href=ble.sh></a>',
    '<a href=foo.html></a>',

    # TODO: capitalization should be allowed
    #'<META><a></a>',

    # TODO: Test <svg> and <math> ?
]

VALID_XML = [
    '<meta></meta>',
]

INVALID_TAG_LEX = [
    # not allowed, but 3 < 4 is allowed
    '<p x="3 > 4"></p>',
    '<a foo=bar !></a>',  # bad attr

    # should be escaped
    #'<a href="&"></a>',
    #'<a href=">"></a>',
]


class ValidateTest(unittest.TestCase):

    def testInvalid(self):
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
        counters = html.Counters()
        for s in VALID_PARSE:
            html.Validate(s, html.BALANCED_TAGS, counters)
            print('HTML5 %r' % s)
            print('HTML5 attrs %r' % counters.debug_attrs)

    def testValidXml(self):
        counters = html.Counters()
        for s in VALID_XML:
            html.Validate(s, html.BALANCED_TAGS | html.NO_SPECIAL_TAGS,
                          counters)
            print('XML %r' % s)
            print('XML attrs %r' % counters.debug_attrs)


if __name__ == '__main__':
    unittest.main()
