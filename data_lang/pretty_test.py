#!/usr/bin/env python2
# coding=utf8

import unittest
import libc
import os
# module under test
from data_lang.pretty import (PrettyPrinter, NULL_STYLE, NUMBER_STYLE)

from data_lang import j8
from _devbuild.gen.value_asdl import value, value_t
from mycpp import mylib, mops
from core import ansi

TEST_DATA_FILENAME = os.path.join(os.path.dirname(__file__), "pretty_test.txt")


def IntValue(i):
    # type: (int) -> value_t
    return value.Int(mops.IntWiden(i))


class PrettyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Use settings that make testing easier.
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

    def testsFromFile(self):
        chunks = [(None, [])]
        for line in open(TEST_DATA_FILENAME).read().splitlines():
            if line.startswith("> "):
                chunks[-1][1].append(line[2:])
            elif line.startswith("#"):
                pass
            elif line.strip() == "":
                pass
            else:
                for keyword in ["Width", "Input", "Expect"]:
                    if line.startswith(keyword):
                        if chunks[-1][0] != keyword:
                            chunks.append((keyword, []))
                        parts = line.split(" > ", 1)
                        if len(parts) == 2:
                            chunks[-1][1].append(parts[1])
                        break
                else:
                    raise Exception(
                        "Invalid pretty printing test case line. Lines must start with one of: Width, Input, Expect, >, #",
                        line)

        test_cases = []
        width = 80
        value = ""
        for (keyword, lines) in chunks:
            block = "\n".join(lines)
            if keyword == "Width":
                width = int(block)
            elif keyword == "Input":
                value = block
            elif keyword == "Expect":
                test_cases.append((width, value, block))
            else:
                pass

        for (width, value, expected) in test_cases:
            self.assertPretty(width, value, expected)

    def testStyles(self):
        self.printer.SetUseStyles(True)
        self.assertPretty(
            20, '[null, "ok", 15]', '[' + NULL_STYLE + 'null' + ansi.RESET +
            ', "ok", ' + NUMBER_STYLE + '15' + ansi.RESET + ']')
        self.printer.SetUseStyles(False)

    def testTypePrefix(self):
        self.printer.SetShowTypePrefix(True)
        self.assertPretty(25, '[null, "ok", 15]', '(List)   [null, "ok", 15]')
        self.assertPretty(24, '[null, "ok", 15]', '(List)\n[null, "ok", 15]')
        self.printer.SetShowTypePrefix(False)


if __name__ == '__main__':
    # To simulate the OVM_MAIN patch in pythonrun.c
    libc.cpython_reset_locale()
    unittest.main()
