#!/usr/bin/env python
"""
osh/ast_.py -- Parse osh.asdl and dynamically create classes on this module.
"""

import sys

from asdl import asdl_ as asdl
from asdl import format as fmt
from asdl import py_meta

from core.id_kind import Id
from core import util


_ColoredString = fmt._ColoredString
MakeTree = fmt.MakeTree
_STRING_LITERAL = fmt._STRING_LITERAL
_OTHER_TYPE = fmt._OTHER_TYPE


def _AbbreviateToken(token, out):
  if token.id != Id.Lit_Chars:
    c = _ColoredString(str(token.id), _OTHER_TYPE)
    out.append(c)

  out.append(_ColoredString(token.val, _STRING_LITERAL))


def _GetFieldNames(node):
  # Don't let the 'spids' field disable abbreviation
  return [n for n, _ in node.fields if n != 'spids']


def AbbreviateNodes(obj, node):
  """
  Args:
    obj: py_meta.Obj to print
    node: homogeneous node after MakeTree prints it; can be mutated
  """
  if node.node_type == 'token':
    node.abbrev = True
    node.node_type = 'T'
    node.show_node_type = False
    node.left = '<'
    node.right = '>'
    _AbbreviateToken(obj, node.unnamed_fields)

  elif node.node_type == 'LiteralPart':
    node.abbrev = True
    node.node_type = 'L'
    node.show_node_type = False

    _AbbreviateToken(obj.token, node.unnamed_fields)

  elif node.node_type == 'SimpleVarSub':
    node.abbrev = True
    node.node_type = '$'
    _AbbreviateToken(obj.token, node.unnamed_fields)

  elif node.node_type == 'BracedVarSub':
    if _GetFieldNames(node) != ['token']:
      return  # we have other fields to display; don't abbreviate

    node.abbrev = True
    node.node_type = '${'
    _AbbreviateToken(obj.token, node.unnamed_fields)

  elif node.node_type == 'DoubleQuotedPart':
    node.abbrev = True
    node.node_type = 'DQ'

    for part in obj.parts:
      node.unnamed_fields.append(MakeTree(part, AbbreviateNodes))

  elif node.node_type == 'SingleQuotedPart':
    node.abbrev = True
    node.node_type = 'SQ'

    for token in obj.tokens:
      node.unnamed_fields.append(MakeTree(token, AbbreviateNodes))

  elif node.node_type == 'CompoundWord':
    node.abbrev = True
    node.node_type = 'W'
    node.show_node_type = False
    node.left = '{'
    node.right = '}'

    for part in obj.parts:
      node.unnamed_fields.append(MakeTree(part, AbbreviateNodes))

  elif node.node_type == 'SimpleCommand':
    if _GetFieldNames(node) != ['words']:
      return  # we have other fields to display; don't abbreviate

    node.abbrev = True
    node.node_type = 'C'

    for w in obj.words:
      # Recursively call MakeTree here?
      # Well actually then the printer needs to recursively handle it
      node.unnamed_fields.append(MakeTree(w, AbbreviateNodes))


def PrettyPrint(node, f=sys.stdout):
  ast_f = fmt.DetectConsoleOutput(f)
  tree = fmt.MakeTree(node, AbbreviateNodes)
  fmt.PrintTree(tree, ast_f)
  f.write('\n')


def LoadSchema(f):
  app_types = {'id': asdl.UserType(Id)}

  asdl_module = asdl.parse(f)

  if not asdl.check(asdl_module, app_types):
    raise AssertionError('ASDL file is invalid')

  type_lookup = asdl.ResolveTypes(asdl_module, app_types)
  return asdl_module, type_lookup


# TODO: This should be the only lines in this module?
# PrettyPrint can go in osh/ast_lib ?  or ast_util?

f = util.GetResourceLoader().open('osh/osh.asdl')
asdl_module, type_lookup = LoadSchema(f)

root = sys.modules[__name__]
if 0:
  py_meta.MakeTypes(asdl_module, root, type_lookup)
else:
  # Exported for the generated code to use
  TYPE_LOOKUP = type_lookup

  # Get the types from elsewhere
  from _devbuild.gen import osh_asdl
  py_meta.AssignTypes(osh_asdl, root)

f.close()
