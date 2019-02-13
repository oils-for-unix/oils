#!/usr/bin/python
"""
typed_arith_abbrev.py
"""
from __future__ import print_function

from asdl import typed_runtime as runtime

def arith_expr__Unary(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = 'U'
  n = runtime.PrettyLeaf(str(obj.op), runtime.Color_StringConst)
  p_node.unnamed_fields.append(n)
  p_node.unnamed_fields.append(obj.a.AbbreviatedTree())
  return p_node


def arith_expr__Binary(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = 'B'
  n = runtime.PrettyLeaf(str(obj.op), runtime.Color_StringConst)
  p_node.unnamed_fields.append(n)
  p_node.unnamed_fields.append(obj.left.AbbreviatedTree())
  p_node.unnamed_fields.append(obj.right.AbbreviatedTree())
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



