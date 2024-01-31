"""Methods on IO type"""
from __future__ import print_function

from _devbuild.gen.value_asdl import value, value_t

from core import error
from core import vm
from mycpp.mylib import log
from osh import prompt

from typing import cast, TYPE_CHECKING
if TYPE_CHECKING:
    from frontend import typed_args

_ = log


class PromptVal(vm._Callable):
    """
    _io->promptVal('$') is like \$ 
    It expands to $ or # when root
    """

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # "self" param is guaranteed to succeed
        io = rd.PosIO()
        what = rd.PosStr()
        rd.Done()  # no more args

        # Bug fix: protect against crash later in PromptVal()
        if len(what) != 1:
            raise error.Expr(
                'promptVal() expected a single char, got %r' % what,
                rd.LeftParenToken())

        prompt_ev = cast(prompt.Evaluator, io.prompt_ev)
        return value.Str(prompt_ev.PromptVal(what))
