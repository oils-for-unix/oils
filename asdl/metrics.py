#!/usr/bin/env python2
"""
metrics.py
"""
from __future__ import print_function

from asdl import visitor
from asdl import ast

# type checking not turned on yet
from typing import List, Dict, IO, TYPE_CHECKING
from asdl.ast import SimpleSum
from asdl.ast import Sum
from asdl.ast import SubTypeDecl
from asdl.ast import Product

if TYPE_CHECKING:
    from asdl.front_end import TypeLookup


class MetricsVisitor(visitor.AsdlVisitor):
    """Collect metrics"""

    def __init__(self, f):
        # type: (IO[bytes]) -> None
        visitor.AsdlVisitor.__init__(self, f)

    def VisitSimpleSum(self, sum, sum_name, depth):
        # type: (SimpleSum, str, int) -> None
        pass

    def VisitCompoundSum(self, sum, sum_name, depth):
        # type: (Sum, str, int) -> None
        num_variants = 0
        for i, variant in enumerate(sum.types):
            if variant.shared_type:
                continue  # Don't generate a class for shared types.
            num_variants += 1
        self.f.write('%d %s\n' % (num_variants, sum_name))

    def VisitSubType(self, subtype):
        # type: (SubTypeDecl) -> None
        pass

    def VisitProduct(self, product, name, depth):
        # type: (Product, str, int) -> None
        pass


class ClosureWalk(object):
    """Analyze how many unique IDs needed for all of syntax.asdl command_t."""

    def __init__(self, type_lookup, seen):
        # type: (TypeLookup, Dict[str, bool]) -> None
        self.type_lookup = type_lookup
        self.seen = seen
        self.shared = {}  # type: Dict[str, bool]
        self.visited = {}  # type: Dict[str, bool]

    def DoModule(self, module, type_name):
        # type: (ast.Module, str) -> None
        for d in module.dfns:
            if isinstance(d, ast.SubTypeDecl):
                # Don't count these types
                continue

            elif isinstance(d, ast.TypeDecl):
                # Only walk for what the user asked for, e.g. the command_t type
                if d.name == type_name:
                    self.DoType(d.name, d.value)
            else:
                raise AssertionError(d)

    def DoType(self, type_name, typ):
        # type: (str, ast.asdl_type_t) -> None
        """Given an AST node, add the types it references to seen"""
        assert typ is not None, typ

        if isinstance(typ, ast.Product):
            #log('fields %s', ast_node.fields)
            self.seen[type_name] = True
            self.DoFields(typ.fields)

        elif isinstance(typ, ast.Sum):
            for cons in typ.types:
                # Shared variants will live in a different namespace!
                if cons.shared_type:
                    self.shared[cons.shared_type] = True
                    continue
                key = '%s.%s' % (type_name, cons.name)
                self.seen[key] = True
                self.DoFields(cons.fields)

        elif isinstance(typ, ast.Use):
            # Note: we don't 'use core value { value }'?  We don't need to walk
            # that one, because it's really a "cached" value attached to the
            # AST, not part of the SYNTAX.
            pass
        else:
            raise AssertionError(typ)

    def DoFields(self, field_ast_nodes):
        # type: (List[ast.Field]) -> None
        for field in field_ast_nodes:
            self.DoTypeExpr(field.typ)

    def DoTypeExpr(self, ty_expr):
        # type: (ast.type_expr_t) -> None
        """Given an AST node, add the types it references to seen"""
        if isinstance(ty_expr, ast.NamedType):
            type_name = ty_expr.name

            if type_name in self.visited:
                return

            self.visited[type_name] = True

            #typ = self.type_lookup.get(type_name)
            typ = ty_expr.resolved
            if typ is None:
                return

            self.DoType(type_name, typ)

        elif isinstance(ty_expr, ast.ParameterizedType):
            for child in ty_expr.children:
                self.DoTypeExpr(child)

        else:
            raise AssertionError()
