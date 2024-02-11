"""
gen_cpp.py - turn yaks.asdl representation into C++
"""
from __future__ import print_function

from _devbuild.gen.yaks_asdl import Program, mod_def, mod_def_e
from mycpp.mylib import tagswitch, log

from typing import cast

_ = log


def GenCpp(prog):
    # type: (Program) -> None

    for module in prog.modules:
        for d in module.defs:
            UP_d = d
            with tagswitch(d) as case:
                if case(mod_def_e.Func):
                    d = cast(mod_def.Func, UP_d)
                    log('Function %s', d.name)
