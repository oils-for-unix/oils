"""Methods on IO type"""
from __future__ import print_function

from _devbuild.gen.value_asdl import value, value_t

from core import vm
from mycpp.mylib import log
from osh import prompt

from typing import cast, TYPE_CHECKING
if TYPE_CHECKING:
    from frontend import typed_args

_ = log


class PromptChar(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # "self" param is guaranteed to succeed
        io = rd.PosIO()
        rd.Done()  # no more args

        prompt_ev = cast(prompt.Evaluator, io.prompt_ev)
        return value.Str(prompt_ev.PromptChar())
