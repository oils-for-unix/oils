"""
visitor.py - AST pass that accepts everything.
"""
from typing import overload, Union, Optional

import mypy
from mypy.visitor import ExpressionVisitor, StatementVisitor
from mypy.nodes import (Expression, Statement, ExpressionStmt, StrExpr,
                        CallExpr)

from mycpp.crash import catch_errors
from mycpp.util import split_py_name
from mycpp import util

from typing import Optional, TypeVar, List, Tuple

T = TypeVar('T')


class UnsupportedException(Exception):
    pass


class SimpleVisitor(ExpressionVisitor[None], StatementVisitor[None]):
    """
    A simple AST visitor that accepts every node in the AST. Derrived classes
    can override the visit methods that are relevant to them.
    """

    def __init__(self) -> None:
        self.current_class_name: Optional[util.SymbolPath] = None

        # So we can report multiple at once
        # module path, line number, message
        self.errors_keep_going: List[Tuple[str, int, str]] = []

    #
    # COPIED from IRBuilder
    #

    @overload
    def accept(self, node: Expression) -> None:
        ...

    @overload
    def accept(self, node: Statement) -> None:
        ...

    def accept(self, node: Union[Statement, Expression]) -> Optional[T]:
        with catch_errors(self.module_path, node.line):
            if isinstance(node, Expression):
                try:
                    res = node.accept(self)
                    #res = self.coerce(res, self.node_type(node), node.line)

                # If we hit an error during compilation, we want to
                # keep trying, so we can produce more error
                # messages. Generate a temp of the right type to keep
                # from causing more downstream trouble.
                except UnsupportedException:
                    res = self.alloc_temp(self.node_type(node))
                return res
            else:
                try:
                    node.accept(self)
                except UnsupportedException:
                    pass
                return None

    def report_error(self, node: Union[Statement, Expression],
                     msg: str) -> None:
        err = (self.module_path, node.line, msg)
        self.errors_keep_going.append(err)

    # Not in superclasses:

    def visit_mypy_file(self, o: 'mypy.nodes.MypyFile') -> None:
        if util.ShouldSkipPyFile(o):
            return

        self.module_path = o.path

        for node in o.defs:
            # skip module docstring
            if isinstance(node, ExpressionStmt) and isinstance(
                    node.expr, StrExpr):
                continue
            self.accept(node)

    # LITERALS

    def visit_for_stmt(self, o: 'mypy.nodes.ForStmt') -> None:
        self.accept(o.index)  # index var expression
        self.accept(o.expr)
        self.accept(o.body)
        if o.else_body:
            raise AssertionError("can't translate for-else")

    def visit_with_stmt(self, o: 'mypy.nodes.WithStmt') -> None:
        assert len(o.expr) == 1, o.expr
        expr = o.expr[0]
        assert isinstance(expr, CallExpr), expr
        self.accept(expr)
        self.accept(o.body)

    def visit_func_def(self, o: 'mypy.nodes.FuncDef') -> None:
        if o.name == '__repr__':  # Don't translate
            return

        for arg in o.arguments:
            if arg.initializer:
                self.accept(arg.initializer)

        self.accept(o.body)

    def visit_class_def(self, o: 'mypy.nodes.ClassDef') -> None:
        self.current_class_name = split_py_name(o.fullname)
        for stmt in o.defs.body:
            self.accept(stmt)
        self.current_class_name = None

    # Statements

    def visit_assignment_stmt(self, o: 'mypy.nodes.AssignmentStmt') -> None:
        for lval in o.lvalues:
            self.accept(lval)

        self.accept(o.rvalue)

    def visit_operator_assignment_stmt(
            self, o: 'mypy.nodes.OperatorAssignmentStmt') -> None:
        self.accept(o.lvalue)
        self.accept(o.rvalue)

    def visit_block(self, block: 'mypy.nodes.Block') -> None:
        for stmt in block.body:
            # Ignore things that look like docstrings
            if (isinstance(stmt, ExpressionStmt) and
                    isinstance(stmt.expr, StrExpr)):
                continue

            self.accept(stmt)

    def visit_expression_stmt(self, o: 'mypy.nodes.ExpressionStmt') -> None:
        self.accept(o.expr)

    def visit_while_stmt(self, o: 'mypy.nodes.WhileStmt') -> None:
        self.accept(o.expr)
        self.accept(o.body)

    def visit_return_stmt(self, o: 'mypy.nodes.ReturnStmt') -> None:
        if o.expr:
            self.accept(o.expr)

    def visit_if_stmt(self, o: 'mypy.nodes.IfStmt') -> None:
        if util.ShouldVisitIfExpr(o):
            for expr in o.expr:
                self.accept(expr)

        if util.ShouldVisitIfBody(o):
            for body in o.body:
                self.accept(body)

        if util.ShouldVisitElseBody(o):
            self.accept(o.else_body)

    def visit_raise_stmt(self, o: 'mypy.nodes.RaiseStmt') -> None:
        if o.expr:
            self.accept(o.expr)

    def visit_try_stmt(self, o: 'mypy.nodes.TryStmt') -> None:
        self.accept(o.body)
        for handler in o.handlers:
            self.accept(handler)

    def visit_del_stmt(self, o: 'mypy.nodes.DelStmt') -> None:
        self.accept(o.expr)

    # Expressions

    def visit_generator_expr(self, o: 'mypy.nodes.GeneratorExpr') -> None:
        self.accept(o.left_expr)

        for expr in o.indices:
            self.accept(expr)

        for expr in o.sequences:
            self.accept(expr)

        for l in o.condlists:
            for expr in l:
                self.accept(expr)

    def visit_list_comprehension(self,
                                 o: 'mypy.nodes.ListComprehension') -> None:
        self.accept(o.generator)

    def visit_member_expr(self, o: 'mypy.nodes.MemberExpr') -> None:
        self.accept(o.expr)

    def visit_yield_expr(self, o: 'mypy.nodes.YieldExpr') -> None:
        self.accept(o.expr)

    def visit_op_expr(self, o: 'mypy.nodes.OpExpr') -> None:
        self.accept(o.left)
        self.accept(o.right)

    def visit_comparison_expr(self, o: 'mypy.nodes.ComparisonExpr') -> None:
        for operand in o.operands:
            self.accept(operand)

    def visit_unary_expr(self, o: 'mypy.nodes.UnaryExpr') -> None:
        # e.g. -42 or 'not x'
        self.accept(o.expr)

    def visit_list_expr(self, o: 'mypy.nodes.ListExpr') -> None:
        for item in o.items:
            self.accept(item)

    def visit_dict_expr(self, o: 'mypy.nodes.DictExpr') -> None:
        for k, v in o.items:
            self.accept(k)
            self.accept(v)

    def visit_tuple_expr(self, o: 'mypy.nodes.TupleExpr') -> None:
        for item in o.items:
            self.accept(item)

    def visit_index_expr(self, o: 'mypy.nodes.IndexExpr') -> None:
        self.accept(o.base)
        self.accept(o.index)

    def visit_slice_expr(self, o: 'mypy.nodes.SliceExpr') -> None:
        if o.begin_index:
            self.accept(o.begin_index)

        if o.end_index:
            self.accept(o.end_index)

        if o.stride:
            self.accept(o.stride)

    def visit_conditional_expr(self, o: 'mypy.nodes.ConditionalExpr') -> None:
        self.accept(o.cond)
        self.accept(o.if_expr)
        self.accept(o.else_expr)

    def visit_call_expr(self, o: 'mypy.nodes.CallExpr') -> None:
        self.accept(o.callee)
        for arg in o.args:
            self.accept(arg)
