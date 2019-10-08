#!/usr/bin/env python2
"""
lexer_main.py
"""
from __future__ import print_function

import os
import sys

from core import alloc
from frontend import lexer
from frontend import match

from core.util import log

from typing import cast


def run_tests():
  # type: () -> None

  # TODO: Make matcher optional

  arena = alloc.Arena()
  line_lexer = lexer.LineLexer(match.MATCHER, '', arena)
  print('lexer_main.py')



def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
