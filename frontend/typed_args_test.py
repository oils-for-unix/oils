#!/usr/bin/env python2
"""
typed_args_test.py: Tests for typed_args.py
"""

import unittest

from _devbuild.gen.runtime_asdl import value
from core import error
from frontend import typed_args  # module under test

from typing import cast


class TypedArgsTest(unittest.TestCase):
    def testReaderPosArgs(self):
        # Not enough args...
        reader = typed_args.Reader([], {})
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
        reader = typed_args.Reader(list(pos_args), {})

        # Haven't processed any args yet...
        self.assertRaises(error.TypeErrVerbose, reader.Done)

        # Arg is wrong type...
        self.assertRaises(error.TypeErrVerbose, reader.PosStr)

        # Normal operation from here on
        reader = typed_args.Reader(pos_args, {})
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
        reader = typed_args.Reader([], kwargs)

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
