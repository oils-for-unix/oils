#!/usr/bin/env python2
from __future__ import print_function

from _devbuild.gen.pretty_asdl import doc, doc_t
from _devbuild.gen.value_asdl import value_e, value_t

from mycpp.mylib import log, tagswitch

_ = log


def FromValue(val):
    # type: (value_t) -> doc_t
    """Stub to turn an Oils value into a PPL.
    """
    with tagswitch(val) as case:
        # e.g. see data_lang/j8.py
        # It has options like SHOW_CYCLES and SHOW_NON_DATA

        if case(value_e.Null):
            return doc.Newline

        elif case(value_e.Bool):
            return doc.Newline

        elif case(value_e.Int):
            return doc.Newline

        elif case(value_e.Float):
            return doc.Newline

        elif case(value_e.Str):
            return doc.Newline

        else:
            raise AssertionError()


# vim: sw=4
