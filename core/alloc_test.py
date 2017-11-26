#!/usr/bin/env python
"""
alloc_test.py: Tests for alloc.py
"""

import unittest

import alloc  # module under test


class AllocTest(unittest.TestCase):

  def setUp(self):
    p = alloc.Pool()
    self.arena = p.NewArena()

  def testPool(self):
    arena = self.arena
    arena.PushSource('one.oil')

    line_id = arena.AddLine('line 1', 1)
    self.assertEqual(0, line_id)
    line_id = arena.AddLine('line 2', 2)
    self.assertEqual(1, line_id)

    span_id = arena.AddLineSpan(None)
    self.assertEqual(1, span_id)

    arena.PopSource()

    self.assertEqual(('one.oil', 1), arena.GetDebugInfo(0))
    self.assertEqual(('one.oil', 2), arena.GetDebugInfo(1))

  def testPushSource(self):
    arena = self.arena

    arena.PushSource('one.oil')
    arena.AddLine('echo 1a', 1)
    arena.AddLine('source two.oil', 2)

    arena.PushSource('two.oil')
    arena.AddLine('echo 2a', 1)
    id2 = arena.AddLine('echo 2b', 2)  # line 2 of two.oil
    arena.PopSource()

    id3 = arena.AddLine('echo 1c', 3)  # line 3 of one.oil
    arena.PopSource()

    # TODO: fix these assertions
    self.assertEqual(('two.oil', 2), arena.GetDebugInfo(id2))
    self.assertEqual(('one.oil', 3), arena.GetDebugInfo(id3))


if __name__ == '__main__':
  unittest.main()
