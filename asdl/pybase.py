#!/usr/bin/env python2
"""pybase.py."""
from __future__ import print_function

from mycpp import mylib

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.hnode_asdl import hnode_t
    from asdl.runtime import TraversalState


class Obj(object):
    # NOTE: We're using CAPS for these static fields, since they are constant at
    # runtime after metaprogramming.
    ASDL_TYPE = None  # Used for type checking


class SimpleObj(int):
    """Base type of simple sum types."""
    # TODO: Get rid of this indirection?  Although mycpp might use it.
    pass


class CompoundObj(Obj):
    # The tag is set for variant types, which are subclasses of sum
    # types.  Never set for product types.
    _type_tag = 0  # Starts at 1.  Zero is invalid

    def PrettyTree(self, do_abbrev, trav=None):
        # type: (bool, TraversalState) -> hnode_t
        raise NotImplementedError(self.__class__.__name__)

    def __repr__(self):
        # type: () -> str
        # TODO: Break this circular dependency.
        from asdl import format as fmt

        ast_f = fmt.TextOutput(mylib.BufWriter())  # No color by default.
        tree = self.PrettyTree(False)
        fmt.PrintTree(tree, ast_f)
        s, _ = ast_f.GetRaw()
        return s
