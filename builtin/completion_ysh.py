#!/usr/bin/env python2
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.syntax_asdl import loc
from core import completion
from core.error import e_usage
from core import vm
from data_lang import j8
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import log
from frontend import flag_util
from frontend import args

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value


class CompExport(vm._Builtin):

    def __init__(self, root_comp):
        # type: (completion.RootCompleter) -> None
        self.root_comp = root_comp

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        arg_r = args.Reader(cmd_val.argv, cmd_val.arg_locs)
        arg_r.Next()

        attrs = flag_util.ParseMore('compexport', arg_r)
        arg = arg_types.compexport(attrs.attrs)

        if arg.c is None:
            e_usage('expected a -c string, like sh -c', loc.Missing)

        arg_begin = mops.BigTruncate(arg.begin)
        arg_end = mops.BigTruncate(arg.end)

        begin = 0 if arg_begin == -1 else arg_begin
        end = len(arg.c) if arg_end == -1 else arg_end

        #log('%r begin %d end %d', arg.c, begin, end)

        # Copied from completion.ReadlineCallback
        comp = completion.Api(line=arg.c, begin=begin, end=end)
        it = self.root_comp.Matches(comp)

        #print(comp)
        #print(self.root_comp)

        comp_matches = list(it)
        comp_matches.reverse()

        if arg.format == 'jlines':
            buf = mylib.BufWriter()
            for m in comp_matches:
                # Note: everything is quoted, that seems simpler.
                j8.EncodeString(m, buf)
                print(buf.getvalue())
                buf.clear()

        elif arg.format == 'tsv8':
            log('TSV8 format not implemented')
        else:
            raise AssertionError()

        return 0
