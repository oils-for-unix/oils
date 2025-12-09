#!/usr/bin/env python2
"""
invalid_ctx_raise.py
"""
from __future__ import print_function

from typing import Any

from mycpp import mylib


class ctx_MaybePure(object):
    """Regression for early return."""

    def __init__(self):
        # type: () -> None
        self.member = 'bar'

    def __enter__(self):
        # type: () -> None
        """no-op, but it has to exist to be used as context manager."""
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None

        if self.member is not None:
            # raise is not allowed
            raise ValueError()


def run_tests():
    # type: () -> None

    i = 0
    for j in xrange(1000):
        with ctx_MaybePure():
            i += 1
        mylib.MaybeCollect()
    print(i)


if __name__ == '__main__':
    run_tests()
