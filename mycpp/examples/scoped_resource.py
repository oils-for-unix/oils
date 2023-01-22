#!/usr/bin/env python2
"""
scoped_resource.py
"""
from __future__ import print_function

import os
import sys

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

  def __enter__(self):
    # type: () -> None
    """no-op, but it has to exist to be used as context manager."""
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
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


def run_tests():
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


def run_benchmarks():
  # type: () -> None
  d = DirStack()
  for i in xrange(1000000):
    try:
      with ctx_DirStack(d, 'foo') as _:
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
