from __future__ import print_function
"""
fmt.py: Stub for code formatter.

See doc/pretty-printing.md.
"""

from mycpp import mylib
from tools import ysh_ify

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import command_t
    from core import alloc


def Format(arena, node):
    # type: (alloc.Arena, command_t) -> None
    """
    Stub that prints, copied from ysh_ify.LosslessCat

    TODO: implement formatter (on a coarse tree)
    """
    cursor = ysh_ify.Cursor(arena, mylib.Stdout())
    cursor.PrintUntilEnd()
