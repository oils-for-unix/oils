#!/usr/bin/env python3
"""
osh/ast_.py -- Parse osh.asdl and dynamically create classes on this module.
"""

import os
import sys

from asdl import py_meta
from asdl import asdl_ as asdl

from core.id_kind import Id


from asdl import format as fmt

_ColoredString = fmt._ColoredString
MakeTree = fmt.MakeTree
_STRING_LITERAL = fmt._STRING_LITERAL
_OTHER_TYPE = fmt._OTHER_TYPE


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
    if obj.id != Id.Lit_Chars:
      c = _ColoredString(str(obj.id), _OTHER_TYPE)
      node.unnamed_fields.append(c)

    node.unnamed_fields.append(_ColoredString(obj.val, _STRING_LITERAL))

  elif node.node_type == 'LiteralPart':
    node.abbrev = True
    node.node_type = 'L'
    node.show_node_type = False
    node.left = '['
    node.right = ']'

    token = obj.token
    if token.id != Id.Lit_Chars:
      c = _ColoredString(str(token.id), _OTHER_TYPE)
      node.unnamed_fields.append(c)
    node.unnamed_fields.append(_ColoredString(token.val, _STRING_LITERAL))

  elif node.node_type == 'DoubleQuotedPart':
    node.abbrev = True
    node.node_type = 'DQ'
    node.left = '['
    node.right = ']'

    for part in obj.parts:
      node.unnamed_fields.append(MakeTree(part, AbbreviateNodes))

  elif node.node_type == 'SingleQuotedPart':
    node.abbrev = True
    node.node_type = 'SQ'
    node.left = '['
    node.right = ']'

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
    field_names = [n for n, _ in node.fields]
    if field_names != ['words']:
      return  # we have other fields to display; don't abbreviate

    node.abbrev = True
    node.node_type = 'C'

    for w in obj.words:
      # Recursively call MakeTree here?
      # Well actually then the printer needs to recursively handle it
      node.unnamed_fields.append(MakeTree(w, AbbreviateNodes))

  elif node.node_type == 'BracedVarSub':
    field_names = [n for n, _ in node.fields]
    if field_names != ['name']:
      return  # we have other fields to display; don't abbreviate

    node.abbrev = True
    node.node_type = '$'
    node.left = '['
    node.right = ']'
    node.unnamed_fields.append(_ColoredString(obj.name, _STRING_LITERAL))

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


def _ParseAndMakeTypes(schema_path, root):
  # TODO: A better syntax for this might be:
  #
  #     id = external
  #
  # in osh.asdl.  Then we can show an error if it's not provided.
  app_types = {'id': asdl.UserType(Id)}

  module = asdl.parse(schema_path)

  # Check for type errors
  if not asdl.check(module, app_types):
    raise AssertionError('ASDL file is invalid')
  py_meta.MakeTypes(module, root, app_types)


bin_dir = os.path.dirname(os.path.abspath(sys.argv[0]))  # ~/git/oil/bin
schema_path = os.path.join(bin_dir, '../osh/osh.asdl')  # ~/git/oil/osh

root = sys.modules[__name__]

_ParseAndMakeTypes(schema_path, root)
