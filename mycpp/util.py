"""
util.py
"""
from __future__ import print_function

import sys
from mypy.nodes import (CallExpr, IfStmt, Block, Expression, MypyFile,
                        MemberExpr, IntExpr, NameExpr, ComparisonExpr)
from mypy.types import Instance, Type

from typing import Any, Optional, List, Tuple, Union

# Used by cppgen_pass and const_pass

# mycpp/examples/small_str.py sorta works with this!
#SMALL_STR = True

SMALL_STR = False

SymbolPath = Tuple[str, ...]


def log(msg: str, *args: Any) -> None:
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)


def SymbolToString(parts: SymbolPath,
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


def SplitPyName(name: str) -> SymbolPath:
    ret = tuple(name.split('.'))
    if len(ret) and ret[0] == 'mycpp':
        # Drop the prefix 'mycpp.' if present. This makes names compatible with
        # the examples that use testpkg.
        return ret[1:]

    return ret


CaseList = List[Tuple[Expression, Block]]

CaseError = Tuple[str, int, str]


def CollectSwitchCases(
        module_path: str,
        if_node: IfStmt,
        out: CaseList,
        errors: Optional[List[CaseError]] = None) -> Union[Block, int]:
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
        return -1  # error code

    out.append((expr, body))

    if if_node.else_body:
        first_of_block = if_node.else_body.body[0]
        # BUG: this is meant for 'elif' only.  But it also triggers for
        #
        # else:
        #   if 0:

        if isinstance(first_of_block, IfStmt):
            return CollectSwitchCases(module_path, first_of_block, out, errors)
        else:
            # default case - no expression
            return if_node.else_body

    return -2  # NO DEFAULT BLOCK


def ShouldSkipPyFile(node: MypyFile) -> bool:
    # Skip some stdlib stuff.  A lot of it is brought in by 'import
    # typing'. These module are special; their contents are currently all
    # built-in primitives.
    return node.fullname in ('__future__', 'sys', 'types', 'typing', 'abc',
                             '_ast', 'ast', '_weakrefset', 'collections',
                             'cStringIO', 're', 'builtins')


def IsStr(t: Type) -> bool:
    """Helper to check if a type is a string."""
    return isinstance(t, Instance) and t.type.fullname == 'builtins.str'


def _ShouldSkipIf(stmt: IfStmt) -> bool:
    cond = stmt.expr[0]

    # Omit anything that looks like if __name__ == ...
    if (isinstance(cond, ComparisonExpr) and
            isinstance(cond.operands[0], NameExpr) and
            cond.operands[0].name == '__name__'):
        return True

    if isinstance(cond, NameExpr) and cond.name == 'TYPE_CHECKING':
        # Omit if TYPE_CHECKING blocks.  They contain type expressions that
        # don't type check!
        return True

    return False


def GetSpecialIfCondition(stmt: IfStmt) -> Optional[str]:
    cond = stmt.expr[0]
    if isinstance(cond, NameExpr) and cond.name == 'TYPE_CHECKING':
        return cond.name

    if isinstance(cond, MemberExpr) and cond.name in ('PYTHON', 'CPP'):
        return cond.name

    return None


def ShouldVisitIfExpr(stmt: IfStmt) -> bool:
    if _ShouldSkipIf(stmt) or GetSpecialIfCondition(stmt) in ('PYTHON', 'CPP'):
        return False

    cond = stmt.expr[0]
    if isinstance(cond, IntExpr) and cond.value == 0:
        return False

    return True


def ShouldVisitIfBody(stmt: IfStmt) -> bool:
    if _ShouldSkipIf(stmt):
        return False

    cond = stmt.expr[0]
    if isinstance(cond, MemberExpr) and cond.name == 'PYTHON':
        return False

    if isinstance(cond, IntExpr) and cond.value == 0:
        return False

    return True


def ShouldVisitElseBody(stmt: IfStmt) -> bool:
    if _ShouldSkipIf(stmt):
        return False

    cond = stmt.expr[0]
    if isinstance(cond, MemberExpr) and cond.name == 'CPP':
        return False

    return stmt.else_body is not None


def IsUnusedVar(var_name: str) -> bool:
    return var_name == '_' or var_name.startswith('unused')


def SkipAssignment(var_name: str) -> bool:
    """
    Skip at the top level:
      _ = log 
      unused1 = log

    Always skip:
      x, _ = mytuple  # no second var
    """
    # __all__ should be excluded
    return IsUnusedVar(var_name)
