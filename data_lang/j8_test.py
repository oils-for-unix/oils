#!/usr/bin/env python2
from __future__ import print_function

import unittest

from _devbuild.gen.syntax_asdl import Id, Id_str
from core import error
from data_lang import j8
from mycpp.mylib import log


def _PrintTokens(lex):
    log('---')
    log('J8 Case %r', lex.s)
    pos = 0
    while True:
        id_, end_pos, decoded = lex.Next()
        val = lex.s[pos:end_pos]
        d = repr(decoded) if decoded is not None else '-'
        log('    %20s %15r %15s', Id_str(id_), val, d)
        if id_ == Id.Eol_Tok:
            break
        pos = end_pos
    log('')


class J8Test(unittest.TestCase):

    def testJ8(self):
        s = '{}'
        p = j8.Parser(s, True)
        obj = p.ParseValue()
        print(obj)

    def testNil8Errors(self):
        cases = [
            '()',
            '(42)',
            '(:)',
            # extra input
            '(command.Simple))',
        ]
        for s in cases:
            p = j8.Nil8Parser(s, True)
            try:
                obj = p.ParseNil8()
            except error.Decode as e:
                print(e)
            else:
                self.fail('Expected error.Decode when parsing %r' % s)

    def testNil8(self):
        cases = [
            '(unquoted)',
            '(command.Simple)',
            '(<-)',  # symbol
            "(<- 1 b'hi')",  # any kinds of args
            "(<- 1 'hi' (f [1 2 3]))",  # symbol
            '[]',
            '[42]',
            '[42 43]',
            '[42 ["a" "b"]]',
            '42',
            '"hi"',
        ]
        for s in cases:
            p = j8.Nil8Parser(s, True)
            obj = p.ParseNil8()
            print(s)
            print('    %s' % obj)
            print()

    def testLexerDecoder(self):
        lex = j8.LexerDecoder(r'{"hi": "bye \n"}', True)
        _PrintTokens(lex)

        lex = j8.LexerDecoder(r"{u'unicode': b'bytes \y1f \yff'}", True)
        _PrintTokens(lex)

        lex = j8.LexerDecoder(
            r'{"mu \u03BC \u0001":' + r"b'mu \u{03bc} \u{2620}'", True)
        _PrintTokens(lex)

        lex = j8.LexerDecoder(r'{"x": [1, 2, 3.14, true]}', True)
        _PrintTokens(lex)

        lex = j8.LexerDecoder(
            r'''
        [
          1e9, 1e-9, -1e9, -1E-9, 42
        ]
        ''', True)
        _PrintTokens(lex)

        try:
            lex = j8.LexerDecoder('"\x01"', True)
            _PrintTokens(lex)
        except error.Decode as e:
            print(e)
        else:
            self.fail('Expected failure')

        try:
            lex = j8.LexerDecoder('"\x1f"', True)
            _PrintTokens(lex)
        except error.Decode as e:
            print(e)
        else:
            self.fail('Expected failure')

    def testMoreTokens(self):
        cases = [
            'true # comment',
            'truez8 # identifier',
            'truez8>  # symbol',
            '(<= 1 3)  # less than',
            # Can allow hex identifiers here like 123
            '(<- 123 (Token))',
            '(Node left:(-> 123))',
        ]
        for s in cases:
            lex = j8.LexerDecoder(s, True)
            _PrintTokens(lex)

    def testErrorMessagePosition(self):
        lex = j8.LexerDecoder("[ u'hi']", False)
        try:
            _PrintTokens(lex)
        except error.Decode as e:
            print(e)
            self.assertEquals(2, e.start_pos)
            self.assertEquals(4, e.end_pos)
        else:
            self.fail('Expected failure')


class YajlTest(unittest.TestCase):
    """
    Note on old tests for YAJL.  Differences

    - It decoded to Python 2 str() type, not unicode()
    - Bug in emitting \\xff literally, which is not valid JSON
      - turns out there is a C level option for this
    """
    pass


if __name__ == '__main__':
    unittest.main()

# vim: sw=4
