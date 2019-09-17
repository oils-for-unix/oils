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
      schema_ast, type_lookup = front_end.LoadSchema(f, {}, verbose=False)
    #print(type_lookup)

    # Test fully-qualified name
    self.assertTrue('bool_expr__LogicalNot' in type_lookup)
    self.assertTrue('op_id__Plus' in type_lookup)

  def testSharedVariant(self):
    with open('asdl/shared_variant.asdl') as f:
      schema_ast, type_lookup = front_end.LoadSchema(f, {}, verbose=True)
    #print(type_lookup)


if __name__ == '__main__':
  unittest.main()
