#!/usr/bin/python
"""
gen_cpp.py
"""
from __future__ import print_function

from asdl import visitor


# Used by core/asdl_gen.py
class CEnumVisitor(visitor.AsdlVisitor):

  def VisitSimpleSum(self, sum, name, depth):
    # Just use #define, since enums aren't namespaced.
    for i, variant in enumerate(sum.types):
      self.Emit('#define %s__%s %d' % (name, variant.name, i + 1), depth)
    self.Emit("", depth)

