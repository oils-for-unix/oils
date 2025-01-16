#!/usr/bin/env python2
from __future__ import print_function

from _devbuild.gen.htm8_asdl import (h8_id, h8_id_t, h8_id_str, attr_name)

import unittest
import re

from typing import List, Tuple

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

        attr_lexer = htm8.AttrLexer(h)
        attr_lexer.Init(lx.TagNamePos(), end_pos)

        # There is no tag
        n, name_start, name_end = attr_lexer.ReadName()
        self.assertEqual(n, attr_name.Done)
        self.assertEqual(-1, name_start)
        self.assertEqual(-1, name_end)

    def testInvalid(self):
        h = '<a !>'
        lx = htm8.Lexer(h)

        tok_id, end_pos = lx.Read()
        self.assertEqual(h8_id.StartTag, tok_id)

        attr_lexer = htm8.AttrLexer(h)
        attr_lexer.Init(lx.TagNamePos(), end_pos)

        n, name_start, name_end = attr_lexer.ReadName()
        self.assertEqual(n, attr_name.Invalid)
        self.assertEqual(-1, name_start)
        self.assertEqual(-1, name_end)

    def testEmpty(self):
        h = '<img src=/>'
        lx = htm8.Lexer(h)

        tok_id, end_pos = lx.Read()
        self.assertEqual(h8_id.StartEndTag, tok_id)

        attr_lexer = htm8.AttrLexer(h)
        attr_lexer.Init(lx.TagNamePos(), end_pos)

        n, name_start, name_end = attr_lexer.ReadName()
        self.assertEqual(n, attr_name.Ok)
        self.assertEqual(5, name_start)
        self.assertEqual(8, name_end)
        self.assertEqual(False, attr_lexer.next_value_is_missing)

        self.assertEqual(True, attr_lexer.AttrNameEquals('src'))
        self.assertEqual(False, attr_lexer.AttrNameEquals('srcz'))

    def testMissing(self):
        h = '<img SRC/>'
        lx = htm8.Lexer(h)

        tok_id, end_pos = lx.Read()
        self.assertEqual(h8_id.StartEndTag, tok_id)

        attr_lexer = htm8.AttrLexer(h)
        attr_lexer.Init(lx.TagNamePos(), end_pos)

        n, name_start, name_end = attr_lexer.ReadName()
        self.assertEqual(n, attr_name.Ok)
        self.assertEqual(5, name_start)
        self.assertEqual(8, name_end)
        self.assertEqual(True, attr_lexer.next_value_is_missing)

        self.assertEqual(True, attr_lexer.AttrNameEquals('src'))
        self.assertEqual(False, attr_lexer.AttrNameEquals('srcz'))

    def testAttr(self):
        h = '<a x=foo>'
        lx = htm8.Lexer(h)

        tok_id, end_pos = lx.Read()
        self.assertEqual(h8_id.StartTag, tok_id)

        attr_lexer = htm8.AttrLexer(h)
        attr_lexer.Init(lx.TagNamePos(), end_pos)
        n, name_start, name_end = attr_lexer.ReadName()
        self.assertEqual(n, attr_name.Ok)
        self.assertEqual(3, name_start)
        self.assertEqual(4, name_end)

        # Note: internal state set according to =


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
