#!/usr/bin/env python2
"""
invalid_except.py
"""
from __future__ import print_function

from mycpp.mylib import switch, str_switch, tagswitch


def NoDefault():
    # type: () -> None

    s = "foo"
    with str_switch(s) as case:
        if case("bar"):
            print('bar')


def TagSwitch():
    # type: () -> None

    s = "foo"
    with tagswitch(s) as case:
        if 42:
            print('ONE')
            print('dupe')

        elif 43:
            print('TWO')

        else:
            print('neither')


def SwitchMustHaveCase():
    # type: () -> None

    i = 49
    with switch(i) as case:
        if 42:
            print('ONE')
            print('dupe')

        elif 43:
            print('TWO')

        else:
            print('neither')


def StrSwitchNoTuple():
    # type: () -> None

    s = "foo"
    with str_switch(s) as case:
        # Problem: if you switch on length, do you duplicate the bogies
        if case('spam', 'different len'):
            print('ONE')
            print('dupe')

        elif case('foo'):
            print('TWO')

        else:
            print('neither')


def StrSwitchNoInt():
    # type: () -> None

    s = "foo"
    with str_switch(s) as case:
        # integer not allowed
        if case(42):
            print('ONE')
            print('dupe')

        else:
            print('neither')


def run_tests():
    # type: () -> None
    pass
