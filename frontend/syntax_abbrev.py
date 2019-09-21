"""
syntax_abbrev.py - Abbreviations for pretty-printing syntax.asdl.
"""

from _devbuild.gen.id_kind_asdl import Id
from asdl import runtime


def _AbbreviateToken(tok, out):
  # type: (token, List[runtime._PrettyBase]) -> None
  if tok.id != Id.Lit_Chars:
    n1 = runtime.PrettyLeaf(tok.id.name, runtime.Color_OtherConst)
    out.append(n1)

  n2 = runtime.PrettyLeaf(tok.val, runtime.Color_StringConst)
  out.append(n2)


def _token(obj):
  # type: (token) -> PrettyNode
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = ''  # don't show

  p_node.left = '<'
  p_node.right = '>'
  _AbbreviateToken(obj, p_node.unnamed_fields)
  return p_node


def _speck(obj):
  # type: (speck) -> PrettyNode
  """Always abbreviate a speck as the Id."""
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = ''  # don't show

  n1 = runtime.PrettyLeaf(obj.id.name, runtime.Color_OtherConst)
  p_node.unnamed_fields.append(n1)
  return p_node


def _double_quoted(obj):
  # type: (double_quoted) -> PrettyNode
  if obj.left.id != Id.Left_DoubleQuote:
    return None  # Fall back on obj._AbbreviatedTree()

  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = 'DQ'

  for part in obj.parts:
    p_node.unnamed_fields.append(part.AbbreviatedTree())
  return p_node


def _single_quoted(obj):
  # type: (single_quoted) -> PrettyNode

  # Only abbreviate 'foo', not $'foo\n'
  if obj.left.id != Id.Left_SingleQuoteRaw:
    return None  # Fall back on obj._AbbreviatedTree()

  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = 'SQ'

  for token in obj.tokens:
    p_node.unnamed_fields.append(token.AbbreviatedTree())
  return p_node


def _simple_var_sub(obj):
  # type: (simple_var_sub) -> PrettyNode
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = '$'
  _AbbreviateToken(obj.token, p_node.unnamed_fields)
  return p_node


def _braced_var_sub(obj):
  # type: (braced_var_sub) -> PrettyNode
  p_node = runtime.PrettyNode()
  if obj.prefix_op or obj.bracket_op or obj.suffix_op:
    return None  # we have other fields to display; don't abbreviate

  p_node.abbrev = True
  p_node.node_type = '${'
  _AbbreviateToken(obj.token, p_node.unnamed_fields)
  return p_node


def _word_part__Literal(obj):
  # type: (word_part__Literal) -> PrettyNode
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = ''  # don't show

  _AbbreviateToken(obj.token, p_node.unnamed_fields)
  return p_node


def _word__Compound(obj):
  # type: (word__Compound) -> PrettyNode
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = ''  # don't show
  p_node.left = '{'
  p_node.right = '}'

  for part in obj.parts:
    p_node.unnamed_fields.append(part.AbbreviatedTree())
  return p_node


def _command__Simple(obj):
  # type: (command__Simple) -> PrettyNode
  p_node = runtime.PrettyNode()
  if obj.redirects or obj.more_env or obj.block:
    return None  # we have other fields to display; don't abbreviate

  p_node.abbrev = True
  p_node.node_type = 'C'

  for w in obj.words:
    p_node.unnamed_fields.append(w.AbbreviatedTree())
  return p_node
