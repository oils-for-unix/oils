"""
debug.py - Pretty-print the AST
"""
from mypy.visitor import ExpressionVisitor, StatementVisitor
from mypy.nodes import Expression, Statement
from mypy.types import Type

from typing import overload, Union, Optional, Any, Dict

from crash import catch_errors
from util import log


T = None

class UnsupportedException(Exception):
    pass


class Print(ExpressionVisitor[T], StatementVisitor[None]):

    def __init__(self, types: Dict[Expression, Type]):
      self.types = types
      self.indent = 0

    def log(self, msg, *args):
      ind_str = self.indent * '  '
      log(ind_str + msg, *args)

    #
    # COPIED from IRBuilder
    #

    @overload
    def accept(self, node: Expression) -> T: ...

    @overload
    def accept(self, node: Statement) -> None: ...

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

    # Not in superclasses:

    def visit_mypy_file(self, o: 'mypy.nodes.MypyFile') -> T:
        # Skip some stdlib stuff.  A lot of it is brought in by 'import
        # typing'.
        if o.fullname() in (
            '__future__', 'sys', 'types', 'typing', 'abc', '_ast', 'ast',
            '_weakrefset', 'collections', 'cStringIO', 're', 'builtins'):

            # These module are special; their contents are currently all
            # built-in primitives.
            return

        self.log('')
        self.log('mypyfile %s', o.fullname())

        self.module_path = o.path

        self.indent += 1
        for node in o.defs:
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
        self.log('NameExpr %s', o.name)

    def visit_member_expr(self, o: 'mypy.nodes.MemberExpr') -> T:
        self.log('MemberExpr')
        self.log('  expr %s', o.expr)
        self.log('  name %s', o.name)

    def visit_yield_from_expr(self, o: 'mypy.nodes.YieldFromExpr') -> T:
        pass

    def visit_yield_expr(self, o: 'mypy.nodes.YieldExpr') -> T:
        pass

    def visit_call_expr(self, o: 'mypy.nodes.CallExpr') -> T:
        self.log('CallExpr')
        self.accept(o.callee)  # could be f() or obj.method()

        self.indent += 1
        for arg in o.args:
          self.accept(arg)
          # The type of each argument
          #self.log(':: %s', self.types[arg])
        self.indent -= 1
        #self.log(  'args %s', o.args)

        self.log('  arg_kinds %s', o.arg_kinds)
        self.log('  arg_names %s', o.arg_names)

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
          self.log('operand')
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
        self.log('UnaryExpr %s', o.op)
        self.indent += 1
        self.accept(o.expr)
        self.indent -= 1

    def visit_list_expr(self, o: 'mypy.nodes.ListExpr') -> T:
        pass

    def visit_dict_expr(self, o: 'mypy.nodes.DictExpr') -> T:
        pass

    def visit_tuple_expr(self, o: 'mypy.nodes.TupleExpr') -> T:
        pass

    def visit_set_expr(self, o: 'mypy.nodes.SetExpr') -> T:
        pass

    def visit_index_expr(self, o: 'mypy.nodes.IndexExpr') -> T:
        self.log('Index')
        self.accept(o.base)
        self.accept(o.index)

    def visit_type_application(self, o: 'mypy.nodes.TypeApplication') -> T:
        pass

    def visit_lambda_expr(self, o: 'mypy.nodes.LambdaExpr') -> T:
        pass

    def visit_list_comprehension(self, o: 'mypy.nodes.ListComprehension') -> T:
        pass

    def visit_set_comprehension(self, o: 'mypy.nodes.SetComprehension') -> T:
        pass

    def visit_dictionary_comprehension(self, o: 'mypy.nodes.DictionaryComprehension') -> T:
        pass

    def visit_generator_expr(self, o: 'mypy.nodes.GeneratorExpr') -> T:
        pass

    def visit_slice_expr(self, o: 'mypy.nodes.SliceExpr') -> T:
        self.log('Slice')
        self.indent += 1
        self.log('begin %s', o.begin_index)
        self.log('end %s', o.end_index)

        if o.begin_index:
          self.accept(o.begin_index)

        if o.end_index:
          self.accept(o.end_index)

        if o.stride:
          self.accept(o.stride)
        self.indent -= 1

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
        # How does this get reached??

        # Ah wtf, why is there no type on here!
        # I thought we did parse_and_typecheck already?

        if 1:
          self.log('AssignmentStmt')
          #self.log('  type %s', o.type)
          #self.log('  unanalyzed_type %s', o.unanalyzed_type)

          # NICE!  Got the lvalue 
          for lval in o.lvalues:
            try:
              self.log('  lval %s :: %s', lval, self.types[lval])
            except KeyError:  # TODO: handle this
              pass
          try:
            r = self.types[o.rvalue]
          except KeyError:
            # This seems to only happen for Ellipsis, I guess in the abc module
            #log('    NO TYPE FOR RVALUE: %s', o.rvalue)
            pass
          else:
            #self.log('    %s :: %s', o.rvalue, r)
            self.indent += 1
            self.log('    rvalue :: %s', r)
            self.accept(o.rvalue)
            self.indent -= 1
            #self.log('  o.rvalue %s', o.rvalue)

    def visit_for_stmt(self, o: 'mypy.nodes.ForStmt') -> T:
        self.log('ForStmt')
        self.log('  index_type %s', o.index_type)
        self.log('  inferred_item_type %s', o.inferred_item_type)
        self.log('  inferred_iterator_type %s', o.inferred_iterator_type)
        self.accept(o.index)  # index var expression
        self.accept(o.expr)  # the thing being iterated over
        self.accept(o.body)
        if o.else_body:
          self.accept(o.else_body)

    def visit_with_stmt(self, o: 'mypy.nodes.WithStmt') -> T:
        pass

    def visit_del_stmt(self, o: 'mypy.nodes.DelStmt') -> T:
        pass

    def visit_func_def(self, o: 'mypy.nodes.FuncDef') -> T:
        # got the type here, nice!
        typ = o.type
        self.log('FuncDef %s :: %s', o.name(), typ)
        #self.log('%s', type(typ))

        for t, name in zip(typ.arg_types, typ.arg_names):
          self.log('  arg %s %s', t, name)
        self.log('  ret %s', o.type.ret_type)

        self.indent += 1
        for arg in o.arguments:
          # We can't use __str__ on these Argument objects?  That seems like an
          # oversight
          #self.log('%r', arg)

          self.log('Argument %s', arg.variable)
          self.log('  type_annotation %s', arg.type_annotation)
          # I think these are for default values
          self.log('  initializer %s', arg.initializer)
          self.log('  kind %s', arg.kind)

        self.accept(o.body)
        self.indent -= 1

    def visit_overloaded_func_def(self, o: 'mypy.nodes.OverloadedFuncDef') -> T:
        pass

    def visit_class_def(self, o: 'mypy.nodes.ClassDef') -> T:
        # woohoo!!
        self.log('ClassDef %s', o.name)
        for b in o.base_type_exprs:
          self.log('  base_type_expr %s', b)
        self.indent += 1
        self.accept(o.defs)
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
        pass

    def visit_import_from(self, o: 'mypy.nodes.ImportFrom') -> T:
        pass

    def visit_import_all(self, o: 'mypy.nodes.ImportAll') -> T:
        pass

    # Statements

    def visit_block(self, block: 'mypy.nodes.Block') -> T:
        self.log('Block')
        self.indent += 1
        for stmt in block.body:
            #log('-- %d', self.indent)
            self.accept(stmt)
        self.indent -= 1

    def visit_expression_stmt(self, o: 'mypy.nodes.ExpressionStmt') -> T:
        self.log('ExpressionStmt')
        self.indent += 1
        self.accept(o.expr)
        self.indent -= 1

    def visit_operator_assignment_stmt(self, o: 'mypy.nodes.OperatorAssignmentStmt') -> T:
        self.log('OperatorAssignmentStmt %s', o.op)
        self.indent += 1
        self.accept(o.lvalue)
        self.accept(o.rvalue)
        self.indent -= 1

    def visit_while_stmt(self, o: 'mypy.nodes.WhileStmt') -> T:
        self.log('WhileStmt')
        self.accept(o.expr)
        self.accept(o.body)

    def visit_return_stmt(self, o: 'mypy.nodes.ReturnStmt') -> T:
        self.log('ReturnStmt')
        if o.expr:
          self.indent += 1
          self.accept(o.expr)
          self.indent -= 1

    def visit_assert_stmt(self, o: 'mypy.nodes.AssertStmt') -> T:
        pass

    def visit_if_stmt(self, o: 'mypy.nodes.IfStmt') -> T:
        self.log('IfStmt')
        self.indent += 1
        for e in o.expr:
          self.accept(e)
        for node in o.body:
          self.accept(node)
        if o.else_body:
          self.accept(o.else_body)
        self.indent -= 1

    def visit_break_stmt(self, o: 'mypy.nodes.BreakStmt') -> T:
        self.log('BreakStmt')

    def visit_continue_stmt(self, o: 'mypy.nodes.ContinueStmt') -> T:
        self.log('ContinueStmt')

    def visit_pass_stmt(self, o: 'mypy.nodes.PassStmt') -> T:
        pass

    def visit_raise_stmt(self, o: 'mypy.nodes.RaiseStmt') -> T:
        self.log('RaiseStmt')
        if o.expr:
          self.indent += 1
          self.accept(o.expr)
          self.indent -= 1

    def visit_try_stmt(self, o: 'mypy.nodes.TryStmt') -> T:
        self.log('TryStmt')
        self.indent += 1

        self.accept(o.body)

        for t, v, handler in zip(o.types, o.vars, o.handlers):
          self.log('except %s as %s', t, v)
          self.indent += 1
          self.accept(handler)
          self.indent -= 1

        if o.else_body:
          self.accept(o.else_body)
        if o.finally_body:
          self.accept(o.finally_body)

        self.indent -= 1

    def visit_print_stmt(self, o: 'mypy.nodes.PrintStmt') -> T:
        pass

    def visit_exec_stmt(self, o: 'mypy.nodes.ExecStmt') -> T:
        pass
