"""
control_flow_pass.py - AST pass that builds a control flow graph.
"""
import collections
from typing import overload, Union, Optional, Dict

import mypy
from mypy.visitor import ExpressionVisitor, StatementVisitor
from mypy.nodes import (Block, Expression, Statement, ExpressionStmt, StrExpr,
                        CallExpr, FuncDef, IfStmt, NameExpr, MemberExpr)

from mypy.types import CallableType, Instance, Type, UnionType

from mycpp.crash import catch_errors
from mycpp.util import join_name, split_py_name
from mycpp import util
from mycpp import pass_state

T = None  # TODO: Make it type check?


class UnsupportedException(Exception):
    pass


class Build(ExpressionVisitor[T], StatementVisitor[None]):

    def __init__(self, types: Dict[Expression, Type], virtual, local_vars, imported_names):

        self.types = types
        self.cfgs = collections.defaultdict(pass_state.ControlFlowGraph)
        self.current_statement_id = None
        self.current_class_name = None
        self.current_func_node = None
        self.loop_stack = []
        self.virtual = virtual
        self.local_vars = local_vars
        self.imported_names = imported_names

    def current_cfg(self):
        if not self.current_func_node:
            return None

        return self.cfgs[split_py_name(self.current_func_node.fullname)]

    def resolve_callee(self, o: CallExpr) -> Optional[util.SymbolPath]:

        if isinstance(o.callee, NameExpr):
            return split_py_name(o.callee.fullname)

        elif isinstance(o.callee, MemberExpr):
            if isinstance(o.callee.expr, NameExpr):
                is_module = (isinstance(o.callee.expr, NameExpr) and
                             o.callee.expr.name in self.imported_names)
                if is_module:
                    return split_py_name(
                        o.callee.expr.fullname) + (o.callee.name, )

                elif o.callee.expr.name == 'self':
                    assert self.current_class_name
                    return self.current_class_name + (o.callee.name, )

                else:
                    local_type = None
                    for name, t in self.local_vars.get(self.current_func_node,
                                                       []):
                        if name == o.callee.expr.name:
                            local_type = t
                            break

                    if local_type:
                        if isinstance(local_type, str):
                            return split_py_name(local_type) + (
                                o.callee.name, )

                        elif isinstance(local_type, Instance):
                            return split_py_name(
                                local_type.type.fullname) + (o.callee.name, )

                        elif isinstance(local_type, UnionType):
                            assert len(local_type.items) == 2
                            return split_py_name(
                                local_type.items[0].type.fullname) + (
                                    o.callee.expr.name, )

                        else:
                            assert not isinstance(local_type, CallableType)
                            # primitive type or string. don't care.
                            return None

                    else:
                        # context or exception handler. probably safe to ignore.
                        return None

            else:
                t = self.types.get(o.callee.expr)
                if isinstance(t, Instance):
                    return split_py_name(t.type.fullname) + (o.callee.name, )

                elif isinstance(t, UnionType):
                    assert len(t.items) == 2
                    return split_py_name(
                        t.items[0].type.fullname) + (o.callee.name, )

                elif o.callee.expr and getattr(o.callee.expr, 'fullname',
                                               None):
                    return split_py_name(
                        o.callee.expr.fullname) + (o.callee.name, )

                else:
                    # constructors of things that we don't care about.
                    return None

        # Don't currently get here
        raise AssertionError()

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
                    # here. Don't create statements from blocks to avoid
                    # stuttering.
                    if cfg and not isinstance(node, Block):
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
        with pass_state.CfgLoopContext(
                cfg, entry=self.current_statement_id) as loop:
            self.accept(o.expr)
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
                self.accept(expr)
                assert expr is not None, expr
                with branch_ctx.AddBranch():
                    self.accept(body)

            if default_block:
                with branch_ctx.AddBranch():
                    self.accept(default_block)

    def visit_with_stmt(self, o: 'mypy.nodes.WithStmt') -> T:
        cfg = self.current_cfg()
        assert len(o.expr) == 1, o.expr
        expr = o.expr[0]
        assert isinstance(expr, CallExpr), expr
        self.accept(expr)

        callee_name = expr.callee.name
        if callee_name == 'switch':
            self._handle_switch(expr, o, cfg)
        elif callee_name == 'str_switch':
            self._handle_switch(expr, o, cfg)
        elif callee_name == 'tagswitch':
            self._handle_switch(expr, o, cfg)
        else:
            with pass_state.CfgBlockContext(cfg, self.current_statement_id):
                self.accept(o.body)

    def visit_func_def(self, o: 'mypy.nodes.FuncDef') -> T:
        if o.name == '__repr__':  # Don't translate
            return

        # For virtual methods, pretend that the method on the base class calls
        # the same method on every subclass. This way call sites using the
        # abstract base class will over-approximate the set of call paths they
        # can take when checking if they can reach MaybeCollect().
        if self.current_class_name and self.virtual.IsVirtual(
                self.current_class_name, o.name):
            key = (self.current_class_name, o.name)
            base = self.virtual.virtuals[key]
            if base:
                sub = join_name(self.current_class_name + (o.name, ),
                                delim='.')
                base_key = base[0] + (base[1], )
                cfg = self.cfgs[base_key]
                cfg.AddFact(0, pass_state.FunctionCall(sub))

        self.current_func_node = o
        self.accept(o.body)
        self.current_func_node = None
        self.current_statement_id = None

    def visit_class_def(self, o: 'mypy.nodes.ClassDef') -> T:
        self.current_class_name = split_py_name(o.fullname)
        for stmt in o.defs.body:
            # Ignore things that look like docstrings
            if (isinstance(stmt, ExpressionStmt) and
                    isinstance(stmt.expr, StrExpr)):
                continue

            if isinstance(stmt, FuncDef) and stmt.name == '__repr__':
                continue

            self.accept(stmt)

        self.current_class_name = None

    # Statements

    def visit_assignment_stmt(self, o: 'mypy.nodes.AssignmentStmt') -> T:
        for lval in o.lvalues:
            self.accept(lval)

        self.accept(o.rvalue)

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
        with pass_state.CfgLoopContext(
                cfg, entry=self.current_statement_id) as loop:
            self.accept(o.expr)
            self.loop_stack.append(loop)
            self.accept(o.body)
            self.loop_stack.pop()

    def visit_return_stmt(self, o: 'mypy.nodes.ReturnStmt') -> T:
        cfg = self.current_cfg()
        if cfg:
            cfg.AddDeadend(self.current_statement_id)

        if o.expr:
            self.accept(o.expr)

    def visit_if_stmt(self, o: 'mypy.nodes.IfStmt') -> T:
        cfg = self.current_cfg()
        for expr in o.expr:
            self.accept(expr)

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

        if o.expr:
            self.accept(o.expr)

    def visit_try_stmt(self, o: 'mypy.nodes.TryStmt') -> T:
        cfg = self.current_cfg()
        with pass_state.CfgBranchContext(cfg,
                                         self.current_statement_id) as try_ctx:
            with try_ctx.AddBranch() as try_block:
                self.accept(o.body)

            for t, v, handler in zip(o.types, o.vars, o.handlers):
                with try_ctx.AddBranch(try_block.exit):
                    self.accept(handler)

    def visit_del_stmt(self, o: 'mypy.nodes.DelStmt') -> T:
        self.accept(o.expr)

    # Expressions

    def visit_member_expr(self, o: 'mypy.nodes.MemberExpr') -> T:
        self.accept(o.expr)

    def visit_yield_expr(self, o: 'mypy.nodes.YieldExpr') -> T:
        self.accept(o.expr)

    def visit_op_expr(self, o: 'mypy.nodes.OpExpr') -> T:
        self.accept(o.left)
        self.accept(o.right)

    def visit_comparison_expr(self, o: 'mypy.nodes.ComparisonExpr') -> T:
        for operand in o.operands:
            self.accept(operand)

    def visit_unary_expr(self, o: 'mypy.nodes.UnaryExpr') -> T:
        self.accept(o.expr)

    def visit_list_expr(self, o: 'mypy.nodes.ListExpr') -> T:
        if o.items:
            for item in o.items:
                self.accept(item)

    def visit_dict_expr(self, o: 'mypy.nodes.DictExpr') -> T:
        if o.items:
            for k, v in o.items:
                self.accept(k)
                self.accept(v)

    def visit_tuple_expr(self, o: 'mypy.nodes.TupleExpr') -> T:
        if o.items:
            for item in o.items:
                self.accept(item)

    def visit_index_expr(self, o: 'mypy.nodes.IndexExpr') -> T:
        self.accept(o.base)

    def visit_slice_expr(self, o: 'mypy.nodes.SliceExpr') -> T:
        if o.begin_index:
            self.accept(o.begin_index)

        if o.end_index:
            self.accept(o.end_index)

        if o.stride:
            self.accept(o.stride)

    def visit_conditional_expr(self, o: 'mypy.nodes.ConditionalExpr') -> T:
        self.accept(o.cond)
        self.accept(o.if_expr)
        self.accept(o.else_expr)

    def visit_call_expr(self, o: 'mypy.nodes.CallExpr') -> T:
        cfg = self.current_cfg()
        if self.current_func_node:
            full_callee = self.resolve_callee(o)
            if full_callee:
                cfg.AddFact(
                    self.current_statement_id,
                    pass_state.FunctionCall(join_name(full_callee, delim='.')))

        self.accept(o.callee)
        for arg in o.args:
            self.accept(arg)
