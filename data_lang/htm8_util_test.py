#!/usr/bin/env python2
from __future__ import print_function

import unittest

from data_lang import htm8
from data_lang import htm8_util
#from doctools.util import log


class LexerTest(unittest.TestCase):

    def testInvalid(self):
        # type: () -> None
        from data_lang.htm8_test import ValidTokenList
        for s in INVALID_LEX:
            try:
                tokens = ValidTokenList(s)
            except htm8.LexError as e:
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
    ('<foo x=y></foo>', '<foo x="y"></foo>'),
    #('<foo x="&"></foo>', '<foo x="&amp;"></foo>'),
    ('<foo x="&"></foo>', ''),

    # Allowed with BadAmpersand
    ('<p> x & y </p>', '<p> x &amp; y </p>'),

    # No ambiguity
    ('<img src=/ >', '<img src="/" >'),
    ('<img src="/">', UNCHANGED),
    ('<img src=foo/ >', '<img src="foo/" >'),
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
    ('<button disabled></button>', '<button disabled=""></button>'),
    ('<button disabled=></button>', '<button disabled=""></button>'),
    ('<button disabled= ></button>', '<button disabled= ""></button>'),

    # single quoted is pretty common
    ("<a href='single'></a>", ''),

    # Conceding to reality - I used these myself
    ('<a href=ble.sh></a>', '<a href="ble.sh"></a>'),
    ('<a href=foo.html></a>', '<a href="foo.html"></a>'),
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
    # bad attr
    '<a foo=bar !></a>',

    # BUG: are we "overshooting" here?  We don't have a sentinel
    # I wonder if a one-pass lex is just simpler:
    # - It works with micro-syntax
    # - And it doesn't have this problem, as well as the stupid / problem
    # - You can add a sentinel, but then you mess up COW of forked processes,
    #   potentially
    # - As long as you don't allocate, I think it's not going to be any faster
    # to skip the attributes
    # - We could also handle <a href=">"> then
 
    # Not allowed, but 3 < 4 is allowed
    '<p x="3 > 4"></p>',
    # with single quotes
    "<p x='3 > 4'></p>",
    # Same thing
    '<a href=">"></a>',
]


class ValidateTest(unittest.TestCase):

    def testInvalid(self):
        # type: () -> None
        counters = htm8_util.Counters()
        for s in INVALID_LEX + INVALID_TAG_LEX + INVALID_ATTR_LEX:
            try:
                htm8_util.Validate(s, htm8_util.BALANCED_TAGS, counters)
            except htm8.LexError as e:
                print(e)
            else:
                self.fail('Expected LexError %r' % s)

        for s in INVALID_PARSE:
            try:
                htm8_util.Validate(s, htm8_util.BALANCED_TAGS, counters)
            except htm8.ParseError as e:
                print(e)
            else:
                self.fail('Expected ParseError')

    def testValid(self):
        # type: () -> None
        counters = htm8_util.Counters()
        for s, _ in VALID_PARSE:
            print('HTML5 %r' % s)
            htm8_util.Validate(s, htm8_util.BALANCED_TAGS, counters)
            #print('HTML5 attrs %r' % counters.debug_attrs)

    def testValidXml(self):
        # type: () -> None
        counters = htm8_util.Counters()
        for s in VALID_XML:
            print('XML %r' % s)
            htm8_util.Validate(
                s, htm8_util.BALANCED_TAGS | htm8_util.NO_SPECIAL_TAGS,
                counters)
            #print('XML attrs %r' % counters.debug_attrs)


class XmlTest(unittest.TestCase):

    def testValid(self):
        # type: () -> None
        counters = htm8_util.Counters()
        for h, expected_xml in VALID_LEX + VALID_PARSE:
            actual = htm8_util.ToXml(h)
            if expected_xml == UNCHANGED:  # Unchanged
                self.assertEqual(h, actual)
            elif expected_xml == '':  # Skip
                pass
            else:
                self.assertEqual(expected_xml, actual)


if __name__ == '__main__':
    unittest.main()
