#!/usr/bin/env python2
from __future__ import print_function

from _devbuild.gen.runtime_asdl import cmd_value, ProcArgs, Cell
from _devbuild.gen.syntax_asdl import (loc, loc_t, ArgList, command_t, expr_t,
                                       Token)
from _devbuild.gen.value_asdl import (value, value_e, value_t, RegexMatch, Obj,
                                      cmd_frag, cmd_frag_e, cmd_frag_str,
                                      LiteralBlock)
from core import error
from core.error import e_usage
from frontend import location
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import log, tagswitch

from typing import Dict, List, Optional, cast

_ = log


def DoesNotAccept(proc_args):
    # type: (Optional[ProcArgs]) -> None
    if proc_args is not None:
        e_usage('got unexpected typed args', proc_args.typed_args.left)


def OptionalCommandBlock(cmd_val):
    # type: (cmd_value.Argv) -> Optional[value.Command]

    cmd = None  # type: Optional[value.Command]
    if cmd_val.proc_args:
        r = ReaderForProc(cmd_val)
        cmd = r.OptionalCommandBlock()
        r.Done()
    return cmd


def OptionalBlock(cmd_val):
    # type: (cmd_value.Argv) -> Optional[command_t]
    """Helper for shopt, etc."""

    cmd = None  # type: Optional[command_t]
    if cmd_val.proc_args:
        r = ReaderForProc(cmd_val)
        cmd = r.OptionalBlock()
        r.Done()
    return cmd


def OptionalLiteralBlock(cmd_val):
    # type: (cmd_value.Argv) -> Optional[LiteralBlock]
    """Helper for Hay """

    block = None  # type: Optional[LiteralBlock]
    if cmd_val.proc_args:
        r = ReaderForProc(cmd_val)
        block = r.OptionalLiteralBlock()
        r.Done()
    return block


def GetCommandFrag(bound):
    # type: (value.Command) -> command_t

    frag = bound.frag
    with tagswitch(frag) as case:
        if case(cmd_frag_e.LiteralBlock):
            lit = cast(LiteralBlock, frag)
            return lit.brace_group
        elif case(cmd_frag_e.Expr):
            expr = cast(cmd_frag.Expr, frag)
            return expr.c
        else:
            raise AssertionError(cmd_frag_str(frag.tag()))


def ReaderForProc(cmd_val):
    # type: (cmd_value.Argv) -> Reader

    proc_args = cmd_val.proc_args

    if proc_args:
        # mycpp rewrite: doesn't understand 'or' pattern
        pos_args = (proc_args.pos_args
                    if proc_args.pos_args is not None else [])
        named_args = (proc_args.named_args
                      if proc_args.named_args is not None else {})

        arg_list = (proc_args.typed_args if proc_args.typed_args is not None
                    else ArgList.CreateNull())
        block_arg = proc_args.block_arg
    else:
        pos_args = []
        named_args = {}
        arg_list = ArgList.CreateNull()
        block_arg = None

    rd = Reader(pos_args, named_args, block_arg, arg_list)

    # Fix location info bug with 'try' or try foo' -- it should get a typed arg
    rd.SetFallbackLocation(cmd_val.arg_locs[0])
    return rd


