#!/usr/bin/env python2
"""
named_args.py
"""
from __future__ import print_function

import os
import sys

import mylib
from mylib import log


def add(x, y=2, z=3):
  # type: (int, int, int) -> int
  return x + y + z


def run_tests():
  # type: () -> None

  # 6 7 8

  log("%s", add(1))
  log("%s", add(1, y=3))
  log("%s", add(1, z=5))

  # Hm the CallableType doesn't have default args, because two functions could
  # have the same type siganature, but different args, and you don't know which
  # one is being called:
  #
  # def f1(s, x=1):
  #   pass
  # def f2(s='hi', x=42):
  #   pass


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
