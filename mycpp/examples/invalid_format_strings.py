#!/usr/bin/env python2
"""
invalid_format_strings.py
"""
from __future__ import print_function

from mycpp.mylib import log


def run_tests():
    # type: () -> None

    x = 33

    print('x = %x' % x)

    # caught by MyPy
    # print('x = %z' % x)

    print('x = %c' % x)

    log('x = %c', x)
