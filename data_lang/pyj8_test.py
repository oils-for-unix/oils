#!/usr/bin/env python2
"""
pyj8_test.py: Tests for pyj8.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.syntax_asdl import Id, Id_str
from core import error
from data_lang import pyj8  # module under test
from data_lang import j8
from mycpp import mylib
from mycpp.mylib import log


def _EncodeString(s, options):
    # type: (str, int) -> str
    buf = mylib.BufWriter()
    pyj8.WriteString(s, options, buf)
    return buf.getvalue()


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

    def testEncode(self):
        en = _EncodeString('hello', 0)
        print(en)

        en = _EncodeString('\xff-\xfe-\xff-\xfe', 0)
        print(en)

        # multiple errrors
        en = _EncodeString('hello\xffthere \xfe\xff gah', 0)
        print(en)

        # valid mu
        en = _EncodeString('hello \xce\xbc there', 0)
        print(en)

        # two first bytes - invalid
        en = _EncodeString('hello \xce\xce there', 0)
        print(en)

        # two cont bytes - invalid
        en = _EncodeString('hello \xbc\xbc there', 0)
        print(en)

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


if __name__ == '__main__':
    unittest.main()

# vim: sw=4
