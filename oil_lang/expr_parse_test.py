#!/usr/bin/env python2
"""
expr_parse_test.py: Tests for expr_parse.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.id_kind_asdl import Kind
from core.meta import ID_SPEC
#from frontend import lex
#from pgen2.pgen2_main import OilTokenDef # module under test


class FooTest(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def testOilTokenDef(self):
    # Used for
    #tok_def = OilTokenDef()

    # NOTE: These overlap with Kind.Op.

    # We need ID_SPEC.ExprOperators(), which has Op, Arith, and Expr kinds.

    # We don't have:
    # LexerPairs(Kind.Op)
    # LexerPairs(Kind.Expr)

    # Because we really need a lookup for a MODE.
    # Problem: _UNQUOTED is used in both DBracket and ShCommand mode.


    arith = ID_SPEC.LexerPairs(Kind.Arith)
    print(arith)

    # Doesn't have one.
    #left = ID_SPEC.LexerPairs(Kind.Left)
    #print(left)


if __name__ == '__main__':
  unittest.main()
