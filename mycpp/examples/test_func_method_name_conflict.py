#!/usr/bin/env python2
"""
test_func_method_name_conflict.py
"""

import os


def a():
    # type: () -> int
    return 1


class A:

    def __init__(self):
        # type: () -> None
        pass

    def a(self):
        # type: () -> int
        raise AssertionError()
        return 1

    def b(self):
        # type: () -> None
        a()  # should call the free function


def run_tests():
    # type: () -> None
    cls = A()
    cls.b()


def run_benchmarks():
    # type: () -> None
    pass


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        run_benchmarks()
    else:
        run_tests()
