#!/usr/bin/env python2
"""Typed_args.py."""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_e, value_t, cmd_value
from _devbuild.gen.syntax_asdl import (loc, loc_t, ArgList, BlockArg, command,
                                       command_t, expr_e, expr_t, CommandSub,
                                       proc_sig, proc_sig_e)
from core import error
from core.error import e_usage
from frontend import location
from mycpp.mylib import dict_erase, tagswitch

from typing import Optional, Dict, List, TYPE_CHECKING, cast
if TYPE_CHECKING:
    from ysh.expr_eval import ExprEvaluator


def EvalProcDefaults(expr_ev, node):
    # type: (ExprEvaluator, command.Proc) -> Optional[List[value_t]]
    """Evaluated at time of proc DEFINITION, not time of call."""

    # TODO: remove the mutable default issue that Python has: f(x=[])
    # Whitelist Bool, Int, Float, Str.

    defaults = None  # type: List[value_t]
    UP_sig = node.sig

    if UP_sig.tag() == proc_sig_e.Closed:
        sig = cast(proc_sig.Closed, UP_sig)
        no_val = None  # type: value_t
        defaults = [no_val] * len(sig.word_params)
        for i, p in enumerate(sig.word_params):
            if p.default_val:
                val = expr_ev.EvalExpr(p.default_val, loc.Missing)
                defaults[i] = val
    return defaults


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

    def __init__(self, pos_args, named_args, args_node, is_bound=False):
        # type: (List[value_t], Dict[str, value_t], ArgList, bool) -> None
        self.pos_args = pos_args
        self.pos_consumed = 0
        # TODO: Add LHS of attribute expression to value.BoundFunc and pass
        # that through to here?
        self.is_bound = is_bound
        self.named_args = named_args
        self.args_node = args_node

    def LeftParenToken(self):
        # type: () -> loc_t
        """
        Used by functions in library/func_misc.py
        """
        return self.args_node.left

    def LeastSpecificLocation(self):
        # type: () -> loc_t
        """Returns the least specific blame location.

        Applicable to procs as well.
        """
        # return LeftParenToken() if available
        if self.args_node.left:  # may be None for proc like 'json write'
            return self.args_node.left

        return loc.Missing

    ### Words: untyped args for procs

    def Word(self):
        # type: () -> str
        return None  # TODO

    def RestWords(self):
        # type: () -> List[str]
        return None  # TODO

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

        if pos >= 0 and pos < len(self.args_node.pos_args):
            l = location.TokenForExpr(self.args_node.pos_args[pos])

            if l is not None:
                return l

        # Fall back on call
        return self.LeastSpecificLocation()

    def PosNode(self, i):
        # type: (int) -> expr_t
        """Returns the expression handle for the ith positional argument. The
        caller can use this to produce more specific error messages."""
        return self.args_node.pos_args[i]

    def _GetNextPos(self):
        # type: () -> value_t
        if len(self.pos_args) == 0:
            raise error.TypeErrVerbose(
                'Expected at least %d typed args, but only got %d' %
                (self.pos_consumed + 1, self.pos_consumed),
                self.LeastSpecificLocation())

        self.pos_consumed += 1
        return self.pos_args.pop(0)

    def PosStr(self):
        # type: () -> str
        arg = self._GetNextPos()
        UP_arg = arg
        if arg.tag() == value_e.Str:
            arg = cast(value.Str, UP_arg)
            return arg.s

        raise error.TypeErr(arg, 'Arg %d should be a Str' % self.pos_consumed,
                            self.BlamePos())

    def PosBool(self):
        # type: () -> bool
        arg = self._GetNextPos()
        UP_arg = arg
        if arg.tag() == value_e.Bool:
            arg = cast(value.Bool, UP_arg)
            return arg.b

        raise error.TypeErr(arg, 'Arg %d should be a Bool' % self.pos_consumed,
                            self.BlamePos())

    def PosInt(self):
        # type: () -> int
        arg = self._GetNextPos()
        UP_arg = arg
        if arg.tag() == value_e.Int:
            arg = cast(value.Int, UP_arg)
            return arg.i

        raise error.TypeErr(arg, 'Arg %d should be a Int' % self.pos_consumed,
                            self.BlamePos())

    def PosFloat(self):
        # type: () -> float
        arg = self._GetNextPos()
        UP_arg = arg
        if arg.tag() == value_e.Float:
            arg = cast(value.Float, UP_arg)
            return arg.f

        raise error.TypeErr(arg,
                            'Arg %d should be a Float' % self.pos_consumed,
                            self.BlamePos())

    def PosList(self):
        # type: () -> List[value_t]
        arg = self._GetNextPos()
        UP_arg = arg
        if arg.tag() == value_e.List:
            arg = cast(value.List, UP_arg)
            return arg.items

        raise error.TypeErr(arg, 'Arg %d should be a List' % self.pos_consumed,
                            self.BlamePos())

    def PosDict(self):
        # type: () -> Dict[str, value_t]
        arg = self._GetNextPos()
        UP_arg = arg
        if arg.tag() == value_e.Dict:
            arg = cast(value.Dict, UP_arg)
            return arg.d

        raise error.TypeErr(arg, 'Arg %d should be a Dict' % self.pos_consumed,
                            self.BlamePos())

    def PosExpr(self):
        # type: () -> expr_t
        arg = self._GetNextPos()
        UP_arg = arg
        if arg.tag() == value_e.Expr:
            arg = cast(value.Expr, UP_arg)
            return arg.e

        raise error.TypeErr(arg, 'Arg %d should be a Expr' % self.pos_consumed,
                            self.BlamePos())

    def PosCommand(self):
        # type: () -> command_t
        arg = self._GetNextPos()
        UP_arg = arg
        if arg.tag() == value_e.Command:
            arg = cast(value.Command, UP_arg)
            return arg.body

        raise error.TypeErr(arg,
                            'Arg %d should be a Command' % self.pos_consumed,
                            self.BlamePos())

    def PosValue(self):
        # type: () -> value_t
        return self._GetNextPos()

    def NumPos(self):
        # type: () -> int
        return len(self.pos_args)

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

    def NamedNode(self, name):
        # type: (str) -> Optional[expr_t]
        """Returns the expression handle for the argument with the given name. The
        caller can use this to produce more specific error messages."""
        # TODO
        return None

    def NamedStr(self, param_name, default_):
        # type: (str, str) -> str
        if param_name not in self.named_args:
            return default_

        val = self.named_args[param_name]
        UP_val = val
        if val.tag() == value_e.Str:
            dict_erase(self.named_args, param_name)
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
            dict_erase(self.named_args, param_name)
            return val.b

        raise error.TypeErr(val, 'Named arg %r should be a Bool' % param_name,
                            self._BlameNamed(param_name))

    def NamedInt(self, param_name, default_):
        # type: (str, int) -> int
        if param_name not in self.named_args:
            return default_

        val = self.named_args[param_name]
        UP_val = val
        if val.tag() == value_e.Int:
            val = cast(value.Int, UP_val)
            dict_erase(self.named_args, param_name)
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
            dict_erase(self.named_args, param_name)
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
            dict_erase(self.named_args, param_name)
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
            dict_erase(self.named_args, param_name)
            return val.d

        raise error.TypeErr(val, 'Named arg %r should be a Dict' % param_name,
                            self._BlameNamed(param_name))

    def RestNamed(self):
        # type: () -> Dict[str, value_t]
        ret = self.named_args
        self.named_args = {}
        return ret

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

            blame = self.args_node.named_delim  # type: loc_t
            if blame is None:
                blame = self.LeastSpecificLocation()

            raise error.TypeErrVerbose(
                'Got unexpected named args: %s' % bad_args, blame)


