"""
util.py
"""
from __future__ import print_function

import sys
from mypy.nodes import (CallExpr, IfStmt, Block, Expression, MypyFile,
                       MemberExpr, IntExpr, NameExpr, ComparisonExpr)
from mypy.types import Instance, Type

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


def join_name(parts: SymbolPath,
              strip_package: bool = False,
              delim: str = '::') -> str:
    """
    Join the given name path into a string with the given delimiter.
    Use strip_package to remove the top-level directory (e.g. `core`, `ysh`)
    when dealing with C++ namespaces.
    """
    if not strip_package:
        return delim.join(parts)

    if len(parts) > 1:
        return delim.join(('', ) + parts[1:])

    return parts[0]


def split_py_name(name: str) -> SymbolPath:
    ret = tuple(name.split('.'))
    if len(ret) and ret[0] == 'mycpp':
        # Drop the prefix 'mycpp.' if present. This makes names compatible with
        # the examples that use testpkg.
        return ret[1:]

    return ret


def _collect_cases(module_path: str,
                   if_node: IfStmt,
                   out: list[tuple[Expression, Block]],
                   errors=None) -> Optional[Block] | bool:
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


def ShouldSkipPyFile(node: MypyFile) -> bool:
    # Skip some stdlib stuff.  A lot of it is brought in by 'import
    # typing'. These module are special; their contents are currently all
    # built-in primitives.
    return node.fullname in ('__future__', 'sys', 'types', 'typing', 'abc',
                             '_ast', 'ast', '_weakrefset', 'collections',
                             'cStringIO', 're', 'builtins')


def IsStr(t: Type):
    """Helper to check if a type is a string."""
    return isinstance(t, Instance) and t.type.fullname == 'builtins.str'


def MaybeSkipIfStmt(visitor, stmt: IfStmt) -> bool:
    """Returns true if the caller should not visit the entire if statement."""
    cond = stmt.expr[0]

    # Omit anything that looks like if __name__ == ...
    if (isinstance(cond, ComparisonExpr) and
            isinstance(cond.operands[0], NameExpr) and
            cond.operands[0].name == '__name__'):
        return True

    if isinstance(cond, IntExpr) and cond.value == 0:
        # But write else: body
        # Note: this would be invalid at the top level!
        if stmt.else_body:
            visitor.accept(stmt.else_body)

        return True

    if isinstance(cond, NameExpr) and cond.name == 'TYPE_CHECKING':
        # Omit if TYPE_CHECKING blocks.  They contain type expressions that
        # don't type check!
        return True

    if isinstance(cond, MemberExpr) and cond.name == 'CPP':
        # just take the if block
        if hasattr(visitor, 'def_write_ind'):
            visitor.def_write_ind('// if MYCPP\n')
            visitor.def_write_ind('')

        for node in stmt.body:
            visitor.accept(node)

        if hasattr(visitor, 'def_write_ind'):
            visitor.def_write_ind('// endif MYCPP\n')

        return True

    if isinstance(cond, MemberExpr) and cond.name == 'PYTHON':
        # only accept the else block
        if stmt.else_body:
            if hasattr(visitor, 'def_write_ind'):
                visitor.def_write_ind('// if not PYTHON\n')
                visitor.def_write_ind('')

            visitor.accept(stmt.else_body)

            if hasattr(visitor, 'def_write_ind'):
                visitor.def_write_ind('// endif MYCPP\n')

        return True

    return False
