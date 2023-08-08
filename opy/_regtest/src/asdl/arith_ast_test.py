#!/usr/bin/env python
from __future__ import print_function
"""
arith_ast_test.py: Tests for arith_ast.py
"""

import cStringIO
import unittest

from asdl import py_meta
from asdl import asdl_
from asdl import const
from asdl import encode

from asdl import arith_ast  # module under test

# Sanity check.  Doesn't pass because this unit test exposes implementation
# details, like the concrete classes.
#from _tmp import arith_ast_asdl as arith_ast


ArithVar = arith_ast.ArithVar
ArithUnary = arith_ast.ArithUnary
ArithBinary = arith_ast.ArithBinary
Const = arith_ast.Const
Slice = arith_ast.Slice
arith_expr = arith_ast.arith_expr
source_location = arith_ast.source_location
op_id_e = arith_ast.op_id_e

cflow_e = arith_ast.cflow_e
#cflow_t = arith_ast.cflow_t


class ArithAstTest(unittest.TestCase):

  def testFieldDefaults(self):
    s = arith_ast.Slice()
    s.a = ArithVar('foo')
    self.assertEqual(None, s.begin)
    self.assertEqual(None, s.end)
    self.assertEqual(None, s.stride)
    print(s)

    func = arith_ast.FuncCall()
    func.name = 'f'
    self.assertEqual([], func.args)
    print(func)

    t = arith_ast.token(5, 'x')
    self.assertEqual(5, t.id)
    self.assertEqual('x', t.value)
    self.assertEqual(const.NO_INTEGER, t.span_id)

  def testTypeCheck(self):
    v = ArithVar('name')
    # Integer is not allowed
    self.assertRaises(AssertionError, ArithVar, 1)

    v = ArithUnary(op_id_e.Minus, Const(99))
    # Raw integer is not allowed
    self.assertRaises(AssertionError, ArithUnary, op_id_e.Minus, 99)

    v = ArithUnary(op_id_e.Minus, Const(99))
    # Raw integer is not allowed
    #self.assertRaises(AssertionError, ArithUnary, op_id_e.Minus, op_id_e.Plus)

  def testExtraFields(self):
    v = ArithVar('z')

    # TODO: Attach this to EVERY non-simple constructor?  Those are subclasses
    # of Sum types.
    # What about product types?
    #print(v.xspans)

  def testEncode(self):
    obj = arith_ast.Const(99)
    print('Encoding into binary:')
    print(obj)

    enc = encode.Params()
    f = cStringIO.StringIO()
    out = encode.BinOutput(f)
    encode.EncodeRoot(obj, enc, out)
    e = f.getvalue()

    #print(repr(e))
    #print(e[0:4], e[4:8], e[8:])

    # Header is OHP version 1
    self.assertEqual(b'OHP\x01', e[0:4])

    self.assertEqual(b'\x04', e[4:5])  # alignment 4

    # TODO: Fix after spids
    return
    self.assertEqual(b'\x02\x00\x00', e[5:8])  # root ref 2

    self.assertEqual(b'\x01', e[8:9])  # tag 1 is const
    self.assertEqual(b'\x63\x00\x00', e[9:12])  # 0x63 = 99

  def testConstructorType(self):
    n1 = ArithVar('x')
    n2 = ArithVar(name='y')
    print(n1)
    print(n2)

    # Not good because not assigned?
    n3 = ArithVar()

    # NOTE: You cannot instantiate a product type directly?  It's just used for
    # type checking.  What about OCaml?
    # That means you just need to create classes for the records (Constructor).
    # They all descend from Obj.  They don't need

    n3 = ArithVar()
    try:
      n4 = ArithVar('x', name='X')
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

    assert isinstance(s.ASDL_TYPE, asdl_.Product)

    # Implementation detail for dynamic type checking
    assert isinstance(s, py_meta.CompoundObj)

  def testSimpleSumType(self):
    # TODO: Should be op_id_i.Plus -- instance
    # Should be op_id_s.Plus

    print()
    print('-- SIMPLE SUM --')
    print()

    o = op_id_e.Plus
    assert isinstance(o, py_meta.SimpleObj)

    # Implementation detail for dynamic type checking
    assert isinstance(o.ASDL_TYPE, asdl_.Sum)

  def testCompoundSumType(self):
    print()
    print('-- COMPOUND SUM --')
    print()

    # TODO: Should be cflow_t.Break() and cflow_i.Break
    c = arith_ast.Break()
    assert isinstance(c, arith_ast.Break)
    assert isinstance(c, arith_ast.cflow)
    assert isinstance(c, py_meta.CompoundObj)

    # Implementation detail for dynamic type checking
    assert isinstance(c.ASDL_TYPE, asdl_.Constructor), c.ASDL_TYPE

  def testOtherTypes(self):
    c = Const(66)
    print(c)

    print((Slice(Const(1), Const(5), Const(2))))

    print((op_id_e.Plus))

    # Class for sum type
    print(arith_expr)

    # Invalid because only half were assigned
    #print(ArithBinary(op_id_e.Plus, Const(5)))

    n = ArithBinary()
    #n.CheckUnassigned()
    n.op_id = op_id_e.Plus
    n.left = Const(5)
    #n.CheckUnassigned()
    n.right = Const(6)
    n.CheckUnassigned()

    arith_expr_e = arith_ast.arith_expr_e
    self.assertEqual(arith_expr_e.Const, c.tag)
    self.assertEqual(arith_expr_e.ArithBinary, n.tag)


if __name__ == '__main__':
  unittest.main()
