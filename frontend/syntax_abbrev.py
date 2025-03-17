"""
syntax_abbrev.py - Abbreviations for pretty-printing syntax.asdl.
"""

from _devbuild.gen.id_kind_asdl import Id, Id_str
from _devbuild.gen.hnode_asdl import hnode, hnode_t, color_e
from asdl import runtime

from typing import List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import (Token, CompoundWord, DoubleQuoted,
                                           SingleQuoted, BracedVarSub,
                                           SimpleVarSub, command, expr)

__all__ = [
    '_Token', '_CompoundWord', '_DoubleQuoted', '_SingleQuoted',
    '_BracedVarSub', '_SimpleVarSub', '_command__Simple', '_expr__Var',
    '_expr__Const'
]


def _AbbreviateToken(tok, out):
    # type: (Token, List[hnode_t]) -> None
    tok_str = tok.line.content[tok.col:tok.col + tok.length]
    n1 = runtime.NewLeaf(Id_str(tok.id, dot=False), color_e.OtherConst)
    out.append(n1)
    n2 = runtime.NewLeaf(tok_str, color_e.StringConst)
    out.append(n2)


def _Token(obj):
    # type: (Token) -> hnode_t
    p_node = runtime.NewRecord('')  # don't show node type

    p_node.left = '<'
    p_node.right = '>'
    p_node.unnamed_fields = []
    _AbbreviateToken(obj, p_node.unnamed_fields)
    return p_node


def _CompoundWord(obj):
    # type: (CompoundWord) -> hnode_t
    p_node = runtime.NewRecord('w')
    p_node.left = '('
    p_node.right = ')'

    p_node.unnamed_fields = []
    for part in obj.parts:
        p_node.unnamed_fields.append(part.PrettyTree(True))
    return p_node


def _DoubleQuoted(obj):
    # type: (DoubleQuoted) -> hnode_t
    if obj.left.id != Id.Left_DoubleQuote:
        return None  # Fall back on obj._PrettyTree(True)

    p_node = runtime.NewRecord('DQ')

    p_node.unnamed_fields = []
    for part in obj.parts:
        p_node.unnamed_fields.append(part.PrettyTree(True))
    return p_node


def _SingleQuoted(obj):
    # type: (SingleQuoted) -> hnode_t

    # Only abbreviate 'foo', not $'foo\n' or r'foo'
    if obj.left.id != Id.Left_SingleQuote:
        return None  # Fall back on obj._PrettyTree(True)

    p_node = runtime.NewRecord('SQ')

    p_node.unnamed_fields = []
    n2 = runtime.NewLeaf(obj.sval, color_e.StringConst)
    p_node.unnamed_fields.append(n2)
    return p_node


def _SimpleVarSub(obj):
    # type: (SimpleVarSub) -> hnode_t
    p_node = runtime.NewRecord('$')

    p_node.unnamed_fields = []
    if obj.tok.id in (Id.VSub_DollarName, Id.VSub_Number):  # $myvar or $1
        # We want to show the variable name
        # _AbbreviateToken(obj.tok, p_node.unnamed_fields)
        tok = obj.tok
        # Omit $
        var_name = tok.line.content[tok.col + 1:tok.col + tok.length]
        n1 = runtime.NewLeaf(var_name, color_e.StringConst)
        p_node.unnamed_fields.append(n1)
    else:  # $?
        n1 = runtime.NewLeaf(Id_str(obj.tok.id, dot=False), color_e.OtherConst)
        p_node.unnamed_fields.append(n1)

    return p_node


def _BracedVarSub(obj):
    # type: (BracedVarSub) -> Optional[hnode_t]
    p_node = runtime.NewRecord('${')
    if (obj.prefix_op is not None or obj.bracket_op is not None or
            obj.suffix_op is not None):
        return None  # we have other fields to display; don't abbreviate

    p_node.unnamed_fields = []
    _AbbreviateToken(obj.name_tok, p_node.unnamed_fields)
    return p_node


def _command__Simple(obj):
    # type: (command.Simple) -> Optional[hnode_t]
    p_node = runtime.NewRecord('C')
    if (len(obj.more_env) or obj.typed_args is not None or
            obj.block is not None or obj.is_last_cmd == True):
        return None  # we have other fields to display; don't abbreviate

    p_node.unnamed_fields = []
    for w in obj.words:
        p_node.unnamed_fields.append(w.PrettyTree(True))
    return p_node


def _expr__Var(obj):
    # type: (expr.Var) -> hnode_t
    p_node = runtime.NewRecord('Var')

    assert obj.left.id == Id.Expr_Name, obj.name
    n1 = runtime.NewLeaf(obj.name, color_e.StringConst)
    p_node.unnamed_fields = [n1]
    return p_node


def _expr__Const(obj):
    # type: (expr.Const) -> hnode_t
    p_node = runtime.NewRecord('Const')

    tok = obj.c
    n1 = runtime.NewLeaf(Id_str(tok.id, dot=False), color_e.OtherConst)
    n2 = runtime.NewLeaf(tok.tval, color_e.StringConst)

    p_node.unnamed_fields = [n1, n2]
    return p_node
