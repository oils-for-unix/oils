#!/usr/bin/env python2
"""
reader_test.py: Tests for reader.py
"""

import cStringIO
import unittest

from _devbuild.gen.syntax_asdl import source
from core import alloc
from core import test_lib
from frontend import reader  # module under test


class ReaderTest(unittest.TestCase):

  def testStringLineReader(self):
    arena = test_lib.MakeArena('<reader_test.py>')

    r = reader.StringLineReader('one\ntwo', arena)
    self.assertEqual((0, 'one\n', 0), r.GetLine())
    self.assertEqual((1, 'two', 0), r.GetLine())
    self.assertEqual((-1, None, 0), r.GetLine())

  def testLineReadersAreEquivalent(self):
    a1 = alloc.Arena()
    r1 = reader.StringLineReader('one\ntwo', a1)

    a2 = alloc.Arena()
    f = cStringIO.StringIO('one\ntwo')
    r2 = reader.FileLineReader(f, a2)

    a3 = alloc.Arena()
    lines = [(0, 'one\n', 0), (1, 'two', 0)]
    r3 = reader.VirtualLineReader(lines, a3)

    for a in [a1, a2, a3]:
      a.PushSource(source.MainFile('reader_test.py'))

    for r in [r1, r2, r3]:
      print(r)
      # Lines are added to the arena with a line_id.
      self.assertEqual((0, 'one\n', 0), r.GetLine())
      self.assertEqual((1, 'two', 0), r.GetLine())
      self.assertEqual((-1, None, 0), r.GetLine())


if __name__ == '__main__':
  unittest.main()
