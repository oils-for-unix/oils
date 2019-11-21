#!/usr/bin/env python2
"""
history_test.py: Tests for history.py
"""
from __future__ import print_function

import unittest
import sys

from core import test_lib
from core import util
from osh import history  # module under test
from frontend import parse_lib

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
  parse_opts = parse_lib.OilParseOptions()
  parse_ctx = parse_lib.ParseContext(arena, parse_opts, {}, None)
  parse_ctx.Init_Trail(parse_lib.Trail())

  debug_f = util.DebugFile(sys.stdout)
  readline = _MockReadlineHistory(history_items)
  return history.Evaluator(readline, parse_ctx, debug_f)


class HistoryEvaluatorTest(unittest.TestCase):

  def testInvalidHistoryItems(self):
    hist_ev = _MakeHistoryEvaluator([
      'echo ( a )',
    ])
    # If you can't parse a command, then it's an error
    self.assertRaises(util.HistoryError, hist_ev.Eval, 'echo !$')

  def testReplacements(self):
    hist_ev = _MakeHistoryEvaluator([
      'echo 1',
      'echo ${two:-}',
      'ls /echo/',
    ])

    self.assertEqual('echo hi', hist_ev.Eval('echo hi'))

    # Search for prefix
    self.assertEqual('echo ${two:-}\n', hist_ev.Eval('!echo\n'))
    # Search for substring
    self.assertEqual('echo ${two:-} ', hist_ev.Eval('!?two '))

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

    # Commented out
    self.assertEqual('echo hi  # !$', hist_ev.Eval('echo hi  # !$'))

    # This is not technically a comment, but it's hard to re-lex.
    self.assertEqual('echo hi#!$', hist_ev.Eval('echo hi#!$'))

    # Workaround: the comment char can be single-quoted.
    self.assertEqual("echo 'hi#'${two:-}", hist_ev.Eval("echo 'hi#'!$"))

  def testParsing(self):
    hist_ev = _MakeHistoryEvaluator([
      'echo 1',
      'echo $three ${4:-} "${five@P}"',
    ])
    self.assertEqual('echo "${five@P}"', hist_ev.Eval('echo !$'))
    self.assertEqual('echo $three', hist_ev.Eval('echo !^'))
    self.assertEqual(
        'echo -n $three ${4:-} "${five@P}"', hist_ev.Eval('echo -n !*'))

  def testNonCommands(self):
    hist_ev = _MakeHistoryEvaluator([
      'echo hi | wc -l',
    ])
    self.assertEqual('echo -l', hist_ev.Eval('echo !$'))

    hist_ev = _MakeHistoryEvaluator([
      'for i in 1 2 3; do echo xx; done',
    ])
    self.assertEqual('echo xx', hist_ev.Eval('echo !$'))

    hist_ev = _MakeHistoryEvaluator([
      '{ echo yy; }',
    ])
    self.assertEqual('echo yy', hist_ev.Eval('echo !$'))


if __name__ == '__main__':
  unittest.main()
