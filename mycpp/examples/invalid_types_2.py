#!/usr/bin/env python2
"""
invalid_types_2.py
"""
from __future__ import print_function

import os

from mycpp.mylib import log

from typing import List


def run_tests():
    # type: () -> None

    x = 33  # type: List[int]
    log('x = %d', x)


def run_benchmarks():
    # type: () -> None
    raise NotImplementedError()


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
