#!/usr/bin/env python2
"""
func_reflect.py - Functions for reflecting on Oils code - OSH or YSH.
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import (scope_e)
from _devbuild.gen.syntax_asdl import source
from _devbuild.gen.value_asdl import (value, value_e, value_t, cmd_frag)

from core import alloc
from core import error
from core import main_loop
from core import state
from core import vm
from data_lang import j8
from frontend import location
from frontend import reader
from frontend import typed_args
from mycpp import mops
from mycpp.mylib import log, tagswitch
from ysh import expr_eval

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from frontend import parse_lib
    from display import ui

_ = log


class Id(vm._Callable):
    """Return an integer object ID, like Python's id().

    Long shot: pointer tagging, boxless value_t, and small string optimization
    could mean that value.Str is no longer heap-allocated, and thus doesn't
    have a GC ID?

    What about value.{Bool,Int,Float}?

    I guess only mutable objects can have IDs then
    """

    def __init__(self):
        # type: () -> None
        vm._Callable.__init__(self)

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        val = rd.PosValue()
        rd.Done()

        # Select mutable values for now
        with tagswitch(val) as case:
            if case(value_e.List, value_e.Dict, value_e.Obj):
                id_ = j8.HeapValueId(val)
                return value.Int(mops.IntWiden(id_))
            else:
                raise error.TypeErr(val, 'id() expected List, Dict, or Obj',
                                    rd.BlamePos())
        raise AssertionError()


class GetFrame(vm._Callable):

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        unused_self = rd.PosObj()
        index = rd.PosInt()
        rd.Done()

        # TODO: 0 is global, -1 is current, -2 is parent
        return value.Frame(self.mem.CurrentFrame())


class BindFrame(vm._Callable):

    def __init__(self):
        # type: () -> None
        vm._Callable.__init__(self)

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # TODO: also take an ExprFrag -> Expr

        frag = rd.PosCommandFrag()
        frame = rd.PosFrame()
        rd.Done()
        return value.Command(cmd_frag.Expr(frag), frame)


class Shvar_get(vm._Callable):
    """Look up with dynamic scope."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        name = rd.PosStr()
        rd.Done()
        return state.DynamicGetVar(self.mem, name, scope_e.Dynamic)


class GetVar(vm._Callable):
    """Look up a variable, with normal scoping rules."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        name = rd.PosStr()
        rd.Done()
        return state.DynamicGetVar(self.mem, name, scope_e.LocalOrGlobal)


class SetVar(vm._Callable):
    """Set a variable in the local scope.

    We could have a separae setGlobal() too.
    """

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        var_name = rd.PosStr()
        val = rd.PosValue()
        rd.Done()
        self.mem.SetNamed(location.LName(var_name), val, scope_e.LocalOnly)
        return value.Null


class ParseCommand(vm._Callable):

    def __init__(self, parse_ctx, mem, errfmt):
        # type: (parse_lib.ParseContext, state.Mem, ui.ErrorFormatter) -> None
        self.parse_ctx = parse_ctx
        self.mem = mem
        self.errfmt = errfmt

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        code_str = rd.PosStr()
        rd.Done()

        line_reader = reader.StringLineReader(code_str, self.parse_ctx.arena)
        c_parser = self.parse_ctx.MakeOshParser(line_reader)

        # TODO: it would be nice to point to the location of the expression
        # argument
        src = source.Dynamic('parseCommand()', rd.LeftParenToken())
        with alloc.ctx_SourceCode(self.parse_ctx.arena, src):
            try:
                cmd = main_loop.ParseWholeFile(c_parser)
            except error.Parse as e:
                # This prints the location
                self.errfmt.PrettyPrintError(e)

                # TODO: add inner location info to this structured error
                raise error.Structured(3, "Syntax error in parseCommand()",
                                       rd.LeftParenToken())

        # TODO: It's a little weird that this captures?
        # We should have scoping like 'eval $mystr'
        # Or we should have
        #
        # var c = parseCommand('echo hi')  # raw AST
        # var block = Block(c)  # attachs the current frame
        #
        # Yeah we might need this for value.Expr too, to control evaluation of
        # names
        #
        # value.Expr vs. value.BoundExpr - it's bound to the frame it's defined
        # in
        # value.Command vs. value.Block - BoundCommand?

        return value.Command(cmd_frag.Expr(cmd), self.mem.CurrentFrame())


class ParseExpr(vm._Callable):

    def __init__(self, parse_ctx, errfmt):
        # type: (parse_lib.ParseContext, ui.ErrorFormatter) -> None
        self.parse_ctx = parse_ctx
        self.errfmt = errfmt

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        code_str = rd.PosStr()
        rd.Done()

        return value.Null


class EvalExpr(vm._Callable):

    def __init__(self, expr_ev):
        # type: (expr_eval.ExprEvaluator) -> None
        self.expr_ev = expr_ev

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        unused_self = rd.PosObj()
        lazy = rd.PosExpr()
        rd.Done()

        result = self.expr_ev.EvalExpr(lazy, rd.LeftParenToken())

        return result
