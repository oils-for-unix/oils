"""
const_pass.py - AST pass that collects constants.

Immutable string constants like 'StrFromC("foo")' are moved to the top level of
the generated C++ program for efficiency.
"""
import json

from mypy.nodes import (Expression, StrExpr, CallExpr)
from mypy.types import Type

from mycpp import format_strings
from mycpp import util
from mycpp.util import log
from mycpp import visitor

from typing import Dict, List, Any


class Collect(visitor.SimpleVisitor):

    def __init__(self, types: Dict[Expression,
                                   Type], const_lookup: Dict[Expression, str],
                 const_code: List[str]) -> None:

        self.types = types
        self.const_lookup = const_lookup
        self.const_code = const_code
        self.unique_id = 0

        self.indent = 0

    def _EmitStringConstant(self, msg: str, *args: Any) -> None:
        if args:
            msg = msg % args
        self.const_code.append(msg)

    def log(self, msg: str, *args: Any) -> None:
        if 0:  # quiet
            ind_str = self.indent * '  '
            log(ind_str + msg, *args)

    # LITERALS

    def visit_str_expr(self, o: StrExpr) -> None:
        id_ = 'str%d' % self.unique_id
        self.unique_id += 1

        raw_string = format_strings.DecodeMyPyString(o.value)

        if util.SMALL_STR:
            self._EmitStringConstant('GLOBAL_STR2(%s, %s);', id_,
                                     json.dumps(raw_string))
        else:
            self._EmitStringConstant('GLOBAL_STR(%s, %s);', id_,
                                     json.dumps(raw_string))

        self.const_lookup[o] = id_

    # Expression

    def visit_call_expr(self, o: CallExpr) -> None:
        self.log('CallExpr')
        self.accept(o.callee)  # could be f() or obj.method()
        if o.callee.name == 'probe':
            # don't generate constants for probe names
            return

        # This is what the SimpleVisitor superclass does
        for arg in o.args:
            self.accept(arg)
