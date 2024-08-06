#!/usr/bin/env python2
"""
gc_stack_roots.py
"""
from __future__ import print_function

import os

from mycpp import mylib
from mycpp.mylib import log

from typing import Any, List
"""
Helpers
"""


def print_list(l):
    # type: (List[str]) -> None
    for s in l:
        print(s)


def calls_collect():
    # type: () -> None
    mylib.MaybeCollect()


def ignore_and_collect(l):
    # type: (List[str]) -> None
    mylib.MaybeCollect()


def collect_and_return(l):
    # type: (List[str]) -> List[str]
    mylib.MaybeCollect()
    return l


def collect_and_slice(s):
    # type: (str) -> str
    mylib.MaybeCollect()
    return s[1:]


class ctx_Stasher(object):

    def __init__(self, l):
        # type: (List[str]) -> None
        self.l = l

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        print_list(self.l)


"""
Test cases
"""


def no_collect():
    # type: () -> None
    """
    There's no need to gernate any stack roots in this case. There is no threat
    of anything being swept.
    """
    l = ['no', 'collect']  # type: List[str]
    print_list(l)


def simple_collect():
    # type: () -> None
    """
    Only l1 needs to be rooted here. l2 is not live after the call to collect.
    """
    l1 = ['foo', 'bar']  # type: List[str]
    l2 = ['bing', 'bong']  # type: List[str]
    print_list(l2)
    if len(l1):
        mylib.MaybeCollect()

    print_list(l1)


def indirect_collect():
    # type: () -> None
    """
    l should be rooted since it is live after an indirect call to collect.
    """
    l = ['indirect', 'collect']
    calls_collect()
    print_list(l)


def arg_roots():
    # type: () -> None
    """
    If a function might collect it should unconditionally root its arguments.
    It should root them even if it doesn't use them directly because we can't
    gaurantee that the caller will even have been able to root them, e.g. in the
    case of function composition or an arugment being constructed inline.
    """
    l1 = ['OK']  # Should be rooted by ignore_and_collect().
    ignore_and_collect(l1)
    print_list(l1)

    # The temporary list should be rooted by collect_and_return().
    l2 = collect_and_return(['not', 'swept'])
    print_list(l2)


def alias():
    # type: () -> None
    """
    Only one of l1 and l2 needs to be rooted here. In this case we should choose
    l2 since it is live after the collector runs.
    """
    l1 = ['foo', 'bar']  # type: List[str]
    l2 = l1
    mylib.MaybeCollect()
    print_list(l2)


def collect_scoped_resource():
    # type: () -> None
    """
    Similar to function arguments, members of context managers should be rooted
    by their constructors. However, unlike normal functions these constructors
    should do so even if they don't cause a collection. The caller might trigger
    garbage collection while the manager is still in scope and the members will
    get swept if they weren't already rooted further up in the call stack.
    """
    with ctx_Stasher(['context', 'member']) as ctx:
        mylib.MaybeCollect()


def collect_in_loop():
    # type: () -> None
    """
    Temporary variables used in loops should be rooted if a collection might
    happen within the loop body.
    """
    for s in ['watch', 'out']:
        mylib.MaybeCollect()
        print(s)


def collect_in_comprehension():
    # type: () -> None
    """
    Temporary variables used in list comprehensions should be rooted if a
    collection might happen.
    """
    l = ['%s' % collect_and_slice(s) for s in ['foo', 'bar']] # type: List[str]
    for s in l:
        print(s)


def run_tests():
    # type: () -> None
    no_collect()
    simple_collect()
    indirect_collect()
    arg_roots()
    alias()
    collect_scoped_resource()
    # TODO: maybe move these two to invalid examples if we decide to disallow.
    #collect_in_loop()
    #collect_in_comprehension()


def run_benchmarks():
    # type: () -> None
    pass


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
