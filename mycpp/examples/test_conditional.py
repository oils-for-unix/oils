#!/usr/bin/env python2
"""
conditional.py
"""
from __future__ import print_function

import os
import sys

from typing import List

from mycpp import mylib
from mycpp.mylib import log


def run_tests():
    # type: () -> None

    # NOTE: Output is meant to be inspected
    if mylib.CPP:
        log('CPP')
    else:
        log('CPP')

    if mylib.PYTHON:
        log('PYTHON')
    else:
        log('PYTHON')

    if 0:
        log('ZERO')

    log('int = %d', int('123'))
    log('bool = %d', bool(42))

    mylist = []  # type: List[int]

    #if mylist:  # translation time error
    if len(mylist):
        print('mylist')

    # translation error
    #x = 1 if mylist else 2
    x = 1 if len(mylist) else 2

    log("x = %d", x)

    # Expressions where parens are needed
    a = False
    if a and (False or True):
        print('yes')
    else:
        print('no')


def run_benchmarks():
    # type: () -> None
    raise NotImplementedError()


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
