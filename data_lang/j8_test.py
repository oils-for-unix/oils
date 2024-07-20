#!/usr/bin/env python2
from __future__ import print_function

import unittest

from _devbuild.gen.syntax_asdl import Id, Id_str
from core import error
from data_lang import j8
from mycpp.mylib import log


class FunctionsTest(unittest.TestCase):

    def testUtf8Encode(self):
        CASES = [
            (u'\u0065'.encode('utf-8'), 0x0065),
            (u'\u0100'.encode('utf-8'), 0x0100),
            (u'\u1234'.encode('utf-8'), 0x1234),
            (u'\U00020000'.encode('utf-8'), 0x00020000),
            # Out of range is checked elsewhere
            #('\xef\xbf\xbd', 0x10020000),
        ]

        for expected, code_point in CASES:
            print('')
            print('Utf8Encode case %r %r' % (expected, code_point))
            self.assertEqual(expected, j8.Utf8Encode(code_point))


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


class Nil8Test(unittest.TestCase):

    def testNil8Errors(self):
        cases = [
            #'()',
            #'(42)',
            #'(:)',
            # extra input
            '(command.Simple))',
            '(',
            '(obj.field',
            '(obj.',

            # Expected a value afterward
            '(obj.)',
            '(obj.+',
            '(obj.+)',
            '(obj.[)',
        ]
        for s in cases:
            p = j8.Nil8Parser(s, True)
            try:
                obj = p.ParseNil8()
            except error.Decode as e:
                print(e)
            else:
                self.fail('Expected error.Decode when parsing %r' % s)

    def testNil8Operator(self):
        # Should be equivalent!

        cases = [
            # These are equivalent, note that parens like (key: "value") add another layer
            ('(: key "value")', 'key: "value"'),
            ('((: k "v") (: k2 "v2"))', '(k: "v" k2: "v2")'),
            ('(@ "str" x123)', '"str" @ x123'),
            ('((! a b) c)', '( a ! b c)'),
            ('(c (! a b))', '( c a ! b )'),
            ('(. (. obj field1) field2)', 'obj.field1.field2'),
            ('((-> obj method) (. obj field))', '(obj->method obj.field1)'),
        ]
        for prefix, infix in cases:
            print()
            print('PREFIX %s' % prefix)
            p = j8.Nil8Parser(prefix, True)
            obj1 = p.ParseNil8()
            print(obj1)
            log('len %d', len(obj1.items))

            print()
            print('INFIX %s' % infix)
            p = j8.Nil8Parser(infix, True)
            obj2 = p.ParseNil8()
            print(obj2)
            log('len %d', len(obj2.items))

            self.assertEqual(obj1.tag(), obj2.tag(),
                             '%s != %s' % (obj1.tag(), obj2.tag()))
            self.assertEqual(len(obj1.items), len(obj2.items))

    def testNil8(self):
        cases = [
            '(unquoted)',
            '(command.Simple)',
            '(f x)',
            '(f 42 "hi")',
            '((-> obj method) (. obj field))',

            # address
            '(@ x123 (Token "foo"))',
            '(: key "value")',
            '(. x123)',  # dereference, could be @

            #'(Token "foo") @ x123',

            # TODO: parse like infix
            '(Token key:"value" k2:"v2")',

            # Should be parsed like infix operator
            '(key !x123)',
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


class J8Test(unittest.TestCase):

    def testJ8(self):
        s = '{}'
        p = j8.Parser(s, True)
        obj = p.ParseValue()
        print(obj)

    def testLexerDecoder(self):
        lex = j8.LexerDecoder(r'{"hi": "bye \n"}', True, 'J8')
        _PrintTokens(lex)

        lex = j8.LexerDecoder(r"{u'unicode': b'bytes \y1f \yff'}", True, 'J8')
        _PrintTokens(lex)

        lex = j8.LexerDecoder(
            r'{"mu \u03BC \u0001":' + r"b'mu \u{03bc} \u{2620}'", True, 'J8')
        _PrintTokens(lex)

        lex = j8.LexerDecoder(r'{"x": [1, 2, 3.14, true]}', True, 'J8')
        _PrintTokens(lex)

        lex = j8.LexerDecoder(
            r'''
        [
          1e9, 1e-9, -1e9, -1E-9, 42
        ]
        ''', True, 'J8')
        _PrintTokens(lex)

        try:
            lex = j8.LexerDecoder('"\x01"', True, 'J8')
            _PrintTokens(lex)
        except error.Decode as e:
            print(e)
        else:
            self.fail('Expected failure')

        try:
            lex = j8.LexerDecoder('"\x1f"', True, 'J8')
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
            lex = j8.LexerDecoder(s, True, 'J8')
            _PrintTokens(lex)

    def testErrorMessagePosition(self):
        lex = j8.LexerDecoder("[ u'hi']", False, 'J8')
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
