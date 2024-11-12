#!/usr/bin/env python2
"""
test_scoped_resource.py
"""
from __future__ import print_function

import os
import sys

from mycpp import mylib
from mycpp.mylib import log
from typing import List, Dict, Optional, Any


class ctx_Eval(object):
    """
    Based on bug #1986
    """

    def __init__(self, vars):
        # type: (Optional[Dict[str, str]]) -> None
        self.vars = vars
        if vars is not None:
            self.restore = []  # type: List[str]
            self.restore.append('x')

        # Collection must be here to trigger bug
        mylib.MaybeCollect()

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        if self.vars is not None:
            self.restore.pop()


def run_tests():
    # type: () -> None

    d = {'x': 'y'}  # type: Dict[str, str]
    for i in xrange(0, 1000):
        #with ctx_Eval(d):
        #    print('d %d' % i)

        with ctx_Eval(None):
            print('none %d' % i)

        # Not enough to trigger bug
        # mylib.MaybeCollect()


def run_benchmarks():
    # type: () -> None
    pass


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
