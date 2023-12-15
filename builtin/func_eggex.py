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


M = 0  # _match() _group()
S = 1  # _start()
E = 2  # _end()

class MatchAccess(vm._Callable):
    """
    _match(0) or _match():   get the whole match _match(1) ..

    _match(N):  submatch
    """

    def __init__(self, mem, which_func):
        # type: (state.Mem, int) -> None
        vm._Callable.__init__(self)
        self.mem = mem
        self.which_func = which_func

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # TODO: Support strings for named captures
        i = rd.OptionalInt(default_=0)

        s, indices = self.mem.GetRegexIndices()
        num_groups = len(indices) / 2  # including group 0
        if i < num_groups:
            start = indices[2 * i]
            if self.which_func == S:
                return value.Int(start)

            end = indices[2 * i + 1]
            if self.which_func == E:
                return value.Int(end)

            if start == -1:
                return value.Null
            else:
                return value.Str(s[start:end])
        else:
            if num_groups == 0:
                msg = 'No regex capture groups'
            else:
                msg = 'Expected capture group less than %d, got %d' % (
                    num_groups, i)
            raise error.UserError(2, msg, rd.LeftParenToken())


# vim: sw=4
