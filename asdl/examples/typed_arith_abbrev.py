"""
typed_arith_abbrev.py - Abbreviations for pretty-printing typed_arith.asdl.
"""

from asdl import runtime
from _devbuild.gen.hnode_asdl import hnode, color_e

__all__ = [
    '_arith_expr__Unary', '_arith_expr__Binary', '_arith_expr__Const',
    '_arith_expr__Var'
]


def _arith_expr__Unary(obj):
    # type: (arith_expr__Unary) -> hnode.Record

    p_node = runtime.NewRecord('U')
    n = runtime.NewLeaf(str(obj.op), color_e.StringConst)
    p_node.unnamed_fields = [n]
    p_node.unnamed_fields.append(obj.a.PrettyTree(True))  # type: ignore
    return p_node


def _arith_expr__Binary(obj):
    # type: (arith_expr__Binary) -> Optional[hnode.Record]

    if obj.op == '=':  # test for fallback
        return None

    p_node = runtime.NewRecord('B')
    n = runtime.NewLeaf(str(obj.op), color_e.StringConst)
    p_node.unnamed_fields = [n]
    p_node.unnamed_fields.append(obj.left.PrettyTree(True))  # type: ignore
    p_node.unnamed_fields.append(obj.right.PrettyTree(True))  # type: ignore
    return p_node


def _arith_expr__Const(obj):
    # type: (arith_expr__Const) -> hnode.Record
    p_node = runtime.NewRecord('')
    n = runtime.NewLeaf(str(obj.i), color_e.OtherConst)
    p_node.unnamed_fields = [n]
    return p_node


def _arith_expr__Var(obj):
    # type: (arith_expr__Var) -> hnode.Record
    p_node = runtime.NewRecord('$')
    n = runtime.NewLeaf(str(obj.name), color_e.StringConst)
    p_node.unnamed_fields = [n]
    return p_node
