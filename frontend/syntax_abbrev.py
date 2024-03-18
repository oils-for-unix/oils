"""
syntax_abbrev.py - Abbreviations for pretty-printing syntax.asdl.

This module is not used directly, but is combined with generated code.
"""

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.hnode_asdl import hnode_t
from asdl import runtime


def _AbbreviateToken(tok, out):
    # type: (Token, List[hnode_t]) -> None
    if tok.id in (Id.Lit_Chars, Id.Lit_CharsWithoutPrefix, Id.VSub_Name,
                  Id.VSub_Number):
        tok_str = tok.line.content[tok.col : tok.col+tok.length]
        n1 = runtime.NewLeaf(tok_str, color_e.StringConst)
    else:
        n1 = runtime.NewLeaf(Id_str(tok.id), color_e.OtherConst)
    out.append(n1)


def _Token(obj):
    # type: (Token) -> hnode_t
    p_node = runtime.NewRecord('')  # don't show node type
    p_node.abbrev = True

    p_node.left = '<'
    p_node.right = '>'
    _AbbreviateToken(obj, p_node.unnamed_fields)
    return p_node


def _CompoundWord(obj):
    # type: (CompoundWord) -> hnode_t
    p_node = runtime.NewRecord('')  # don't show node type
    p_node.abbrev = True
    p_node.left = '{'
    p_node.right = '}'

    for part in obj.parts:
        p_node.unnamed_fields.append(part.AbbreviatedTree())
    return p_node


def _DoubleQuoted(obj):
    # type: (DoubleQuoted) -> hnode_t
    if obj.left.id != Id.Left_DoubleQuote:
        return None  # Fall back on obj._AbbreviatedTree()

    p_node = runtime.NewRecord('DQ')
    p_node.abbrev = True

    for part in obj.parts:
        p_node.unnamed_fields.append(part.AbbreviatedTree())
    return p_node


def _SingleQuoted(obj):
    # type: (SingleQuoted) -> hnode_t

    # Only abbreviate 'foo', not $'foo\n' or r'foo'
    if obj.left.id != Id.Left_SingleQuote:
        return None  # Fall back on obj._AbbreviatedTree()

    p_node = runtime.NewRecord('SQ')
    p_node.abbrev = True

    n2 = runtime.NewLeaf(obj.sval, color_e.StringConst)
    p_node.unnamed_fields.append(n2)
    return p_node


def _SimpleVarSub(obj):
    # type: (SimpleVarSub) -> hnode_t
    p_node = runtime.NewRecord('$')
    p_node.abbrev = True

    if obj.tok.id in (Id.VSub_DollarName, Id.VSub_Number):  # $myvar or $1
        # We want to show the variable name
        # _AbbreviateToken(obj.tok, p_node.unnamed_fields)
        tok = obj.tok
        # Omit $
        var_name = tok.line.content[tok.col+1 : tok.col+tok.length]
        n1 = runtime.NewLeaf(var_name, color_e.StringConst)
        p_node.unnamed_fields.append(n1)
    else:  # $?
        n1 = runtime.NewLeaf(Id_str(obj.tok.id), color_e.OtherConst)
        p_node.unnamed_fields.append(n1)

    return p_node


def _BracedVarSub(obj):
    # type: (BracedVarSub) -> hnode_t
    p_node = runtime.NewRecord('${')
    if obj.prefix_op or obj.bracket_op or obj.suffix_op:
        return None  # we have other fields to display; don't abbreviate

    p_node.abbrev = True
    _AbbreviateToken(obj.token, p_node.unnamed_fields)
    return p_node


def _command__Simple(obj):
    # type: (command.Simple) -> hnode_t
    p_node = runtime.NewRecord('C')
    if (obj.redirects or obj.more_env or obj.typed_args or obj.block or
            obj.do_fork == False):
        return None  # we have other fields to display; don't abbreviate

    p_node.abbrev = True

    for w in obj.words:
        p_node.unnamed_fields.append(w.AbbreviatedTree())
    return p_node


def _expr__Var(obj):
    # type: (expr.Var) -> hnode_t
    p_node = runtime.NewRecord('Var')
    p_node.abbrev = True

    assert obj.left.id == Id.Expr_Name, obj.name
    n1 = runtime.NewLeaf(obj.name, color_e.StringConst)
    p_node.unnamed_fields.append(n1)
    return p_node


def _expr__Const(obj):
    # type: (expr.Const) -> hnode_t
    p_node = runtime.NewRecord('Const')
    p_node.abbrev = True

    tok = obj.c
    out = p_node.unnamed_fields

    n1 = runtime.NewLeaf(Id_str(tok.id), color_e.OtherConst)
    out.append(n1)

    n2 = runtime.NewLeaf(tok.tval, color_e.StringConst)
    out.append(n2)
    return p_node
