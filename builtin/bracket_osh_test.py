#!/usr/bin/env python2
from __future__ import print_function

import unittest

from _devbuild.gen.id_kind_asdl import Id
from core import test_lib
from builtin import bracket_osh  # module under test


class BracketTest(unittest.TestCase):

    def testStringWordEmitter(self):
        # Test
        argv = '-z X -o -z Y -a -z X'.split()
        cmd_val = test_lib.MakeBuiltinArgv(argv)
        e = bracket_osh._StringWordEmitter(cmd_val)
        while True:
            w = e.ReadWord(None)
            print(w)
            if w.id == Id.Eof_Real:
                break


if __name__ == '__main__':
    unittest.main()
