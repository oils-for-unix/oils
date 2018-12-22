#!/usr/bin/python -S
"""
builtin_comp_test.py: Tests for builtin_comp.py
"""
from __future__ import print_function

import unittest

from core import alloc

from osh import state
from osh import builtin_comp  # module under test

from testdata.init_completion_testdata import CASES  # generated data


# TODO:
# test_lib _MakeRootCompleter
# test_lib.EvalCode
# And then inspect memory values afterward I guess.
#
# Hm but the function will return?
# Maybe you have to look at stdout?
#
# or you could inject EXPECTED_CUR, EXPECTED_PREV, etc.

class BuiltinCompTest(unittest.TestCase):

  def testInitCompletion(self):
    return
    arena = alloc.SideArena('<MakeTestEvaluator>')
    mem = state.Mem('', [], {}, arena)

    print(CASES)
    argv = []

    # TODO: Look at variables

    # Extra arguments
    builtin_comp.InitCompletion(['-s', 'foo', 'bar'], mem)

    print(mem.GetVar('words'))
    print(mem.GetVar('cur'))
    print(mem.GetVar('prev'))
    print(mem.GetVar('cword'))
    print(mem.GetVar('split'))


if __name__ == '__main__':
  unittest.main()
