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
                    # Most statements have empty visitors because they don't
                    # require any special logic. Create statements for them
                    # here. Blocks and loops are handled by their visitors.
                    if (cfg and not isinstance(node, Block) and
                            not isinstance(node, ForStmt) and
                            not isinstance(node, WhileStmt)):
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
        with pass_state.CfgBranchContext(
                cfg, self.current_statement_id) as branch_ctx:
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

    def visit_func_def(self, o: 'mypy.nodes.FuncDef') -> T:
        if o.name == '__repr__':  # Don't translate
            return

        self.cfgs[split_py_name(o.fullname)] = pass_state.ControlFlowGraph()
        self.current_func_node = o
        self.accept(o.body)
        self.current_func_node = None

    def visit_class_def(self, o: 'mypy.nodes.ClassDef') -> T:
        for stmt in o.defs.body:
            # Ignore things that look like docstrings
            if (isinstance(stmt, ExpressionStmt) and
                    isinstance(stmt.expr, StrExpr)):
                continue

            if isinstance(stmt, FuncDef) and stmt.name == '__repr__':
                continue

            self.accept(stmt)

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

    def visit_if_stmt(self, o: 'mypy.nodes.IfStmt') -> T:
        cfg = self.current_cfg()
        if not cfg:
            return

        with pass_state.CfgBranchContext(
                cfg, self.current_statement_id) as branch_ctx:
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

    def visit_raise_stmt(self, o: 'mypy.nodes.RaiseStmt') -> T:
        cfg = self.current_cfg()
        if cfg:
            cfg.AddDeadend(self.current_statement_id)

    def visit_try_stmt(self, o: 'mypy.nodes.TryStmt') -> T:
        cfg = self.current_cfg()
        if not cfg:
            return

        with pass_state.CfgBranchContext(cfg,
                                         self.current_statement_id) as try_ctx:
            with try_ctx.AddBranch() as try_block:
                self.accept(o.body)

            for t, v, handler in zip(o.types, o.vars, o.handlers):
                with try_ctx.AddBranch(try_block.exit):
                    self.accept(handler)
