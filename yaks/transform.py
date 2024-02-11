"""
transform.py - turn homogeneous nil8.asdl represention into heterogeneous
yaks.asdl representation
"""
from __future__ import print_function

from _devbuild.gen.nil8_asdl import nvalue, nvalue_e, nvalue_t
from _devbuild.gen.yaks_asdl import (Module, Program, mod_def, mod_def_t,
                                     ktype, ktype_t, stmt, stmt_t, kexpr_t,
                                     Int, Token, Signature, NameType)

from mycpp.mylib import log, tagswitch

from typing import cast, List

_ = log


def MustBeSymbol(nval):
    # type: (nvalue_t) -> str
    if nval.tag() != nvalue_e.Symbol:
        raise AssertionError('Expected symbol')
    return cast(nvalue.Symbol, nval).s


def TransformExpr(nval):
    # type: (nvalue_t) -> kexpr_t

    UP_nval = nval
    with tagswitch(nval) as case:
        if case(nvalue_e.Int):
            nval = cast(nvalue.Int, UP_nval)
            loc = Token('path', 'chunk', 0, 3)  # TODO
            return Int(nval.i, loc)

        else:
            raise AssertionError()


def TransformType(nval):
    # type: (nvalue_t) -> ktype_t
    return ktype.Int


def TransformParams(nval):
    # type: (nvalue_t) -> List[NameType]
    """
    (func f [
      [x Int] [y Int] [z [List Int]]
    ] => Int
      (return (+ x y))
    )

    With default args and prefix *:

    runtime_asdl::Cell* GetCell(BigStr* name, runtime_asdl::scope_t which_scopes = scope_e::Shopt);

    (method GetCell [
      [name (*BigStr)]
      [which_scopes runtime_asdl::scope_t=scope_e::Shopt]
    ] => (*runtime_asdl::Cell)
      (call print "hi")
    )
    """
    return []


def TransformSignature(nval):
    # type: (nvalue_t) -> Signature

    if nval.tag() != nvalue_e.List:
        raise AssertionError('Expected signature to be a List')

    UP_sig_n = nval
    sig_n = cast(nvalue.List, UP_sig_n)

    if len(sig_n.items) != 3:
        raise AssertionError(
            'Signature should have 3 items: =>  params  return')

    first = MustBeSymbol(sig_n.items[0])
    if first != '=>':
        raise AssertionError('Signature should start with =>')

    return Signature(TransformParams(sig_n.items[1]),
                     TransformType(sig_n.items[2]))


def TransformFunc(nval):
    # type: (nvalue.List) -> mod_def.Func

    func_name = MustBeSymbol(nval.items[1])
    out_stmts = []  # type: List[stmt_t]

    sig = TransformSignature(nval.items[2])
    func = mod_def.Func(func_name, sig, out_stmts)

    stmts = nval.items[3:]
    for st in stmts:
        if st.tag() != nvalue_e.List:
            raise AssertionError('Expected statement to be a List')

        UP_stmt_n = st
        stmt_n = cast(nvalue.List, UP_stmt_n)

        if len(stmt_n.items) == 0:
            raise AssertionError("Statement shouldn't be empty")

        first = MustBeSymbol(stmt_n.items[0])

        if first == 'call':
            pass

        elif first == 'return':
            expr = TransformExpr(stmt_n.items[1])
            out_stmts.append(stmt.Return(expr))

        elif first == 'break':
            pass

        elif first == 'continue':
            pass

        else:
            raise AssertionError('Invalid statment %r' % first)

    return func


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
            raise AssertionError("Module shouldn't be empty")

        first = MustBeSymbol(def_n.items[0])

        if first == 'global':
            pass

        elif first == 'func':
            out_defs.append(TransformFunc(def_n))

        elif first == 'class':
            #out_defs.append(TransformClass(def_n))
            pass

        else:
            raise AssertionError('Invalid module def %r' % first)

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
