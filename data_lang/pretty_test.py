#!/usr/bin/env python2
# coding=utf8

import unittest
import libc
# module under test
from data_lang.pretty import (PrettyPrinter, NULL_STYLE, NUMBER_STYLE)

from data_lang import j8
from _devbuild.gen.value_asdl import value, value_t
from mycpp import mylib, mops
from core import ansi

def IntValue(i):
    # type: (int) -> value_t
    return value.Int(mops.IntWiden(i))

class PrettyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.printer = PrettyPrinter()
        cls.printer.SetIndent(2)
        cls.printer.SetUseStyles(False)
        cls.printer.SetShowTypePrefix(False)

    def assertPretty(self, width, value_str, expected):
        # type: (int, str, str) -> None
        parser = j8.Parser(value_str, True)
        val = parser.ParseValue()
        buf = mylib.BufWriter()
        self.printer.SetMaxWidth(width)
        self.printer.PrintValue(val, buf)
        actual = buf.getvalue()
        if actual != expected:
            # Print the different with real newlines, for easier reading.
            print("ACTUAL:")
            print(actual)
            print("EXPECTED:")
            print(expected)
            print("END")
        self.assertEqual(buf.getvalue(), expected)

    def testNull(self):
        self.assertPretty(10, "null", "null")

    def testBool(self):
        self.assertPretty(10, "true", "true")
        self.assertPretty(10, "false", "false")

    def testInt(self):
        self.assertPretty(10, "0", "0")
        self.assertPretty(10, "-123", "-123")
        self.assertPretty(10,
            "123456789123456789123456789",
            "123456789123456789123456789")

    def testFloat(self):
        self.assertPretty(10, "  0.0  ", "0.0")
        self.assertPretty(10, "1.0", "1.0")
        self.assertPretty(10, "-0.000", "-0.0")
        self.assertPretty(10, "2.99792458e8", "299792458.0")

    def testString(self):
        self.assertPretty(10, ' "hello"', '"hello"')
        self.assertPretty(10,
            '"\\"For the `n`\'th time,\\" she said."',
            '"\\"For the `n`\'th time,\\" she said."')

    def testStyles(self):
        self.printer.SetUseStyles(True)
        self.assertPretty(
            20,
            '[null, "ok", 15]',
            '[' + NULL_STYLE + 'null' + ansi.RESET + ', "ok", '
                + NUMBER_STYLE + '15' + ansi.RESET + ']')
        self.printer.SetUseStyles(False)

    def testWideChars(self):
        self.assertPretty(
            16,
            u'["世界", "您好"]'.encode('utf-8'),
            u'["世界", "您好"]'.encode('utf-8')
        )
        self.assertPretty(
            15,
            u'["世界", "您好"]'.encode('utf-8'),
            '\n'.join([
                u'[',
                u'  "世界",',
                u'  "您好"',
                u']'
            ]).encode('utf-8')
        )

    def testTypePrefix(self):
        self.printer.SetShowTypePrefix(True)
        self.assertPretty(
            25,
            '[null, "ok", 15]',
            '(List)   [null, "ok", 15]')
        self.assertPretty(
            24,
            '[null, "ok", 15]',
            '(List)\n[null, "ok", 15]')
        self.printer.SetShowTypePrefix(False)

    def testList(self):
        self.assertPretty(20, "[]", "[]")
        self.assertPretty(
            20,
            "[100, 200, 300]",
            "[100, 200, 300]")
        self.assertPretty(
            10,
            "[100, 200, 300]",
            "\n".join([
                "[",
                "  100,",
                "  200,",
                "  300",
                "]"
            ]))
        self.assertPretty(
            20,
            "[[100, 200, 300], [100, 200, 300]]",
            "\n".join([
                "[",
                "  [100, 200, 300],",
                "  [100, 200, 300]",
                "]"
            ]))
        self.assertPretty(
            19,
            "[[100, 200, 300], [100, 200, 300]]",
            "\n".join([
                "[",
                "  [100, 200, 300],",
                "  [100, 200, 300]",
                "]"
            ]))

    def testDict(self):
        self.assertPretty(24, "{}", "{}")
        self.assertPretty(
            24,
            '{"x":100, "y":200, "z":300}',
            '{x: 100, y: 200, z: 300}')
        self.assertPretty(
            23,
            '{"x":100, "y":200, "z":300}',
            "\n".join([
                '{',
                '  x: 100,',
                '  y: 200,',
                '  z: 300',
                '}'
            ]))
        self.assertPretty(
            49,
            '''{
                "letters": {"1": "A", "2": "B", "3": "C"},
                "numbers": {"1": "one", "2": "two", "3": "three"}
            }''',
            "\n".join([
                '{',
                '  letters: {"1": "A", "2": "B", "3": "C"},',
                '  numbers: {"1": "one", "2": "two", "3": "three"}',
                '}'
            ]))
        self.assertPretty(
            42,
            '''{
                "letters": {"1": "A", "2": "B", "3": "C"},
                "numbers": {"1": "one", "2": "two", "3": "three"}
            }''',
            "\n".join([
                '{',
                '  letters: {"1": "A", "2": "B", "3": "C"},',
                '  numbers: {',
                '    "1": "one",',
                '    "2": "two",',
                '    "3": "three"',
                '  }',
                '}'
            ]))
        self.assertPretty(
            41,
            '''{
                "letters": {"1": "A", "2": "B", "3": "C"},
                "numbers": {"1": "one", "2": "two", "3": "three"}
            }''',
            "\n".join([
                '{',
                '  letters: {',
                '    "1": "A",',
                '    "2": "B",',
                '    "3": "C"',
                '  },',
                '  numbers: {',
                '    "1": "one",',
                '    "2": "two",',
                '    "3": "three"',
                '  }',
                '}'
            ]))

    def testEverythingAtOnce(self):
        everything = u"""{
            'primitives': {
                'simple_primitives': [null, false, true],
                'numeric_primitives': [-123456789, 123.456789],
                'stringy_primitives': 'string'
            },
            'compounds': [
                [1, 2, 3],
                {'dict': 'ionary'}
            ],
            'variety-pack': [
                null,
                ['Los', 'pollitos', 'dicen', 'pío', 'pío', 'pío'],
                [1, [2, [3, [4, [5, [6]]]]]],
                [[[[[5], 4], 3], 2], 1]
            ]
        }""".encode('utf-8')
        self.assertPretty(54, everything,
            "\n".join([
                '{',
                '  primitives: {',
                '    simple_primitives: [null, false, true],',
                '    numeric_primitives: [-123456789, 123.456789],',
                '    stringy_primitives: "string"',
                '  },',
                '  compounds: [[1, 2, 3], {dict: "ionary"}],',
                '  "variety-pack": [',
                '    null,',
                '    ["Los", "pollitos", "dicen", "pío", "pío", "pío"],',
                '    [1, [2, [3, [4, [5, [6]]]]]],',
                '    [[[[[5], 4], 3], 2], 1]',
                '  ]',
                '}'
            ]))
        self.assertPretty(49, everything,
            "\n".join([
                '{',
                '  primitives: {',
                '    simple_primitives: [null, false, true],',
                '    numeric_primitives: [-123456789, 123.456789],',
                '    stringy_primitives: "string"',
                '  },',
                '  compounds: [[1, 2, 3], {dict: "ionary"}],',
                '  "variety-pack": [',
                '    null,',
                '    [',
                '      "Los",',
                '      "pollitos",',
                '      "dicen",',
                '      "pío",',
                '      "pío",',
                '      "pío"',
                '    ],',
                '    [1, [2, [3, [4, [5, [6]]]]]],',
                '    [[[[[5], 4], 3], 2], 1]',
                '  ]',
                '}'
            ]))
        self.assertPretty(43, everything,
            "\n".join([
                '{',
                '  primitives: {',
                '    simple_primitives: [null, false, true],',
                '    numeric_primitives: [',
                '      -123456789,',
                '      123.456789',
                '    ],',
                '    stringy_primitives: "string"',
                '  },',
                '  compounds: [[1, 2, 3], {dict: "ionary"}],',
                '  "variety-pack": [',
                '    null,',
                '    [',
                '      "Los",',
                '      "pollitos",',
                '      "dicen",',
                '      "pío",',
                '      "pío",',
                '      "pío"',
                '    ],',
                '    [1, [2, [3, [4, [5, [6]]]]]],',
                '    [[[[[5], 4], 3], 2], 1]',
                '  ]',
                '}'
            ]))
        self.assertPretty(33, everything,
            "\n".join([
                '{',
                '  primitives: {',
                '    simple_primitives: [',
                '      null,',
                '      false,',
                '      true',
                '    ],',
                '    numeric_primitives: [',
                '      -123456789,',
                '      123.456789',
                '    ],',
                '    stringy_primitives: "string"',
                '  },',
                '  compounds: [',
                '    [1, 2, 3],',
                '    {dict: "ionary"}',
                '  ],',
                '  "variety-pack": [',
                '    null,',
                '    [',
                '      "Los",',
                '      "pollitos",',
                '      "dicen",',
                '      "pío",',
                '      "pío",',
                '      "pío"',
                '    ],',
                '    [1, [2, [3, [4, [5, [6]]]]]],',
                '    [[[[[5], 4], 3], 2], 1]',
                '  ]',
                '}'
            ]))
        self.assertPretty(32, everything,
            "\n".join([
                '{',
                '  primitives: {',
                '    simple_primitives: [',
                '      null,',
                '      false,',
                '      true',
                '    ],',
                '    numeric_primitives: [',
                '      -123456789,',
                '      123.456789',
                '    ],',
                '    stringy_primitives: "string"',
                '  },',
                '  compounds: [',
                '    [1, 2, 3],',
                '    {dict: "ionary"}',
                '  ],',
                '  "variety-pack": [',
                '    null,',
                '    [',
                '      "Los",',
                '      "pollitos",',
                '      "dicen",',
                '      "pío",',
                '      "pío",',
                '      "pío"',
                '    ],',
                '    [',
                '      1,',
                '      [2, [3, [4, [5, [6]]]]]',
                '    ],',
                '    [[[[[5], 4], 3], 2], 1]',
                '  ]',
                '}'
            ]))
        self.assertPretty(26, everything,
            "\n".join([
                '{',
                '  primitives: {',
                '    simple_primitives: [',
                '      null,',
                '      false,',
                '      true',
                '    ],',
                '    numeric_primitives: [',
                '      -123456789,',
                '      123.456789',
                '    ],',
                '    stringy_primitives: "string"',
                '  },',
                '  compounds: [',
                '    [1, 2, 3],',
                '    {dict: "ionary"}',
                '  ],',
                '  "variety-pack": [',
                '    null,',
                '    [',
                '      "Los",',
                '      "pollitos",',
                '      "dicen",',
                '      "pío",',
                '      "pío",',
                '      "pío"',
                '    ],',
                '    [',
                '      1,',
                '      [',
                '        2,',
                '        [3, [4, [5, [6]]]]',
                '      ]',
                '    ],',
                '    [',
                '      [[[[5], 4], 3], 2],',
                '      1',
                '    ]',
                '  ]',
                '}'
            ]))


if __name__ == '__main__':
    # To simulate the OVM_MAIN patch in pythonrun.c
    libc.cpython_reset_locale()
    unittest.main()
