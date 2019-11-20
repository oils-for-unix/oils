#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
arith_parse_test.py: Tests for arith_parse.py
"""

import unittest

from _devbuild.gen.types_asdl import lex_mode_e
from core import error
from core import test_lib
from frontend import parse_lib
from osh import cmd_exec
from osh import expr_eval
from osh import split
from osh import word_eval
from osh import state

#from osh import arith_parse


def ParseAndEval(code_str):
  arena = test_lib.MakeArena('<arith_parse_test.py>')
  w_parser = test_lib.InitWordParser(code_str, arena=arena)
  w_parser._Next(lex_mode_e.Arith)  # Calling private method
  anode = w_parser._ReadArithExpr()  # need the right lex state?
  print('node:', anode)

  mem = state.Mem('', [], {}, arena)
  parse_opts = parse_lib.OilParseOptions()
  exec_opts = state.ExecOpts(mem, parse_opts, None)

  exec_deps = cmd_exec.Deps()
  splitter = split.SplitContext(mem)
  exec_deps.splitter = splitter

  ev = word_eval.CompletionWordEvaluator(mem, exec_opts, exec_deps, arena)

  arith_ev = expr_eval.ArithEvaluator(mem, exec_opts, ev, arena)
  value = arith_ev.Eval(anode)
  return value


def testEvalExpr(e, expected):
  print('expression:', e)
  actual = ParseAndEval(e)
  if actual != expected:
    raise AssertionError('%s => %r, expected %r' % (e, actual, expected))


def testSyntaxError(ex):
  try:
    actual = ParseAndEval(ex)
  except error.Parse as e:
    print(ex, '\t\t', e)
  else:
    raise AssertionError('Expected parse error: %r, got %r' % (ex, actual))


class ArithTest(unittest.TestCase):

  def testEval(self):
    testEvalExpr('(7)', 7)

    # Doesn't matter if you eval 2-3 first here
    testEvalExpr('1 + 2 - 3', 0)

    testEvalExpr('1 + 2 * 3', 7)

    testEvalExpr('7 - 9 * (2 - 3)', 16)
    testEvalExpr('2 * 3 * 4', 24)

    testEvalExpr('2 ** 3 ** 4', 2 ** (3 ** 4))

    testEvalExpr('(2 ** 3) ** 4', 4096)

    testEvalExpr('5', 5)
    testEvalExpr('4 + 2', 6)
    testEvalExpr('9 - 8 - 7', -6)
    testEvalExpr('9 - (8 - 7)', 8)
    testEvalExpr('(9 - 8) - 7', -6)
    testEvalExpr('2 + 3 ** 2 * 3 + 4', 33)

    testEvalExpr('4 * 3 / 2', 6)
    testEvalExpr('3 * 2 % 4', 2)
    testEvalExpr('+ 1', 1)
    testEvalExpr('- 5', -5)
    testEvalExpr('-2-3', -5)

    # Comma has lower precedence
    testEvalExpr('1 ? 2 : 3, 4 ? 5 : 6', 5)

    # Two commas
    testEvalExpr('1 , 2, 3', 3)

    # TODO: fix the rest
    return

    testEvalExpr('0 = 2 > 3', 0)  # => 0 > 3 => 0

    # string becomes integer"
    #testEvalExpr(['ab21xx', ':', '[^0-9]*([0-9]*)', '+', '3'], 24)

    #testEvalExpr(['ab21xx', ':', '[^0-9]*([0-9]*)'], '21')

    #testEvalExpr(['ab21xx', ':', '(.)'], 'a')

    # integer becomes string.  -3 as a string is less than '-3-'
    #testEvalExpr(['2', '-', '5', '<', '-3-'], True)
    #testEvalExpr(['2', '-', '5', '<', '-2-'], False)

    # Arithemetic compare
    testEvalExpr(['-3', '<', '-2'], True)
    # String compare
    #testEvalExpr(['-3', '<', '-2-'], False)

    #testEvalExpr(['3a', ':', '(.)', '=', '1', '+', '2'], True)

    # More stuff:
    # expr / => /  -- it's just a plain string
    # expr / : . => 1
    # expr \( / \) => /   -- this is dumb
    # expr + match => match  -- + is escaping, wtf
    #
    #testEvalExpr(['ab21xx', ':', '[^0-9]*([0-9]*)', '+', '3'], 24)

  def testEvalConstants(self):
    # Octal constant
    testEvalExpr('011', 9)

    # Hex constant
    testEvalExpr('0xA', 10)

    # Arbitrary base constant
    testEvalExpr('64#z', 35)
    testEvalExpr('64#Z', 61)
    testEvalExpr('64#@', 62)
    testEvalExpr('64#_', 63)

  def testErrors(self):
    # Now try some bad ones

    testSyntaxError('')
    testSyntaxError(')')
    testSyntaxError('(')

    # If ( is an error, I think this should be too.
    # For now left it out.  Don't want to look up opinfo.
    #
    # In GNU expr, this is an error because + is escaping char!
    #testSyntaxError('+')
    #testSyntaxError('/')

    testSyntaxError('()')  # Not valid, expr also fails.
    testSyntaxError('( 1')
    testSyntaxError('(1 + (3 * 4)')
    testSyntaxError('(1 + (3 * 4) 5')  # Not valid, expr also fails.

    testSyntaxError(';')
    testSyntaxError('- ;')

    #testSyntaxError('1 1')
    #testSyntaxError('( 1 ) ( 2 )')

    # NOTE: @ implicitly ends it now
    #testSyntaxError('1 @ 2')


if __name__ == '__main__':
  unittest.main()
