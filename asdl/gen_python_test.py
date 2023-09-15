#!/usr/bin/env python2
"""gen_python_test.py."""
from __future__ import print_function

import unittest

from asdl import pybase

from _devbuild.gen import typed_demo_asdl
from _devbuild.gen.typed_arith_asdl import arith_expr, arith_expr_e
from _devbuild.gen.typed_demo_asdl import (
        source_location,
        flag_type, flag_type_str,
        op_id_e, op_id_str,
        cflow, cflow_t,
        Strings, Dicts, Maybes, op_array)


class ArithAstTest(unittest.TestCase):

    def testPrettyPrint(self):
        s = op_id_str(op_id_e.Plus)
        self.assertEqual('op_id.Plus', s)
        print(s)

        obj = flag_type.Bool
        s = flag_type_str(obj.tag())

        self.assertEqual('flag_type.Bool', s)
        print(s)

        s= flag_type_str(obj.tag(), dot=False)
        self.assertEqual('Bool', s)
        print(s)

    def testStringDefaults(self):
        st = Strings('', '')
        self.assertEqual('', st.required)
        self.assertEqual('', st.optional)

        # ZERO ARG "constructor" (static method)
        st = Strings.CreateNull(alloc_lists=True)
        self.assertEqual('', st.required)
        self.assertEqual(None, st.optional)

        # N arg constructor with None
        st = Strings('', None)
        self.assertEqual('', st.required)
        self.assertEqual(None, st.optional)

    def testArrayDefault(self):
        obj = op_array.CreateNull()
        self.assertEqual(None, obj.ops)

        obj = op_array.CreateNull(alloc_lists=True)
        self.assertEqual([], obj.ops)

    def testMapDefault(self):
        # TODO: alloc_dicts=True
        obj = Dicts.CreateNull(alloc_lists=True)
        self.assertEqual(None, obj.ss)

    def testOptionalDefault(self):
        obj = Maybes.CreateNull(alloc_lists=True)

        # These are None
        self.assertEqual(None, obj.op)
        self.assertEqual(None, obj.arg)

    def testFieldDefaults(self):
        s = arith_expr.Slice.CreateNull(alloc_lists=True)
        s.a = arith_expr.Var('foo')
        self.assertEqual(None, s.begin)
        self.assertEqual(None, s.end)
        self.assertEqual(None, s.stride)
        print(s)

        func = arith_expr.FuncCall.CreateNull(alloc_lists=True)
        func.name = 'f'
        self.assertEqual([], func.args)
        print(func)

    def testExtraFields(self):
        v = arith_expr.Var('z')

        # TODO: Attach this to EVERY non-simple constructor?  Those are subclasses
        # of Sum types.
        # What about product types?
        #print(v.xspans)

    def testConstructor(self):
        n1 = arith_expr.Var('x')
        n2 = arith_expr.Var(name='y')
        print(n1)
        print(n2)

        # Not good because not assigned?
        n3 = arith_expr.Var.CreateNull(alloc_lists=True)

        # NOTE: You cannot instantiate a product type directly?  It's just used for
        # type checking.  What about OCaml?
        # That means you just need to create classes for the records (arith_expr.Constructor).
        # They all descend from Obj.  They don't need

        n3 = arith_expr.Var.CreateNull(alloc_lists=True)
        try:
            n4 = arith_expr.Var('x', name='X')
        except TypeError as e:
            pass
        else:
            raise AssertionError("Should have failed")

    def testProductType(self):
        print()
        print('-- PRODUCT --')
        print()

        s = source_location.CreateNull(alloc_lists=True)
        s.path = 'hi'
        s.line = 1
        s.col = 2
        s.length = 3
        print(s)

        # Implementation detail for dynamic type checking
        assert isinstance(s, pybase.CompoundObj)

    def testSimpleSumType(self):
        # TODO: Should be op_id_i.Plus -- instance
        # Should be op_id_s.Plus

        print()
        print('-- SIMPLE SUM --')
        print()

        o = op_id_e.Plus
        assert isinstance(o, pybase.SimpleObj)

    def testCompoundSumType(self):
        print()
        print('-- COMPOUND SUM --')
        print()

        c = cflow.Break
        assert isinstance(c, typed_demo_asdl.cflow__Break)
        assert isinstance(c, cflow_t)
        assert isinstance(c, pybase.CompoundObj)

    def testOtherTypes(self):
        c = arith_expr.Const(66)
        print(c)

        sl = arith_expr.Slice(
            arith_expr.Const(1),
            arith_expr.Const(5),
            arith_expr.Const(2),
            arith_expr.Const(3),
        )
        print(sl)

        print((op_id_e.Plus))

        # Class for sum type
        print(arith_expr)

        # Invalid because only half were assigned
        #print(arith_expr.Binary(op_id_e.Plus, arith_expr.Const(5)))

        n = arith_expr.Binary.CreateNull(alloc_lists=True)
        #n.CheckUnassigned()
        n.op_id = op_id_e.Plus
        n.left = arith_expr.Const(5)
        #n.CheckUnassigned()
        n.right = arith_expr.Const(6)
        #n.CheckUnassigned()

        self.assertEqual(arith_expr_e.Const, c.tag())
        self.assertEqual(arith_expr_e.Binary, n.tag())


if __name__ == '__main__':
    unittest.main()
