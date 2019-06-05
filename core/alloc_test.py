#!/usr/bin/env python2
"""
alloc_test.py: Tests for alloc.py
"""

import unittest

from _devbuild.gen.syntax_asdl import source
from core import alloc  # module under test


class AllocTest(unittest.TestCase):

  def setUp(self):
    self.arena = alloc.Arena()

  def testArena(self):
    arena = self.arena
    arena.PushSource(source.MainFile('one.oil'))

    line_id = arena.AddLine('line 1', 1)
    self.assertEqual(0, line_id)
    line_id = arena.AddLine('line 2', 2)
    self.assertEqual(1, line_id)

    span_id = arena.AddLineSpan(0, 1, 2)
    self.assertEqual(0, span_id)

    arena.PopSource()

    self.assertEqual('one.oil', arena.GetLineSource(0).path)
    self.assertEqual(1, arena.GetLineNumber(0))

    self.assertEqual('one.oil', arena.GetLineSource(1).path)
    self.assertEqual(2, arena.GetLineNumber(1))

  def testPushSource(self):
    arena = self.arena

    arena.PushSource(source.MainFile('one.oil'))
    arena.AddLine('echo 1a', 1)
    arena.AddLine('source two.oil', 2)

    arena.PushSource(source.MainFile('two.oil'))
    arena.AddLine('echo 2a', 1)
    id2 = arena.AddLine('echo 2b', 2)  # line 2 of two.oil
    arena.PopSource()

    id3 = arena.AddLine('echo 1c', 3)  # line 3 of one.oil
    arena.PopSource()

    self.assertEqual('two.oil', arena.GetLineSource(id2).path)
    self.assertEqual(2, arena.GetLineNumber(id2))

    self.assertEqual('one.oil', arena.GetLineSource(id3).path)
    self.assertEqual(3, arena.GetLineNumber(id3))


if __name__ == '__main__':
  unittest.main()
