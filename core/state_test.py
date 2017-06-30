#!/usr/bin/python -S
"""
state_test.py: Tests for state.py
"""

import unittest

from core import state  # module under test


class MemTest(unittest.TestCase):

  def testGet(self):
    mem = state.Mem('', [], {})
    mem.Push(['a', 'b'])
    print(mem.Get('HOME'))
    mem.Pop()
    print(mem.Get('NONEXISTENT'))

  def testArgv(self):
    mem = state.Mem('', [], {})
    mem.Push(['a', 'b'])
    self.assertEqual(['a', 'b'], mem.GetArgv())

    mem.Push(['x', 'y'])
    self.assertEqual(['x', 'y'], mem.GetArgv())

    status = mem.Shift(1)
    self.assertEqual(['y'], mem.GetArgv())
    self.assertEqual(0, status)

    status = mem.Shift(1)
    self.assertEqual([], mem.GetArgv())
    self.assertEqual(0, status)

    status = mem.Shift(1)
    self.assertEqual([], mem.GetArgv())
    self.assertEqual(1, status)  # error

    mem.Pop()
    self.assertEqual(['a', 'b'], mem.GetArgv())

  def testArgv2(self):
    mem = state.Mem('', ['x', 'y'], {})

    mem.Shift(1)
    self.assertEqual(['y'], mem.GetArgv())

    mem.SetArgv(['i', 'j', 'k'])
    self.assertEqual(['i', 'j', 'k'], mem.GetArgv())


if __name__ == '__main__':
  unittest.main()
