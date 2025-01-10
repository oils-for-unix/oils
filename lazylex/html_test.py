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


def Lex(h):
    print(repr(h))
    lex = html.ValidTokens(h)
    tokens = list(lex)
    for tok_id, end_pos in tokens:
        log('%d %s', end_pos, html.TokenName(tok_id))
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
        for tok_id, end_pos in html._Tokens(TEST_HTML, 0, n):
            if tok_id == html.Invalid:
                raise RuntimeError()
            print(tok_id)

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

    def testInvalid(self):
        Tok = html.Tok

        INVALID = [
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
        ]

        for s in INVALID:
            lex = html.ValidTokens(s)
            try:
                for i in xrange(5):
                    tok_id, pos = next(lex)
            except html.LexError as e:
                print(e)
            else:
                self.fail('Expected LexError')


if __name__ == '__main__':
    unittest.main()
