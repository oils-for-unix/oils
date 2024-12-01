"""
const_pass.py - AST pass that collects string constants.

Instead of emitting a dynamic allocation StrFromC("foo"), we emit a
GLOBAL_STR(str99, "foo"), and then a reference to str99.
"""
import mypy

from mycpp import util
from mycpp.util import log
from mycpp import pass_state
from mycpp import visitor

from typing import List, Optional

_ = log


class Pass(visitor.SimpleVisitor):

    def __init__(self, virtual: pass_state.Virtual,
                 forward_decls: List[str]) -> None:
        visitor.SimpleVisitor.__init__(self)
        self.virtual = virtual  # output
        self.forward_decls = forward_decls  # output

    def oils_visit_mypy_file(self, o: 'mypy.nodes.MypyFile') -> None:
        mod_parts = o.fullname.split('.')
        comment = 'forward declare'

        self.write('namespace %s {  // %s\n', mod_parts[-1], comment)
        self.write('\n')

        self.indent += 1

        # Do default traversal
        super().oils_visit_mypy_file(o)

        self.indent -= 1

        self.write('\n')
        self.write('}  // %s namespace %s\n', comment, mod_parts[-1])
        self.write('\n')

    def oils_visit_class_def(
            self, o: 'mypy.nodes.ClassDef',
            base_class_name: Optional[util.SymbolPath]) -> None:
        self.write_ind('class %s;\n', o.name)
        if base_class_name:
            self.virtual.OnSubclass(base_class_name, self.current_class_name)

        # Do default traversal
        super().oils_visit_class_def(o, base_class_name)

    def oils_visit_func_def(self, o: 'mypy.nodes.FuncDef') -> None:
        self.virtual.OnMethod(self.current_class_name, o.name)
