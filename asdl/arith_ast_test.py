#!/usr/bin/env python3
"""
arith_ast_test.py: Tests for arith_ast.py
"""

import io
import unittest

from asdl import arith_ast  # module under test
from asdl import format as fmt
from asdl import py_meta
from asdl import encode


ArithVar = arith_ast.ArithVar
ArithUnary = arith_ast.ArithUnary
ArithBinary = arith_ast.ArithBinary
Const = arith_ast.Const
Slice = arith_ast.Slice
arith_expr = arith_ast.arith_expr
source_location = arith_ast.source_location
op_id = arith_ast.op_id


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

  def testTypeCheck(self):
    v = ArithVar('name')
    # Integer is not allowed
    self.assertRaises(AssertionError, ArithVar, 1)

    v = ArithUnary(op_id.Minus, Const(99))
    # Raw integer is not allowed
    self.assertRaises(AssertionError, ArithUnary, op_id.Minus, 99)

    v = ArithUnary(op_id.Minus, Const(99))
    # Raw integer is not allowed
    #self.assertRaises(AssertionError, ArithUnary, op_id.Minus, op_id.Plus)

  def testExtraFields(self):
    v = ArithVar('z')

    # TODO: Attach this to EVERY non-simple constructor?  Those are subclasses
    # of Sum types.
    # What about product types?
    #print(v.xspans)

  def testTypes(self):

    print(ArithVar)
    print('FIELDS', ArithVar.FIELDS)
    print('DESCRIPTOR_LOOKUP', ArithVar.DESCRIPTOR_LOOKUP)
    print('DESCRIPTOR', ArithVar.DESCRIPTOR)

    print(ArithUnary)
    print(ArithUnary.FIELDS)

    print(ArithBinary)
    print(ArithBinary.FIELDS)

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
    except AssertionError as e:
      pass
    else:
      raise AssertionError("Should have failed")

    #n5 = ArithVar(None)

    s = source_location()
    s.path = 'hi'
    s.line = 1
    s.col = 2
    s.length = 3
    print(s)

    c = Const(66)
    print(c)
    # Test out hierarchy
    assert isinstance(c, Const)
    assert isinstance(c, arith_expr)
    assert isinstance(c, py_meta.CompoundObj)

    #print(Const('invalid'))

    print(Slice(Const(1), Const(5), Const(2)))

    print(op_id.Plus)

    # Class for sum type
    print(arith_expr)

    # Invalid because only half were assigned
    #print(ArithBinary(op_id.Plus, Const(5)))

    n = ArithBinary()
    #n.CheckUnassigned()
    n.op_id = op_id.Plus
    n.left = Const(5)
    #n.CheckUnassigned()
    n.right = Const(6)
    n.CheckUnassigned()

    arith_expr_e = arith_ast.arith_expr_e
    self.assertEqual(arith_expr_e.Const, c.tag)
    self.assertEqual(arith_expr_e.ArithBinary, n.tag)

  def testEncode(self):
    obj = arith_ast.Const(99)
    print('Encoding into binary:')
    print(obj)

    enc = encode.Params()
    f = io.BytesIO()
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


if __name__ == '__main__':
  unittest.main()
