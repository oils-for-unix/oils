#!/usr/bin/python
"""
typed_arith_abbrev.py
"""
from __future__ import print_function

# Causes a circular import!  Gah.
#from _devbuild.gen import typed_arith_asdl as A
#from typing import Optional

from asdl import runtime
_PrettyBase = runtime._PrettyBase


def arith_expr__Unary(obj):
  # X type: (A.arith_expr__Unary) -> Optional[_PrettyBase]

  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = 'U'
  n = runtime.PrettyLeaf(str(obj.op), runtime.Color_StringConst)
  p_node.unnamed_fields.append(n)
  p_node.unnamed_fields.append(obj.a.AbbreviatedTree())  # type: ignore
  return p_node


def arith_expr__Binary(obj):
  # X type: (A.arith_expr__Binary) -> Optional[_PrettyBase]

  if obj.op == '=':  # test for fallback
    return None

  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = 'B'
  n = runtime.PrettyLeaf(str(obj.op), runtime.Color_StringConst)
  p_node.unnamed_fields.append(n)
  p_node.unnamed_fields.append(obj.left.AbbreviatedTree())  # type: ignore
  p_node.unnamed_fields.append(obj.right.AbbreviatedTree())  # type: ignore
  return p_node


def arith_expr__Const(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = None  # omit it
  n = runtime.PrettyLeaf(str(obj.i), runtime.Color_OtherConst)
  p_node.unnamed_fields.append(n)
  return p_node


def arith_expr__Var(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = '$'
  n = runtime.PrettyLeaf(str(obj.name), runtime.Color_StringConst)
  p_node.unnamed_fields.append(n)
  return p_node

