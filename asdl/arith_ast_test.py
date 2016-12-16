#!/usr/bin/env python3
"""
arith_ast_test.py: Tests for arith_ast.py
"""

import unittest

import arith_ast  # module under test
import py_meta


class ArithAstTest(unittest.TestCase):

  def testTypes(self):
    ArithVar = arith_ast.ArithVar
    ArithUnary = arith_ast.ArithUnary
    ArithBinary = arith_ast.ArithBinary
    Const = arith_ast.Const
    Slice = arith_ast.Slice
    arith_expr = arith_ast.arith_expr
    source_location = arith_ast.source_location
    op_id = arith_ast.op_id

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

    print(source_location())
    
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


if __name__ == '__main__':
  unittest.main()
