#!/usr/bin/env python2
"""
invalid_format_strings.py
"""
from __future__ import print_function


def run_tests():
    # type: () -> None

    x = 33

    print('x = %z' % x)

    # TODO: this doesn't fail at translate time

    # With StrFormat(), it will make it to C++ runtime, past C++ compile time
    #print('x = %x' % x)

    # Similarly for '%-2d' I believe
