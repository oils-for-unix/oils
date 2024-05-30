"""
control_flow_pass.py - AST pass that builds a control flow graph.
"""
from typing import overload, Union, Optional, Dict

import mypy
from mypy.visitor import ExpressionVisitor, StatementVisitor
from mypy.nodes import (Block, Expression, Statement, ExpressionStmt, StrExpr,
                        ForStmt, WhileStmt, CallExpr, FuncDef, IfStmt)

from mypy.types import Type

from mycpp.crash import catch_errors
from mycpp.util import split_py_name
from mycpp import util
from mycpp import pass_state

T = None  # TODO: Make it type check?


class UnsupportedException(Exception):
    pass


class Build(ExpressionVisitor[T], StatementVisitor[None]):

    def __init__(self, types: Dict[Expression, Type]):

        self.types = types
        self.cfgs = {}
        self.current_statement_id = None
        self.current_func_node = None
        self.loop_stack = []

    def current_cfg(self):
        if not self.current_func_node:
            return None

        return self.cfgs.get(split_py_name(self.current_func_node.fullname))

    #
    # COPIED from IRBuilder
    #

    @overload
    def accept(self, node: Expression) -> T:
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
                    cfg = self.current_cfg()
                    if cfg and not isinstance(node, Block) and not isinstance(node, ForStmt) and not isinstance(node, WhileStmt):
                        self.current_statement_id = cfg.AddStatement()

                    node.accept(self)
                except UnsupportedException:
                    pass
                return None

    # Not in superclasses:

    def visit_mypy_file(self, o: 'mypy.nodes.MypyFile') -> T:
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

    def visit_int_expr(self, o: 'mypy.nodes.IntExpr') -> T:
        pass

    def visit_str_expr(self, o: 'mypy.nodes.StrExpr') -> T:
        pass

    def visit_bytes_expr(self, o: 'mypy.nodes.BytesExpr') -> T:
        pass

    def visit_unicode_expr(self, o: 'mypy.nodes.UnicodeExpr') -> T:
        pass

    def visit_float_expr(self, o: 'mypy.nodes.FloatExpr') -> T:
        pass

    def visit_complex_expr(self, o: 'mypy.nodes.ComplexExpr') -> T:
        pass

    # Expression

    def visit_ellipsis(self, o: 'mypy.nodes.EllipsisExpr') -> T:
        pass

    def visit_star_expr(self, o: 'mypy.nodes.StarExpr') -> T:
        pass

    def visit_name_expr(self, o: 'mypy.nodes.NameExpr') -> T:
        pass

    def visit_member_expr(self, o: 'mypy.nodes.MemberExpr') -> T:
        pass

    def visit_yield_from_expr(self, o: 'mypy.nodes.YieldFromExpr') -> T:
        pass

    def visit_yield_expr(self, o: 'mypy.nodes.YieldExpr') -> T:
        pass

    def visit_call_expr(self, o: 'mypy.nodes.CallExpr') -> T:
        pass

    def visit_op_expr(self, o: 'mypy.nodes.OpExpr') -> T:
        pass

    def visit_comparison_expr(self, o: 'mypy.nodes.ComparisonExpr') -> T:
        pass

    def visit_cast_expr(self, o: 'mypy.nodes.CastExpr') -> T:
        pass

    def visit_reveal_expr(self, o: 'mypy.nodes.RevealExpr') -> T:
        pass

    def visit_super_expr(self, o: 'mypy.nodes.SuperExpr') -> T:
        pass

    def visit_assignment_expr(self, o: 'mypy.nodes.AssignmentExpr') -> T:
        pass

    def visit_unary_expr(self, o: 'mypy.nodes.UnaryExpr') -> T:
        pass

    def visit_list_expr(self, o: 'mypy.nodes.ListExpr') -> T:
        pass

    def visit_dict_expr(self, o: 'mypy.nodes.DictExpr') -> T:
        pass

    def visit_tuple_expr(self, o: 'mypy.nodes.TupleExpr') -> T:
        pass

    def visit_set_expr(self, o: 'mypy.nodes.SetExpr') -> T:
        pass

    def visit_index_expr(self, o: 'mypy.nodes.IndexExpr') -> T:
        pass

    def visit_type_application(self, o: 'mypy.nodes.TypeApplication') -> T:
        pass

    def visit_lambda_expr(self, o: 'mypy.nodes.LambdaExpr') -> T:
        pass

    def visit_list_comprehension(self, o: 'mypy.nodes.ListComprehension') -> T:
        pass

    def visit_set_comprehension(self, o: 'mypy.nodes.SetComprehension') -> T:
        pass

    def visit_dictionary_comprehension(
            self, o: 'mypy.nodes.DictionaryComprehension') -> T:
        pass

    def visit_generator_expr(self, o: 'mypy.nodes.GeneratorExpr') -> T:
        pass

    def visit_slice_expr(self, o: 'mypy.nodes.SliceExpr') -> T:
        pass

    def visit_conditional_expr(self, o: 'mypy.nodes.ConditionalExpr') -> T:
        pass

    def visit_backquote_expr(self, o: 'mypy.nodes.BackquoteExpr') -> T:
        pass

    def visit_type_var_expr(self, o: 'mypy.nodes.TypeVarExpr') -> T:
        pass

    def visit_type_alias_expr(self, o: 'mypy.nodes.TypeAliasExpr') -> T:
        pass

    def visit_namedtuple_expr(self, o: 'mypy.nodes.NamedTupleExpr') -> T:
        pass

    def visit_enum_call_expr(self, o: 'mypy.nodes.EnumCallExpr') -> T:
        pass

    def visit_typeddict_expr(self, o: 'mypy.nodes.TypedDictExpr') -> T:
        pass

    def visit_newtype_expr(self, o: 'mypy.nodes.NewTypeExpr') -> T:
        pass

    def visit__promote_expr(self, o: 'mypy.nodes.PromoteExpr') -> T:
        pass

    def visit_await_expr(self, o: 'mypy.nodes.AwaitExpr') -> T:
        pass

    def visit_temp_node(self, o: 'mypy.nodes.TempNode') -> T:
        pass

    def visit_assignment_stmt(self, o: 'mypy.nodes.AssignmentStmt') -> T:
        pass

    def visit_for_stmt(self, o: 'mypy.nodes.ForStmt') -> T:
        cfg = self.current_cfg()
        if not cfg:
            return

        with pass_state.CfgLoopContext(cfg) as loop:
            self.loop_stack.append(loop)
            self.accept(o.body)
            self.loop_stack.pop()

    def _handle_switch(self, expr, o, cfg):
        assert len(o.body.body) == 1, o.body.body
        if_node = o.body.body[0]
        assert isinstance(if_node, IfStmt), if_node
        cases = []
        default_block = util._collect_cases(self.module_path, if_node, cases)
        with pass_state.CfgBranchContext(cfg, self.current_statement_id) as branch_ctx:
            for expr, body in cases:
                assert expr is not None, expr
                with branch_ctx.AddBranch():
                    self.accept(body)

            if default_block:
                with branch_ctx.AddBranch():
                    self.accept(default_block)

    def visit_with_stmt(self, o: 'mypy.nodes.WithStmt') -> T:
        cfg = self.current_cfg()
        if not cfg:
            return

        assert len(o.expr) == 1, o.expr
        expr = o.expr[0]
        assert isinstance(expr, CallExpr), expr

        callee_name = expr.callee.name
        if callee_name == 'switch':
            self._handle_switch(expr, o, cfg)
        elif callee_name == 'str_switch':
            self._handle_switch(expr, o, cfg)
        elif callee_name == 'tagswitch':
            self._handle_switch(expr, o, cfg)
        else:
            with pass_state.CfgBlockContext(cfg, self.current_statement_id):
                for stmt in o.body.body:
                    self.accept(stmt)

    def visit_del_stmt(self, o: 'mypy.nodes.DelStmt') -> T:
        pass

    def visit_func_def(self, o: 'mypy.nodes.FuncDef') -> T:
        if o.name == '__repr__':  # Don't translate
            return

        self.cfgs[split_py_name(o.fullname)] = pass_state.ControlFlowGraph()
        self.current_func_node = o
        self.accept(o.body)
        self.current_func_node = None

    def visit_overloaded_func_def(self,
                                  o: 'mypy.nodes.OverloadedFuncDef') -> T:
        pass

    def visit_class_def(self, o: 'mypy.nodes.ClassDef') -> T:
        for stmt in o.defs.body:
            # Ignore things that look like docstrings
            if (isinstance(stmt, ExpressionStmt) and
                    isinstance(stmt.expr, StrExpr)):
                continue

            if isinstance(stmt, FuncDef) and stmt.name == '__repr__':
                continue

            self.accept(stmt)

    def visit_global_decl(self, o: 'mypy.nodes.GlobalDecl') -> T:
        pass

    def visit_nonlocal_decl(self, o: 'mypy.nodes.NonlocalDecl') -> T:
        pass

    def visit_decorator(self, o: 'mypy.nodes.Decorator') -> T:
        pass

    def visit_var(self, o: 'mypy.nodes.Var') -> T:
        pass

    # Module structure

    def visit_import(self, o: 'mypy.nodes.Import') -> T:
        pass

    def visit_import_from(self, o: 'mypy.nodes.ImportFrom') -> T:
        pass

    def visit_import_all(self, o: 'mypy.nodes.ImportAll') -> T:
        pass

    # Statements

    def visit_block(self, block: 'mypy.nodes.Block') -> T:
        for stmt in block.body:
            # Ignore things that look like docstrings
            if (isinstance(stmt, ExpressionStmt) and
                    isinstance(stmt.expr, StrExpr)):
                continue

            self.accept(stmt)

    def visit_expression_stmt(self, o: 'mypy.nodes.ExpressionStmt') -> T:
        self.accept(o.expr)

    def visit_operator_assignment_stmt(
            self, o: 'mypy.nodes.OperatorAssignmentStmt') -> T:
        pass

    def visit_while_stmt(self, o: 'mypy.nodes.WhileStmt') -> T:
        cfg = self.current_cfg()
        if not cfg:
            return

        with pass_state.CfgLoopContext(cfg) as loop:
            self.loop_stack.append(loop)
            self.accept(o.body)
            self.loop_stack.pop()

    def visit_return_stmt(self, o: 'mypy.nodes.ReturnStmt') -> T:
        cfg = self.current_cfg()
        if cfg:
            cfg.AddDeadend(self.current_statement_id)

    def visit_assert_stmt(self, o: 'mypy.nodes.AssertStmt') -> T:
        pass

    def visit_if_stmt(self, o: 'mypy.nodes.IfStmt') -> T:
        cfg = self.current_cfg()
        if not cfg:
            return

        with pass_state.CfgBranchContext(cfg, self.current_statement_id) as branch_ctx:
            with branch_ctx.AddBranch():
                for node in o.body:
                    self.accept(node)

            if o.else_body:
                with branch_ctx.AddBranch():
                    self.accept(o.else_body)

    def visit_break_stmt(self, o: 'mypy.nodes.BreakStmt') -> T:
        if len(self.loop_stack):
            self.loop_stack[-1].AddBreak(self.current_statement_id)

    def visit_continue_stmt(self, o: 'mypy.nodes.ContinueStmt') -> T:
        if len(self.loop_stack):
            self.loop_stack[-1].AddContinue(self.current_statement_id)

    def visit_pass_stmt(self, o: 'mypy.nodes.PassStmt') -> T:
        pass

    def visit_raise_stmt(self, o: 'mypy.nodes.RaiseStmt') -> T:
        cfg = self.current_cfg()
        if cfg:
            cfg.AddDeadend(self.current_statement_id)

    def visit_try_stmt(self, o: 'mypy.nodes.TryStmt') -> T:
        cfg = self.current_cfg()
        if not cfg:
            return

        with pass_state.CfgBranchContext(cfg, self.current_statement_id) as try_ctx:
            with try_ctx.AddBranch() as try_block:
                self.accept(o.body)

            for t, v, handler in zip(o.types, o.vars, o.handlers):
                with try_ctx.AddBranch(try_block.exit):
                    self.accept(handler)

    def visit_print_stmt(self, o: 'mypy.nodes.PrintStmt') -> T:
        pass

    def visit_exec_stmt(self, o: 'mypy.nodes.ExecStmt') -> T:
        pass
