"""
ir_pass.py - Translate (eventually) the mypy AST into our own IR.
"""
from typing import Dict

import mypy
from mypy.nodes import Expression, NameExpr
from mypy.types import Type

from mycpp.util import split_py_name
from mycpp import visitor
from mycpp import util
from mycpp import pass_state


class Build(visitor.SimpleVisitor):

    def __init__(self, types: Dict[Expression, Type]):

        self.types = types
        self.dot_exprs: Dict[mypy.nodes.MemberExpr, pass_state.member_t] = {}

        self.imported_names = set()  # MemberExpr -> module::Foo() or self->foo
        # HACK for conditional import inside mylib.PYTHON
        # in core/shell.py
        self.imported_names.add('help_meta')

    # Statements

    def visit_import(self, o: 'mypy.nodes.Import') -> None:
        for name, as_name in o.ids:
            if as_name is not None:
                # import time as time_
                self.imported_names.add(as_name)
            else:
                # import libc
                self.imported_names.add(name)

    def visit_import_from(self, o: 'mypy.nodes.ImportFrom') -> None:
        """
        Write C++ namespace aliases and 'using' for imports.
        We need them in the 'decl' phase for default arguments like
        runtime_asdl::scope_e -> scope_e
        """
        # For MemberExpr . -> module::func() or this->field.  Also needed in
        # the decl phase for default arg values.
        for name, alias in o.names:
            if alias:
                self.imported_names.add(alias)
            else:
                self.imported_names.add(name)

    # Expressions

    def visit_member_expr(self, o: 'mypy.nodes.MemberExpr') -> None:
        # Why do we not get some of the types?  e.g. hnode.Record in asdl/runtime
        # But this might suffice for the "Str_v" and "value_v" refactoring.
        # We want to rewrite w.parts not to w->parts, but to w.parts() (method call)

        is_small_str = False
        if util.SMALL_STR:
            lhs_type = self.types.get(o.expr)
            if util.IsStr(lhs_type):
                is_small_str = True
            else:
                #self.log('NOT a string %s %s', o.expr, o.name)
                pass
            """
            if lhs_type is not None and isinstance(lhs_type, Instance):
                self.log('lhs_type %s expr %s name %s',
                         lhs_type.type.fullname, o.expr, o.name)

             """

        # hack for MyType.CreateNull(alloc_lists=True)
        #          MyType.Take(other)
        is_asdl = o.name in ('CreateNull', 'Take')
        is_module = (isinstance(o.expr, NameExpr) and
                     o.expr.name in self.imported_names)

        # This is an approximate hack that assumes that locals don't shadow
        # imported names.  Might be a problem with names like 'word'?
        if is_small_str:
            self.dot_exprs[o] = pass_state.StackObjectMember(
                o.expr, self.types[o.expr], o.name)
        elif is_asdl:
            self.dot_exprs[o] = pass_state.StaticObjectMember(
                self.types[o].ret_type.type.fullname, o.name)
        elif is_module:
            self.dot_exprs[o] = pass_state.ModuleMember(
                split_py_name(o.expr.fullname or o.expr.name), o.name)

        else:
            self.dot_exprs[o] = pass_state.HeapObjectMember(
                o.expr, self.types[o.expr], o.name)

        self.accept(o.expr)
