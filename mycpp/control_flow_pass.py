"""
control_flow_pass.py - AST pass that builds a control flow graph.
"""
import collections
from typing import overload, Union, Optional, Dict

import mypy
from mypy.nodes import (Block, Expression, Statement, ExpressionStmt, StrExpr,
                        CallExpr, FuncDef, IfStmt, NameExpr, MemberExpr,
                        IndexExpr, TupleExpr, IntExpr)

from mypy.types import CallableType, Instance, Type, UnionType, NoneTyp, TupleType

from mycpp.crash import catch_errors
from mycpp.util import join_name, split_py_name
from mycpp.visitor import SimpleVisitor, T
from mycpp import util
from mycpp.util import SymbolPath
from mycpp import pass_state

from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from mycpp import cppgen_pass


class UnsupportedException(Exception):
    pass


def GetObjectTypeName(t: Type) -> SymbolPath:
    if isinstance(t, Instance):
        return split_py_name(t.type.fullname)

    elif isinstance(t, UnionType):
        assert len(t.items) == 2
        if isinstance(t.items[0], NoneTyp):
            return GetObjectTypeName(t.items[1])

        return GetObjectTypeName(t.items[0])

    assert False, t


INVALID_ID = -99  # statement IDs are positive


class Build(SimpleVisitor):

    def __init__(self, types: Dict[Expression,
                                   Type], virtual: pass_state.Virtual,
                 local_vars: 'cppgen_pass.LocalVars',
                 dot_exprs: 'cppgen_pass.DotExprs') -> None:

        self.types = types
        self.cfgs: Dict[SymbolPath,
                        pass_state.ControlFlowGraph] = collections.defaultdict(
                            pass_state.ControlFlowGraph)
        self.current_statement_id = INVALID_ID
        self.current_class_name: Optional[SymbolPath] = None
        self.current_func_node: Optional[FuncDef] = None
        self.loop_stack: List[pass_state.CfgLoopContext] = []
        self.virtual = virtual
        self.local_vars = local_vars
        self.dot_exprs = dot_exprs
        self.heap_counter = 0
        # statement object -> SymbolPath of the callee
        self.callees: Dict[Statement, SymbolPath] = {}
        self.current_lval = None

    def current_cfg(self) -> pass_state.ControlFlowGraph:
        if not self.current_func_node:
            return None

        return self.cfgs[split_py_name(self.current_func_node.fullname)]

    def resolve_callee(self, o: CallExpr) -> Optional[util.SymbolPath]:
        """
        Returns the fully qualified name of the callee in the given call
        expression.

        Member functions are prefixed by the names of the classes that contain
        them. For example, the name of the callee in the last statement of the
        snippet below is `module.SomeObject.Foo`.

            x = module.SomeObject()
            x.Foo()

        Free-functions defined in the local module are referred to by their
        normal fully qualified names. The function `foo` in a module called
        `moduleA` would is named `moduleA.foo`. Calls to free-functions defined
        in imported modules are named the same way.
        """

        if isinstance(o.callee, NameExpr):
            return split_py_name(o.callee.fullname)

        elif isinstance(o.callee, MemberExpr):
            if isinstance(o.callee.expr, NameExpr):
                is_module = isinstance(self.dot_exprs.get(o.callee),
                                       pass_state.ModuleMember)
                if is_module:
                    return (split_py_name(o.callee.expr.fullname) +
                            (o.callee.name, ))

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
                            return (split_py_name(local_type) +
                                    (o.callee.name, ))

                        elif isinstance(local_type, Instance):
                            return (split_py_name(local_type.type.fullname) +
                                    (o.callee.name, ))

                        elif isinstance(local_type, UnionType):
                            assert len(local_type.items) == 2
                            return (split_py_name(
                                local_type.items[0].type.fullname) +
                                    (o.callee.expr.name, ))

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
                    return (split_py_name(t.items[0].type.fullname) +
                            (o.callee.name, ))

                elif o.callee.expr and getattr(o.callee.expr, 'fullname',
                                               None):
                    return (split_py_name(o.callee.expr.fullname) +
                            (o.callee.name, ))

                else:
                    # constructors of things that we don't care about.
                    return None

        # Don't currently get here
        raise AssertionError()

    def get_ref_name(self, expr: Expression) -> Optional[util.SymbolPath]:
        """
        To do dataflow analysis we need to track changes to objects, which
        requires naming them. This function returns the name of the object
        referred to by the given expression. If the expression doesn't refer to
        an object or variable it returns None.

        Objects are named slightly differently than they appear in the source
        code.

        Objects referenced by local variables are referred to by the name of the
        local. For example, the name of the object in both statements below is
        `x`.

            x = module.SomeObject()
            x = None

        Member expressions are named after the parent object's type. For
        example, the names of the objects in the member assignment statements
        below are both `module.SomeObject.member_a`. This makes it possible to
        track data flow across object members without having to track individual
        heap objects, which would increase the search space for analyses and
        slow things down.

            x = module.SomeObject()
            y = module.SomeObject()
            x.member_a = 'foo'
            y.member_a = 'bar'

        Index expressions are named after their bases, for the same reasons as
        member expressions. The coarse-grained precision should lead to an
        over-approximation of where objects are in use, but should not miss any
        references. This should be fine for our purposes. In the snippet below
        the last two assignments are named `x` and `module.SomeObject.a_list`.

            x = [None] # list[Thing]
            y = module.SomeObject()
            x[0] = Thing()
            y.a_list[1] = Blah()

        Index expressions over tuples are treated differently, though. Tuples
        have a fixed size, tend to be small, and their elements have distinct
        types. So, each element can be (and probably needs to be) individually
        named. In the snippet below, the name of the RHS in the second
        assignment is `t.0`.

            t = (1, 2, 3, 4)
            x = t[0]

        The examples above all deal with assignments, but these rules apply to
        any expression that uses an object or variable.
        """
        if isinstance(expr,
                      NameExpr) and expr.name not in {'True', 'False', 'None'}:
            return (expr.name, )

        elif isinstance(expr, MemberExpr):
            dot_expr = self.dot_exprs[expr]
            if isinstance(dot_expr, pass_state.ModuleMember):
                return dot_expr.module_path + (dot_expr.member, )

            elif isinstance(dot_expr, pass_state.HeapObjectMember):
                obj_name = self.get_ref_name(dot_expr.object_expr)
                if obj_name:
                    # XXX: add a new case like pass_state.ExpressionMember for
                    # cases when the LHS of . isn't a reference (e.g.
                    # builtin/assign_osh.py:54)
                    return obj_name + (dot_expr.member, )

            elif isinstance(dot_expr, pass_state.StackObjectMember):
                return self.get_ref_name(
                    dot_expr.object_expr) + (dot_expr.member, )

        elif isinstance(expr, IndexExpr):
            if isinstance(self.types[expr.base], TupleType):
                assert isinstance(expr.index, IntExpr)
                return self.get_ref_name(expr.base) + (str(expr.index.value), )

            return self.get_ref_name(expr.base)

        return None

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

    # Statements

    def visit_for_stmt(self, o: 'mypy.nodes.ForStmt') -> None:
        cfg = self.current_cfg()
        with pass_state.CfgLoopContext(
                cfg, entry=self.current_statement_id) as loop:
            self.accept(o.expr)
            self.loop_stack.append(loop)
            self.accept(o.body)
            self.loop_stack.pop()

    def _handle_switch(self, expr, o, cfg) -> None:
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

    def visit_with_stmt(self, o: 'mypy.nodes.WithStmt') -> None:
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

    def visit_func_def(self, o: 'mypy.nodes.FuncDef') -> None:
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
        cfg = self.current_cfg()
        for arg in o.arguments:
            cfg.AddFact(0,
                        pass_state.Definition((arg.variable.name, ), '$Empty'))

        self.accept(o.body)
        self.current_func_node = None
        self.current_statement_id = INVALID_ID

    def visit_class_def(self, o: 'mypy.nodes.ClassDef') -> None:
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

    def visit_while_stmt(self, o: 'mypy.nodes.WhileStmt') -> None:
        cfg = self.current_cfg()
        with pass_state.CfgLoopContext(
                cfg, entry=self.current_statement_id) as loop:
            self.accept(o.expr)
            self.loop_stack.append(loop)
            self.accept(o.body)
            self.loop_stack.pop()

    def visit_return_stmt(self, o: 'mypy.nodes.ReturnStmt') -> None:
        cfg = self.current_cfg()
        if cfg:
            cfg.AddDeadend(self.current_statement_id)

        if o.expr:
            self.accept(o.expr)

    def visit_if_stmt(self, o: 'mypy.nodes.IfStmt') -> None:
        cfg = self.current_cfg()

        if util.ShouldVisitIfExpr(o):
            for expr in o.expr:
                self.accept(expr)

        with pass_state.CfgBranchContext(
                cfg, self.current_statement_id) as branch_ctx:
            if util.ShouldVisitIfBody(o):
                with branch_ctx.AddBranch():
                    for node in o.body:
                        self.accept(node)

            if util.ShouldVisitElseBody(o):
                with branch_ctx.AddBranch():
                    self.accept(o.else_body)

    def visit_break_stmt(self, o: 'mypy.nodes.BreakStmt') -> None:
        if len(self.loop_stack):
            self.loop_stack[-1].AddBreak(self.current_statement_id)

    def visit_continue_stmt(self, o: 'mypy.nodes.ContinueStmt') -> None:
        if len(self.loop_stack):
            self.loop_stack[-1].AddContinue(self.current_statement_id)

    def visit_raise_stmt(self, o: 'mypy.nodes.RaiseStmt') -> None:
        cfg = self.current_cfg()
        if cfg:
            cfg.AddDeadend(self.current_statement_id)

        if o.expr:
            self.accept(o.expr)

    def visit_try_stmt(self, o: 'mypy.nodes.TryStmt') -> None:
        cfg = self.current_cfg()
        with pass_state.CfgBranchContext(cfg,
                                         self.current_statement_id) as try_ctx:
            with try_ctx.AddBranch() as try_block:
                self.accept(o.body)

            for t, v, handler in zip(o.types, o.vars, o.handlers):
                with try_ctx.AddBranch(try_block.exit):
                    self.accept(handler)

    def visit_assignment_stmt(self, o: 'mypy.nodes.AssignmentStmt') -> None:
        cfg = self.current_cfg()
        if cfg:
            assert len(o.lvalues) == 1
            lval = o.lvalues[0]
            lval_names = []
            if isinstance(lval, TupleExpr):
                lval_names.extend(
                    [self.get_ref_name(item) for item in lval.items])

            else:
                lval_names.append(self.get_ref_name(lval))

            assert lval_names, o

            rval_type = self.types[o.rvalue]
            rval_names = []
            if isinstance(o.rvalue, CallExpr):
                # The RHS is either an object constructor or something that
                # returns a primitive type (e.g. Tuple[int, int] or str).
                # XXX: When we add inter-procedural analysis we should treat
                # these not as definitions but as some new kind of assignment.
                rval_names = [None for _ in lval_names]

            elif isinstance(o.rvalue, TupleExpr) and len(lval_names) == 1:
                # We're constructing a tuple. Since tuples have have a fixed
                # (and usually small) size, we can name each of the
                # elements.
                base = lval_names[0]
                lval_names = [
                    base + (str(i), ) for i in range(len(o.rvalue.items))
                ]
                rval_names = [
                    self.get_ref_name(item) for item in o.rvalue.items
                ]

            elif isinstance(rval_type, TupleType):
                # We're unpacking a tuple. Like the tuple construction case,
                # give each element a name.
                rval_name = self.get_ref_name(o.rvalue)
                assert rval_name, o.rvalue
                rval_names = [
                    rval_name + (str(i), ) for i in range(len(lval_names))
                ]

            else:
                rval_names = [self.get_ref_name(o.rvalue)]

            assert len(rval_names) == len(lval_names)

            for lhs, rhs in zip(lval_names, rval_names):
                assert lhs, lval
                if rhs:
                    # In this case rhe RHS is another variable. Record the
                    # assignment so we can keep track of aliases.
                    cfg.AddFact(self.current_statement_id,
                                pass_state.Assignment(lhs, rhs))
                else:
                    # In this case the RHS is either some kind of literal (e.g.
                    # [] or 'foo') or a call to an object constructor. Mark this
                    # statement as an (re-)definition of a variable.
                    cfg.AddFact(
                        self.current_statement_id,
                        pass_state.Definition(
                            lhs, '$HeapObject(h{})'.format(self.heap_counter)),
                    )
                    self.heap_counter += 1

        for lval in o.lvalues:
            self.current_lval = lval
            self.accept(lval)
            self.current_lval = None

        self.accept(o.rvalue)

    # Expressions

    def visit_member_expr(self, o: 'mypy.nodes.MemberExpr') -> None:
        self.accept(o.expr)
        cfg = self.current_cfg()
        if (cfg and
                not isinstance(self.dot_exprs[o], pass_state.ModuleMember) and
                o != self.current_lval):
            ref = self.get_ref_name(o)
            if ref:
                cfg.AddFact(self.current_statement_id, pass_state.Use(ref))

    def visit_name_expr(self, o: 'mypy.nodes.NameExpr') -> None:
        cfg = self.current_cfg()
        if cfg and o != self.current_lval:
            is_local = False
            for name, t in self.local_vars.get(self.current_func_node, []):
                if name == o.name:
                    is_local = True
                    break

            ref = self.get_ref_name(o)
            if ref and is_local:
                cfg.AddFact(self.current_statement_id, pass_state.Use(ref))

    def visit_call_expr(self, o: 'mypy.nodes.CallExpr') -> None:
        cfg = self.current_cfg()
        if self.current_func_node:
            full_callee = self.resolve_callee(o)
            if full_callee:
                self.callees[o] = full_callee
                cfg.AddFact(
                    self.current_statement_id,
                    pass_state.FunctionCall(join_name(full_callee, delim='.')))

                for i, arg in enumerate(o.args):
                    arg_ref = self.get_ref_name(arg)
                    if arg_ref:
                        cfg.AddFact(self.current_statement_id,
                                    pass_state.Bind(arg_ref, full_callee, i))

        self.accept(o.callee)
        for arg in o.args:
            self.accept(arg)
