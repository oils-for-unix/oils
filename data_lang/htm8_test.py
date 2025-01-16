#!/usr/bin/env python2
from __future__ import print_function

from _devbuild.gen.htm8_asdl import (h8_id, h8_id_t, h8_id_str, attr_name,
                                     attr_name_str, attr_value_e,
                                     attr_value_str)

import unittest
import re

from typing import List, Tuple, Any

from data_lang import htm8
from doctools.util import log

with open('data_lang/testdata/hello.htm8') as f:
    TEST_HTML = f.read()


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
        _ATTR_RE = htm8._ATTR_RE
        m = _ATTR_RE.match(' empty= val')
        print(m.groups())


class FunctionsTest(unittest.TestCase):

    def testFindLineNum(self):
        # type: () -> None
        s = 'foo\n' * 3
        for pos in [1, 5, 10, 50]:  # out of bounds
            line_num = htm8._FindLineNum(s, pos)
            print(line_num)


def _MakeAttrLexer(t, h, expected_tag=h8_id.StartTag):
    # type: (Any, str) -> htm8.AttrLexer

    lx = htm8.Lexer(h)

    tok_id, end_pos = lx.Read()
    t.assertEqual(expected_tag, tok_id)

    attr_lx = htm8.AttrLexer(h)
    attr_lx.Init(lx.TagNamePos(), end_pos)

    return attr_lx


