#!/usr/bin/env python2
"""
invalid_except.py
"""
from __future__ import print_function


def f():
    # type: () -> None

    # Duplicate to see if we can get THREE errors out of mycpp

    try:
        print('hi')
    except IOError:
        print('bad')

    try:
        print('hi')
    except OSError as e:
        print('bad')


def run_tests():
    # type: () -> None

    f()

    try:
        print('hi')
    except (IOError, OSError) as e:
        pass

    # Invalid finally, not except
    try:
        print('hi')
    finally:
        print('finally')
