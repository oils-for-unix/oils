"""
ir_pass.py - Translate (eventually) the mypy AST into our own IR.
"""
from typing import Dict, Optional

import mypy
from mypy.nodes import Expression, NameExpr
from mypy.types import Type

from mycpp.util import SplitPyName
from mycpp import visitor
from mycpp import util
from mycpp import pass_state

DotExprs = Dict[mypy.nodes.MemberExpr, pass_state.member_t]


class Build(visitor.SimpleVisitor):

    def __init__(self, types: Dict[Expression, Type], dot_exprs: DotExprs):
        visitor.SimpleVisitor.__init__(self)

        self.types = types
        self.dot_exprs = dot_exprs

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

    def oils_visit_member_expr(self, o: 'mypy.nodes.MemberExpr') -> None:
        # Why is self.types[o] missing some types?  e.g. hnode.Record() call in
        # asdl/runtime.py, failing with KeyError NameExpr
        lhs_type = self.types.get(o.expr)  # type: Optional[Type]

        is_small_str = False
        if util.SMALL_STR:
            if util.IsStr(lhs_type):
                is_small_str = True

        # This is an approximate hack that assumes that locals don't shadow
        # imported names.  Might be a problem with names like 'word'?
        if is_small_str:
            # mystr.upper()
            dot = pass_state.StackObjectMember(
                o.expr, lhs_type, o.name)  # type: pass_state.member_t

        elif o.name in ('CreateNull', 'Take'):
            # heuristic for MyType::CreateNull()
            #               MyType::Take(other)
            type_name = self.types[o].ret_type.type.fullname
            dot = pass_state.StaticClassMember(type_name, o.name)
        elif (isinstance(o.expr, NameExpr) and o.expr.name in self.imported_names):
            # heuristic for state::Mem()
            module_path = SplitPyName(o.expr.fullname or o.expr.name)
            dot = pass_state.ModuleMember(module_path, o.name)
        else:
            # mylist->append(42)
            dot = pass_state.HeapObjectMember(o.expr, lhs_type, o.name)

        self.dot_exprs[o] = dot

        self.accept(o.expr)
