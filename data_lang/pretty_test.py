#!/usr/bin/env python2

import unittest
from data_lang import pretty  # module under test

from _devbuild.gen.value_asdl import value, value_t
from mycpp import mylib, mops

class PrettyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.printer = pretty.PrettyPrinter()
        cls.printer.Init_MaxWidth(10) # small width for testing

    def assertPretty(self, val, expected):
        # type: (value_t, String) -> None
        buf = mylib.BufWriter()
        self.printer.PrintValue(val, buf)
        self.assertEqual(buf.getvalue(), expected)

    def testNull(self):
        self.assertPretty(value.Null, "null")

    def testBool(self):
        self.assertPretty(value.Bool(True), "true")
        self.assertPretty(value.Bool(False), "false")

    def testInt(self):
        self.assertPretty(value.Int(mops.IntWiden(0)), "0")
        self.assertPretty(value.Int(mops.IntWiden(-123)), "-123")
        self.assertPretty(
            value.Int(mops.IntWiden(123456789123456789123456789)),
            "123456789123456789123456789"
        )

    def testFloat(self):
        self.assertPretty(value.Float(0.), "0.0")
        self.assertPretty(value.Float(-0.0), "-0.0")
        self.assertPretty(value.Float(2.99792458e8), "299792458.0")

    def testFloat(self):
        self.assertPretty(value.Str('hello'), '"hello"')
        self.assertPretty(
            value.Str('"For the `n`\'th time," she said.'),
            '"\\"For the `n`\'th time,\\" she said."')

if __name__ == '__main__':
    unittest.main()
