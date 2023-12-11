"""YSH Str methods"""

from __future__ import print_function

from _devbuild.gen.value_asdl import (value, value_t)

from core import vm
from frontend import typed_args
from mycpp.mylib import log

_ = log


class StartsWith(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        string = rd.PosStr()
        match = rd.PosStr()
        rd.Done()

        res = string.startswith(match)
        return value.Bool(res)


class Trim(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        string = rd.PosStr()
        rd.Done()

        # TODO: Make this remove unicode spaces
        # Note that we're not calling this function strip() because it doesn't
        # implement Python's whole API.
        # trim() is shorter and it's consistent with JavaScript.
        res = string.strip()
        return value.Str(res)


class Upper(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        string = rd.PosStr()
        rd.Done()

        res = string.upper()
        return value.Str(res)


class Search(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        """
        s => search(eggex, pos=0)
        """

        eggex = rd.PosEggex()
        # don't confuse 'start' and 'pos'?
        # Python has 2 kinds of 'pos'
        pos = rd.NamedInt('pos', 0)
        rd.Done()

        # TODO:
        #
        # call libc.regex_search(str ERE, int flags, str s, int pos)
        #
        # which should return non-empty List[int] of positions, or None
        #
        # - it uses the regcomp cache
        # - TODO: eggex evaluation has to cache the group names, and number of
        #   groups

        return value.Null