class Reader(object):
    """
    func f(a Str) { echo hi }

        is equivalent to

        t = typed_args.Reader(pos_args, named_args)
        a = t.PosStr()
        t.Done()  # checks for no more args

    func f(a Str, b Int, ...args; c=0, d='foo', ...named) { echo hi }
      echo hi
    }

        is equivalent to

        t = typed_args.Reader(pos_args, named_args)
        a = t.PosStr()
        b = t.PosInt()
        args = t.RestPos()

        t.NamedInt('c', 0)
        t.NamedStr('d', 'foo')
        named = t.RestNamed()

        t.Done()

    procs have more options:

    proc p(a, b; a Str, b Int; c=0; block) { echo hi }

    Builtin procs use:

    - args.Reader() and generated flag_def.py APIs for the words
    - typed_args.Reader() for the positional/named typed args, constructed with
      ReaderForProc()
    """

    def __init__(
            self,
            pos_args,  # type: List[value_t]
            named_args,  # type: Dict[str, value_t]
            block_arg,  # type: Optional[value_t]
            arg_list,  # type: ArgList
            is_bound=False,  # type: bool
    ):
        # type: (...) -> None

        self.pos_args = pos_args
        self.pos_consumed = 0
        # TODO: Add LHS of attribute expression to value.BoundFunc and pass
        # that through to here?
        self.is_bound = is_bound
        self.named_args = named_args
        self.block_arg = block_arg

        # Note: may be ArgList.CreateNull()
        self.arg_list = arg_list

        self.fallback_loc = loc.Missing  # type: loc_t

    def SetFallbackLocation(self, blame_loc):
        # type: (loc_t) -> None
        """ In case of empty ArgList, the location we'll blame """
        self.fallback_loc = blame_loc

    def LeftParenToken(self):
        # type: () -> Token
        """ Used by functions in library/func_misc.py """
        return self.arg_list.left

    def LeastSpecificLocation(self):
        # type: () -> loc_t
        """Returns the least specific blame location.

        Applicable to procs as well.
        """
        # arg_list.left may be None for 'json write', which uses ReaderForProc,
        # ArgList.CreateNull()
        if self.arg_list.left:
            return self.arg_list.left

        return self.fallback_loc

    ### Typed positional args

    def BlamePos(self):
        # type: () -> loc_t
        """Returns the location of the most recently consumed argument.

        If no arguments have been consumed, the location of the function call
        is returned.
        """
        pos = self.pos_consumed - 1
        if self.is_bound:
            # Token for the first "argument" of a bound function call isn't in
            # the same part of the expression
            pos -= 1

        if self.arg_list.pos_args is None:
            # PluginCall() and CallConvertFunc() don't have pos_args
            return self.LeastSpecificLocation()

        if 0 <= pos and pos < len(self.arg_list.pos_args):
            l = location.TokenForExpr(self.arg_list.pos_args[pos])

            if l is not None:
                return l

        # Fall back on call
        return self.LeastSpecificLocation()

    def PosValue(self):
        # type: () -> value_t
        if len(self.pos_args) == 0:
            # TODO: Print the builtin name
            raise error.TypeErrVerbose(
                'Expected at least %d typed args, but only got %d' %
                (self.pos_consumed + 1, self.pos_consumed),
                self.LeastSpecificLocation())

        self.pos_consumed += 1
        val = self.pos_args.pop(0)

        # Should be value.Null
        assert val is not None
        return val

    def OptionalValue(self):
        # type: () -> Optional[value_t]
        if len(self.pos_args) == 0:
            return None
        self.pos_consumed += 1
        return self.pos_args.pop(0)

    def _ToStr(self, val):
        # type: (value_t) -> str
        if val.tag() == value_e.Str:
            return cast(value.Str, val).s

        raise error.TypeErr(val, 'Arg %d should be a Str' % self.pos_consumed,
                            self.BlamePos())

    def _ToBool(self, val):
        # type: (value_t) -> bool
        if val.tag() == value_e.Bool:
            return cast(value.Bool, val).b

        raise error.TypeErr(val, 'Arg %d should be a Bool' % self.pos_consumed,
                            self.BlamePos())

    def _ToInt(self, val):
        # type: (value_t) -> mops.BigInt
        if val.tag() == value_e.Int:
            return cast(value.Int, val).i

        raise error.TypeErr(val, 'Arg %d should be an Int' % self.pos_consumed,
                            self.BlamePos())

    def _ToFloat(self, val):
        # type: (value_t) -> float
        if val.tag() == value_e.Float:
            return cast(value.Float, val).f

        raise error.TypeErr(val,
                            'Arg %d should be a Float' % self.pos_consumed,
                            self.BlamePos())

    def _ToBashArray(self, val):
        # type: (value_t) -> List[str]
        if val.tag() == value_e.BashArray:
            return cast(value.BashArray, val).strs

        raise error.TypeErr(val,
                            'Arg %d should be a BashArray' % self.pos_consumed,
                            self.BlamePos())

    def _ToSparseArray(self, val):
        # type: (value_t) -> value.SparseArray
        if val.tag() == value_e.SparseArray:
            return cast(value.SparseArray, val)

        raise error.TypeErr(
            val, 'Arg %d should be a SparseArray' % self.pos_consumed,
            self.BlamePos())

    def _ToList(self, val):
        # type: (value_t) -> List[value_t]
        if val.tag() == value_e.List:
            return cast(value.List, val).items

        raise error.TypeErr(val, 'Arg %d should be a List' % self.pos_consumed,
                            self.BlamePos())

    def _ToDict(self, val):
        # type: (value_t) -> Dict[str, value_t]
        if val.tag() == value_e.Dict:
            return cast(value.Dict, val).d

        raise error.TypeErr(val, 'Arg %d should be a Dict' % self.pos_consumed,
                            self.BlamePos())

    def _ToObj(self, val):
        # type: (value_t) -> Obj
        if val.tag() == value_e.Obj:
            return cast(Obj, val)

        raise error.TypeErr(val, 'Arg %d should be a Obj' % self.pos_consumed,
                            self.BlamePos())

    def _ToPlace(self, val):
        # type: (value_t) -> value.Place
        if val.tag() == value_e.Place:
            return cast(value.Place, val)

        raise error.TypeErr(val,
                            'Arg %d should be a Place' % self.pos_consumed,
                            self.BlamePos())

    def _ToMatch(self, val):
        # type: (value_t) -> RegexMatch
        if val.tag() == value_e.Match:
            return cast(RegexMatch, val)

        raise error.TypeErr(val,
                            'Arg %d should be a Match' % self.pos_consumed,
                            self.BlamePos())

    def _ToEggex(self, val):
        # type: (value_t) -> value.Eggex
        if val.tag() == value_e.Eggex:
            return cast(value.Eggex, val)

        raise error.TypeErr(val,
                            'Arg %d should be an Eggex' % self.pos_consumed,
                            self.BlamePos())

    def _ToExpr(self, val):
        # type: (value_t) -> expr_t
        if val.tag() == value_e.Expr:
            return cast(value.Expr, val).e

        raise error.TypeErr(val, 'Arg %d should be a Expr' % self.pos_consumed,
                            self.BlamePos())

    def _ToFrame(self, val):
        # type: (value_t) -> Dict[str, Cell]
        if val.tag() == value_e.Frame:
            return cast(value.Frame, val).frame

        raise error.TypeErr(val,
                            'Arg %d should be a Frame' % self.pos_consumed,
                            self.BlamePos())

    def _ToCommandFrag(self, val):
        # type: (value_t) -> command_t
        if val.tag() == value_e.CommandFrag:
            return cast(value.CommandFrag, val).c

        # TODO: remove this.  Many builtin commands rely on it.
        if val.tag() == value_e.Command:
            bound = cast(value.Command, val)
            return GetCommandFrag(bound)

        raise error.TypeErr(
            val, 'Arg %d should be a CommandFrag' % self.pos_consumed,
            self.BlamePos())

    def _ToCommand(self, val):
        # type: (value_t) -> value.Command
        if val.tag() == value_e.Command:
            return cast(value.Command, val)
        raise error.TypeErr(val,
                            'Arg %d should be a Command' % self.pos_consumed,
                            self.BlamePos())

    def _ToLiteralBlock(self, val):
        # type: (value_t) -> LiteralBlock
        """ Used by Hay """
        if val.tag() == value_e.Command:
            frag = cast(value.Command, val).frag
            with tagswitch(frag) as case:
                if case(cmd_frag_e.LiteralBlock):
                    lit = cast(LiteralBlock, frag)
                    return lit
                else:
                    raise AssertionError()

        raise error.TypeErr(
            val, 'Arg %d should be a LiteralBlock' % self.pos_consumed,
            self.BlamePos())

    def PosStr(self):
        # type: () -> str
        val = self.PosValue()
        return self._ToStr(val)

    def OptionalStr(self, default_=None):
        # type: (Optional[str]) -> Optional[str]
        val = self.OptionalValue()
        if val is None:
            return default_
        return self._ToStr(val)

    def PosBool(self):
        # type: () -> bool
        val = self.PosValue()
        return self._ToBool(val)

    def PosInt(self):
        # type: () -> mops.BigInt
        val = self.PosValue()
        return self._ToInt(val)

    def OptionalInt(self, default_):
        # type: (int) -> mops.BigInt
        val = self.OptionalValue()
        if val is None:
            return mops.BigInt(default_)
        return self._ToInt(val)

    def PosFloat(self):
        # type: () -> float
        val = self.PosValue()
        return self._ToFloat(val)

    def PosBashArray(self):
        # type: () -> List[str]
        val = self.PosValue()
        return self._ToBashArray(val)

    def PosSparseArray(self):
        # type: () -> value.SparseArray
        val = self.PosValue()
        return self._ToSparseArray(val)

    def PosList(self):
        # type: () -> List[value_t]
        val = self.PosValue()
        return self._ToList(val)

    def PosDict(self):
        # type: () -> Dict[str, value_t]
        val = self.PosValue()
        return self._ToDict(val)

    def PosObj(self):
        # type: () -> Obj
        val = self.PosValue()
        return self._ToObj(val)

    def PosPlace(self):
        # type: () -> value.Place
        val = self.PosValue()
        return self._ToPlace(val)

    def PosEggex(self):
        # type: () -> value.Eggex
        val = self.PosValue()
        return self._ToEggex(val)

    def PosMatch(self):
        # type: () -> RegexMatch
        val = self.PosValue()
        return self._ToMatch(val)

    def PosFrame(self):
        # type: () -> Dict[str, Cell]
        val = self.PosValue()
        return self._ToFrame(val)

    def PosCommandFrag(self):
        # type: () -> command_t
        val = self.PosValue()
        return self._ToCommandFrag(val)

    def PosCommand(self):
        # type: () -> value.Command
        val = self.PosValue()
        return self._ToCommand(val)

    def PosExpr(self):
        # type: () -> expr_t
        val = self.PosValue()
        return self._ToExpr(val)

    #
    # Block arg
    #

    def OptionalCommandBlock(self):
        # type: () -> Optional[value.Command]
        if self.block_arg is None:
            return None
        return self._ToCommand(self.block_arg)

    def RequiredBlock(self):
        # type: () -> command_t
        if self.block_arg is None:
            raise error.TypeErrVerbose('Expected a block arg',
                                       self.LeastSpecificLocation())
        return self._ToCommandFrag(self.block_arg)

    def OptionalBlock(self):
        # type: () -> Optional[command_t]
        if self.block_arg is None:
            return None
        return self._ToCommandFrag(self.block_arg)

    def OptionalLiteralBlock(self):
        # type: () -> Optional[LiteralBlock]
        """
        Used by Hay
        """
        if self.block_arg is None:
            return None
        return self._ToLiteralBlock(self.block_arg)

    def RestPos(self):
        # type: () -> List[value_t]
        ret = self.pos_args
        self.pos_args = []
        return ret

    ### Typed named args

    def _BlameNamed(self, name):
        # type: (str) -> loc_t
        """Returns the location of the given named argument."""
        # TODO: be more specific
        return self.LeastSpecificLocation()

    def NamedStr(self, param_name, default_):
        # type: (str, str) -> str
        if param_name not in self.named_args:
            return default_

        val = self.named_args[param_name]
        UP_val = val
        if val.tag() == value_e.Str:
            mylib.dict_erase(self.named_args, param_name)
            val = cast(value.Str, UP_val)
            return val.s

        raise error.TypeErr(val, 'Named arg %r should be a Str' % param_name,
                            self._BlameNamed(param_name))

    def NamedBool(self, param_name, default_):
        # type: (str, bool) -> bool
        if param_name not in self.named_args:
            return default_

        val = self.named_args[param_name]
        UP_val = val
        if val.tag() == value_e.Bool:
            val = cast(value.Bool, UP_val)
            mylib.dict_erase(self.named_args, param_name)
            return val.b

        raise error.TypeErr(val, 'Named arg %r should be a Bool' % param_name,
                            self._BlameNamed(param_name))

    def NamedInt(self, param_name, default_):
        # type: (str, int) -> mops.BigInt
        if param_name not in self.named_args:
            return mops.BigInt(default_)

        val = self.named_args[param_name]
        UP_val = val
        if val.tag() == value_e.Int:
            val = cast(value.Int, UP_val)
            mylib.dict_erase(self.named_args, param_name)
            return val.i

        raise error.TypeErr(val, 'Named arg %r should be a Int' % param_name,
                            self._BlameNamed(param_name))

    def NamedFloat(self, param_name, default_):
        # type: (str, float) -> float
        if param_name not in self.named_args:
            return default_

        val = self.named_args[param_name]
        UP_val = val
        if val.tag() == value_e.Float:
            val = cast(value.Float, UP_val)
            mylib.dict_erase(self.named_args, param_name)
            return val.f

        raise error.TypeErr(val, 'Named arg %r should be a Float' % param_name,
                            self._BlameNamed(param_name))

    def NamedList(self, param_name, default_):
        # type: (str, List[value_t]) -> List[value_t]
        if param_name not in self.named_args:
            return default_

        val = self.named_args[param_name]
        UP_val = val
        if val.tag() == value_e.List:
            val = cast(value.List, UP_val)
            mylib.dict_erase(self.named_args, param_name)
            return val.items

        raise error.TypeErr(val, 'Named arg %r should be a List' % param_name,
                            self._BlameNamed(param_name))

    def NamedDict(self, param_name, default_):
        # type: (str, Dict[str, value_t]) -> Dict[str, value_t]
        if param_name not in self.named_args:
            return default_

        val = self.named_args[param_name]
        UP_val = val
        if val.tag() == value_e.Dict:
            val = cast(value.Dict, UP_val)
            mylib.dict_erase(self.named_args, param_name)
            return val.d

        raise error.TypeErr(val, 'Named arg %r should be a Dict' % param_name,
                            self._BlameNamed(param_name))

    def RestNamed(self):
        # type: () -> Dict[str, value_t]
        ret = self.named_args
        self.named_args = {}
        return ret

    def Done(self):
        # type: () -> None
        """
        Check that no extra arguments were passed

        4 checks: words, pos, named, block

        It's a little weird that we report all errors at the end, but no
        problem
        """
        # Note: Python throws TypeError on mismatch
        if len(self.pos_args):
            n = self.pos_consumed
            # Excluding implicit first arg should make errors less confusing
            if self.is_bound:
                n -= 1

            self.pos_consumed += 1  # point to the first uncomsumed arg

            raise error.TypeErrVerbose(
                'Expected %d typed args, but got %d' %
                (n, n + len(self.pos_args)), self.BlamePos())

        if len(self.named_args):
            bad_args = ', '.join(self.named_args.keys())

            blame = self.arg_list.semi_tok  # type: loc_t
            if blame is None:
                blame = self.LeastSpecificLocation()

            raise error.TypeErrVerbose(
                'Got unexpected named args: %s' % bad_args, blame)
