# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

# Modifications:
# Copyright 2006 Google, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.
from __future__ import print_function

"""Parser driver.

A high-level interface to parse a file into a syntax tree.
"""

__author__ = "Guido van Rossum <guido@python.org>"


import sys

from . import parse, token, tokenize


def log(msg, *args):
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)


def classify(gr, typ, value):
    """Turn a token into a label.  (Internal)"""
    if typ == token.NAME:
        # Keep a listing of all used names
        # OIL note: removed because it's only used by lib2to3
        #self.used_names.add(value)

        # Check for reserved words
        ilabel = gr.keywords.get(value)
        if ilabel is not None:
            return ilabel
    ilabel = gr.tokens.get(typ)
    if ilabel is None:
        raise parse.ParseError("bad token", typ, value)
    return ilabel


def PushTokens(p, tokens, gr, start_symbol, opmap=token.opmap, debug=False):
    """Parse a series of tokens and return the syntax tree.

    NOTE: This function is specific to Python's lexer.
    """
    # XXX Move the prefix computation into a wrapper around tokenize.
    # NOTE: It's mainly for lib2to3.

    p.setup(gr.symbol2number[start_symbol])

    lineno = 1
    column = 0
    type_ = value = start = end = line_text = None
    prefix = ""
    for quintuple in tokens:
        type_, value, start, end, line_text = quintuple
        #log('token %s %r', type_, value)
        if start != (lineno, column):
            assert (lineno, column) <= start, ((lineno, column), start)
            s_lineno, s_column = start
            if lineno < s_lineno:
                prefix += "\n" * (s_lineno - lineno)
                lineno = s_lineno
                column = 0
            if column < s_column:
                prefix += line_text[column:s_column]
                column = s_column
        if type_ in (tokenize.COMMENT, tokenize.NL):
            prefix += value
            lineno, column = end
            if value.endswith("\n"):
                lineno += 1
                column = 0
            continue

        if type_ == token.OP:
            type_ = opmap[value]

        if debug:
            log("%s %r (prefix=%r)", token.tok_name[type_], value, prefix)

        ilabel = classify(gr, type_, value)
        opaque = (value, prefix, start)
        if p.addtoken(type_, opaque, ilabel):
            if debug:
                log("Stop.")
            break
        prefix = ""
        lineno, column = end
        if value.endswith("\n"):
            lineno += 1
            column = 0
    else:
        # We never broke out -- EOF is too soon (how can this happen???)
        opaque = (value, prefix, start)
        raise parse.ParseError("incomplete input", type_, opaque)
    return p.rootnode
