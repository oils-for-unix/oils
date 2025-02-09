#!/usr/bin/env python2
"""
func_reflect.py - Functions for reflecting on Oils code - OSH or YSH.
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import scope_e
from _devbuild.gen.syntax_asdl import (Token, source, debug_frame,
                                       debug_frame_e)
from _devbuild.gen.value_asdl import (value, value_e, value_t, cmd_frag)

from core import alloc
from core import error
from core import main_loop
from core import state
from core import vm
from data_lang import j8
from display import ui
from frontend import location
from frontend import reader
from frontend import typed_args
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import log, tagswitch

from typing import List, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from frontend import parse_lib

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
        unused_vm = rd.PosValue()  # vm.id()
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
        index = mops.BigTruncate(rd.PosInt())
        rd.Done()

        length = len(self.mem.var_stack)
        if index < 0:
            index += length
        if 0 <= index and index < length:
            return value.Frame(self.mem.var_stack[index])
        else:
            raise error.Structured(3, "Invalid frame %d" % index,
                                   rd.LeftParenToken())


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
        return value.Null
        # TODO: I guess you have to bind 2 frames?
        #return Command(cmd_frag.Expr(frag), frame, None)


class GetDebugStack(vm._Callable):

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        unused_self = rd.PosObj()
        rd.Done()

        debug_frames = [
            value.DebugFrame(fr) for fr in self.mem.debug_stack
            if fr.tag() in (debug_frame_e.Call, debug_frame_e.Source)
        ]  # type: List[value_t]
        return value.List(debug_frames)


def _FormatDebugFrame(buf, frame_index, token):
    # type: (mylib.Writer, int, Token) -> None
    """
    Based on _AddCallToken in core/state.py
    Should probably move that into core/dev.py or something, and unify them

    We also want the column number so we can print ^==
    """
    # note: absolute path can be lon,g, but Python prints it too
    call_source = ui.GetLineSourceString(token.line)
    line_num = token.line.line_num
    call_line = token.line.content

    func_str = ''
    # This gives the wrong token?  If we are calling p, it gives the definition
    # of p.  It doesn't give the func/proc that contains the call to p.

    #if def_tok is not None:
    #    #log('DEF_TOK %s', def_tok)
    #    func_str = ' in %s' % lexer.TokenVal(def_tok)

    # should be exactly 1 line
    buf.write('  #%d %s:%d\n' % (frame_index, call_source, line_num))

    maybe_newline = '' if call_line.endswith('\n') else '\n'
    buf.write('    %s%s' % (call_line, maybe_newline))

    buf.write('    ')  # prefix
    ui.PrintCaretLine(call_line, token.col, token.length, buf)


class FormatDebugFrame(vm._Callable):

    def __init__(self):
        # type: () -> None
        vm._Callable.__init__(self)

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        frame = rd.PosDebugFrame()

        # the frame index may be useful if you have concurrent stack traces?
        frame_index = mops.BigTruncate(rd.PosInt())

        rd.Done()

        UP_frame = frame
        buf = mylib.BufWriter()
        with tagswitch(frame) as case:
            if case(debug_frame_e.Call):
                frame = cast(debug_frame.Call, UP_frame)
                #result = 'call '
                _FormatDebugFrame(buf, frame_index, frame.call_tok)
            elif case(debug_frame_e.Source):
                frame = cast(debug_frame.Source, UP_frame)
                #result = 'source '
                _FormatDebugFrame(buf, frame_index, frame.call_tok)
            else:
                raise AssertionError()
        return value.Str(buf.getvalue())


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
        set_global = rd.NamedBool('global', False)
        rd.Done()
        scope = scope_e.GlobalOnly if set_global else scope_e.LocalOnly
        self.mem.SetNamed(location.LName(var_name), val, scope)
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

        return value.Command(cmd_frag.Expr(cmd), self.mem.CurrentFrame(),
                             self.mem.GlobalFrame())


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
