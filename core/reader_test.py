#!/usr/bin/python -S
"""
reader_test.py: Tests for reader.py
"""

import cStringIO
import unittest

from core import alloc
from core import reader  # module under test


class ReaderTest(unittest.TestCase):

  def setUp(self):
    self.pool = alloc.Pool()
    #self.arena = pool.NewArena()

  def testStringLineReader(self):
    # No Arena, gives -1
    r = reader.StringLineReader('one\ntwo')
    self.assertEqual((-1, 'one\n'), r.GetLine())
    self.assertEqual((-1, 'two\n'), r.GetLine())
    self.assertEqual((-1, None), r.GetLine())

  def testLineReadersAreEquivalent(self):
    a1 = self.pool.NewArena()
    r1 = reader.StringLineReader('one\ntwo', arena=a1)

    a2 = self.pool.NewArena()
    f = cStringIO.StringIO('one\ntwo')
    r2 = reader.FileLineReader(f, arena=a2)

    a3 = self.pool.NewArena()
    lines = [(0, 'one\n'), (1, 'two\n')]
    r3 = reader.VirtualLineReader(lines, a3)

    for a in [a1, a2, a3]:
      a.PushSource('reader_test.py')

    for r in [r1, r2, r3]: 
      print(r)
      # Lines are added to the arena with a line_id.
      self.assertEqual((0, 'one\n'), r.GetLine())
      self.assertEqual((1, 'two\n'), r.GetLine())
      self.assertEqual((-1, None), r.GetLine())


if __name__ == '__main__':
  unittest.main()
