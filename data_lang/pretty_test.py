#!/usr/bin/env python2
# coding=utf8

import os
import unittest

from core import ansi
from core import ui
from data_lang import j8
from data_lang import pretty  # module under test
from mycpp import mylib
from typing import Optional

import libc

TEST_DATA_FILENAME = os.path.join(os.path.dirname(__file__), "pretty_test.txt")


def _PrintCase(actual, expected, lineno=None):
    if actual != expected:
        # Print the different with real newlines, for easier reading.
        print("ACTUAL:")
        print(actual)
        print("EXPECTED:")
        print(expected)
        print("END")
        if lineno is not None:
            print("ON LINE " + str(lineno + 1))


class UiTest(unittest.TestCase):
    """Test higher level ui.PrettyPrintValue()."""

    def assertPretty(self, width, value_str, expected):
        # type: (int, str, str, Optional[int]) -> None
        parser = j8.Parser(value_str, True)
        val = parser.ParseValue()

        buf = mylib.BufWriter()
        ui.PrettyPrintValue(val, buf, max_width=width)

        actual = buf.getvalue()
        _PrintCase(actual, expected)
        self.assertEqual(actual, expected)

    def testTypePrefix(self):
        self.assertPretty(25, '[null, "ok", 15]',
                          "(List)   [null, 'ok', 15]\n")
        self.assertPretty(24, '[null, "ok", 15]', "(List)\n[null, 'ok', 15]\n")


class PrettyTest(unittest.TestCase):

    def setUp(self):
        # Use settings that make testing easier.
        self.encoder = pretty.ValueEncoder()
        self.encoder.SetUseStyles(False)

    def assertPretty(self, width, value_str, expected, lineno=None):
        # type: (int, str, str, Optional[int]) -> None
        parser = j8.Parser(value_str, True)
        val = parser.ParseValue()

        buf = mylib.BufWriter()

        doc = self.encoder.Value(val)

        printer = pretty.PrettyPrinter(width)
        printer.PrintDoc(doc, buf)

        actual = buf.getvalue()
        _PrintCase(actual, expected, lineno=lineno)
        self.assertEqual(actual, expected)

    def testsFromFile(self):
        # TODO: convert tests to this new style
        self.encoder.ysh_style = False

        chunks = [(None, -1, [])]
        for lineno, line in enumerate(
                open(TEST_DATA_FILENAME).read().splitlines()):
            if line.startswith("> "):
                chunks[-1][2].append(line[2:])
            elif line.startswith("#"):
                pass
            elif line.strip() == "":
                pass
            else:
                for keyword in ["Width", "Input", "Expect"]:
                    if line.startswith(keyword):
                        if chunks[-1][0] != keyword:
                            chunks.append((keyword, lineno, []))
                        parts = line.split(" > ", 1)
                        if len(parts) == 2:
                            chunks[-1][2].append(parts[1])
                        break
                else:
                    raise Exception(
                        "Invalid pretty printing test case line. Lines must start with one of: Width, Input, Expect, >, #",
                        line)

        test_cases = []
        width = 80
        value = ""
        for (keyword, lineno, lines) in chunks:
            block = "\n".join(lines)
            if keyword == "Width":
                width = int(block)
            elif keyword == "Input":
                value = block
            elif keyword == "Expect":
                test_cases.append((width, value, block, lineno))
            else:
                pass

        for (width, value, expected, lineno) in test_cases:
            self.assertPretty(width, value, expected, lineno)

    def testStyles(self):
        self.encoder.SetUseStyles(True)
        self.assertPretty(
            20, '[null, "ok", 15]',
            '[' + ansi.RED + 'null' + ansi.RESET + ", " + ansi.GREEN + "'ok'" +
            ansi.RESET + ", " + ansi.YELLOW + '15' + ansi.RESET + ']')


if __name__ == '__main__':
    # To simulate the OVM_MAIN patch in pythonrun.c
    libc.cpython_reset_locale()
    unittest.main()