class AttrLexerTest(unittest.TestCase):

    def testNoAttrs(self):
        # type: () -> None

        # TODO: h8_id.StartTag and EndTag will expose the tag_name_pos - the
        # end of the tag name

        h = 'x <a>'
        lx = htm8.Lexer(h)

        # Skip raw data
        tok_id, end_pos = lx.Read()
        self.assertEqual(h8_id.RawData, tok_id)

        tok_id, end_pos = lx.Read()
        self.assertEqual(h8_id.StartTag, tok_id)

        attr_lx = htm8.AttrLexer(h)
        attr_lx.Init(lx.TagNamePos(), end_pos)

        # There is no tag
        n, name_start, name_end = attr_lx.ReadName()
        self.assertEqual(n, attr_name.Done)
        self.assertEqual(-1, name_start)
        self.assertEqual(-1, name_end)

        try:
            result = attr_lx.ReadValue()
        except AssertionError as e:
            print(e)
        else:
            self.fail('should have failed')

        try:
            result = attr_lx.ReadName()
        except AssertionError as e:
            print(e)
        else:
            self.fail('should have failed')

    def testInvalid(self):
        h = '<a !>'
        attr_lx = _MakeAttrLexer(self, h)

        n, name_start, name_end = attr_lx.ReadName()
        self.assertEqual(n, attr_name.Invalid)
        self.assertEqual(-1, name_start)
        self.assertEqual(-1, name_end)

        try:
            result = attr_lx.ReadValue()
        except AssertionError as e:
            print(e)
        else:
            self.fail('should have failed')

    def testEmpty(self):
        h = '<img src=/>'
        attr_lx = _MakeAttrLexer(self, h, expected_tag=h8_id.StartEndTag)

        n, name_start, name_end = attr_lx.ReadName()
        self.assertEqual(n, attr_name.Ok)
        self.assertEqual(5, name_start)
        self.assertEqual(8, name_end)
        self.assertEqual(False, attr_lx.next_value_is_missing)

        self.assertEqual(True, attr_lx.AttrNameEquals('src'))
        self.assertEqual(False, attr_lx.AttrNameEquals('srcz'))

        v, attr_start, attr_end = attr_lx.ReadValue()
        log('v = %s', attr_value_str(v))
        self.assertEqual(attr_value_e.Empty, v)
        self.assertEqual(-1, attr_start)
        self.assertEqual(-1, attr_end)

        n, name_start, name_end = attr_lx.ReadName()
        self.assertEqual(n, attr_name.Done)

    def testMissing(self):
        h = '<img SRC/>'
        attr_lx = _MakeAttrLexer(self, h, expected_tag=h8_id.StartEndTag)

        n, name_start, name_end = attr_lx.ReadName()
        self.assertEqual(n, attr_name.Ok)
        self.assertEqual(5, name_start)
        self.assertEqual(8, name_end)
        self.assertEqual(True, attr_lx.next_value_is_missing)

        self.assertEqual(True, attr_lx.AttrNameEquals('src'))
        self.assertEqual(False, attr_lx.AttrNameEquals('srcz'))

        v, attr_start, attr_end = attr_lx.ReadValue()
        self.assertEqual(attr_value_e.Missing, v)
        self.assertEqual(-1, attr_start)
        self.assertEqual(-1, attr_end)

        n, name_start, name_end = attr_lx.ReadName()
        self.assertEqual(n, attr_name.Done)

    def testUnquoted(self):
        # CAREFUL: /> is a StartEndTag, and / is not part of unquoted value
        h = '<a x=foo/>'
        attr_lx = _MakeAttrLexer(self, h, expected_tag=h8_id.StartEndTag)

        n, name_start, name_end = attr_lx.ReadName()
        self.assertEqual(n, attr_name.Ok)
        self.assertEqual(3, name_start)
        self.assertEqual(4, name_end)

        v, attr_start, attr_end = attr_lx.ReadValue()

        log('v = %s', attr_value_str(v))
        log('unquoted val %r', h[attr_start:attr_end])

        self.assertEqual(attr_value_e.Unquoted, v)
        self.assertEqual(5, attr_start)
        self.assertEqual(8, attr_end)

        n, name_start, name_end = attr_lx.ReadName()
        self.assertEqual(n, attr_name.Done)

    def testDoubleQuoted(self):
        h = '<a x="f&">'
        attr_lx = _MakeAttrLexer(self, h, expected_tag=h8_id.StartTag)

        n, name_start, name_end = attr_lx.ReadName()
        self.assertEqual(n, attr_name.Ok)
        self.assertEqual(3, name_start)
        self.assertEqual(4, name_end)

        v, attr_start, attr_end = attr_lx.ReadValue()

        log('v = %s', attr_value_str(v))
        log('val %r', h[attr_start:attr_end])

        self.assertEqual(attr_value_e.DoubleQuoted, v)
        self.assertEqual(6, attr_start)
        self.assertEqual(8, attr_end)
        self.assertEqual(9, attr_lx.pos)

        n, name_start, name_end = attr_lx.ReadName()
        log('n = %r', attr_name_str(n))
        self.assertEqual(n, attr_name.Done)

    def testSingleQuoted(self):
        h = "<a x='&f'>"
        attr_lx = _MakeAttrLexer(self, h, expected_tag=h8_id.StartTag)

        n, name_start, name_end = attr_lx.ReadName()
        self.assertEqual(n, attr_name.Ok)
        self.assertEqual(3, name_start)
        self.assertEqual(4, name_end)

        v, attr_start, attr_end = attr_lx.ReadValue()

        log('v = %s', attr_value_str(v))
        log('unquoted val %r', h[attr_start:attr_end])

        self.assertEqual(attr_value_e.SingleQuoted, v)
        self.assertEqual(6, attr_start)
        self.assertEqual(8, attr_end)
        self.assertEqual(9, attr_lx.pos)

        n, name_start, name_end = attr_lx.ReadName()
        #log('n = %r', attr_name_str(n))
        self.assertEqual(n, attr_name.Done)

    def testDoubleQuoted_Bad(self):
        h = '<a x="foo>'
        attr_lx = _MakeAttrLexer(self, h, expected_tag=h8_id.StartTag)

        n, name_start, name_end = attr_lx.ReadName()
        self.assertEqual(n, attr_name.Ok)
        self.assertEqual(3, name_start)
        self.assertEqual(4, name_end)

        try:
            v, attr_start, attr_end = attr_lx.ReadValue()
        except htm8.LexError as e:
            print(e)
        else:
            self.fail('Expected LexError')

    def testSingleQuoted_Bad(self):
        h = "<a x='foo>"
        attr_lx = _MakeAttrLexer(self, h, expected_tag=h8_id.StartTag)

        n, name_start, name_end = attr_lx.ReadName()
        self.assertEqual(n, attr_name.Ok)
        self.assertEqual(3, name_start)
        self.assertEqual(4, name_end)

        try:
            v, attr_start, attr_end = attr_lx.ReadValue()
        except htm8.LexError as e:
            print(e)
        else:
            self.fail('Expected LexError')


