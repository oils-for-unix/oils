"""runtime.py.

- Base classes for generated code
- Nodes for pretty printing
"""
from __future__ import print_function

from _devbuild.gen.hnode_asdl import hnode, color_t, color_e

from typing import Optional

# Used throughout the "LST" to indicate we don't have location info.
NO_SPID = -1


def NewRecord(node_type):
    # type: (str) -> hnode.Record
    return hnode.Record(
        node_type,
        [],  # fields
        False,
        '(',
        ')',  # abbrev, left, right
        []  # unnamed fields
    )


def NewLeaf(s, e_color):
    # type: (Optional[str], color_t) -> hnode.Leaf
    """
    TODO: _EmitCodeForField in asdl/gen_{cpp,python}.py does something like
    this for non-string types.  We should keep the style consistent.

    It's related to the none_guard return value of _HNodeExpr().

    The problem there is that we call i0->PrettyTree() or
    i0->AbbreviatedTree().  Although it's not actually polymorphic in C++, only
    Python, so we could handle the nullptr case.

    i.e. PrettyTree() could be a free function using static dispatch, not a
    member.  And then it can handle the nullptr case.
    """
    # for repr of BashArray, which can have 'None'
    if s is None:
        return hnode.Leaf('_', color_e.OtherConst)
    else:
        return hnode.Leaf(s, e_color)


# Constants to avoid 'StrFromC("T")' in ASDL-generated code
TRUE_STR = 'T'
FALSE_STR = 'F'
