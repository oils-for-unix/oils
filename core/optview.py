"""optview.py."""
from __future__ import print_function

from frontend import consts
from frontend import option_def

from typing import List


class _Getter(object):

    def __init__(self, opt0_array, opt_stacks, opt_name):
        # type: (List[bool], List[List[bool]], str) -> None
        self.opt0_array = opt0_array
        self.opt_stacks = opt_stacks
        self.num = consts.OptionNum(opt_name)
        assert self.num != 0, opt_name

    def __call__(self):
        # type: () -> bool
        overlay = self.opt_stacks[self.num]
        if overlay is None or len(overlay) == 0:
            return self.opt0_array[self.num]
        else:
            return overlay[-1]  # The top value


class _View(object):
    """Allow read-only access to a subset of options."""

    def __init__(self, opt0_array, opt_stacks, allowed):
        # type: (List[bool], List[List[bool]], List[str]) -> None
        self.opt0_array = opt0_array
        self.opt_stacks = opt_stacks
        self.allowed = allowed

    def __getattr__(self, opt_name):
        # type: (str) -> _Getter
        """Make the API look like self.exec_opts.strict_control_flow()"""
        if opt_name in self.allowed:
            return _Getter(self.opt0_array, self.opt_stacks, opt_name)
        else:
            raise AttributeError(opt_name)


class Parse(_View):

    def __init__(self, opt0_array, opt_stacks):
        # type: (List[bool], List[List[bool]]) -> None
        _View.__init__(self, opt0_array, opt_stacks,
                       option_def.ParseOptNames())


class Exec(_View):

    def __init__(self, opt0_array, opt_stacks):
        # type: (List[bool], List[List[bool]]) -> None
        _View.__init__(self, opt0_array, opt_stacks, option_def.ExecOptNames())
