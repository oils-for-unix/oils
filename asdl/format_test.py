#!/usr/bin/python -S
"""
format_test.py: Tests for format.py
"""

import cStringIO
import sys
import unittest


from asdl import format as fmt
from asdl import asdl_

from asdl import arith_ast  # module under test


class FormatTest(unittest.TestCase):

  def testRepeatedString(self):
    node = arith_ast.assign('declare', ['-r', '-x'])

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
