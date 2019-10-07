#!/usr/bin/python
"""
Code snippets that are like ASDL generated code.

Even though we may generate our own C++ code, the CALL SITES still have to be
correctly typed-inferred from Python.
"""
from __future__ import print_function

import os

from mylib import log

from typing import Optional, List

# This causes problems
#from asdl import format as fmt


class arith_expr_t(object):
  pass


class arith_expr__Const(arith_expr_t):

  def __init__(self, i):
    # type: (int) -> None
    self.i = i

  #def __init__(self, i=None, spids=None):
    ## type: (Optional[int], Optional[List[int]]) -> None
    #self.i = i
    #self.spids = spids or []


# This causes problems
#class arith_expr(object):
#  Const = arith_expr__Const


def run_tests():
  # type: () -> None

  #x = arith_expr.Const(5)
  x = arith_expr__Const(5)
  log('x = %d', x.i)


def run_benchmarks():
  # type: () -> None
  i = 0
  n = 1000000
  while i < n:
    x = arith_expr__Const(i)
    i = i + 1


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
