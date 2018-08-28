#!/usr/bin/python -S
"""
reader_test.py: Tests for reader.py
"""

import cStringIO
import unittest

from core import alloc
from core import test_lib
from core import reader  # module under test


class ReaderTest(unittest.TestCase):

  def setUp(self):
    self.pool = alloc.Pool()
    #self.arena = pool.NewArena()

  def testStringLineReader(self):
    arena = test_lib.MakeArena('<reader_test.py>')

    r = reader.StringLineReader('one\ntwo', arena)
    self.assertEqual((0, 'one\n', 0), r.GetLine())
    self.assertEqual((1, 'two', 0), r.GetLine())
    self.assertEqual((-1, None, 0), r.GetLine())

  def testLineReadersAreEquivalent(self):
    a1 = self.pool.NewArena()
    r1 = reader.StringLineReader('one\ntwo', a1)

    a2 = self.pool.NewArena()
    f = cStringIO.StringIO('one\ntwo')
    r2 = reader.FileLineReader(f, a2)

    a3 = self.pool.NewArena()
    lines = [(0, 'one\n', 0), (1, 'two', 0)]
    r3 = reader.HereDocLineReader(lines, a3)

    for a in [a1, a2, a3]:
      a.PushSource('reader_test.py')

    for r in [r1, r2, r3]:
      print(r)
      # Lines are added to the arena with a line_id.
      self.assertEqual((0, 'one\n', 0), r.GetLine())
      self.assertEqual((1, 'two', 0), r.GetLine())
      self.assertEqual((-1, None, 0), r.GetLine())


if __name__ == '__main__':
  unittest.main()
