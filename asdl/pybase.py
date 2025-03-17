#!/usr/bin/env python2
"""asdl/pybase.py is a runtime library for ASDL in Python"""
from __future__ import print_function

from mycpp import mylib

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.hnode_asdl import hnode_t
    from asdl.runtime import TraversalState


class SimpleObj(int):
    """Base type of simple sum types, which are integers."""
    # TODO: Get rid of this class?  mycpp uses it to tell if it should generate
    # h8_id or h8_id*.
    pass


class CompoundObj(object):
    # The tag is set for variant types, which are subclasses of sum types.
    # It's not set for product types.
    _type_tag = 0  # Starts at 1.  Zero is invalid

    def PrettyTree(self, do_abbrev, trav=None):
        # type: (bool, TraversalState) -> hnode_t
        raise NotImplementedError(self.__class__.__name__)

    def __repr__(self):
        # type: () -> str
        """Print this ASDL object nicely."""

        # TODO: Break this circular dependency.
        from asdl import format as fmt

        f = mylib.BufWriter()
        tree = self.PrettyTree(False)
        fmt.HNodePrettyPrint(tree, f)
        return f.getvalue()
