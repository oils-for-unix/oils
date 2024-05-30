"""
util.py
"""
from __future__ import print_function

import sys
from mypy.nodes import CallExpr, IfStmt, Block, Expression

from typing import Any, Sequence, Optional

# Used by cppgen_pass and const_pass

# mycpp/examples/small_str.py sorta works with this!
#SMALL_STR = True

SMALL_STR = False

SymbolPath = Sequence[str]


def log(msg: str, *args: Any) -> None:
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)

def join_name(parts: SymbolPath, strip_package: bool = False, delim: str = '::') -> str:
    """
    Join the given name path into a string with the given delimiter.
    Use strip_package to remove the top-level directory (e.g. `core`, `ysh`)
    when dealing with C++ namespaces.
    """
    if not strip_package:
        return delim.join(parts)

    if len(parts) > 1:
        return delim.join(('',) + parts[1:])

    return parts[0]

def split_py_name(name: str) -> SymbolPath:
    ret = tuple(name.split('.'))
    if len(ret) and ret[0] == 'mycpp':
        # Drop the prefix 'mycpp.' if present. This makes names compatible with
        # the examples that use testpkg.
        return ret[1:]

    return ret


def _collect_cases(module_path: str, if_node: IfStmt, out: list[tuple[Expression, Block]], errors = None) -> Optional[Block] | bool:
    """
    The MyPy AST has a recursive structure for if-elif-elif rather than a
    flat one.  It's a bit confusing.

    Appends (expr, block) cases to out param, and returns the default
    block, which has no expression.

    default block may be None.

    Returns False if there is no default block.
    """
    assert isinstance(if_node, IfStmt), if_node
    assert len(if_node.expr) == 1, if_node.expr
    assert len(if_node.body) == 1, if_node.body

    expr = if_node.expr[0]
    body = if_node.body[0]

    if not isinstance(expr, CallExpr):
        if errors is not None:
            errors.append((module_path, expr.line,
                           'Expected call like case(x), got %s' % expr))
        return

    out.append((expr, body))

    if if_node.else_body:
        first_of_block = if_node.else_body.body[0]
        # BUG: this is meant for 'elif' only.  But it also triggers for
        #
        # else:
        #   if 0:

        if isinstance(first_of_block, IfStmt):
            return _collect_cases(module_path, first_of_block, out, errors)
        else:
            # default case - no expression
            return if_node.else_body

    return False  # NO DEFAULT BLOCK - Different than None
