"""
gen_cpp.py - turn yaks.asdl representation into C++
"""
from __future__ import print_function

from _devbuild.gen.yaks_asdl import (Program, mod_def, mod_def_e, ktype,
                                     ktype_e, ktype_t, NameType, stmt, stmt_e,
                                     stmt_t, Int, kexpr_e, kexpr_t, Int)
from mycpp import mylib
from mycpp.mylib import tagswitch, log

from typing import cast

_ = log


def GenType(typ, f):
    # type: (ktype_t, mylib.Writer) -> None

    UP_typ = typ
    with tagswitch(typ) as case:
        if case(ktype_e.Int):
            f.write('int')

        elif case(ktype_e.Str):
            f.write('BigStr*')

        elif case(ktype_e.List):
            typ = cast(ktype.List, UP_typ)
            f.write('List<')
            GenType(typ.T, f)
            f.write('>*')

        else:
            raise AssertionError(typ)


def GenParam(p, f):
    # type: (NameType, mylib.Writer) -> None

    GenType(p.typ, f)
    f.write(' %s' % p.name)


def GenExpr(expr, f):
    # type: (kexpr_t, mylib.Writer) -> None

    UP_expr = expr
    with tagswitch(expr) as case:
        if case(kexpr_e.Int):
            expr = cast(Int, UP_expr)
            f.write('%d' % expr.i)
        else:
            raise AssertionError()


def GenStatement(st, f):
    # type: (stmt_t, mylib.Writer) -> None

    UP_st = st
    with tagswitch(st) as case:
        if case(stmt_e.Return):
            st = cast(stmt.Return, UP_st)
            # TODO: indent
            f.write('  return ')
            GenExpr(st.e, f)
            f.write(';\n')


def GenFunction(func, f):
    # type: (mod_def.Func, mylib.Writer) -> None

    # log('Function %s', func.name)

    GenType(func.sig.return_type, f)
    f.write(' %s(' % func.name)
    for i, p in enumerate(func.sig.params):
        if i != 0:
            f.write(', ')
        GenParam(p, f)
    f.write(') {\n')

    for st in func.statements:
        GenStatement(st, f)
    f.write('}\n')


def GenCpp(prog, f):
    # type: (Program, mylib.Writer) -> None

    # Every program depends on this
    f.write('#include "mycpp/runtime.h"\n')

    for module in prog.modules:

        f.write('namespace %s {\n' % module.name)
        for d in module.defs:
            UP_d = d
            with tagswitch(d) as case:
                if case(mod_def_e.Func):
                    d = cast(mod_def.Func, UP_d)
                    GenFunction(d, f)

        f.write('}  // namespace %s\n' % module.name)
