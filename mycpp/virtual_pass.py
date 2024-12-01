"""
const_pass.py - AST pass that collects string constants.

Instead of emitting a dynamic allocation StrFromC("foo"), we emit a
GLOBAL_STR(str99, "foo"), and then a reference to str99.
"""
import json

import mypy
from mypy.nodes import (StrExpr, CallExpr)

from mycpp import format_strings
from mycpp import util
from mycpp.util import log
from mycpp import pass_state
from mycpp import visitor

from typing import List, Optional

_ = log


class Pass(visitor.SimpleVisitor):

    def __init__(self, 
                 virtual: pass_state.Virtual,
                 forward_decls: List[str]) -> None:
        visitor.SimpleVisitor.__init__(self)
        self.virtual = virtual  # output
        self.forward_decls = forward_decls  # output

    def oils_visit_class_def(self, o: 'mypy.nodes.ClassDef', base_class_name: Optional[util.SymbolPath]) -> None:
        pass

    def oils_visit_func_def(self, o: 'mypy.nodes.FuncDef') -> None:
        self.virtual.OnMethod(self.current_class_name, o.name)

    def visit_str_expr(self, o: StrExpr) -> None:
        str_val = o.value

        # Optimization to save code
        str_id = self.unique.get(str_val)
        if str_id is None:
            str_id = 'str%d' % self.unique_id
            self.unique_id += 1

            self.unique[str_val] = str_id

            raw_string = format_strings.DecodeMyPyString(str_val)
            if util.SMALL_STR:
                self._EmitStringConstant('GLOBAL_STR2(%s, %s);', str_id,
                                         json.dumps(raw_string))
            else:
                self._EmitStringConstant('GLOBAL_STR(%s, %s);', str_id,
                                         json.dumps(raw_string))

        # Different nodes can refer to the same string ID
        self.const_lookup[o] = str_id

    def visit_call_expr(self, o: CallExpr) -> None:
        # Don't generate constants for probe names
        # TODO: we could turn this into a stmt.Probe(), which is not a call_expr
        # Then only the cppgen_pass cares about it
        if o.callee.name == 'probe':
            return

        self.accept(o.callee)  # could be f() or obj.method()

        # This is what the SimpleVisitor superclass does
        for arg in o.args:
            self.accept(arg)