class AttrLexerWrapperTest(unittest.TestCase):

    def testGetAttrRaw(self):
        # type: () -> None
        lex = _MakeAttrLexer(self, '<a>')
        #_PrintTokens(lex)
        self.assertEqual(None, htm8.GetAttrRaw(lex, 'oops'))

        # <a novalue> means lex.Get('novalue') == ''
        # https://developer.mozilla.org/en-US/docs/Web/API/Element/hasAttribute
        # We are not distinguishing <a novalue=""> from <a novalue> in this API
        lex = _MakeAttrLexer(self, '<a novalue>')
        #_PrintTokens(lex)
        self.assertEqual('', htm8.GetAttrRaw(lex, 'novalue'))

    def testGetAttrRaw2(self):
        lex = _MakeAttrLexer(self, '<a href="double quoted">')
        #_PrintTokens(lex)

        log('*** OOPS')
        self.assertEqual(None, htm8.GetAttrRaw(lex, 'oops'))
        lex.Reset()
        log('*** DOUBLE')
        self.assertEqual('double quoted', htm8.GetAttrRaw(lex, 'href'))

    def testGetAttrRaw3(self):
        """Reverse order vs. testGetAttrRaw2"""
        lex = _MakeAttrLexer(self, '<a href="double quoted">')
        #_PrintTokens(lex)

        self.assertEqual('double quoted', htm8.GetAttrRaw(lex, 'href'))
        lex.Reset()
        self.assertEqual(None, htm8.GetAttrRaw(lex, 'oops'))

    def testGetAttrRaw4(self):

        lex = _MakeAttrLexer(self, '<a href=foo class="bar">')
        #_PrintTokens(lex)
        self.assertEqual('bar', htm8.GetAttrRaw(lex, 'class'))

        lex = _MakeAttrLexer(self,
                             '<a href=foo class="bar" />',
                             expected_tag=h8_id.StartEndTag)
        #_PrintTokens(lex)
        self.assertEqual('bar', htm8.GetAttrRaw(lex, 'class'))

        lex = _MakeAttrLexer(self,
                             '<a href="?foo=1&amp;bar=2" />',
                             expected_tag=h8_id.StartEndTag)
        self.assertEqual('?foo=1&amp;bar=2', htm8.GetAttrRaw(lex, 'href'))

    def testAllAttrs(self):
        # type: () -> None
        """
        [('key', 'value')] for all
        """
        # closed
        lex = _MakeAttrLexer(self,
                             '<a href=foo class="bar" />',
                             expected_tag=h8_id.StartEndTag)
        self.assertEqual([('href', 'foo'), ('class', 'bar')],
                         htm8.AllAttrsRaw(lex))

        lex = _MakeAttrLexer(self,
                             '<a href="?foo=1&amp;bar=2" />',
                             expected_tag=h8_id.StartEndTag)
        self.assertEqual([('href', '?foo=1&amp;bar=2')], htm8.AllAttrsRaw(lex))

    def testEmptyMissingValues(self):
        # type: () -> None
        # equivalent to <button disabled="">
        lex = _MakeAttrLexer(self, '<button disabled>')
        all_attrs = htm8.AllAttrsRaw(lex)
        self.assertEqual([('disabled', '')], all_attrs)

        # TODO: restore this
        if 0:
            slices = lex.AllAttrsRawSlice()
            log('slices %s', slices)

        lex = _MakeAttrLexer(
            self, '''<p double="" single='' empty= value missing empty2=>''')
        all_attrs = htm8.AllAttrsRaw(lex)
        self.assertEqual([
            ('double', ''),
            ('single', ''),
            ('empty', 'value'),
            ('missing', ''),
            ('empty2', ''),
        ], all_attrs)
        # TODO: should have
        log('all %s', all_attrs)

        if 0:
            slices = lex.AllAttrsRawSlice()
            log('slices %s', slices)

    def testInvalidTag(self):
        # type: () -> None
        try:
            lex = _MakeAttrLexer(self, '<a foo=bar !></a>')
            all_attrs = htm8.AllAttrsRaw(lex)
        except htm8.LexError as e:
            print(e)
        else:
            self.fail('Expected LexError')


def ValidTokenList(s, no_special_tags=False):
    # type: (str, bool) -> List[Tuple[h8_id_t, int]]
    """A wrapper that can be more easily translated to C++.  Doesn't use iterators."""

    start_pos = 0
    tokens = []
    lx = htm8.Lexer(s, no_special_tags=no_special_tags)
    while True:
        tok_id, end_pos = lx.Read()
        tokens.append((tok_id, end_pos))
        if tok_id == h8_id.EndOfStream:
            break
        if tok_id == h8_id.Invalid:
            raise htm8.LexError(s, start_pos)
        start_pos = end_pos
    return tokens


