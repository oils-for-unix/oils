#!/usr/bin/env python2
"""
func_eggex.py
"""
from __future__ import print_function

from _devbuild.gen.value_asdl import value, value_t
from core import error
from core import state
from core import vm
from frontend import typed_args


class Match(vm._Callable):
    """
    _match(0) or _match():   get the whole match _match(1) ..

    _match(N):  submatch
    """

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # TODO: Support strings for named captures
        i = rd.OptionalInt(default_=0)

        matches = self.mem.GetRegexMatches()
        num_groups = len(matches)  # including group 0
        if i < num_groups:
            captured = matches[i]
            if captured is None:
                return value.Null
            else:
                return value.Str(captured)
        else:
            if num_groups == 0:
                msg = 'No regex capture groups'
            else:
                msg = 'Expected capture group less than %d, got %d' % (
                    num_groups, i)
            raise error.UserError(2, msg, rd.LeftParenToken())


class Start(vm._Callable):
    """Same signature as _match(), but for start positions."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        raise NotImplementedError('_start')


class End(vm._Callable):
    """Same signature as _match(), but for end positions."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        raise NotImplementedError('_end')


# vim: sw=4
