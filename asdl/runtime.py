"""runtime.py.

- Base classes for generated code
- Nodes for pretty printing
"""
from __future__ import print_function

from _devbuild.gen.hnode_asdl import hnode, color_t, color_e

from typing import Optional, Dict

# Used throughout the "LST" to indicate we don't have location info.
NO_SPID = -1


def NewRecord(node_type):
    # type: (str) -> hnode.Record

    # TODO: could CreateNull(alloc_lists=True) to optimize?
    return hnode.Record(
        node_type,
        '(',
        ')',
        [],  # fields
        None,  # unnamed fields
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
    # for repr of InternalStringArray, which can have 'None'
    if s is None:
        return hnode.Leaf('_', color_e.OtherConst)
    else:
        return hnode.Leaf(s, e_color)


class TraversalState:

    def __init__(self):
        # type: () -> None

        # So PrettyTree() and AbbreviatedTree() don't go into infinite loops.

        self.seen = {}  # type: Dict[int, bool]

        # If you have a ref count of 2 or more, you can print a stable ID for
        # the record the FIRST time around.  Then future records will refer to that ID.
        # For a ref count of 1, don't bother printing it.
        self.ref_count = {}  # type: Dict[int, int]


# Constants to avoid 'StrFromC("T")' in ASDL-generated code
TRUE_STR = 'T'
FALSE_STR = 'F'
