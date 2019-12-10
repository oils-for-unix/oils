"""
syntax_abbrev.py - Abbreviations for pretty-printing syntax.asdl.

This module is not used directly, but is combined with generated code.
"""

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.hnode_asdl import hnode_t
from asdl import runtime


def _AbbreviateToken(tok, out):
  # type: (Token, List[hnode_t]) -> None
  if tok.id != Id.Lit_Chars:
    n1 = runtime.NewLeaf(Id_str(tok.id), color_e.OtherConst)
    out.append(n1)

  n2 = runtime.NewLeaf(tok.val, color_e.StringConst)
  out.append(n2)


def _Token(obj):
  # type: (Token) -> hnode_t
  p_node = runtime.NewRecord('')  # don't show node type
  p_node.abbrev = True

  p_node.left = '<'
  p_node.right = '>'
  _AbbreviateToken(obj, p_node.unnamed_fields)
  return p_node


def _compound_word(obj):
  # type: (compound_word) -> hnode_t
  p_node = runtime.NewRecord('')  # don't show node type
  p_node.abbrev = True
  p_node.left = '{'
  p_node.right = '}'

  for part in obj.parts:
    p_node.unnamed_fields.append(part.AbbreviatedTree())
  return p_node


def _speck(obj):
  # type: (speck) -> hnode_t
  """Always abbreviate a speck as the Id."""
  p_node = runtime.NewRecord('')  # don't show node type
  p_node.abbrev = True

  n1 = runtime.NewLeaf(Id_str(obj.id), color_e.OtherConst)
  p_node.unnamed_fields.append(n1)
  return p_node


def _double_quoted(obj):
  # type: (double_quoted) -> hnode_t
  if obj.left.id != Id.Left_DoubleQuote:
    return None  # Fall back on obj._AbbreviatedTree()

  p_node = runtime.NewRecord('DQ')
  p_node.abbrev = True

  for part in obj.parts:
    p_node.unnamed_fields.append(part.AbbreviatedTree())
  return p_node


def _single_quoted(obj):
  # type: (single_quoted) -> hnode_t

  # Only abbreviate 'foo', not $'foo\n'
  if obj.left.id != Id.Left_SingleQuoteRaw:
    return None  # Fall back on obj._AbbreviatedTree()

  p_node = runtime.NewRecord('SQ')
  p_node.abbrev = True

  for token in obj.tokens:
    p_node.unnamed_fields.append(token.AbbreviatedTree())
  return p_node


def _simple_var_sub(obj):
  # type: (simple_var_sub) -> hnode_t
  p_node = runtime.NewRecord('$')
  p_node.abbrev = True
  _AbbreviateToken(obj.token, p_node.unnamed_fields)
  return p_node


def _braced_var_sub(obj):
  # type: (braced_var_sub) -> hnode_t
  p_node = runtime.NewRecord('${')
  if obj.prefix_op or obj.bracket_op or obj.suffix_op:
    return None  # we have other fields to display; don't abbreviate

  p_node.abbrev = True
  _AbbreviateToken(obj.token, p_node.unnamed_fields)
  return p_node


def _command__Simple(obj):
  # type: (command__Simple) -> hnode_t
  p_node = runtime.NewRecord('C')
  if obj.redirects or obj.more_env or obj.block:
    return None  # we have other fields to display; don't abbreviate

  p_node.abbrev = True

  for w in obj.words:
    p_node.unnamed_fields.append(w.AbbreviatedTree())
  return p_node


def _expr__Var(obj):
  # type: (expr__Var) -> hnode_t
  p_node = runtime.NewRecord('Var')
  p_node.abbrev = True

  assert obj.name.id == Id.Expr_Name, obj.name
  n1 = runtime.NewLeaf(obj.name.val, color_e.StringConst)
  p_node.unnamed_fields.append(n1)
  return p_node


def _expr__Const(obj):
  # type: (expr__Const) -> hnode_t
  p_node = runtime.NewRecord('Const')
  p_node.abbrev = True

  tok = obj.c
  out = p_node.unnamed_fields

  n1 = runtime.NewLeaf(Id_str(tok.id), color_e.OtherConst)
  out.append(n1)

  n2 = runtime.NewLeaf(tok.val, color_e.StringConst)
  out.append(n2)
  return p_node
