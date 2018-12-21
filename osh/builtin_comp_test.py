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


class BuiltinCompTest(unittest.TestCase):

  def testInitCompletion(self):
    arena = alloc.SideArena('<MakeTestEvaluator>')
    mem = state.Mem('', [], {}, arena)

    print(CASES)
    argv = []

    # TODO: Look at variables

    builtin_comp.InitCompletion(['-s'], mem)

    print(mem.GetVar('words'))
    print(mem.GetVar('cur'))
    print(mem.GetVar('prev'))
    print(mem.GetVar('cword'))
    print(mem.GetVar('split'))


if __name__ == '__main__':
  unittest.main()
