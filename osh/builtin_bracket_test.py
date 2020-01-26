#!/usr/bin/env python2
"""
builtin_bracket_test.py: Tests for builtin_bracket.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.id_kind_asdl import Id
from core import test_lib
from osh import builtin_bracket  # module under test


class BracketTest(unittest.TestCase):

  def testStringWordEmitter(self):
    # Test
    argv = '-z X -o -z Y -a -z X'.split()
    cmd_val = test_lib.MakeBuiltinArgv(argv)
    e = builtin_bracket._StringWordEmitter(cmd_val)
    while True:
      w = e.ReadWord(None)
      print(w)
      if w.id == Id.Eof_Real:
        break


if __name__ == '__main__':
  unittest.main()
