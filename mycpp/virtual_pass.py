"""
virtual_pass.py - forward declarations, and virtuals

TODO: Join with ir_pass.py
"""
import mypy

from mypy.nodes import (Expression, NameExpr, MemberExpr, TupleExpr)
from mypy.types import Type, Instance, TupleType

from mycpp import util
from mycpp.util import log
from mycpp import pass_state
from mycpp import visitor
from mycpp import cppgen_pass

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    #from mycpp import cppgen_pass
    pass

_ = log


class MyTypeInfo:
    """Like mypy.nodes.TypeInfo"""

    def __init__(self, fullname: str) -> None:
        self.fullname = fullname


class Primitive(Instance):

    def __init__(self, name: str) -> None:
        self.type = MyTypeInfo(name)  # type: ignore


MYCPP_INT = Primitive('builtins.int')


class Pass(visitor.SimpleVisitor):

    def __init__(
        self,
        types: Dict[Expression, Type],
        virtual: pass_state.Virtual,
        forward_decls: List[str],
        all_member_vars: 'cppgen_pass.AllMemberVars',
        all_local_vars: 'cppgen_pass.AllLocalVars',
    ) -> None:
        visitor.SimpleVisitor.__init__(self)
        self.types = types
        self.virtual = virtual  # output
        self.forward_decls = forward_decls  # output
        self.all_member_vars = all_member_vars
        self.all_local_vars = all_local_vars

        self.current_member_vars: Dict[str, 'cppgen_pass.MemberVar'] = {}
        self.current_local_vars: List[Tuple[str, Type]] = []

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
            base_class_name: Optional[util.SymbolPath]) -> None:
        self.write_ind('class %s;\n', o.name)
        if base_class_name:
            self.virtual.OnSubclass(base_class_name, self.current_class_name)

        # Do default traversal of methods, associating member vars with the
        # ClassDef node
        self.current_member_vars = {}
        super().oils_visit_class_def(o, base_class_name)
        self.all_member_vars[o] = self.current_member_vars

    def oils_visit_func_def(self, o: 'mypy.nodes.FuncDef') -> None:
        self.virtual.OnMethod(self.current_class_name, o.name)

        self.current_local_vars = []

        # Add function params as locals, to be rooted
        arg_types = o.type.arg_types
        arg_names = [arg.variable.name for arg in o.arguments]
        for name, typ in zip(arg_names, arg_types):
            self.current_local_vars.append((name, typ))

        # Traverse to collect member variables
        super().oils_visit_func_def(o)
        self.all_local_vars[o] = self.current_local_vars

    def oils_visit_assign_to_listcomp(self, o: 'mypy.nodes.AssignmentStmt',
                                      lval: NameExpr) -> None:

        super().oils_visit_assign_to_listcomp(o, lval)

        #self.accept(lval)
        #self.accept(o.rvalue.generator)

    def oils_visit_assignment_stmt(self, o: 'mypy.nodes.AssignmentStmt',
                                   lval: Expression, rval: Expression) -> None:

        if isinstance(lval, MemberExpr):
            self._MaybeAddMember(lval, self.current_member_vars)

        # Handle:
        #    x = y
        # These two are special cases in cppgen_pass, but not here
        #    x = NewDict()
        #    x = cast(T, y)
        #
        # Note: this has duplicates: the 'done' set in visit_block() handles
        # it.  Could make it a Dict.
        if isinstance(lval, NameExpr):
            self.current_local_vars.append((lval.name, self.types[lval]))

        # Handle local vars, like _write_tuple_unpacking

        # This handles:
        #    a, b = func_that_returns_tuple()
        # We also need to handle:
        #    for a, b in foo:
        #      pass
        #    result = [a for a, b in foo]

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

        super().oils_visit_assignment_stmt(o, lval, rval)

    def oils_visit_for_stmt(self, o: 'mypy.nodes.ForStmt',
                            func_name: Optional[str]) -> None:
        # TODO: copied from cppgen_pass - this could be destructured in visitor.py
        index0_name: Optional[str] = None
        if func_name == 'enumerate':
            assert isinstance(o.index, TupleExpr), o.index
            index0 = o.index.items[0]
            assert isinstance(index0, NameExpr), index0
            index0_name = index0.name  # generate int i = 0; ; ++i

        if index0_name:
            # can't initialize two things in a for loop, so do it on a separate line
            self.current_local_vars.append((index0_name, MYCPP_INT))

        # Notes:
        # - index0_name - can we remove this?
        #   - it only happens in for i, x in enumerate(...):
        #     because for (x, y) makes locally scoped vars
        #   - we could initialize it to zero inside the loop
        #     and then increment it, at the end
        super().oils_visit_for_stmt(o, func_name)

    def _MaybeAddMember(
            self, lval: MemberExpr,
            current_member_vars: Dict[str, 'cppgen_pass.MemberVar']) -> None:

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
            current_member_vars[lval.name] = (lval_type, c_type, is_managed)


# class_member_vars - Dict replacing current_member_vars
# - collect for each ClassDef node
#   - might as well keep them all
# _MaybeAddMember() is only called in 2 places
#
# Special case
# - ctx_member_vars
