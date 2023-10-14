#!/usr/bin/env python2
"""
reader_test.py: Tests for reader.py
"""

import cStringIO
import unittest

from _devbuild.gen.syntax_asdl import source, SourceLine
from core import alloc
from core import test_lib
from frontend import reader  # module under test


class ReaderTest(unittest.TestCase):

    def testStringLineReader(self):
        arena = test_lib.MakeArena('<reader_test.py>')

        r = reader.StringLineReader('one\ntwo', arena)

        src_line, offset = r.GetLine()
        self.assertEqual('one\n', src_line.content),
        self.assertEqual(1, src_line.line_num)
        self.assertEqual(0, offset)

        src_line, offset = r.GetLine()
        self.assertEqual('two', src_line.content),
        self.assertEqual(2, src_line.line_num)
        self.assertEqual(0, offset)

        src_line, offset = r.GetLine()
        self.assertEqual(None, src_line)
        self.assertEqual(0, offset)

    def testLineReadersAreEquivalent(self):
        a1 = alloc.Arena()
        r1 = reader.StringLineReader('one\ntwo', a1)

        a2 = alloc.Arena()
        f = cStringIO.StringIO('one\ntwo')
        r2 = reader.FileLineReader(f, a2)

        a3 = alloc.Arena()

        line1 = SourceLine(1, 'one\n', None)
        line2 = SourceLine(2, 'two', None)

        lines = [(line1, 0), (line2, 0)]
        r3 = reader.VirtualLineReader(lines, a3)

        for a in [a1, a2, a3]:
            a.PushSource(source.MainFile('reader_test.py'))

        for r in [r1, r2, r3]:
            print(r)

            src_line, offset = r.GetLine()
            self.assertEqual('one\n', src_line.content),
            self.assertEqual(1, src_line.line_num)
            self.assertEqual(0, offset)

            src_line, offset = r.GetLine()
            self.assertEqual('two', src_line.content),
            self.assertEqual(2, src_line.line_num)
            self.assertEqual(0, offset)

            src_line, offset = r.GetLine()
            self.assertEqual(None, src_line)
            self.assertEqual(0, offset)


if __name__ == '__main__':
    unittest.main()
