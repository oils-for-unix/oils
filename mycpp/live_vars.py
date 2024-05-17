"""
const_pass.py - AST pass that collects constants.

Immutable string constants like 'StrFromC("foo")' are moved to the top level of
the generated C++ program for efficiency.
"""
from typing import overload, Union, Optional, Dict, List

import mypy
from mypy.visitor import ExpressionVisitor, StatementVisitor
from mypy.nodes import (Expression, Statement, ExpressionStmt, StrExpr,
                        ComparisonExpr, NameExpr, MemberExpr, CallExpr)

from mypy.types import Type

from mycpp.crash import catch_errors
from mycpp.util import log
from mycpp import pass_state

T = None  # TODO: Make it type check?

IGNORE_NAMES = set({'self'})

class UnsupportedException(Exception):
    pass


def _StripMycpp(name):
    """
    Strip the prefix 'mycpp.' from a fully resolved class, module, or function name.
    This makes names compatible with the examples that use testpkg.
    """
    if name.startswith('mycpp.'):
        return name[6:]

    return name


class Collect(ExpressionVisitor[T], StatementVisitor[None]):

    def __init__(self, types: Dict[Expression, Type],
                 callee_map: Dict[CallExpr, str],
                 call_graph: pass_state.CallGraph,
                 live_vars: pass_state.LiveVars):

        self.types = types
        self.unique_id = 0

        self.indent = 0

        self.live_vars = live_vars
        self.call_graph = call_graph
        self.callee_map = callee_map

        self.imported_names = set()  # MemberExpr -> module::Foo() or self->foo
        self.module_aliases: Dict[str, str] = {}

        self.current_class_name = None
        self.current_func_name = None

        self.statement_id = -1
        self.loop_stack: List[int] = None
        self.locals = {}

        self.vars = None
        self.current_rval = None
        self.current_call = None
        self.current_loop = None

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
                if self.current_func_name:
                    prev = self.statement_id
                    self.statement_id += 1
                    self.live_vars.EmitEdge(
                        self.current_func_name,
                        prev,
                        self.statement_id
                    )

                try:
                    node.accept(self)
                except UnsupportedException:
                    pass
                return None

    def log(self, msg, *args):
        if 0:  # quiet
            ind_str = self.indent * '  '
            log(ind_str + msg, *args)

    def push_loop(self):
        assert self.loop_stack is not None
        self.loop_stack.append(self.statement_id)

    def pop_loop(self):
        assert self.loop_stack is not None
        loop_entrance = self.loop_stack.pop()
        self.live_vars.EmitEdge(
            self.current_func_name,
            self.statement_id,
            loop_entrance
        )

    def add_var_def(self, name):
        if self.statement_id == -1 or name in IGNORE_NAMES:
            return

        self.live_vars.EmitDef(self.current_func_name, self.statement_id, name)

    def add_var_use(self, name):
        if self.statement_id == -1 or name not in self.locals:
            return

        self.live_vars.EmitUse(self.current_func_name, self.statement_id, name)

    def add_collect_call(self):
        if self.statement_id == -1:
            return

        self.live_vars.EmitCollect(self.current_func_name, self.statement_id)

    def resolve_callee(self, o: CallExpr) -> Optional[str]:
        return self.callee_map.get(o)

    # Not in superclasses:

    def visit_mypy_file(self, o: 'mypy.nodes.MypyFile') -> T:
        # Skip some stdlib stuff.  A lot of it is brought in by 'import
        # typing'.
        self.full_module_name = o.fullname
        if o.fullname in ('__future__', 'sys', 'types', 'typing', 'abc',
                          '_ast', 'ast', '_weakrefset', 'collections',
                          'cStringIO', 're', 'builtins'):

            # These module are special; their contents are currently all
            # built-in primitives.
            return

        self.module_path = o.path

        self.indent += 1
        for node in o.defs:
            # skip module docstring
            if isinstance(node, ExpressionStmt) and isinstance(
                    node.expr, StrExpr):
                continue
            self.accept(node)
        self.indent -= 1

    # LITERALS

    def visit_int_expr(self, o: 'mypy.nodes.IntExpr') -> T:
        self.log('IntExpr %d', o.value)

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
        #self.log('NameExpr %s', o.name)
        if self.vars is not None:
            self.vars.append(o.name)

        if self.current_rval or self.current_call:
            self.add_var_use(o.name)

    def visit_member_expr(self, o: 'mypy.nodes.MemberExpr') -> T:
        if o.expr:
            self.accept(o.expr)

    def visit_yield_from_expr(self, o: 'mypy.nodes.YieldFromExpr') -> T:
        pass

    def visit_yield_expr(self, o: 'mypy.nodes.YieldExpr') -> T:
        pass

    def visit_call_expr(self, o: 'mypy.nodes.CallExpr') -> T:
        self.log('CallExpr')
        full_callee = self.resolve_callee(o)
        self.current_call = o
        self.accept(o.callee)  # could be f() or obj.method()

        if self.call_graph.PathExists(full_callee, 'mylib.MaybeCollect'):
            self.add_collect_call()

        self.indent += 1
        for arg in o.args:
            self.accept(arg)
            # The type of each argument
            #self.log(':: %s', self.types[arg])

        self.current_call = None
        self.indent -= 1
        #self.log(  'args %s', o.args)

        #self.log('  arg_kinds %s', o.arg_kinds)
        #self.log('  arg_names %s', o.arg_names)

    def visit_op_expr(self, o: 'mypy.nodes.OpExpr') -> T:
        self.log('OpExpr')
        self.indent += 1
        self.accept(o.left)
        self.accept(o.right)
        self.indent -= 1

    def visit_comparison_expr(self, o: 'mypy.nodes.ComparisonExpr') -> T:
        self.log('ComparisonExpr')
        self.log('  operators %s', o.operators)
        self.indent += 1

        for operand in o.operands:
            self.indent += 1
            self.accept(operand)
            self.indent -= 1

        self.indent -= 1

    def visit_cast_expr(self, o: 'mypy.nodes.CastExpr') -> T:
        pass

    def visit_reveal_expr(self, o: 'mypy.nodes.RevealExpr') -> T:
        pass

    def visit_super_expr(self, o: 'mypy.nodes.SuperExpr') -> T:
        pass

    def visit_assignment_expr(self, o: 'mypy.nodes.AssignmentExpr') -> T:
        pass

    def visit_unary_expr(self, o: 'mypy.nodes.UnaryExpr') -> T:
        # e.g. a[-1] or 'not x'
        self.accept(o.expr)

    def visit_list_expr(self, o: 'mypy.nodes.ListExpr') -> T:
        # lists are MUTABLE, so we can't generate constants at the top level

        # but we want to visit the string literals!
        for item in o.items:
            self.accept(item)

    def visit_dict_expr(self, o: 'mypy.nodes.DictExpr') -> T:
        for k, v in o.items:
            self.accept(k)
            self.accept(v)

    def visit_tuple_expr(self, o: 'mypy.nodes.TupleExpr') -> T:
        for item in o.items:
            self.accept(item)

    def visit_set_expr(self, o: 'mypy.nodes.SetExpr') -> T:
        pass

    def visit_index_expr(self, o: 'mypy.nodes.IndexExpr') -> T:
        self.accept(o.base)
        self.accept(o.index)

    def visit_type_application(self, o: 'mypy.nodes.TypeApplication') -> T:
        pass

    def visit_lambda_expr(self, o: 'mypy.nodes.LambdaExpr') -> T:
        pass

    def visit_list_comprehension(self, o: 'mypy.nodes.ListComprehension') -> T:
        gen = o.generator  # GeneratorExpr
        left_expr = gen.left_expr
        index_expr = gen.indices[0]
        seq = gen.sequences[0]
        cond = gen.condlists[0]

        # We might use all of these, so collect constants.
        self.accept(left_expr)
        self.accept(index_expr)
        self.accept(seq)
        for c in cond:
            self.accept(c)

    def visit_set_comprehension(self, o: 'mypy.nodes.SetComprehension') -> T:
        pass

    def visit_dictionary_comprehension(
            self, o: 'mypy.nodes.DictionaryComprehension') -> T:
        pass

    def visit_generator_expr(self, o: 'mypy.nodes.GeneratorExpr') -> T:
        pass

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
        assert len(o.lvalues) == 1, o.lvalues
        lval = o.lvalues[0]

        self.vars = []
        self.accept(lval)
        found_vars = self.vars
        self.vars = None
        t = self.types.get(lval)
        for var_name in found_vars:
            if var_name and var_name not in IGNORE_NAMES:
                # XXX: limit to managed types? cppgen_pass has the info. having
                # some false-positives probably won't hurt at this stage...
                self.locals[var_name] = t
                self.add_var_def(var_name)

        self.current_rval = o.rvalue
        self.accept(o.rvalue)
        self.current_rval = None

    def visit_for_stmt(self, o: 'mypy.nodes.ForStmt') -> T:
        self.log('ForStmt')
        #self.log('  index_type %s', o.index_type)
        #self.log('  inferred_item_type %s', o.inferred_item_type)
        #self.log('  inferred_iterator_type %s', o.inferred_iterator_type)
        self.current_loop = o

        self.vars = []
        self.accept(o.index)  # index var expression
        found_vars = self.vars
        for var_name in found_vars:
            if var_name and var_name not in IGNORE_NAMES:
                self.locals[var_name] = None
                self.add_var_def(var_name)
        self.vars = None

        self.current_rval = o
        self.accept(o.expr)  # the thing being iterated over
        self.current_loop = None
        self.current_rval = None
        self.push_loop()
        self.accept(o.body)
        self.pop_loop()
        if o.else_body:
            raise AssertionError("can't translate for-else")

    def visit_with_stmt(self, o: 'mypy.nodes.WithStmt') -> T:
        assert len(o.expr) == 1, o.expr
        self.accept(o.expr[0])
        self.accept(o.body)

    def visit_del_stmt(self, o: 'mypy.nodes.DelStmt') -> T:
        self.accept(o.expr)

    def visit_func_def(self, o: 'mypy.nodes.FuncDef') -> T:
        # got the type here, nice!
        typ = o.type

        assert self.statement_id == -1
        self.statement_id = 0
        self.loop_stack = []
        self.locals = {}

        func_name = o.name
        if self.current_class_name:
            func_name = '%s.%s' % (self.current_class_name, o.name)

        func_name = _StripMycpp('%s.%s' % (self.full_module_name, func_name))
        self.current_func_name = func_name

        for t, name in zip(typ.arg_types, typ.arg_names):
            self.log('  arg %s %s', t, name)
        self.log('  ret %s', o.type.ret_type)

        self.indent += 1
        for arg, arg_type in zip(o.arguments, typ.arg_types):
            if arg.variable.name not in IGNORE_NAMES:
                self.locals[arg.variable.name] = arg_type
                self.add_var_def(arg.variable.name)

            # e.g. foo=''
            if arg.initializer:
                self.accept(arg.initializer)

            # We can't use __str__ on these Argument objects?  That seems like an
            # oversight
            #self.log('%r', arg)

            self.log('Argument %s', arg.variable)
            self.log('  type_annotation %s', arg.type_annotation)
            # I think these are for default values
            self.log('  initializer %s', arg.initializer)
            self.log('  kind %s', arg.kind)

        self.accept(o.body)
        self.current_func_name = None
        self.statement_id = -1
        self.loop_stack = None
        self.locals = {}
        self.indent -= 1

    def visit_overloaded_func_def(self,
                                  o: 'mypy.nodes.OverloadedFuncDef') -> T:
        pass

    def visit_class_def(self, o: 'mypy.nodes.ClassDef') -> T:
        self.log('const_pass ClassDef %s', o.name)
        for b in o.base_type_exprs:
            self.log('  base_type_expr %s', b)
        self.indent += 1
        self.current_class_name = o.name
        self.accept(o.defs)
        self.current_class_name = None
        self.indent -= 1

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
        for name, as_name in o.ids:
            if as_name is not None:
                # import time as time_
                self.imported_names.add(as_name)
            else:
                # import libc
                self.imported_names.add(name)

    def visit_import_from(self, o: 'mypy.nodes.ImportFrom') -> T:
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
                self.module_aliases[alias] = '%s.%s' % (o.id, alias)
            else:
                self.imported_names.add(name)
                self.module_aliases[name] = '%s.%s' % (o.id, name)

    def visit_import_all(self, o: 'mypy.nodes.ImportAll') -> T:
        pass

    # Statements

    def visit_block(self, block: 'mypy.nodes.Block') -> T:
        self.log('Block')
        self.indent += 1

        for stmt in block.body:
            # Ignore things that look like docstrings
            if isinstance(stmt, ExpressionStmt) and isinstance(
                    stmt.expr, StrExpr):
                continue
            #log('-- %d', self.indent)
            self.accept(stmt)
        self.indent -= 1

    def visit_expression_stmt(self, o: 'mypy.nodes.ExpressionStmt') -> T:
        self.log('ExpressionStmt')
        self.indent += 1
        self.accept(o.expr)
        self.indent -= 1

    def visit_operator_assignment_stmt(
            self, o: 'mypy.nodes.OperatorAssignmentStmt') -> T:
        self.log('OperatorAssignmentStmt')

    def visit_while_stmt(self, o: 'mypy.nodes.WhileStmt') -> T:
        self.log('WhileStmt')
        self.current_rval = o
        self.current_loop = o
        self.accept(o.expr)
        self.current_loop = None
        self.current_rval = None
        self.push_loop()
        self.accept(o.body)
        self.pop_loop()

    def visit_return_stmt(self, o: 'mypy.nodes.ReturnStmt') -> T:
        self.log('ReturnStmt')
        if o.expr:
            self.current_rval = o.expr
            self.accept(o.expr)
            self.current_rval = None

    def visit_assert_stmt(self, o: 'mypy.nodes.AssertStmt') -> T:
        pass

    def visit_if_stmt(self, o: 'mypy.nodes.IfStmt') -> T:
        # Copied from cppgen_pass.py
        # Not sure why this wouldn't be true
        assert len(o.expr) == 1, o.expr

        # Omit anything that looks like if __name__ == ...
        cond = o.expr[0]
        if (isinstance(cond, ComparisonExpr) and
                isinstance(cond.operands[0], NameExpr) and
                cond.operands[0].name == '__name__'):
            return

        # Omit if TYPE_CHECKING blocks.  They contain type expressions that
        # don't type check!
        if isinstance(cond, NameExpr) and cond.name == 'TYPE_CHECKING':
            return
        # mylib.CPP
        if isinstance(cond, MemberExpr) and cond.name == 'CPP':
            # just take the if block
            for node in o.body:
                self.accept(node)
            return
        # mylib.PYTHON
        if isinstance(cond, MemberExpr) and cond.name == 'PYTHON':
            if o.else_body:
                self.accept(o.else_body)
            return

        self.log('IfStmt')
        self.indent += 1
        for e in o.expr:
            self.current_rval = e
            self.accept(e)
            self.current_rval = None

        for node in o.body:
            self.accept(node)

        if o.else_body:
            self.accept(o.else_body)
        self.indent -= 1

    def visit_break_stmt(self, o: 'mypy.nodes.BreakStmt') -> T:
        pass

    def visit_continue_stmt(self, o: 'mypy.nodes.ContinueStmt') -> T:
        if self.loop_stack is None:
            return

        self.live_vars.EmitEdge(self.current_func_name,
                            self.statement_id,
                            self.loop_stack[-1])

    def visit_pass_stmt(self, o: 'mypy.nodes.PassStmt') -> T:
        pass

    def visit_raise_stmt(self, o: 'mypy.nodes.RaiseStmt') -> T:
        if o.expr:
            self.accept(o.expr)

    def visit_try_stmt(self, o: 'mypy.nodes.TryStmt') -> T:
        self.accept(o.body)
        for t, v, handler in zip(o.types, o.vars, o.handlers):
            self.accept(handler)

        #if o.else_body:
        #  raise AssertionError('try/else not supported')
        #if o.finally_body:
        #  raise AssertionError('try/finally not supported')

    def visit_print_stmt(self, o: 'mypy.nodes.PrintStmt') -> T:
        pass

    def visit_exec_stmt(self, o: 'mypy.nodes.ExecStmt') -> T:
        pass
