"""
virtual_pass.py - forward declarations, and virtuals

TODO: Join with ir_pass.py
"""
import mypy

from mypy.nodes import (Expression, NameExpr)
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

    def __init__(self, types: Dict[Expression,
                                   Type], virtual: pass_state.Virtual,
                 forward_decls: List[str]) -> None:
        visitor.SimpleVisitor.__init__(self)
        self.types = types
        self.virtual = virtual  # output
        self.forward_decls = forward_decls  # output

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

        # Do default traversal of methods
        super().oils_visit_class_def(o, base_class_name)

    def oils_visit_func_def(self, o: 'mypy.nodes.FuncDef') -> None:
        self.virtual.OnMethod(self.current_class_name, o.name)

    def _MaybeAddMember(
            self, lval: Expression,
            current_member_vars: Dict[str, 'cppgen_pass.MemberVar']) -> None:
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
