"""
conversion_pass.py - forward declarations, and virtuals
"""
import mypy

from mypy.nodes import (Expression, NameExpr, MemberExpr, TupleExpr, CallExpr,
                        FuncDef, Argument)
from mypy.types import Type, Instance, TupleType, NoneType

from mycpp import util
from mycpp.util import log, SplitPyName
from mycpp import pass_state
from mycpp import visitor
from mycpp import cppgen_pass

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    #from mycpp import cppgen_pass
    pass

_ = log

DotExprs = Dict[MemberExpr, pass_state.member_t]


class MyTypeInfo:
    """Like mypy.nodes.TypeInfo"""

    def __init__(self, fullname: str) -> None:
        self.fullname = fullname


class Primitive(Instance):

    def __init__(self, name: str, args: List[Type] = None) -> None:
        self.type = MyTypeInfo(name)  # type: ignore
        self.args = args if args is not None else []


MYCPP_INT = Primitive('builtins.int')


class Pass(visitor.SimpleVisitor):

    def __init__(
            self,
            types: Dict[Expression, Type],
            virtual: pass_state.Virtual,
            forward_decls: List[str],
            all_member_vars: 'cppgen_pass.AllMemberVars',
            all_local_vars: 'cppgen_pass.AllLocalVars',
            module_dot_exprs: DotExprs,
            yield_out_params: Dict[FuncDef, Tuple[str, str]],  # output
    ) -> None:
        visitor.SimpleVisitor.__init__(self)

        # Input
        self.types = types

        # These are all outputs we compute
        self.virtual = virtual
        self.forward_decls = forward_decls
        self.all_member_vars = all_member_vars
        self.all_local_vars = all_local_vars
        self.module_dot_exprs = module_dot_exprs
        # Used to add another param to definition, and
        #     yield x --> YIELD->append(x)
        self.yield_out_params = yield_out_params

        # Internal state
        self.current_member_vars: Dict[str, 'cppgen_pass.MemberVar'] = {}
        self.current_local_vars: List[Tuple[str, Type]] = []

        # Where do we need to update current_local_vars?
        #
        # x = 42                  # oils_visit_assignment_stmt
        # a, b = foo

        # x = [y for y in other]  # oils_visit_assign_to_listcomp_:
        #
        # Special case for enumerate:
        #   for i, x in enumerate(other):
        #
        # def f(p, q):   # params are locals, _WriteFuncParams
        #                # but only if update_locals

        self.imported_names = set()  # MemberExpr -> module::Foo() or self->foo
        # HACK for conditional import inside mylib.PYTHON
        # in core/shell.py
        self.imported_names.add('help_meta')

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
        elif (isinstance(o.expr, NameExpr) and
              o.expr.name in self.imported_names):
            # heuristic for state::Mem()
            module_path = SplitPyName(o.expr.fullname or o.expr.name)
            dot = pass_state.ModuleMember(module_path, o.name)
        else:
            # mylist->append(42)
            dot = pass_state.HeapObjectMember(o.expr, lhs_type, o.name)

        self.module_dot_exprs[o] = dot

        self.accept(o.expr)

    def oils_visit_mypy_file(self, o: 'mypy.nodes.MypyFile') -> None:
        mod_parts = o.fullname.split('.')
        comment = 'forward declare'

        self.write('namespace %s {  // %s\n', mod_parts[-1], comment)

        # Do default traversal
        self.indent += 1
        super().oils_visit_mypy_file(o)
        self.indent -= 1

        self.write('}\n')
        self.write('\n')

    def oils_visit_class_def(
            self, o: 'mypy.nodes.ClassDef',
            base_class_sym: Optional[util.SymbolPath]) -> None:
        self.write_ind('class %s;\n', o.name)
        if base_class_sym:
            self.virtual.OnSubclass(base_class_sym, self.current_class_name)

        # Do default traversal of methods, associating member vars with the
        # ClassDef node
        self.current_member_vars = {}
        super().oils_visit_class_def(o, base_class_sym)
        self.all_member_vars[o] = self.current_member_vars

    def _ValidateDefaultArg(self, arg: Argument) -> None:
        t = self.types[arg.initializer]

        valid = False
        if isinstance(t, NoneType):
            valid = True
        if isinstance(t, Instance):
            # Allowing strings since they're immutable, e.g.
            # prefix='' seems OK
            if t.type.fullname in ('builtins.bool', 'builtins.int',
                                   'builtins.float', 'builtins.str'):
                valid = True

            # ASDL enums lex_mode_t, scope_t, ...
            if t.type.fullname.endswith('_t'):
                valid = True

            # Hack for loc__Missing.  Should detect the general case.
            if t.type.fullname.endswith('loc__Missing'):
                valid = True

        if not valid:
            self.report_error(
                arg,
                'Invalid default arg %r of type %s (not None, bool, int, float, ASDL enum)'
                % (arg.initializer, t))

    def _ValidateDefaultArgs(self, func_def: FuncDef) -> None:
        arguments = func_def.arguments

        num_defaults = 0
        for arg in arguments:
            if arg.initializer:
                self._ValidateDefaultArg(arg)
                num_defaults += 1

        if num_defaults > 1:
            # Report on first arg
            self.report_error(
                arg, '%s has %d default arguments.  Only 1 is allowed' %
                (func_def.name, num_defaults))
            return

    def oils_visit_func_def(self, o: 'mypy.nodes.FuncDef') -> None:
        self._ValidateDefaultArgs(o)

        self.virtual.OnMethod(self.current_class_name, o.name)

        self.current_local_vars = []

        # Add params as local vars, but only if we're NOT in a constructor.
        # This is borrowed from cppgen_pass -
        #   _ConstructorImpl has update_locals=False, likewise for decl
        # Is this just a convention?
        # Counterexample: what if locals are used in __init__ after allocation?
        # Are we assuming we never do mylib.MaybeCollect() inside a
        # constructor?  We can check that too.

        if self.current_method_name != '__init__':
            # Add function params as locals, to be rooted
            arg_types = o.type.arg_types
            arg_names = [arg.variable.name for arg in o.arguments]
            for name, typ in zip(arg_names, arg_types):
                if name == 'self':
                    continue
                self.current_local_vars.append((name, typ))

        # Traverse to collect member variables
        super().oils_visit_func_def(o)
        self.all_local_vars[o] = self.current_local_vars

        # Is this function is a generator?  Then associate the node with an
        # accumulator param (name and type).
        # This is info is consumed by both the Decl and Impl passes
        _, _, c_iter_list_type = cppgen_pass.GetCReturnType(o.type.ret_type)
        if c_iter_list_type is not None:
            self.yield_out_params[o] = ('YIELD', c_iter_list_type)

    def oils_visit_assign_to_listcomp(self, lval: NameExpr,
                                      left_expr: Expression,
                                      index_expr: Expression, seq: Expression,
                                      cond: Expression) -> None:
        # We need to consider 'result' a local var:
        #     result = [x for x in other]

        # what about yield accumulator, like
        # it_g = g(n)
        self.current_local_vars.append((lval.name, self.types[lval]))

        super().oils_visit_assign_to_listcomp(lval, left_expr, index_expr, seq,
                                              cond)

    def _MaybeAddMember(self, lval: MemberExpr) -> None:
        assert not self.at_global_scope, "Members shouldn't be assigned at the top level"

        # Collect statements that look like self.foo = 1
        # Only do this in __init__ so that a derived class mutating a field
        # from the base class doesn't cause duplicate C++ fields.  (C++
        # allows two fields of the same name!)
        #
        # HACK for WordParser: also include Reset().  We could change them
        # all up front but I kinda like this.
        if self.current_method_name not in ('__init__', 'Reset'):
            return

        if isinstance(lval.expr, NameExpr) and lval.expr.name == 'self':
            #log('    lval.name %s', lval.name)
            lval_type = self.types[lval]
            c_type = cppgen_pass.GetCType(lval_type)
            is_managed = cppgen_pass.CTypeIsManaged(c_type)
            self.current_member_vars[lval.name] = (lval_type, c_type,
                                                   is_managed)

    def oils_visit_assignment_stmt(self, o: 'mypy.nodes.AssignmentStmt',
                                   lval: Expression, rval: Expression) -> None:

        if isinstance(lval, MemberExpr):
            self._MaybeAddMember(lval)

        # Handle:
        #    x = y
        # These two are special cases in cppgen_pass, but not here
        #    x = NewDict()
        #    x = cast(T, y)
        #
        # Note: this has duplicates: the 'done' set in visit_block() handles
        # it.  Could make it a Dict.
        if isinstance(lval, NameExpr):
            rval_type = self.types[rval]

            # Two pieces of logic adapted from cppgen_pass: is_iterator and is_cast.
            # Can we simplify them?

            is_iterator = (isinstance(rval_type, Instance) and
                           rval_type.type.fullname == 'typing.Iterator')

            # Downcasted vars are BLOCK-scoped, not FUNCTION-scoped, so they
            # don't become local vars.  They are also ALIASED, so they don't
            # need to be rooted.
            is_downcast_and_shadow = False
            if (isinstance(rval, CallExpr) and
                    isinstance(rval.callee, NameExpr) and
                    rval.callee.name == 'cast'):
                to_cast = rval.args[1]
                if (isinstance(to_cast, NameExpr) and
                        to_cast.name.startswith('UP_')):
                    is_downcast_and_shadow = True

            if (not self.at_global_scope and not is_iterator and
                    not is_downcast_and_shadow):
                self.current_local_vars.append((lval.name, self.types[lval]))

        # Handle local vars, like _write_tuple_unpacking

        # This handles:
        #    a, b = func_that_returns_tuple()
        if isinstance(lval, TupleExpr):
            rval_type = self.types[rval]
            assert isinstance(rval_type, TupleType), rval_type

            for i, (lval_item,
                    item_type) in enumerate(zip(lval.items, rval_type.items)):
                #self.log('*** %s :: %s', lval_item, item_type)
                if isinstance(lval_item, NameExpr):
                    if util.SkipAssignment(lval_item.name):
                        continue
                    self.current_local_vars.append((lval_item.name, item_type))

                # self.a, self.b = foo()
                if isinstance(lval_item, MemberExpr):
                    self._MaybeAddMember(lval_item)

        super().oils_visit_assignment_stmt(o, lval, rval)

    def oils_visit_for_stmt(self, o: 'mypy.nodes.ForStmt',
                            func_name: Optional[str]) -> None:
        # TODO: this variable should be BLOCK scoped, not function scoped, like
        # the tuple variables for i, x
        index0_name: Optional[str] = None
        if func_name == 'enumerate':
            assert isinstance(o.index, TupleExpr), o.index
            index0 = o.index.items[0]
            assert isinstance(index0, NameExpr), index0
            index0_name = index0.name  # generate int i = 0; ; ++i

        if index0_name:
            # can't initialize two things in a for loop, so do it on a separate line
            self.current_local_vars.append((index0_name, MYCPP_INT))

        super().oils_visit_for_stmt(o, func_name)