def Lex(h, no_special_tags=False):
    # type: (str, bool) -> List[Tuple[int, int]]
    print(repr(h))
    tokens = ValidTokenList(h, no_special_tags=no_special_tags)
    start_pos = 0
    for tok_id, end_pos in tokens:
        frag = h[start_pos:end_pos]
        log('%d %s %r', end_pos, h8_id_str(tok_id), frag)
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
        h = '''
        hi <!-- line 1
                line 2 --><br/>'''
        tokens = Lex(h)

        self.assertEqual(
            [
                (h8_id.RawData, 12),
                (h8_id.Comment, 50),  # <? err ?>
                (h8_id.StartEndTag, 55),
                (h8_id.EndOfStream, 55),
            ],
            tokens)

    def testProcessingInstruction(self):
        # type: () -> None
        # <?xml ?> header
        h = 'hi <? err ?>'
        tokens = Lex(h)

        self.assertEqual(
            [
                (h8_id.RawData, 3),
                (h8_id.Processing, 12),  # <? err ?>
                (h8_id.EndOfStream, 12),
            ],
            tokens)

    def testScriptStyle(self):
        # type: () -> None
        h = '''
        hi <script src=""> if (x < 1 && y > 2 ) { console.log(""); }
        </script>
        '''
        tokens = Lex(h)

        expected = [
            (h8_id.RawData, 12),
            (h8_id.StartTag, 27),  # <script>
            (h8_id.HtmlCData, 78),  # JavaScript code is HTML CData
            (h8_id.EndTag, 87),  # </script>
            (h8_id.RawData, 96),  # \n
            (h8_id.EndOfStream, 96),  # \n
        ]
        self.assertEqual(expected, tokens)

        # Test case matching
        tokens = Lex(h.replace('script', 'scrIPT'))
        self.assertEqual(expected, tokens)

    def testScriptStyleXml(self):
        # type: () -> None
        h = 'hi <script src=""> &lt; </script>'
        # XML mode
        tokens = Lex(h, no_special_tags=True)

        self.assertEqual(
            [
                (h8_id.RawData, 3),
                (h8_id.StartTag, 18),  # <script>
                (h8_id.RawData, 19),  # space
                (h8_id.CharEntity, 23),  # </script>
                (h8_id.RawData, 24),  # \n
                (h8_id.EndTag, 33),  # \n
                (h8_id.EndOfStream, 33),  # \n
            ],
            tokens)

    def testCData(self):
        # type: () -> None

        # from
        # /home/andy/src/languages/Python-3.11.5/Lib/test/xmltestdata/c14n-20/inC14N4.xml
        h = '<compute><![CDATA[value>"0" && value<"10" ?"valid":"error"]]></compute>'
        tokens = Lex(h)

        self.assertEqual([
            (h8_id.StartTag, 9),
            (h8_id.CData, 61),
            (h8_id.EndTag, 71),
            (h8_id.EndOfStream, 71),
        ], tokens)

    def testEntity(self):
        # type: () -> None

        # from
        # /home/andy/src/Python-3.12.4/Lib/test/xmltestdata/c14n-20/inC14N5.xml
        h = '&ent1;, &ent2;!'

        tokens = Lex(h)

        self.assertEqual([
            (h8_id.CharEntity, 6),
            (h8_id.RawData, 8),
            (h8_id.CharEntity, 14),
            (h8_id.RawData, 15),
            (h8_id.EndOfStream, 15),
        ], tokens)

    def testStartTag(self):
        # type: () -> None

        h = '<a>hi</a>'
        tokens = Lex(h)

        self.assertEqual([
            (h8_id.StartTag, 3),
            (h8_id.RawData, 5),
            (h8_id.EndTag, 9),
            (h8_id.EndOfStream, 9),
        ], tokens)

        # Make sure we don't consume too much
        h = '<a><source>1.7</source></a>'

        tokens = Lex(h)

        self.assertEqual([
            (h8_id.StartTag, 3),
            (h8_id.StartTag, 11),
            (h8_id.RawData, 14),
            (h8_id.EndTag, 23),
            (h8_id.EndTag, 27),
            (h8_id.EndOfStream, 27),
        ], tokens)

        return

        h = '''
        <configuration>
          <source>1.7</source>
        </configuration>'''

        tokens = Lex(h)

        self.assertEqual([
            (h8_id.RawData, 9),
            (h8_id.StartTag, 24),
            (h8_id.RawData, 9),
            (h8_id.EndOfStream, 9),
        ], tokens)

    def testBad(self):
        # type: () -> None
        h = '&'
        tokens = Lex(h)

        self.assertEqual([
            (h8_id.BadAmpersand, 1),
            (h8_id.EndOfStream, 1),
        ], tokens)

        h = '>'
        tokens = Lex(h)

        self.assertEqual([
            (h8_id.BadGreaterThan, 1),
            (h8_id.EndOfStream, 1),
        ], tokens)

    def testEndOfStream(self):
        # type: () -> None

        # NUL is end
        h = 'a\0b'
        tokens = Lex(h)

        self.assertEqual([
            (h8_id.RawData, 1),
            (h8_id.EndOfStream, 2),
        ], tokens)


if __name__ == '__main__':
    unittest.main()
