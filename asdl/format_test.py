#!/usr/bin/env python2
"""
format_test.py: Tests for format.py
"""

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
    f1 = fmt.TextOutput(f)
    f2 = fmt.HtmlOutput(f)

    for ast_f in [f1, f2]:
      tree = node.PrettyTree()

      fmt.PrintTree(tree, ast_f)
      pretty_str = f.getvalue()
      print(pretty_str)

      if ast_f is f1:
        self.assertEqual('(assign name:declare flags:[-r -x])', pretty_str)

      t2 = node.AbbreviatedTree()

      fmt.PrintTree(t2, ast_f)


if __name__ == '__main__':
  unittest.main()
