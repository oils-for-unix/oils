"""
virtual_pass.py - forward declarations, and virtuals

TODO: Join with ir_pass.py
"""
import mypy

from mypy.nodes import (Expression, NameExpr, MemberExpr)
from mypy.types import Type

from mycpp import util
from mycpp.util import log
from mycpp import pass_state
from mycpp import visitor
from mycpp import cppgen_pass

from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    #from mycpp import cppgen_pass
    pass

_ = log


class Pass(visitor.SimpleVisitor):

    def __init__(
        self,
        types: Dict[Expression, Type],
        virtual: pass_state.Virtual,
        forward_decls: List[str],
        all_member_vars: 'cppgen_pass.AllMemberVars',
    ) -> None:
        visitor.SimpleVisitor.__init__(self)
        self.types = types
        self.virtual = virtual  # output
        self.forward_decls = forward_decls  # output
        self.all_member_vars = all_member_vars

        self.current_member_vars: Dict[str, 'cppgen_pass.MemberVar'] = {}

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

        # Traverse to collect member variables
        super().oils_visit_func_def(o)

    def oils_visit_assignment_stmt(self, o: 'mypy.nodes.AssignmentStmt',
                                   lval: Expression, rval: Expression) -> None:

        if isinstance(lval, MemberExpr):
            self._MaybeAddMember(lval, self.current_member_vars)

        super().oils_visit_assignment_stmt(o, lval, rval)

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
