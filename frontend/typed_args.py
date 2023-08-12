#!/usr/bin/env python2
"""Typed_args.py."""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value_t, value_str
from _devbuild.gen.syntax_asdl import (loc, ArgList, BlockArg, command_t,
                                       expr_e, expr_t, CommandSub)
from core import error
from core.error import e_usage
from mycpp.mylib import tagswitch

from typing import Optional, Dict, List, cast


class Spec(object):
    """Utility to express argument specifications (runtime typechecking)."""

    def __init__(self, pos_args, named_args):
        # type: (List[int], Dict[str, int]) -> None
        """Empty constructor for mycpp."""
        self.pos_args = pos_args
        self.named_args = named_args

    def AssertArgs(self, func_name, pos_args, named_args):
        # type: (str, List[value_t], Dict[str, value_t]) -> None
        """Assert any type differences between the spec and the given args."""
        nargs = len(pos_args)
        expected = len(self.pos_args)
        if nargs != expected:
            raise error.InvalidType(
                "%s() expects %d arguments but %d were given" %
                (func_name, expected, nargs), loc.Missing)

        nargs = len(named_args)
        expected = len(self.named_args)
        if len(named_args) != 0:
            raise error.InvalidType(
                "%s() expects %d named arguments but %d were given" %
                (func_name, expected, nargs), loc.Missing)

        for i in xrange(len(pos_args)):
            expected = self.pos_args[i]
            got = pos_args[i]
            if got.tag() != expected:
                msg = "%s() expected %s" % (func_name, value_str(expected))
                raise error.InvalidType2(got, msg, loc.Missing)

        for name in named_args:
            expected = self.named_args[name]
            got = named_args[name]
            if got.tag() != expected:
                msg = "%s() expected %s" % (func_name, value_str(expected))
                raise error.InvalidType2(got, msg, loc.Missing)


class Reader(object):
    """
    func f(a Str) {

        is equivalent to

        t = typed_args.Reader(pos_args, named_args)
        a = t.PosStr()
        t.Done()  # checks for no more args

    func f(a Str, b Int, ...args; c=0, d='foo', ...named) {

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

    proc p(a, b; a Str, b Int; c=0; block) {

        is equivalent to

        t = typed_args.Reader(argv, pos_args, named_args)

        a = t.Word()
        b = t.Word()

        t.NamedInt('c', 0)

        block = t.Block()

        t.Done()
    """

    def __init__(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> None
        self.pos_args = pos_args
        self.named_args = named_args

    ### Words: untyped args for procs

    def Word(self):
        # type: () -> str
        return None  # TODO

    def RestWords(self):
        # type: () -> List[str]
        return None  # TODO

    ### Typed positional args

    # TODO: may need location info
    def PosStr(self):
        # type: () -> str
        return None  # TODO

    def PosInt(self):
        # type: () -> int
        return -1  # TODO

    def RestPos(self):
        # type: () -> List[value_t]
        return None  # TODO

    ### Typed named args

    def NamedStr(self, param_name, default_):
        # type: (str, str) -> str
        return None  # TODO

    def NamedInt(self, param_name, default_):
        # type: (str, int) -> int
        return -1  # TODO

    def RestNamed(self):
        # type: () -> Dict[str, value_t]
        return None  # TODO

    def Block(self):
        # type: () -> command_t
        """
        Block arg for proc
        """
        # TODO: is this BraceGroup?
        return None  # TODO

    def Done(self):
        # type: () -> None
        """
        Check that no extra arguments were passed

        4 checks: words, pos, named, block

        It's a little weird that we report all errors at the end, but no
        problem
        """
        # Note: Python throws TypeError on mismatch
        pass


def DoesNotAccept(arg_list):
    # type: (Optional[ArgList]) -> None
    if arg_list is not None:
        e_usage('got unexpected typed args', arg_list.left)


def RequiredExpr(arg_list):
    # type: (Optional[ArgList]) -> Optional[expr_t]
    if arg_list is None:
        e_usage('Expected an expression', loc.Missing)

    n = len(arg_list.positional)
    if n == 0:
        e_usage('Expected an expression', arg_list.left)

    elif n == 1:
        return arg_list.positional[0]

    else:
        e_usage('Too many typed args (expected one expression)', arg_list.left)


def GetOneBlock(arg_list):
    # type: (Optional[ArgList]) -> Optional[command_t]
    """Returns the first block arg, if any.

    For cd { }, shopt { }, etc.

    Errors:
      - the first arg isn't a block
      - more than 1 arg
    """

    if arg_list is None:
        return None

    n = len(arg_list.positional)
    if n == 0:
        return None

    elif n == 1:
        arg = arg_list.positional[0]
        UP_arg = arg

        # Could we somehow consolidate these?
        with tagswitch(arg) as case:
            if case(expr_e.BlockArg):  # cd /tmp { echo hi }
                arg = cast(BlockArg, UP_arg)
                return arg.brace_group

            # TODO: we need an expr_ev for cd /tmp (myblock)
            elif case(expr_e.CommandSub):  # cd /tmp (^(echo hi))
                arg = cast(CommandSub, UP_arg)
                return arg.child

            else:
                e_usage('Expected block argument', arg_list.left)

    else:
        e_usage('Too many typed args (expected one block)', arg_list.left)


def GetLiteralBlock(arg_list):
    # type: (Optional[ArgList]) -> Optional[BlockArg]
    """Returns the first block literal arg, if any.

    For Hay evaluation.

    Errors:
      - more than 1 arg
    """

    if arg_list is None:
        return None

    n = len(arg_list.positional)
    if n == 0:
        return None

    elif n == 1:
        arg = arg_list.positional[0]
        if arg.tag() == expr_e.BlockArg:
            return cast(BlockArg, arg)
        else:
            return None

    else:
        e_usage('Too many typed args (expected one block)', arg_list.left)
