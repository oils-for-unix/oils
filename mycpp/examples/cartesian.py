#!/usr/bin/python
"""
cartesian.py: Test lists of strings!
"""
from __future__ import print_function

import os

from typing import List
from mylib import log

# Operations:
# - list literals
# - list indexing  dims[0]
# - list slicing   dims[1:]
# - list append
# - length of list
# - iteration over characters in a string
# - iteration over list
# - recursive function calls
# - string concatenation with +


def Cartesian(dims, out):
  # type: (List[str], List[str]) -> None
  if len(dims) == 1:
    for ch in dims[0]:
      out.append(ch)
  else:
    rest = []  # type: List[str]
    Cartesian(dims[1:], rest)
    for ch in dims[0]:
      for r in rest:
        out.append(ch + r)  # join strings


def run_tests():
  # type: () -> None
  out = []  # type: List[str]
  Cartesian(['ab'], out)
  for s in out:
    print(s)

  print('--')

  out = []
  Cartesian(['ab', '-|_', 'ABC'], out)
  for s in out:
    print(s)


def run_benchmarks():
  # type: () -> None
  i = 0
  n = 200000
  while i < n:
    out = []  # type: List[str]
    Cartesian(['ab', '-|_', 'ABC'], out)
    i = i + 1


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
