#!/usr/bin/env python2
# coding=utf8

import os
import unittest

from _devbuild.gen.value_asdl import value, value_t
from core import ansi
from data_lang import j8
from data_lang import pretty  # module under test
from mycpp import mylib, mops
from typing import Optional

import libc

TEST_DATA_FILENAME = os.path.join(os.path.dirname(__file__), "pretty_test.txt")


def IntValue(i):
    # type: (int) -> value_t
    return value.Int(mops.IntWiden(i))


class PrettyTest(unittest.TestCase):

    def setUp(self):
        # Use settings that make testing easier.
        self.printer = pretty.PrettyPrinter()
        self.printer.SetUseStyles(False)
        self.printer.SetYshStyle()

    def assertPretty(self, width, value_str, expected, lineno=None):
        # type: (int, str, str, Optional[int]) -> None
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
            if lineno is not None:
                print("ON LINE " + str(lineno + 1))
        self.assertEqual(buf.getvalue(), expected)

    def testsFromFile(self):
        # TODO: convert tests to this new style
        self.printer.SetShowTypePrefix(False)
        self.printer.ysh_style = False

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
        self.printer.SetUseStyles(True)
        self.assertPretty(
            20, '[null, "ok", 15]', '(List)\n[' + ansi.BOLD + ansi.RED + 'null' +
            ansi.RESET + ", " + ansi.GREEN + "'ok'" + ansi.RESET + ", " +
            ansi.YELLOW + '15' + ansi.RESET + ']')

    def testTypePrefix(self):
        self.assertPretty(25, '[null, "ok", 15]', "(List)   [null, 'ok', 15]")
        self.assertPretty(24, '[null, "ok", 15]', "(List)\n[null, 'ok', 15]")


if __name__ == '__main__':
    # To simulate the OVM_MAIN patch in pythonrun.c
    libc.cpython_reset_locale()
    unittest.main()
