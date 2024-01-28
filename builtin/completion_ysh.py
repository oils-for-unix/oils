#!/usr/bin/env python2
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.syntax_asdl import loc
from core import completion
from core.error import e_usage
from core import vm
from data_lang import j8
from mycpp import mylib
from mycpp.mylib import log
from frontend import flag_spec
from frontend import args

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value


class CompExport(vm._Builtin):

    def __init__(self, root_comp):
        # type: (completion.RootCompleter) -> None
        self.root_comp = root_comp
        self.j8print = j8.Printer()

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        arg_r = args.Reader(cmd_val.argv, cmd_val.arg_locs)
        arg_r.Next()

        attrs = flag_spec.ParseMore('compexport', arg_r)
        arg = arg_types.compexport(attrs.attrs)

        if arg.c is None:
            e_usage('expected a -c string, like sh -c', loc.Missing)

        begin = 0 if arg.begin == -1 else arg.begin
        end = len(arg.c) if arg.end == -1 else arg.end

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
                # TODO: change to J8 notation
                # - Since there are spaces, maybe_encode() always adds quotes.
                # - Could use a jlines=True J8 option to specify that newlines and
                #   non-UTF-8 unprintable bytes cause quotes.  But not spaces.
                #
                # Also, there's always a trailing space!  Gah.

                self.j8print.EncodeString(m, buf)
                print(buf.getvalue())
                buf.clear()

        elif arg.format == 'tsv8':
            log('TSV8 format not implemented')
        else:
            raise AssertionError()

        return 0
