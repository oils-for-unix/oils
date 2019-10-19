#!/usr/bin/env python2
"""
alloc_main.py
"""
from __future__ import print_function

import os
import sys

from _devbuild.gen.syntax_asdl import source_e, source__MainFile
from core import alloc
from core.util import log

from typing import cast


def run_tests():
  # type: () -> None
  arena = alloc.Arena()
  arena.PushSource(source__MainFile('foo.txt'))
  line_id = arena.AddLine('one', 1)
  log('line_id = %d', line_id)
  line_id = arena.AddLine('two', 2)
  log('line_id = %d', line_id)

  arena.PopSource()

  line = arena.GetLine(1)
  log('line = %s', line)

  n = arena.GetLineNumber(1)
  log('line number = %d', n)

  src = arena.GetLineSource(1)
  UP_src = src
  if src.tag_() == source_e.MainFile:
    src = cast(source__MainFile, UP_src)
    log('source = %s', src.path)


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
