#!/usr/bin/env python2
"""func_init.py"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import value, scope_e
from core import vm
from frontend import lexer
from frontend import location

from typing import TYPE_CHECKING, Dict, List, Callable, Union, cast
if TYPE_CHECKING:
    from core import state


def SetGlobalFunc(mem, name, func):
    # type: (state.Mem, str, vm._Callable) -> None
    assert isinstance(func, vm._Callable), func

    # TODO: Fix this location info
    #left = lexer.DummyToken(Id.Undefined_Tok, '')
    mem.SetValue(location.LName(name), value.Func(func), scope_e.GlobalOnly)
