#!/usr/bin/env python2
"""
func_eggex.py
"""
from __future__ import print_function

import sys

from core import state

from typing import Any


class Match(object):
    """_match(0) or _match():   get the whole match _match(1) ..

    _match(N):  submatch
    """

    def __init__(self, mem):
        # type: (state.Mem) -> None
        self.mem = mem

    def __call__(self, *args):
        # type: (Any) -> Any
        if len(args) == 0:
            return self.mem.GetMatch(0)

        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, int):
                s = self.mem.GetMatch(arg)
                # Oil code doesn't deal well with exceptions!
                #if s is None:
                #  raise IndexError('No such group')
                return s

            # TODO: Support strings
            raise TypeError('Expected an integer, got %r' % arg)

        raise TypeError('Too many arguments')


class Start(object):
    """Same signature as _match(), but for start positions."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        self.mem = mem

    def __call__(self, *args):
        # type: (Any) -> Any
        raise NotImplementedError('_start')


class End(object):
    """Same signature as _match(), but for end positions."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        self.mem = mem

    def __call__(self, *args):
        # type: (Any) -> Any
        raise NotImplementedError('_end')


# vim: sw=4
