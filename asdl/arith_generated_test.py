#!/usr/bin/python -S
"""
arith_generated_test.py: Tests for arith_generated.py
"""
from __future__ import print_function

import unittest

from asdl import asdl_
from asdl import py_meta
from core.util import log

# NOTE: requires asdl/run.sh gen-arith-python
from _tmp import arith_asdl  # module under test

cflow = arith_asdl.cflow
cflow_e = arith_asdl.cflow_e

op_id_e = arith_asdl.op_id_e

arith_expr = arith_asdl.arith_expr
arith_expr_e = arith_asdl.arith_expr_e


class ArithGeneratedTest(unittest.TestCase):

  def testTypeChecking(self):
    print(arith_asdl)

    n = cflow.Break()
    print(n)

    n = cflow.Return(3)
    log('status = %d', n.status)

    print(n)

    # Reflection on the type.  Is there a better way?
    print(n.ASDL_TYPE)
    print(list(n.ASDL_TYPE.GetFields()))
    t = n.ASDL_TYPE.LookupFieldType('status')
    self.assert_(isinstance(t, asdl_.IntType))

    e = op_id_e.Plus
    print(type(e))

    v = arith_expr.ArithVar('name')

    try:
      v2 = arith_expr.ArithVar(1)
    except TypeError:
      pass
    else:
      self.fail_('Expected TypeError')

    v3 = arith_expr.ArithVar()
    v3.name = 'foo'
    try:
      v3.name = 42
    except TypeError:
      pass
    else:
      self.fail_('Expected TypeError')

  def testTypeCheck(self):
    v = arith_expr.ArithVar('name')
    # Integer is not allowed
    self.assertRaises(TypeError, arith_expr.ArithVar, 1)

    v = arith_expr.ArithUnary(op_id_e.Minus, arith_expr.Const(99))
    # Raw integer is not allowed
    self.assertRaises(TypeError, arith_expr.ArithUnary, op_id_e.Minus, 99)

    v = arith_expr.ArithUnary(op_id_e.Minus, arith_expr.Const(99))

    # Should fail
    unrelated_node = cflow.Return()
    self.assertRaises(TypeError, arith_expr.ArithUnary, unrelated_node)

    log('num type checks = %d', py_meta.NUM_TYPE_CHECKS)


if __name__ == '__main__':
  unittest.main()
