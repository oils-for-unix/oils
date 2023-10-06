#!/usr/bin/env python2
"""
string_interning.py
"""
from __future__ import print_function

import os
from mycpp import mylib
from mycpp.mylib import log, InternedStr

def run_tests():
    # type: () -> None
    pass

def run_benchmarks():
    # type: () -> None

    x = InternedStr("foo" + "bar", 0, 6)
    while True:
        if InternedStr("foobar", 0, 6) == x:
            pass
        else:
            break


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
