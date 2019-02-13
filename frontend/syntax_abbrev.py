#!/usr/bin/python
"""
ast_lib.py - Helpers for osh/osh.asdl
"""

import sys

from asdl import format as fmt
from asdl import runtime
from core.meta import Id


def _AbbreviateToken(token, out):
  if token.id != Id.Lit_Chars:
    n1 = runtime.PrettyLeaf(str(token.id), runtime.Color_OtherConst)
    out.append(n1)

  n2 = runtime.PrettyLeaf(token.val, runtime.Color_StringConst)
  out.append(n2)


def _GetFieldNames(p_node):
  # Don't let the 'spids' field disable abbreviation
  return [n for n, _ in p_node.fields if n != 'spids']


def token(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = 'T'
  p_node.show_node_type = False
  p_node.left = '<'
  p_node.right = '>'
  _AbbreviateToken(obj, p_node.unnamed_fields)
  return p_node


def word_part__LiteralPart(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = 'L'
  p_node.show_node_type = False

  _AbbreviateToken(obj.token, p_node.unnamed_fields)
  return p_node


def word_part__SimpleVarSub(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = '$'
  _AbbreviateToken(obj.token, p_node.unnamed_fields)
  return p_node


def word_part__BracedVarSub(obj):
  p_node = runtime.PrettyNode()
  if _GetFieldNames(node) != ['token']:
    return  # we have other fields to display; don't abbreviate

  p_node.abbrev = True
  p_node.node_type = '${'
  _AbbreviateToken(obj.token, p_node.unnamed_fields)
  return p_node


def word_part__DoubleQuotedPart(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = 'DQ'

  for part in obj.parts:
    p_node.unnamed_fields.append(fmt.MakePrettyTree(part, AbbreviateNodes))
  return p_node


# Only abbreviate 'foo', not $'foo\n'
def word_part__SingleQuotedPart(Obj):
  if obj.left.id == Id.Left_SingleQuote:
    p_node = runtime.PrettyNode()
    p_node.abbrev = True
    p_node.node_type = 'SQ'

    for token in obj.tokens:
      p_node.unnamed_fields.append(fmt.MakePrettyTree(token, AbbreviateNodes))
    return p_node

  # TODO: This means don't modify it?
  return None


def word__CompoundWord(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = 'W'
  p_node.show_node_type = False
  p_node.left = '{'
  p_node.right = '}'

  for part in obj.parts:
    p_node.unnamed_fields.append(fmt.MakePrettyTree(part, AbbreviateNodes))
  return p_node


def command__SimpleCommand(obj):
  p_node = runtime.PrettyNode()
  if _GetFieldNames(node) != ['words']:
    return  # we have other fields to display; don't abbreviate

  p_node.abbrev = True
  p_node.node_type = 'C'

  for w in obj.words:
    p_node.unnamed_fields.append(fmt.MakePrettyTree(w, AbbreviateNodes))
  return p_node
