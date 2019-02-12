#!/usr/bin/python
"""
ast_lib.py - Helpers for osh/osh.asdl
"""

import sys

from asdl import format as fmt
from core.meta import Id


_PrettyLeaf = fmt._PrettyLeaf
_STRING_LITERAL = fmt._STRING_LITERAL
_OTHER_TYPE = fmt._OTHER_TYPE


def _AbbreviateToken(token, out):
  if token.id != Id.Lit_Chars:
    n1 = _PrettyLeaf(str(token.id), _OTHER_TYPE)
    out.append(n1)

  n2 = _PrettyLeaf(token.val, _STRING_LITERAL)
  out.append(n2)


def _GetFieldNames(node):
  # Don't let the 'spids' field disable abbreviation
  return [n for n, _ in node.fields if n != 'spids']


def AbbreviateNodes(obj, node):
  """
  Args:
    obj: py_meta.Obj to print
    node: homogeneous node after MakePrettyTree prints it; can be mutated
  """
  if node.node_type == 'token':
    node.abbrev = True
    node.node_type = 'T'
    node.show_node_type = False
    node.left = '<'
    node.right = '>'
    _AbbreviateToken(obj, node.unnamed_fields)

  elif node.node_type == 'word_part.LiteralPart':
    node.abbrev = True
    node.node_type = 'L'
    node.show_node_type = False

    _AbbreviateToken(obj.token, node.unnamed_fields)

  elif node.node_type == 'word_part.SimpleVarSub':
    node.abbrev = True
    node.node_type = '$'
    _AbbreviateToken(obj.token, node.unnamed_fields)

  elif node.node_type == 'word_part.BracedVarSub':
    if _GetFieldNames(node) != ['token']:
      return  # we have other fields to display; don't abbreviate

    node.abbrev = True
    node.node_type = '${'
    _AbbreviateToken(obj.token, node.unnamed_fields)

  elif node.node_type == 'word_part.DoubleQuotedPart':
    node.abbrev = True
    node.node_type = 'DQ'

    for part in obj.parts:
      node.unnamed_fields.append(fmt.MakePrettyTree(part, AbbreviateNodes))

  # Only abbreviate 'foo', not $'foo\n'
  elif (node.node_type == 'word_part.SingleQuotedPart' and
        obj.left.id == Id.Left_SingleQuote):
    node.abbrev = True
    node.node_type = 'SQ'

    for token in obj.tokens:
      node.unnamed_fields.append(fmt.MakePrettyTree(token, AbbreviateNodes))

  elif node.node_type == 'word.CompoundWord':
    node.abbrev = True
    node.node_type = 'W'
    node.show_node_type = False
    node.left = '{'
    node.right = '}'

    for part in obj.parts:
      node.unnamed_fields.append(fmt.MakePrettyTree(part, AbbreviateNodes))

  elif node.node_type == 'command.SimpleCommand':
    if _GetFieldNames(node) != ['words']:
      return  # we have other fields to display; don't abbreviate

    node.abbrev = True
    node.node_type = 'C'

    for w in obj.words:
      node.unnamed_fields.append(fmt.MakePrettyTree(w, AbbreviateNodes))


def PrettyPrint(node, f=sys.stdout):
  ast_f = fmt.DetectConsoleOutput(f)
  tree = fmt.MakePrettyTree(node, AbbreviateNodes)
  fmt.PrintTree(tree, ast_f)
  f.write('\n')
