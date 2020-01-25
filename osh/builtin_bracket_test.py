#!/usr/bin/env python2
"""
builtin_bracket_test.py: Tests for builtin_bracket.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import cmd_value
from osh import builtin_bracket  # module under test


class BracketTest(unittest.TestCase):

  def testStringWordEmitter(self):
    # Test
    argv = '-z X -o -z Y -a -z X'.split()
    arg_vec = cmd_value.Argv(argv, [0] * len(argv))
    e = builtin_bracket._StringWordEmitter(arg_vec)
    while True:
      w = e.ReadWord(None)
      print(w)
      if w.id == Id.Eof_Real:
        break


if __name__ == '__main__':
  unittest.main()
