"""
typed_arith_abbrev.py - Abbreviations for pretty-printing typed_arith.asdl.
"""

from asdl import runtime
from _devbuild.gen.hnode_asdl import hnode__Record

def _arith_expr__Unary(obj):
  # type: (arith_expr__Unary) -> hnode__Record

  p_node = runtime.NewRecord('U')
  p_node.abbrev = True
  n = runtime.NewLeaf(str(obj.op), color_e.StringConst)
  p_node.unnamed_fields.append(n)
  p_node.unnamed_fields.append(obj.a.AbbreviatedTree())  # type: ignore
  return p_node


def _arith_expr__Binary(obj):
  # type: (arith_expr__Binary) -> Optional[hnode__Record]

  if obj.op == '=':  # test for fallback
    return None

  p_node = runtime.NewRecord('B')
  p_node.abbrev = True
  n = runtime.NewLeaf(str(obj.op), color_e.StringConst)
  p_node.unnamed_fields.append(n)
  p_node.unnamed_fields.append(obj.left.AbbreviatedTree())  # type: ignore
  p_node.unnamed_fields.append(obj.right.AbbreviatedTree())  # type: ignore
  return p_node


def _arith_expr__Const(obj):
  # type: (arith_expr__Const) -> hnode__Record
  p_node = runtime.NewRecord('')
  p_node.abbrev = True
  n = runtime.NewLeaf(str(obj.i), color_e.OtherConst)
  p_node.unnamed_fields.append(n)
  return p_node


def _arith_expr__Var(obj):
  # type: (arith_expr__Var) -> hnode__Record
  p_node = runtime.NewRecord('$')
  p_node.abbrev = True
  n = runtime.NewLeaf(str(obj.name), color_e.StringConst)
  p_node.unnamed_fields.append(n)
  return p_node

