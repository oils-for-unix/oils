"""
transform.py - turn homogeneous nil8.asdl represention into heterogeneous
yaks.asdl representation
"""
from __future__ import print_function

from _devbuild.gen.nil8_asdl import nvalue, nvalue_e, nvalue_t
from _devbuild.gen.yaks_asdl import Module, Program, mod_def, mod_def_t, typ
from mycpp.mylib import log

from typing import cast, List

_ = log


def MustBeSymbol(nval):
    # type: (nvalue_t) -> str
    if nval.tag() != nvalue_e.Symbol:
        raise AssertionError('Expected symbol')
    return cast(nvalue.Symbol, nval).s


def TransformFunc(nval):
    # type: (nvalue.List) -> mod_def.Func

    func_name = MustBeSymbol(nval.items[1])
    return mod_def.Func(func_name, [], typ.Int, [])


def TransformModule(nval):
    # type: (nvalue.List) -> Module

    if len(nval.items) < 2:
        raise AssertionError('Module should have at least 2 items, got %d' %
                             len(nval.items))

    mod_name = MustBeSymbol(nval.items[1])
    out_defs = []  # type: List[mod_def_t]
    module = Module(mod_name, out_defs)

    defs = nval.items[2:]

    for d in defs:
        # (global ...) (func ...) (class ...)
        if d.tag() != nvalue_e.List:
            # TODO: location info
            raise AssertionError('Expected module def to be a List')

        UP_def_n = d
        def_n = cast(nvalue.List, UP_def_n)

        if len(def_n.items) == 0:
            raise AssertionError('Empty module def')

        first = def_n.items[0]
        if first.tag() != nvalue_e.Symbol:
            raise AssertionError('Expected first item to be a Symbol')

        UP_first = first
        first = cast(nvalue.Symbol, UP_first)

        print(first.s)

        if first.s == 'global':
            pass

        elif first.s == 'func':
            out_defs.append(TransformFunc(def_n))

        elif first.s == 'class':
            #out_defs.append(TransformClass(def_n))
            pass

    return module


def Transform(nval):
    # type: (nvalue_t) -> Program
    """
    TODO: For imports, add

    - YAKS_PATH
    - dict of modules that is populated?
    """
    if nval.tag() != nvalue_e.List:
        raise AssertionError('Expected module to be a List')

    mod_n = cast(nvalue.List, nval)

    module = TransformModule(mod_n)
    prog = Program('foo', [module])
    return prog
