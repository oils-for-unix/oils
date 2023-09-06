#!/usr/bin/env python2
"""
func_eggex.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_t
from core import error, state, vm
from frontend import typed_args
from ysh import val_ops

from typing import List, Dict


class Match(vm._Callable):
    """_match(0) or _match():   get the whole match _match(1) ..

    _match(N):  submatch
    """

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t
        arg = 0
        if args.NumPos():
            arg = args.PosInt()
            args.Done()

        # TODO: Support strings
        s = self.mem.GetMatch(arg)
        # Oil code doesn't deal well with exceptions!
        #if s is None:
        #  raise IndexError('No such group')
        if s is not None:
            return value.Str(s)

        return value.Null


class Start(vm._Callable):
    """Same signature as _match(), but for start positions."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t
        raise NotImplementedError('_start')


class End(vm._Callable):
    """Same signature as _match(), but for end positions."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t
        raise NotImplementedError('_end')


# vim: sw=4
