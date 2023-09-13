#!/usr/bin/env python2
"""Typed_args.py."""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value_t, cmd_value
from _devbuild.gen.syntax_asdl import (loc, ArgList, BlockArg, command_t,
                                       expr_e, expr_t, CommandSub)
from core import error
from core.error import e_usage
from frontend import lexer
from mycpp.mylib import dict_erase, tagswitch
from ysh import val_ops

from typing import Optional, Dict, List, TYPE_CHECKING, cast
if TYPE_CHECKING:
    from ysh.expr_eval import ExprEvaluator


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

    def __init__(self, argv, pos_args, named_args):
        # type: (List[str], List[value_t], Dict[str, value_t]) -> None
        self.argv = argv
        self.args_consumed = 0
        self.pos_args = pos_args
        self.pos_consumed = 0
        self.named_args = named_args

    ### Words: untyped args for procs

    def Word(self):
        # type: () -> str
        if self.argv is None or len(self.argv) == 0:
            # TODO: like _GetNestPos, we should add location info
            raise error.TypeErrVerbose(
                'Expected at least %d arguments, but only got %d' %
                (self.args_consumed + 1, self.args_consumed), loc.Missing)

        self.args_consumed += 1
        return self.argv.pop(0)

    def RestWords(self):
        # type: () -> List[str]
        return self.argv

    ### Typed positional args

    def _GetNextPos(self):
        # type: () -> value_t
        if self.pos_args is None or len(self.pos_args) == 0:
            # TODO: may need location info
            is_proc = self.argv is not None
            arguments = "typed arguments" if is_proc else "arguments"
            raise error.TypeErrVerbose(
                'Expected at least %d %s, but only got %d' %
                (self.pos_consumed + 1, arguments, self.pos_consumed), loc.Missing)

        self.pos_consumed += 1
        return self.pos_args.pop(0)

    def PosStr(self):
        # type: () -> str
        arg = self._GetNextPos()
        msg = 'Arg %d should be a Str' % self.pos_consumed
        return val_ops.ToStr(arg, msg, loc.Missing)

    def PosInt(self):
        # type: () -> int
        arg = self._GetNextPos()
        msg = 'Arg %d should be an Int' % self.pos_consumed
        return val_ops.ToInt(arg, msg, loc.Missing)

    def PosFloat(self):
        # type: () -> float
        arg = self._GetNextPos()
        msg = 'Arg %d should be a Float' % self.pos_consumed
        return val_ops.ToFloat(arg, msg, loc.Missing)

    def PosList(self):
        # type: () -> List[value_t]
        arg = self._GetNextPos()
        msg = 'Arg %d should be a List' % self.pos_consumed
        return val_ops.ToList(arg, msg, loc.Missing)

    def PosDict(self):
        # type: () -> Dict[str, value_t]
        arg = self._GetNextPos()
        msg = 'Arg %d should be a Dict' % self.pos_consumed
        return val_ops.ToDict(arg, msg, loc.Missing)

    def PosCommand(self):
        # type: () -> command_t
        arg = self._GetNextPos()
        msg = 'Arg %d should be a Command' % self.pos_consumed
        return val_ops.ToCommand(arg, msg, loc.Missing)

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

    def NamedStr(self, param_name, default_):
        # type: (str, str) -> str
        if param_name not in self.named_args:
            return default_

        msg = 'Named arg %r should be a Str' % param_name
        ret = val_ops.ToStr(self.named_args[param_name], msg, loc.Missing)
        dict_erase(self.named_args, param_name)
        return ret

    def NamedInt(self, param_name, default_):
        # type: (str, int) -> int
        if param_name not in self.named_args:
            return default_

        msg = 'Named arg %r should be an Int' % param_name
        ret = val_ops.ToInt(self.named_args[param_name], msg, loc.Missing)
        dict_erase(self.named_args, param_name)
        return ret

    def NamedFloat(self, param_name, default_):
        # type: (str, float) -> float
        if param_name not in self.named_args:
            return default_

        msg = 'Named arg %r should be a Float' % param_name
        ret = val_ops.ToFloat(self.named_args[param_name], msg, loc.Missing)
        dict_erase(self.named_args, param_name)
        return ret

    def NamedList(self, param_name, default_):
        # type: (str, List[value_t]) -> List[value_t]
        if param_name not in self.named_args:
            return default_

        msg = 'Named arg %r should be a List' % param_name
        ret = val_ops.ToList(self.named_args[param_name], msg, loc.Missing)
        dict_erase(self.named_args, param_name)
        return ret

    def NamedDict(self, param_name, default_):
        # type: (str, Dict[str, value_t]) -> Dict[str, value_t]
        if param_name not in self.named_args:
            return default_

        msg = 'Named arg %r should be a Dict' % param_name
        ret = val_ops.ToDict(self.named_args[param_name], msg, loc.Missing)
        dict_erase(self.named_args, param_name)
        return ret

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
            raise error.TypeErrVerbose('Expected %d arguments, but got %d' %
                                    (self.pos_consumed, self.pos_consumed +
                                     len(self.pos_args)), loc.Missing)

        if len(self.named_args):
            bad_args = ','.join(self.named_args.keys())
            raise error.TypeErrVerbose('Got unexpected named args: %s' % bad_args, loc.Missing)


def ReaderFromArgv(cmd_val, expr_ev):
    # type: (cmd_value.Argv, ExprEvaluator) -> Reader
    """
    Build a typed_args.Reader given a builtin command's Argv.

    As part of constructing the Reader, we must evaluate all arguments. This
    function may fail if there are any runtime errors whilst evaluating those
    arguments.
    """
    pos_args = [] if cmd_val.typed_args else None  # type: List[value_t]
    named_args = {} if cmd_val.typed_args else None  # type: Dict[str, value_t]
    if cmd_val.typed_args:
        for i, pos_arg in enumerate(cmd_val.typed_args.pos_args):
            result = expr_ev.EvalExpr(pos_arg, cmd_val.arg_locs[i])
            pos_args.append(result)

        for named_arg in cmd_val.typed_args.named_args:
            result = expr_ev.EvalExpr(named_arg.value, named_arg.name)
            name = lexer.TokenVal(named_arg.name)
            named_args[name] = result

    return Reader(cmd_val.argv, pos_args, named_args)


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
