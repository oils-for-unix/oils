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

  else:
    # Do generic abbreviation here if none of the specific ones applied.
    field_names = getattr(obj, 'FIELDS', None)
    if field_names is not None and len(field_names) == 1:
      field_name = field_names[0]
      actual_desc = obj.DESCRIPTOR_LOOKUP[field_name]
      if not isinstance(actual_desc, asdl.ArrayType):  # Arrays can't be abbreviated
        node.abbrev = True
        out_val = fmt.FormatField(obj, field_name, AbbreviateNodes)
        node.unnamed_fields.append(out_val)


def PrettyPrint(node, f=sys.stdout):
  ast_f = fmt.DetectConsoleOutput(f)
  tree = fmt.MakeTree(node, AbbreviateNodes)
  fmt.PrintTree(tree, ast_f)
  f.write('\n')


def LoadSchema(f):
  app_types = {'id': asdl.UserType(Id)}

  asdl_module = asdl.parse(f)
  # TODO: Need some metaprogramming here to add id and kind.

  # NOTE: This only checks for overlapping sum types, which will no longer be
  # an error.
  if not asdl.check(asdl_module, app_types):
    raise AssertionError('ASDL file is invalid')

  return asdl_module, app_types


# TODO: This should be the only lines in this module?
# PrettyPrint can go in osh/ast_lib ?  or ast_util?

root = sys.modules[__name__]
if 1:
  f = util.GetResourceLoader().open('osh/osh.asdl')
  asdl_module, app_types = LoadSchema(f)
  py_meta.MakeTypes(asdl_module, root, app_types)
  f.close()
else:
  # Get the types from elsewhere
  from _devbuild import osh_asdl
  py_meta.AssignTypes(osh_asdl, root)
