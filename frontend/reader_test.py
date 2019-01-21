#!/usr/bin/python -S
"""
reader_test.py: Tests for reader.py
"""

import cStringIO
import sys
import unittest

from core import alloc
from core import test_lib
from core import util
from frontend import parse_lib
from frontend import reader  # module under test


class ReaderTest(unittest.TestCase):

  def testStringLineReader(self):
    arena = test_lib.MakeArena('<reader_test.py>')

    r = reader.StringLineReader('one\ntwo', arena)
    self.assertEqual((0, 'one\n', 0), r.GetLine())
    self.assertEqual((1, 'two', 0), r.GetLine())
    self.assertEqual((-1, None, 0), r.GetLine())

  def testLineReadersAreEquivalent(self):
    pool = alloc.Pool()
    a1 = pool.NewArena()
    r1 = reader.StringLineReader('one\ntwo', a1)

    a2 = pool.NewArena()
    f = cStringIO.StringIO('one\ntwo')
    r2 = reader.FileLineReader(f, a2)

    a3 = pool.NewArena()
    lines = [(0, 'one\n', 0), (1, 'two', 0)]
    r3 = reader.VirtualLineReader(lines, a3)

    for a in [a1, a2, a3]:
      a.PushSource('reader_test.py')

    for r in [r1, r2, r3]:
      print(r)
      # Lines are added to the arena with a line_id.
      self.assertEqual((0, 'one\n', 0), r.GetLine())
      self.assertEqual((1, 'two', 0), r.GetLine())
      self.assertEqual((-1, None, 0), r.GetLine())


# TODO: This can be replaced by the real thing!  Call read_history_file

class _MockReadlineHistory(object):
  def __init__(self, items):
    self.items = items

  def get_current_history_length(self):
    return len(self.items)

  def get_history_item(self, one_based_index):
    try:
      return self.items[one_based_index - 1]
    except IndexError:
      return None  # matches what readline does


def _MakeHistoryEvaluator(history_items):
  arena = test_lib.MakeArena('<reader_test.py>')
  trail = parse_lib.Trail()
  parse_ctx = parse_lib.ParseContext(arena, {}, trail=trail)
  debug_f = util.DebugFile(sys.stdout)
  readline = _MockReadlineHistory(history_items)
  return reader.HistoryEvaluator(readline, parse_ctx, debug_f)


class HistoryEvaluatorTest(unittest.TestCase):

  def testInvalidHistoryItems(self):
    hist_ev = _MakeHistoryEvaluator([
      'echo ( a )',
      'CURRENT',
    ])
    # If you can't parse a command, then it is
    self.assertRaises(util.HistoryError, hist_ev.Eval, 'echo !$')

  def testReplacements(self):
    hist_ev = _MakeHistoryEvaluator([
      'echo 1',
      'echo ${two:-}',
      'ls /echo/',
      'CURRENT',
    ])

    self.assertEqual('echo hi', hist_ev.Eval('echo hi'))

    # Search for prefix
    self.assertEqual('echo ${two:-}', hist_ev.Eval('!echo'))
    # Search for substring
    self.assertEqual('echo ${two:-}', hist_ev.Eval('!?two'))

    # Indexes and negative indexes
    self.assertEqual('echo 1', hist_ev.Eval('!1'))
    self.assertEqual('ls /echo/', hist_ev.Eval('!-1'))
    self.assertEqual('echo ${two:-}', hist_ev.Eval('!-2'))

    self.assertRaises(util.HistoryError, hist_ev.Eval, 'echo !-999')
    self.assertRaises(util.HistoryError, hist_ev.Eval, '!999')

    self.assertEqual('ls /echo/', hist_ev.Eval('!!'))

    self.assertEqual('echo /echo/', hist_ev.Eval('echo !$'))

  def testBug(self):
    hist_ev = _MakeHistoryEvaluator([
      'echo ${two:-}',
    ])
    self.assertEqual('echo ${two:-}', hist_ev.Eval('echo !$'))

  def testParsing(self):
    hist_ev = _MakeHistoryEvaluator([
      'echo 1',
      'echo $three ${4:-} "${five@P}"',
      'CURRENT',
    ])
    self.assertEqual('echo "${five@P}"', hist_ev.Eval('echo !$'))
    self.assertEqual('echo $three', hist_ev.Eval('echo !^'))
    self.assertEqual(
        'echo -n $three ${4:-} "${five@P}"', hist_ev.Eval('echo -n !*'))

  def testNonCommands(self):
    hist_ev = _MakeHistoryEvaluator([
      'echo hi | wc -l',
      'CURRENT',
    ])
    self.assertEqual('echo -l', hist_ev.Eval('echo !$'))

    hist_ev = _MakeHistoryEvaluator([
      'for i in 1 2 3; do echo xx; done',
      'CURRENT',
    ])
    self.assertEqual('echo xx', hist_ev.Eval('echo !$'))

    hist_ev = _MakeHistoryEvaluator([
      '{ echo yy; }',
      'CURRENT',
    ])
    self.assertEqual('echo yy', hist_ev.Eval('echo !$'))


if __name__ == '__main__':
  unittest.main()
