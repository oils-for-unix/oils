#!/usr/bin/env python2
"""
metrics.py
"""
from __future__ import print_function

from asdl import visitor
from asdl.util import log


class MetricsVisitor(visitor.AsdlVisitor):
    """Collect metrics"""

    def __init__(self, f):
        visitor.AsdlVisitor.__init__(self, f)

    def VisitSimpleSum(self, sum, sum_name, depth):
        pass

    def VisitCompoundSum(self, sum, sum_name, depth):
        num_variants = 0
        for i, variant in enumerate(sum.types):
            if variant.shared_type:
                continue  # Don't generate a class for shared types.
            num_variants += 1
        self.f.write('%d %s\n' % (num_variants, sum_name))

    def VisitSubType(self, subtype):
        pass

    def VisitProduct(self, product, name, depth):
        pass


def CountTypes(schema_ast, action):
    # 78
    log('defs: %d', len(schema_ast.dfns))

    t = schema_ast.type_lookup['command']
    print(t)