def ReaderForProc(cmd_val):
    # type: (cmd_value.Argv) -> Reader

    # mycpp rewrite: doesn't understand 'or' pattern
    pos_args = (cmd_val.pos_args if cmd_val.pos_args is not None else [])
    named_args = (cmd_val.named_args if cmd_val.named_args is not None else {})

    arg_list = (cmd_val.typed_args
                if cmd_val.typed_args is not None else ArgList.CreateNull())

    return Reader(pos_args, named_args, arg_list)


def DoesNotAccept(arg_list):
    # type: (Optional[ArgList]) -> None
    if arg_list is not None:
        e_usage('got unexpected typed args', arg_list.left)


def RequiredExpr(arg_list):
    # type: (Optional[ArgList]) -> Optional[expr_t]
    if arg_list is None:
        e_usage('Expected an expression', loc.Missing)

    n = len(arg_list.pos_args)
    if n == 0:
        e_usage('Expected an expression', arg_list.left)

    elif n == 1:
        return arg_list.pos_args[0]

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

    n = len(arg_list.pos_args)
    if n == 0:
        return None

    elif n == 1:
        arg = arg_list.pos_args[0]
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

    n = len(arg_list.pos_args)
    if n == 0:
        return None

    elif n == 1:
        arg = arg_list.pos_args[0]
        if arg.tag() == expr_e.BlockArg:
            return cast(BlockArg, arg)
        else:
            return None

    else:
        e_usage('Too many typed args (expected one block)', arg_list.left)
