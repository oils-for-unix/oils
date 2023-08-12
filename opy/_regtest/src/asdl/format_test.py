#!/usr/bin/python -S
"""
format_test.py: Tests for format.py
"""

import cStringIO
import unittest

from asdl import format as fmt

from asdl import arith_ast  # module under test


class FormatTest(unittest.TestCase):

  def testSimpleSum(self):
    node = arith_ast.op_id_e.Plus
    print(node)

    f = cStringIO.StringIO()
    ast_f = fmt.TextOutput(f)

    tree = fmt.MakeTree(node)
    fmt.PrintTree(tree, ast_f)

    # Hm this prints 'Plus'.  Doesn't print the class or the number.
    # But those aren't intrinsic.  These are mostly used for their IDENTITY.
    # I think the ASDL_TYPE field contains the relevant info.  Yes!
    pretty_str = f.getvalue()
    print(pretty_str)

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
