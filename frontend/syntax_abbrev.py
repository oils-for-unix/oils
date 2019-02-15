"""
syntax_abbrev.py - Abbreviations for pretty-printing syntax.asdl.
"""

from asdl import runtime
from core.meta import Id


def _AbbreviateToken(token, out):
  if token.id != Id.Lit_Chars:
    n1 = runtime.PrettyLeaf(str(token.id), runtime.Color_OtherConst)
    out.append(n1)

  n2 = runtime.PrettyLeaf(token.val, runtime.Color_StringConst)
  out.append(n2)


def _token(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = ''  # don't show

  p_node.left = '<'
  p_node.right = '>'
  _AbbreviateToken(obj, p_node.unnamed_fields)
  return p_node


def _word_part__LiteralPart(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = ''  # don't show

  _AbbreviateToken(obj.token, p_node.unnamed_fields)
  return p_node


def _word_part__SimpleVarSub(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = '$'
  _AbbreviateToken(obj.token, p_node.unnamed_fields)
  return p_node


def _word_part__BracedVarSub(obj):
  p_node = runtime.PrettyNode()
  if obj.prefix_op or obj.bracket_op or obj.suffix_op:
    return None  # we have other fields to display; don't abbreviate

  p_node.abbrev = True
  p_node.node_type = '${'
  _AbbreviateToken(obj.token, p_node.unnamed_fields)
  return p_node


def _word_part__DoubleQuotedPart(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = 'DQ'

  for part in obj.parts:
    p_node.unnamed_fields.append(part.AbbreviatedTree())
  return p_node


def _word_part__SingleQuotedPart(obj):
  # Only abbreviate 'foo', not $'foo\n'
  if obj.left.id != Id.Left_SingleQuote:
    return None  # Fall back on obj._AbbreviatedTree()

  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = 'SQ'

  for token in obj.tokens:
    p_node.unnamed_fields.append(token.AbbreviatedTree())
  return p_node


def _word__CompoundWord(obj):
  p_node = runtime.PrettyNode()
  p_node.abbrev = True
  p_node.node_type = ''  # don't show
  p_node.left = '{'
  p_node.right = '}'

  for part in obj.parts:
    p_node.unnamed_fields.append(part.AbbreviatedTree())
  return p_node


def _command__SimpleCommand(obj):
  p_node = runtime.PrettyNode()
  if obj.redirects or obj.more_env:
    return None  # we have other fields to display; don't abbreviate

  p_node.abbrev = True
  p_node.node_type = 'C'

  for w in obj.words:
    p_node.unnamed_fields.append(w.AbbreviatedTree())
  return p_node
