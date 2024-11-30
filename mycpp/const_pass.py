"""
const_pass.py - AST pass that collects string constants.

Instead of emitting a dynamic allocation StrFromC("foo"), we emit a
GLOBAL_STR(str99, "foo"), and then a reference to str99.
"""
import json

from mypy.nodes import (Expression, StrExpr, CallExpr)

from mycpp import format_strings
from mycpp import util
from mycpp.util import log
from mycpp import visitor

from typing import Dict, List, Any

_ = log


class Collect(visitor.SimpleVisitor):

    def __init__(self, const_lookup: Dict[Expression, str],
                 const_code: List[str]) -> None:
        self.const_lookup = const_lookup
        self.const_code = const_code

        # Only generate unique strings.
        # Before this optimization, _gen/bin/oils_for_unix.mycpp.cc went up to:
        #     "str2824"
        # After:
        #     "str1789"
        #
        # So it saved over 1000 strings.
        #
        # The C++ compiler should also optimize it, but it's easy for us to
        # generate less source code.

        # unique string value -> id
        self.unique: Dict[str, str] = {}
        self.unique_id = 0

    def _EmitStringConstant(self, msg: str, *args: Any) -> None:
        if args:
            msg = msg % args
        self.const_code.append(msg)

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
        self.accept(o.callee)  # could be f() or obj.method()
        if o.callee.name == 'probe':
            # don't generate constants for probe names
            return

        # This is what the SimpleVisitor superclass does
        for arg in o.args:
            self.accept(arg)
