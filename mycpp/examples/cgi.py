#!/usr/bin/env python2
"""
cgi.py - Copied from Python stdlib.

We don't want the side effects of importing tempfile, which imports random,
which opens /dev/urandom!
"""
from __future__ import print_function

import os

from mycpp import mylib
from mycpp.mylib import log

# For testing what the code generator does
BACKSLASH = '\\'
RAW_BACKSLASH = r'\d+'


def escape(s, quote=False):
    # type: (str, bool) -> str
    '''Replace special characters "&", "<" and ">" to HTML-safe sequences.
    If the optional flag quote is true, the quotation mark character (")
    is also translated.'''
    s = s.replace("&", "&amp;")  # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
    return s


def run_tests():
    # type: () -> None

    mystr = 'xo--xo'
    log('s: %s', mystr)

    log("escaped: %s", escape('<html>', True))

    # Let's only replace one character for now
    log("%s\n", mystr.replace('x', 'X'))


def run_benchmarks():
    # type: () -> None
    i = 0
    n = 1000000
    while i < n:
        escape('<html>', True)
        i = i + 1
        #log("i = %d", i)

        mylib.MaybeCollect()


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
