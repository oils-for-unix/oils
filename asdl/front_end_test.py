#!/usr/bin/env python2
"""
front_end_test.py: Tests for front_end.py
"""
from __future__ import print_function

import unittest

from asdl import front_end  # module under test


class FrontEndTest(unittest.TestCase):

  def testLoadSchema(self):
    with open('asdl/typed_demo.asdl') as f:
      schema_ast, type_lookup = front_end.LoadSchema(f, {}, verbose=True)
    #print(type_lookup)

    # Test fully-qualified name
    self.assertTrue('bool_expr__LogicalNot' in type_lookup)
    self.assertTrue('op_id__Plus' in type_lookup)

  def testSharedVariant(self):
    with open('asdl/shared_variant.asdl') as f:
      schema_ast, type_lookup = front_end.LoadSchema(f, {}, verbose=False)
    #print(type_lookup)

  def testSharedVariantCode(self):
    from _devbuild.gen.shared_variant_asdl import (
        double_quoted, expr, expr_e, word_part, word_part_e
    )
    print(double_quoted)

    print(expr)
    print(expr_e)

    print(word_part)
    print(word_part_e)

    # These have the same value!
    self.assertEqual(1001, expr_e.DoubleQuoted)
    self.assertEqual(expr_e.DoubleQuoted, word_part_e.DoubleQuoted)

    d = double_quoted(5, ['foo', 'bar'])
    d.PrettyPrint()
    print()

    b = expr.Binary(d, d)
    b.PrettyPrint()



if __name__ == '__main__':
  unittest.main()
