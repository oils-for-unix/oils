#!/usr/bin/env python2

"""
Pretty print Oils values (and later other data/languages as well).

(Pretty printing means intelligently choosing whitespace including indentation
and newline placement, to attempt to display data nicely while staying within a
maximum line width.)
"""

# ~~~ Architecture ~~~
#
# Based on a string version of the algorithm from Wadler's "A Prettier Printer".
#
# Pretty printing proceeds in two phases:
#
# 1. Convert the thing you want to print into a `doc`.
# 2. Print the `doc` using a standard algorithm.
#
# This separation keeps the details of the data you want to print separate from
# the printing algorithm.
#
# Some relevant links:
#
# - https://homepages.inf.ed.ac.uk/wadler/papers/prettier/prettier.pdf
# - https://lindig.github.io/papers/strictly-pretty-2000.pdf
# - https://justinpombrio.net/2024/02/23/a-twist-on-Wadlers-printer.html
# - https://lobste.rs/s/1r0aak/twist_on_wadler_s_printer
# - https://lobste.rs/s/aevptj/why_is_prettier_rock_solid

from __future__ import print_function

from _devbuild.gen.pretty_asdl import doc, doc_e, doc_t, DocFragment
from _devbuild.gen.value_asdl import value, value_e, value_t

from typing import cast, List #, Tuple # Dict, Optional

import fastfunc

from mycpp import mops
from mycpp.mylib import log, tagswitch, BufWriter

_ = log

# TODO:
# - options: max_depth, max_lines, stuff about cycles, LOSSY_JSON
# - clean up imports (is there a lint that checks for unused imports?)
# - hook up the printer in core/ui.py::PrettyPrintValue
# - run the linter
# - what's with `_ = log`?

LOSSY_JSON = True

class PrettyPrinter(object):
    """Pretty print an Oils value.

    Uses a strict version of the algorithm from Wadler's "A Prettier Printer".
    (https://homepages.inf.ed.ac.uk/wadler/papers/prettier/prettier.pdf)
    (https://lindig.github.io/papers/strictly-pretty-2000.pdf)
    """

    DEFAULT_MAX_WIDTH = 80

    def __init__(self):
        # type: () -> None
        """Construct a PrettyPrinter with default configuration options.

        Use the Init_*() methods for configuration before printing."""
        self.max_width = PrettyPrinter.DEFAULT_MAX_WIDTH

    def Init_MaxWidth(self, max_width):
        # type: (int) -> None
        self.max_width = max_width

    def PrintValue(self, val, buf):
        # type: (value_t, BufWriter) -> None
        """Pretty print an Oils value to a BufWriter."""

        document = _ValueToDoc(val)
        self._PrintDoc(document, buf)

    def _PrintDoc(self, document, buf):
        # type: (doc_t, BufWriter) -> None
        """Pretty print a `pretty.doc` to a BufWriter."""

        fragments = [DocFragment(document, 0, False)]

        while len(fragments) > 0:
            frag = fragments.pop()
            with tagswitch(frag.node) as case:

                if case(doc_e.Newline):
                    if frag.flat:
                        buf.write(' ')
                    else:
                        buf.write('\n')
                        buf.write_spaces(frag.indent)

                elif case(doc_e.Text):
                    text = cast(doc.Text, frag.node)
                    buf.write(text.string)

                elif case(doc_e.Indent):
                    indented = cast(doc.Indent, frag.node)
                    fragments.append(DocFragment(
                        indented.node,
                        frag.indent + indented.indent,
                        frag.flat
                    ))

                elif case(doc_e.Concat):
                    concat = cast(doc.Concat, frag.node)
                    for node in reversed(concat.nodes):
                        fragments.append(DocFragment(
                            node,
                            frag.indent,
                            frag.flat
                        ))

def _ValueToDoc(val):
    # type: (value_t) -> doc_t
    """Convert an Oils value into a `doc`, which can then be pretty printed."""

    with tagswitch(val) as case:
        if case(value_e.Null):
            return doc.Text("null")

        elif case(value_e.Bool):
            val = cast(value.Bool, val)
            return doc.Text("true" if val.b else "false")

        elif case(value_e.Int):
            val = cast(value.Int, val)
            return doc.Text(mops.ToStr(val.i))

        elif case(value_e.Float):
            val = cast(value.Float, val)
            return doc.Text(str(val.f))

        elif case(value_e.Str):
            val = cast(value.Str, val)
            return doc.Text(fastfunc.J8EncodeString(val.s, LOSSY_JSON))

        else:
            # TODO: handle more cases
            return doc.Newline


# vim: sw=4
