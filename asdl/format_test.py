#!/usr/bin/env python2
"""format_test.py: Tests for format.py."""

import cStringIO
import unittest

from asdl import format as fmt

from _devbuild.gen import typed_demo_asdl as demo_asdl  # module under test


class FormatTest(unittest.TestCase):

    def testSimpleSum(self):
        node = demo_asdl.op_id_e.Plus
        # This calls __repr__, but does NOT call asdl/format.py
        print(node)

        array = demo_asdl.op_array([node, node])
        print(array)

    def testRepeatedString(self):
        node = demo_asdl.assign('declare', ['-r', '-x'])

        f = cStringIO.StringIO()
        tree = node.PrettyTree(False)

        fmt.HNodePrettyPrint(tree, f)
        pretty_str = f.getvalue()
        print(pretty_str)

        self.assertEqual('(assign name:declare flags:[-r  -x])\n', pretty_str)

        t2 = node.PrettyTree(True)
        fmt.HNodePrettyPrint(t2, f)


if __name__ == '__main__':
    unittest.main()
