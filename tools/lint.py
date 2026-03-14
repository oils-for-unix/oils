from __future__ import print_function
"""
lint.py: Stub for linter
"""

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import command_t
    from core import alloc


def Lint(arena, node):
    # type: (alloc.Arena, command_t) -> None
    """
    TODO: implement linter

    a=`echo hi`   # no
    a=$(echo hi)  # yes
    """
    print('TODO')
