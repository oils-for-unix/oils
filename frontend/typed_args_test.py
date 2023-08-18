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
        reader = typed_args.Reader(pos_args, {})

        # Haven't processed any args yet...
        self.assertRaises(error.InvalidType, reader.Done)

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


if __name__ == '__main__':
    unittest.main()
