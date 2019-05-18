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

from . import grammar, parse, token, tokenize


def log(msg, *args):
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)


def PushTokens(p, tokens, start_symbol, convert=None, debug=False):
    """Parse a series of tokens and return the syntax tree."""
    # XXX Move the prefix computation into a wrapper around tokenize.

    p.setup(start=start_symbol)

    # What is all this for?
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
            type_ = grammar.opmap[value]
        if debug:
            log("%s %r (prefix=%r)", token.tok_name[type_], value, prefix)
        if p.addtoken(type_, value, (prefix, start)):
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
        raise parse.ParseError("incomplete input",
                               type_, value, (prefix, start))
    return p.rootnode
