"""
visitor.py - AST pass that accepts everything.
"""
import mypy
from mypy.visitor import ExpressionVisitor, StatementVisitor
from mypy.nodes import (Expression, Statement, StrExpr, CallExpr, NameExpr,
                        MemberExpr)

from mycpp.crash import catch_errors
from mycpp import util
from mycpp.util import split_py_name, log

from typing import (overload, Any, Union, Optional, TypeVar, List, Tuple,
                    TextIO)

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
        self.module_path: Optional[str] = None

        # So we can report multiple at once
        # module path, line number, message
        self.errors_keep_going: List[Tuple[str, int, str]] = []

        self.indent = 0
        self.f = None

    def SetOutputFile(self, f: TextIO) -> None:
        self.f = f

    def log(self, msg: str, *args: Any) -> None:
        """Log to STDERR"""
        ind_str = self.indent * '  '
        log(ind_str + msg, *args)

    def write(self, msg: str, *args: Any) -> None:
        if args:
            msg = msg % args
        assert self.f is not None
        self.f.write(msg)

    def write_ind(self, msg: str, *args: Any) -> None:
        ind_str = self.indent * '  '
        self.write(ind_str + msg, *args)

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

    def not_translated(self, node: Union[Statement, Expression],
                       name: str) -> None:
        self.report_error(node, '%s not translated' % name)

    def not_python2(self, node: Union[Statement, Expression],
                    name: str) -> None:
        self.report_error(node, "%s: shouldn't get here in Python 2" % name)

    def oils_visit_mypy_file(self, o: 'mypy.nodes.MypyFile') -> None:
        for node in o.defs:
            self.accept(node)

    def visit_mypy_file(self, o: 'mypy.nodes.MypyFile') -> None:
        if util.ShouldSkipPyFile(o):
            return

        self.module_path = o.path

        self.oils_visit_mypy_file(o)

        # Now show errors for each file
        for path, line_num, msg in self.errors_keep_going:
            self.log('%s:%s %s', path, line_num, msg)

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

    def oils_visit_func_def(self, o: 'mypy.nodes.FuncDef') -> None:
        """Only the functions we care about in Oils."""
        for arg in o.arguments:
            if arg.initializer:
                self.accept(arg.initializer)

        self.accept(o.body)

    def visit_func_def(self, o: 'mypy.nodes.FuncDef') -> None:
        if o.name == '__repr__':  # Don't translate
            return

        self.oils_visit_func_def(o)

    def oils_visit_class_def(
            self, o: 'mypy.nodes.ClassDef',
            base_class_name: Optional[util.SymbolPath]) -> None:
        for stmt in o.defs.body:
            self.accept(stmt)

    def visit_class_def(self, o: 'mypy.nodes.ClassDef') -> None:
        base_class_name = None  # single inheritance only
        for b in o.base_type_exprs:
            if isinstance(b, NameExpr):
                if b.name != 'object' and b.name != 'Exception':
                    base_class_name = split_py_name(b.fullname)
            elif isinstance(b, MemberExpr):  # vm._Executor -> vm::_Executor
                assert isinstance(b.expr, NameExpr), b
                base_class_name = split_py_name(b.expr.fullname) + (b.name, )

        self.current_class_name = split_py_name(o.fullname)
        self.oils_visit_class_def(o, base_class_name)
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
            self.accept(stmt)

    def visit_expression_stmt(self, o: 'mypy.nodes.ExpressionStmt') -> None:
        # Ignore all docstrings: module, class, and function body
        if isinstance(o.expr, StrExpr):
            return

        # This is likely either
        # f()
        # obj.method()
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
        # Called by visit_list_comprehension
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

    #
    # Not doing anything with these?
    #

    def visit_cast_expr(self, o: 'mypy.nodes.CastExpr') -> None:
        # I think casts are handle in AssignmentStmt
        pass

    def visit_type_application(self, o: 'mypy.nodes.TypeApplication') -> None:
        # what is this?
        pass

    def visit_type_var_expr(self, o: 'mypy.nodes.TypeVarExpr') -> None:
        pass

    def visit_type_alias_expr(self, o: 'mypy.nodes.TypeAliasExpr') -> None:
        pass

    def visit_reveal_expr(self, o: 'mypy.nodes.RevealExpr') -> None:
        pass

    def visit_var(self, o: 'mypy.nodes.Var') -> None:
        # Is this a Python 3 class member?
        pass

    def visit_assert_stmt(self, o: 'mypy.nodes.AssertStmt') -> None:
        # no-op on purpose
        pass

    #
    # Not part of the mycpp dialect
    #

    def visit_lambda_expr(self, o: 'mypy.nodes.LambdaExpr') -> None:
        self.not_translated(o, 'lambda')

    def visit_set_comprehension(self,
                                o: 'mypy.nodes.SetComprehension') -> None:
        self.not_translated(o, 'set comp')

    def visit_dictionary_comprehension(
            self, o: 'mypy.nodes.DictionaryComprehension') -> None:
        self.not_translated(o, 'dict comp')

    def visit_global_decl(self, o: 'mypy.nodes.GlobalDecl') -> None:
        self.not_translated(o, 'global')

    def visit_nonlocal_decl(self, o: 'mypy.nodes.NonlocalDecl') -> None:
        self.not_translated(o, 'nonlocal')

    def visit_exec_stmt(self, o: 'mypy.nodes.ExecStmt') -> None:
        self.report_error(o, 'exec not allowed')

    # Error
    def visit_print_stmt(self, o: 'mypy.nodes.PrintStmt') -> None:
        self.report_error(
            o,
            'File should start with "from __future__ import print_function"')

    # UNHANDLED

    def visit_import_all(self, o: 'mypy.nodes.ImportAll') -> None:
        self.not_translated(o, 'ImportAll')

    def visit_overloaded_func_def(self,
                                  o: 'mypy.nodes.OverloadedFuncDef') -> None:
        self.not_python2(o, 'overloaded func')

    def visit_bytes_expr(self, o: 'mypy.nodes.BytesExpr') -> None:
        self.not_python2(o, 'bytes expr')

    def visit_unicode_expr(self, o: 'mypy.nodes.UnicodeExpr') -> None:
        self.not_translated(o, 'unicode expr')

    def visit_complex_expr(self, o: 'mypy.nodes.ComplexExpr') -> None:
        self.not_translated(o, 'complex expr')

    def visit_set_expr(self, o: 'mypy.nodes.SetExpr') -> None:
        self.not_translated(o, 'set expr')

    def visit_ellipsis(self, o: 'mypy.nodes.EllipsisExpr') -> None:
        # is this in .pyi files only?
        self.not_translated(o, 'ellipsis')

    def visit_yield_from_expr(self, o: 'mypy.nodes.YieldFromExpr') -> None:
        self.not_python2(o, 'yield from')

    def visit_star_expr(self, o: 'mypy.nodes.StarExpr') -> None:
        # mycpp/examples/invalid_python.py doesn't hit this?
        self.not_translated(o, 'star expr')

    def visit_super_expr(self, o: 'mypy.nodes.SuperExpr') -> None:
        self.not_translated(o, 'super expr')

    def visit_assignment_expr(self, o: 'mypy.nodes.AssignmentExpr') -> None:
        # I think this is a := b
        self.not_translated(o, 'assign expr')

    def visit_decorator(self, o: 'mypy.nodes.Decorator') -> None:
        self.not_translated(o, 'decorator')

    def visit_backquote_expr(self, o: 'mypy.nodes.BackquoteExpr') -> None:
        self.not_translated(o, 'backquote')

    def visit_namedtuple_expr(self, o: 'mypy.nodes.NamedTupleExpr') -> None:
        self.not_translated(o, 'namedtuple')

    def visit_enum_call_expr(self, o: 'mypy.nodes.EnumCallExpr') -> None:
        self.not_translated(o, 'enum')

    def visit_typeddict_expr(self, o: 'mypy.nodes.TypedDictExpr') -> None:
        self.not_translated(o, 'typed dict')

    def visit_newtype_expr(self, o: 'mypy.nodes.NewTypeExpr') -> None:
        self.not_translated(o, 'newtype')

    def visit__promote_expr(self, o: 'mypy.nodes.PromoteExpr') -> None:
        self.not_translated(o, 'promote')

    def visit_await_expr(self, o: 'mypy.nodes.AwaitExpr') -> None:
        self.not_translated(o, 'await')

    def visit_temp_node(self, o: 'mypy.nodes.TempNode') -> None:
        self.not_translated(o, 'temp')
