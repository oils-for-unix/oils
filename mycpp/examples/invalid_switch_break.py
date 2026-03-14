#!/usr/bin/env python2
"""
test_switch.py
"""
from __future__ import print_function

import os

from mycpp.mylib import switch, log


def TestBreakSwitch():
    # type: () -> None

    x = 5
    while x < 10:
        with switch(x) as case:
            if case(7):
                print('seven')
                # ERROR - different behavior in C++ and Python
                break

            elif case(1, 2):
                for i in range(x):
                    break  # This is fine, breaks out of the nested loop
                print('one or two')

            elif case(3, 4):
                while True:
                    break  # Also fine, leaves nested loop
                print('three or four')
                break  # ERROR

            else:
                for i in range(1):
                    pass
                print('default')
                break  # ERROR

        x += 1


def run_tests():
    # type: () -> None
    TestBreakSwitch()


def run_benchmarks():
    # type: () -> None
    raise NotImplementedError()


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
