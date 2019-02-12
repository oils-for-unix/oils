#!/usr/bin/python -S
"""
format_test.py: Tests for format.py
"""

import cStringIO
import unittest

from asdl import format as fmt

from _devbuild.gen import demo_asdl  # module under test


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
    ast_f = fmt.TextOutput(f)

    tree = fmt.MakeTree(node)
    #print(tree)

    fmt.PrintTree(tree, ast_f)
    pretty_str = f.getvalue()
    print(pretty_str)

    self.assertEqual('(assign name:declare flags:[-r -x])', pretty_str)


if __name__ == '__main__':
  unittest.main()
