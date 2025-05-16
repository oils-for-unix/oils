#!/usr/bin/env python2
"""
scoped_resource.py
"""
from __future__ import print_function

import os
import sys

from mycpp import mylib
from mycpp.mylib import log
from typing import List, Optional, Any


class MyError(Exception):

    def __init__(self):
        # type: () -> None
        pass


def Error(error):
    # type: (bool) -> None
    if error:
        raise MyError()


#class BadName(object):
class ctx_BadName(object):

    def __init__(self):
        # type: () -> None
        self.i = 42

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.i = 43


class ctx_NoArgs(object):
    """Regression for most vexing parse."""

    def __init__(self):
        # type: () -> None
        print('> NoArgs')

    def __enter__(self):
        # type: () -> None
        """no-op, but it has to exist to be used as context manager."""
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        print('< NoArgs')


class ctx_DirStack(object):

    def __init__(self, state, entry):
        # type: (DirStack, str) -> None
        self.state = state
        state.Push(entry)

        # Bug #1986: add heap-allocated member of context manager
        self.restored = []  # type: List[str]
        self.restored.append('foo')
        self.non_pointer_member = 42  # make sure we don't root this

    def __enter__(self):
        # type: () -> None
        """no-op, but it has to exist to be used as context manager."""
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.restored.pop()
        self.state.Pop()


class DirStack(object):
    """For pushd/popd/dirs."""

    def __init__(self):
        # type: () -> None
        self.stack = []  # type: List[str]
        self.Reset()  # Invariant: it always has at least ONE entry.

    def Reset(self):
        # type: () -> None
        del self.stack[:]
        self.stack.append('CWD')

    def Push(self, entry):
        # type: (str) -> None
        self.stack.append(entry)

    def Pop(self):
        # type: () -> Optional[str]
        if len(self.stack) <= 1:
            return None
        self.stack.pop()  # remove last
        return self.stack[-1]  # return second to last

    def Iter(self):
        # type: () -> List[str]
        """Iterate in reverse order."""
        # mycpp REWRITE:
        #return reversed(self.stack)
        ret = []  # type: List[str]
        ret.extend(self.stack)
        ret.reverse()
        return ret

    def __repr__(self):
        # type: () -> str
        return repr(self.stack)


# C++ translation
#
# class _ErrExit__Context;  // forward declaration
# class _ErrExit {
# };
#
# class _ErrExit__Context {
#   _ErrExit__Context(_ErrExit* state) : state_(state) {
#     state->Push();
#   }
#  ~_ErrExit__Context() {
#     state->Pop();
#   }
# };


def DoWork(d, do_raise):
    # type: (DirStack, bool) -> None

    # problem
    # with self.mem.ctx_Call(...)
    #  PushCall/PopCall
    # with self.mem.ctx_Temp(...)
    #  PushTemp/PopCall
    # with self.mem.ctx_Source(...)
    #  PushSource/PopSource
    #
    # Scope_Call
    # Scope_Temp

    # PROBLEM: WE LOST TYPE CHECKING!
    #with e.Context('zz') as _:
    with ctx_DirStack(d, 'foo') as _:
        log('  in context stack %d', len(d.stack))
        if do_raise:
            Error(do_raise)


def TestGoodRaise():
    # type: () -> None

    # Use cases:
    #
    # Many in cmd_exec.py
    #
    # fd_state.Push(...) and Pop
    # BeginAlias, EndAlias
    # PushSource, PopSource (opens files)
    #   source
    #   eval -- no file opened, but need to change the current file
    # PushTemp, PopTemp for env bindings
    # PushErrExit, PopErrExit
    # loop_level in cmd_exec

    d = DirStack()

    for do_raise in [False, True]:
        log('')
        log('-> dir stack %d', len(d.stack))
        try:
            DoWork(d, do_raise)
        except MyError:
            log('exited with exception')
        log('<- dir stack %d', len(d.stack))

    # C++ translation
    #
    # _Errexit e;
    # e.errexit = true;
    #
    # log("-> errexit %d", e.errexit)
    # {
    #   _ErrExit__Context(e);
    #   log("  errexit %d", e.errexit)
    # }
    # log("<- errexit %d", e.errexit)

    with ctx_NoArgs():
        print('hi')


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
            # return is not allowed
            #return
            pass
            # this is also invalid
            #raise ValueError()


def TestReturn():
    # type: () -> None

    i = 0
    for j in xrange(1000):
        with ctx_MaybePure():
            i += 1
        mylib.MaybeCollect()
    print("i = %d" % i)


def run_tests():
    # type: () -> None
    TestGoodRaise()

    TestReturn()


def run_benchmarks():
    # type: () -> None
    d = DirStack()
    for i in xrange(1000000):
        # Does NOT trigger the bug!
        #mylib.MaybeCollect()
        try:
            with ctx_DirStack(d, 'foo') as _:
                # Bug #1986: add collection in this loop
                mylib.MaybeCollect()
                if i % 10000 == 0:
                    raise MyError()
        except MyError:
            log('exception')


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
