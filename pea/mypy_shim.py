#!/usr/bin/env python3
"""
mypy_shim.py

Convert stdlib ast nodes into MyPy nodes
"""

import os

from typing import Any

from mypy.nodes import (MypyFile, FuncDef, Argument, ReturnStmt, IntExpr,
                        Statement, Block, Var, ARG_POS)

from mypy.types import Type, CallableType

from mycpp.virtual_pass import Primitive

from pea import header
from pea.header import log
from pea import parse


def CreateMyPyFile(path: str) -> MypyFile:
    defs: list[Statement] = []
    stub = MypyFile(defs, [])

    name = 'f'

    v = Var('argv')
    s = ret_type = Primitive('builtins.str')
    type_annotation = Primitive('builtins.list', args=[s])
    initializer = None
    kind = ARG_POS

    arguments = [Argument(v, type_annotation, initializer, kind)]
    body = Block([ReturnStmt(IntExpr(42))])

    # Why are types duplicated?
    arg_types: list[Type] = [type_annotation]
    arg_kinds: list[Any] = [ARG_POS]
    arg_names: list[str] = ['argv']
    ret_type = Primitive('builtins.int')
    fallback = Primitive('builtins.int')  # WHAT is this for?
    func_type = CallableType(arg_types, arg_kinds, arg_names, ret_type,
                             fallback)

    func = FuncDef(name, arguments, body, typ=func_type)
    _ = func
    #defs.append(func)

    # fullname is a property, backed by _fullname
    #
    # mycpp/examples/pea_hello.py -> mycpp

    name = os.path.basename(path)
    mod_name, _ = os.path.splitext(name)

    stub._fullname = mod_name

    prog = header.Program()
    log('Pea begin')

    if not parse.ParseFiles([path], prog):
        raise AssertionError()

    prog.PrintStats()
    log('prog %s', prog)

    return stub
