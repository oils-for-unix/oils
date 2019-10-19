#!/usr/bin/env python2
"""
conditional.py
"""
from __future__ import print_function

import os
import sys

import mylib
from mylib import log


def run_tests():
  # type: () -> None

  # NOTE: Output is meant to be inspected
  if mylib.CPP:
    log('CPP')
  else:
    log('CPP')

  if mylib.PYTHON:
    log('PYTHON')
  else:
    log('PYTHON')

  if 0:
    log('ZERO')


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
