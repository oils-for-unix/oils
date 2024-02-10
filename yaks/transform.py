"""
transform.py - turn homogeneous nil8.asdl represention into heterogeneous
yaks.asdl representation
"""

from _devbuild.gen.yaks_asdl import Module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _devbuild.gen.nil8_asdl import nvalue_t


def Transform(nval):
    # type: (nvalue_t) -> Module

    # TODO: fix this
    # Also need to calculate newlines
    #loc = Token('path', 'chunk', 0, 3)

    #return Bool(False, loc)
    m = Module('foo', [])
    return m


