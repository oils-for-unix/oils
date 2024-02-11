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
        raise AssertionError('Expected Symbol, got %s' % nval)
    return cast(nvalue.Symbol, nval).s


def MustBeList(nval):
    # type: (nvalue_t) -> List[nvalue_t]
    if nval.tag() != nvalue_e.List:
        raise AssertionError('Expected List, got %s' % nval)
    return cast(nvalue.List, nval).items


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

    UP_nval = nval
    with tagswitch(nval) as case:

        if case(nvalue_e.Symbol):
            nval = cast(nvalue.Symbol, UP_nval)

            # TODO: Is there Void type?  That's the same as None in Python?
            # def f() -> None: ...

            if nval.s == 'Bool':
                return ktype.Bool
            elif nval.s == 'Int':
                return ktype.Int
            #elif nval.s == 'Float':
            #    return ktype.Float
            elif nval.s == 'Str':
                return ktype.Str
            else:
                raise AssertionError(nval.s)

        elif case(nvalue_e.List):
            nval = cast(nvalue.List, UP_nval)

            first = MustBeSymbol(nval.items[0])
            if first == 'List':
                return ktype.List(TransformType(nval.items[1]))
            elif first == 'Dict':
                return ktype.Dict(TransformType(nval.items[1]),
                                  TransformType(nval.items[2]))
            else:
                raise AssertionError(first)

        else:
            raise AssertionError()


def TransformParam(param_n):
    # type: (List[nvalue_t]) -> NameType
    """
    [argv [List Int]]
    """

    if len(param_n) != 2:
        raise AssertionError()

    name = MustBeSymbol(param_n[0])
    typ = TransformType(param_n[1])
    return NameType(name, typ)


def TransformParams(params_n):
    # type: (List[nvalue_t]) -> List[NameType]
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
      [which_scopes runtime_asdl::scope_t scope_e::Shopt]
    ] => (*runtime_asdl::Cell)
      (call print "hi")
    )

    Can't use = here because (scope_t=scope_e) would be parsed before
    (scope_e::Shopt)

      [which_scopes runtime_asdl::scope_t=scope_e::Shopt]

    We don't have any precedence rules.
    """
    result = []  # type: List[NameType]
    for p in params_n:
        param_n = MustBeList(p)
        #log('PN %s', param_n)
        result.append(TransformParam(param_n))
    return result


def TransformSignature(nval):
    # type: (nvalue_t) -> Signature

    sig_n = MustBeList(nval)
    if len(sig_n) != 3:
        raise AssertionError(
            'Signature should have 3 items: =>  params  return')

    first = MustBeSymbol(sig_n[0])
    if first != '=>':
        raise AssertionError('Signature should start with =>')

    params_n = MustBeList(sig_n[1])

    return Signature(TransformParams(params_n), TransformType(sig_n[2]))


def TransformFunc(func_n):
    # type: (List[nvalue_t]) -> mod_def.Func

    func_name = MustBeSymbol(func_n[1])
    out_stmts = []  # type: List[stmt_t]

    sig = TransformSignature(func_n[2])
    func = mod_def.Func(func_name, sig, out_stmts)

    stmts = func_n[3:]
    for st in stmts:
        stmt_n = MustBeList(st)

        if len(stmt_n) == 0:
            raise AssertionError("Statement shouldn't be empty")

        first = MustBeSymbol(stmt_n[0])

        if first == 'var':
            pass

        elif first == 'setvar':
            # The simple case could be
            #   x = 42
            # But there are precedence issues
            #   a,42 = (call f 42)
            # This seems better:
            #   (setvar a,42 (call f 42))
            pass

        elif first == 'call':
            pass

        elif first == 'return':
            expr = TransformExpr(stmt_n[1])
            out_stmts.append(stmt.Return(expr))

        elif first == 'break':
            pass

        elif first == 'continue':
            pass

        else:
            raise AssertionError('Invalid statment %r' % first)

    return func


def TransformModule(mod_n):
    # type: (List[nvalue_t]) -> Module

    if len(mod_n) < 2:
        raise AssertionError('Module should have at least 2 items, got %d' %
                             len(mod_n))

    mod_name = MustBeSymbol(mod_n[1])
    out_defs = []  # type: List[mod_def_t]
    module = Module(mod_name, out_defs)

    defs = mod_n[2:]

    for d in defs:
        # (global ...) (func ...) (class ...)
        def_n = MustBeList(d)

        if len(def_n) == 0:
            raise AssertionError("Module shouldn't be empty")

        first = MustBeSymbol(def_n[0])

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
    mod_n = MustBeList(nval)
    module = TransformModule(mod_n)
    prog = Program('foo', [module])
    return prog
