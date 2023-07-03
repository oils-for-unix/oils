#!/usr/bin/env python2
"""
_func_utils.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value_t, value_str
from _devbuild.gen.syntax_asdl import loc
from core import error

from typing import TYPE_CHECKING, Dict, List

class ArgsSpec(object):
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
            raise error.InvalidType("%s() expects %d arguments but %d were given" % (func_name, expected, nargs), loc.Missing)

        nargs = len(named_args)
        expected = len(self.named_args)
        if len(named_args) != 0:
            raise error.InvalidType("%s() expects %d named arguments but %d were given" % (func_name, expected, nargs), loc.Missing)

        for i in xrange(len(pos_args)):
            expected = self.pos_args[i]
            got = pos_args[i].tag()
            if got != expected:
                msg = "%s() expected %s but received %s" % (func_name, value_str(expected), value_str(got))
                raise error.InvalidType(msg, loc.Missing)

        for name in named_args:
            expected = self.named_args[name]
            got = named_args[name].tag()
            if got != expected:
                msg = "%s() expected %s but received %s" % (func_name, value_str(expected), value_str(got))
                raise error.InvalidType(msg, loc.Missing)
