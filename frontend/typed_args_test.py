#!/usr/bin/env python2
"""
typed_args_test.py: Tests for typed_args.py
"""

import unittest

from _devbuild.gen.runtime_asdl import value
from _devbuild.gen.syntax_asdl import ArgList, expr
from core import error
from core import test_lib
from frontend import typed_args  # module under test

from typing import cast


class TypedArgsTest(unittest.TestCase):
    def testReaderPosArgs(self):
        arena = test_lib.MakeArena('')
        line_id = arena.AddLine('foo(a, b, c, d, e, f, g)', 1)
        ltok = arena.NewToken(-1, 3, 1, line_id, '')
        rtok = arena.NewToken(-1, 4, 1, line_id, '')
        pos_exprs = [
            expr.Const(arena.NewToken(-1, 4+2*i, 1, line_id, ''))
            for i in range(7)
        ]
        arg_list = ArgList(ltok, pos_exprs, [], rtok)

        # Not enough args...
        reader = typed_args.Reader([], {}, arg_list)
        self.assertRaises(error.TypeErrVerbose, reader.PosStr)

        pos_args = [
            value.Int(0xc0ffee),
            value.Str('foo'),
            value.List([value.Int(1), value.Int(2), value.Int(3)]),
            value.Dict({'a': value.Int(0xaa), 'b': value.Int(0xbb)}),
            value.Float(3.14),
            value.Int(0xdead),
            value.Int(0xbeef),
            value.Str('bar'),
        ]
        reader = typed_args.Reader(list(pos_args), {}, arg_list)

        # Haven't processed any args yet...
        self.assertRaises(error.TypeErrVerbose, reader.Done)

        # Arg is wrong type...
        with self.assertRaises(error.TypeErrVerbose) as cm:
            reader.PosStr()

        # Check that the error points to the right token
        e = cm.exception
        self.assertEqual(pos_exprs[0].c, e.location)

        # Normal operation from here on
        reader = typed_args.Reader(pos_args, {}, arg_list)
        arg = reader.PosInt()
        self.assertEqual(0xc0ffee, arg)

        arg = reader.PosStr()
        self.assertEqual('foo', arg)

        arg = reader.PosList()
        self.assertEqual(1, cast(value.Int, arg[0]).i)
        self.assertEqual(2, cast(value.Int, arg[1]).i)
        self.assertEqual(3, cast(value.Int, arg[2]).i)

        arg = reader.PosDict()
        self.assertIn('a', arg)
        self.assertEqual(0xaa, arg['a'].i)
        self.assertIn('b', arg)
        self.assertEqual(0xbb, arg['b'].i)

        arg = reader.PosFloat()
        self.assertEqual(3.14, arg)

        rest = reader.RestPos()
        self.assertEqual(3, len(rest))
        self.assertEqual(0xdead, rest[0].i)
        self.assertEqual(0xbeef, rest[1].i)
        self.assertEqual('bar', rest[2].s)

        reader.Done()

    def testReaderKwargs(self):
        # Dummy call. Not testing error messages here.
        arena = test_lib.MakeArena('')
        line_id = arena.AddLine('foo()', 1)
        ltok = arena.NewToken(-1, 0, 3, line_id, '')
        rtok = arena.NewToken(-1, 0, 4, line_id, '')
        arg_list = ArgList(ltok, [], [], rtok)

        kwargs = {
            'hot': value.Int(0xc0ffee),
            'name': value.Str('foo'),
            'numbers': value.List([value.Int(1), value.Int(2), value.Int(3)]),
            'blah': value.Dict({'a': value.Int(0xaa), 'b': value.Int(0xbb)}),
            'pi': value.Float(3.14),
            'a': value.Int(0xdead),
            'b': value.Int(0xbeef),
            'c': value.Str('bar'),
        }
        reader = typed_args.Reader([], kwargs, arg_list)

        # Haven't processed any args yet...
        self.assertRaises(error.TypeErrVerbose, reader.Done)

        arg = reader.NamedInt('hot', -1)
        self.assertEqual(0xc0ffee, arg)

        arg = reader.NamedStr('name', '')
        self.assertEqual('foo', arg)

        arg = reader.NamedList('numbers', [])
        self.assertEqual(1, cast(value.Int, arg[0]).i)
        self.assertEqual(2, cast(value.Int, arg[1]).i)
        self.assertEqual(3, cast(value.Int, arg[2]).i)

        arg = reader.NamedDict('blah', {})
        self.assertIn('a', arg)
        self.assertEqual(0xaa, arg['a'].i)
        self.assertIn('b', arg)
        self.assertEqual(0xbb, arg['b'].i)

        arg = reader.NamedFloat('pi', -1.0)
        self.assertEqual(3.14, arg)

        rest = reader.RestNamed()
        self.assertEqual(3, len(rest))
        self.assertIn('a', rest)
        self.assertEqual(0xdead, rest['a'].i)
        self.assertIn('b', rest)
        self.assertEqual(0xbeef, rest['b'].i)
        self.assertIn('c', rest)
        self.assertEqual('bar', rest['c'].s)


if __name__ == '__main__':
    unittest.main()
