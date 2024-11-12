#!/usr/bin/env python2
"""alloc_test.py: Tests for alloc.py."""

import unittest

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import source
from core import alloc  # module under test


class AllocTest(unittest.TestCase):

    def setUp(self):
        self.arena = alloc.Arena()

    def testArena(self):
        arena = self.arena
        arena.SaveTokens()
        arena.PushSource(source.MainFile('one.ysh'))

        line = arena.AddLine('line 1', 1)
        self.assertEqual(1, line.line_num)
        line = arena.AddLine('line 2', 2)
        self.assertEqual(2, line.line_num)

        tok = arena.NewToken(Id.Undefined_Tok, -1, -1, -1)
        self.assertEqual(0, arena.GetSpanId(tok))

        arena.PopSource()

    def testPushSource(self):
        arena = self.arena

        arena.PushSource(source.MainFile('one.ysh'))
        arena.AddLine('echo 1a', 1)
        arena.AddLine('source two.ysh', 2)

        arena.PushSource(source.MainFile('two.ysh'))
        arena.AddLine('echo 2a', 1)
        line2 = arena.AddLine('echo 2b', 2)  # line 2 of two.ysh
        arena.PopSource()

        line3 = arena.AddLine('echo 1c', 3)  # line 3 of one.ysh
        arena.PopSource()

        self.assertEqual('two.ysh', line2.src.path)
        self.assertEqual(2, line2.line_num)

        self.assertEqual('one.ysh', line3.src.path)
        self.assertEqual(3, line3.line_num)


if __name__ == '__main__':
    unittest.main()
