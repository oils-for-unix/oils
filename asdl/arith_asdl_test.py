#!/usr/bin/env python
"""
arith_asdl_test.py: Tests for arith_asdl.py
"""
from __future__ import print_function

import unittest

from asdl import const
from asdl import runtime

from _tmp import arith_asdl  # module under test

arith_expr = arith_asdl.arith_expr
source_location = arith_asdl.source_location
op_id_e = arith_asdl.op_id_e

cflow = arith_asdl.cflow
cflow_e = arith_asdl.cflow_e


class ArithAstTest(unittest.TestCase):

  def testReflection(self):
    n = cflow.Return(3)
    # Reflection on the type.  Is there a better way?
    print(n.ASDL_TYPE)
    print(list(n.ASDL_TYPE.GetFields()))
    t = n.ASDL_TYPE.LookupFieldType('status')
    self.assert_(isinstance(t, runtime.IntType))

  def testFieldDefaults(self):
    s = arith_expr.Slice()
    s.a = arith_expr.ArithVar('foo')
    self.assertEqual(None, s.begin)
    self.assertEqual(None, s.end)
    self.assertEqual(None, s.stride)
    print(s)

    func = arith_expr.FuncCall()
    func.name = 'f'
    self.assertEqual([], func.args)
    print(func)

    t = arith_asdl.token(5, 'x')
    self.assertEqual(5, t.id)
    self.assertEqual('x', t.value)
    self.assertEqual(const.NO_INTEGER, t.span_id)

  def testTypeCheck(self):
    v = arith_expr.ArithVar('name')
    # Integer is not allowed
    self.assertRaises(TypeError, arith_expr.ArithVar, 1)

    v = arith_expr.ArithUnary(op_id_e.Minus, arith_expr.Const(99))
    # Raw integer is not allowed
    self.assertRaises(TypeError, arith_expr.ArithUnary, op_id_e.Minus, 99)

    v = arith_expr.ArithUnary(op_id_e.Minus, arith_expr.Const(99))
    # Raw integer is not allowed
    #self.assertRaises(AssertionError, arith_expr.ArithUnary, op_id_e.Minus, op_id_e.Plus)

  def testExtraFields(self):
    v = arith_expr.ArithVar('z')

    # TODO: Attach this to EVERY non-simple constructor?  Those are subclasses
    # of Sum types.
    # What about product types?
    #print(v.xspans)

  def testConstructor(self):
    n1 = arith_expr.ArithVar('x')
    n2 = arith_expr.ArithVar(name='y')
    print(n1)
    print(n2)

    # Not good because not assigned?
    n3 = arith_expr.ArithVar()

    # NOTE: You cannot instantiate a product type directly?  It's just used for
    # type checking.  What about OCaml?
    # That means you just need to create classes for the records (arith_expr.Constructor).
    # They all descend from Obj.  They don't need

    n3 = arith_expr.ArithVar()
    try:
      n4 = arith_expr.ArithVar('x', name='X')
    except TypeError as e:
      pass
    else:
      raise AssertionError("Should have failed")

  def testProductType(self):
    print()
    print('-- PRODUCT --')
    print()

    s = source_location()
    s.path = 'hi'
    s.line = 1
    s.col = 2
    s.length = 3
    print(s)

    assert isinstance(s.ASDL_TYPE, runtime.CompoundType)

    # Implementation detail for dynamic type checking
    assert isinstance(s, runtime.CompoundObj)

  def testSimpleSumType(self):
    # TODO: Should be op_id_i.Plus -- instance
    # Should be op_id_s.Plus

    print()
    print('-- SIMPLE SUM --')
    print()

    o = op_id_e.Plus
    assert isinstance(o, runtime.SimpleObj)

    # Implementation detail for dynamic type checking
    assert isinstance(o.ASDL_TYPE, runtime.SumType)

  def testCompoundSumType(self):
    print()
    print('-- COMPOUND SUM --')
    print()

    # TODO: Should be cflow_t.Break() and cflow_i.Break
    c = cflow.Break()
    assert isinstance(c, cflow.Break)
    assert isinstance(c, arith_asdl.cflow)
    assert isinstance(c, runtime.CompoundObj)

    # Implementation detail for dynamic type checking
    assert isinstance(c.ASDL_TYPE, runtime.CompoundType), c.ASDL_TYPE

  def testOtherTypes(self):
    c = arith_expr.Const(66)
    print(c)

    print((arith_expr.Slice(arith_expr.Const(1), arith_expr.Const(5), arith_expr.Const(2))))

    print((op_id_e.Plus))

    # Class for sum type
    print(arith_expr)

    # Invalid because only half were assigned
    #print(arith_expr.ArithBinary(op_id_e.Plus, arith_expr.Const(5)))

    n = arith_expr.ArithBinary()
    #n.CheckUnassigned()
    n.op_id = op_id_e.Plus
    n.left = arith_expr.Const(5)
    #n.CheckUnassigned()
    n.right = arith_expr.Const(6)
    #n.CheckUnassigned()

    arith_expr_e = arith_asdl.arith_expr_e
    self.assertEqual(arith_expr_e.Const, c.tag)
    self.assertEqual(arith_expr_e.ArithBinary, n.tag)


if __name__ == '__main__':
  unittest.main()
