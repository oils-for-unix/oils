#!/usr/bin/env python
"""
escape.py: Test string and list operations.
"""
from __future__ import print_function

import os
from mylib import log

from typing import List


def BackslashEscape(s, meta_chars):
  # type: (str, str) -> str
  """Escaped certain characters with backslashes.

  Used for shell syntax (i.e. quoting completed filenames), globs, and EREs.
  """
  escaped = []  # type: List[str]
  for c in s:
    if c in meta_chars:
      escaped.append('\\')
    escaped.append(c)
  return ''.join(escaped)


GLOB_META_CHARS = r'\*?[]-:!'


def TestNotIn():
  # type: () -> None
  if '.' not in GLOB_META_CHARS:
    print('NOT IN .')
  if '*' not in GLOB_META_CHARS:
    print('NOT IN *')


def run_tests():
  # type: () -> None

  log("result: %s", BackslashEscape('echo *.[ch] *.?', GLOB_META_CHARS))

  # 200K iterations takes ~433 ms in Python, and ~311 ms in C with -O2 (~600 ms
  # with -O0)  The algorithm is very inefficient.  There are many tiny objects
  # being allocated.

  TestNotIn()


def run_benchmarks():
  # type: () -> None

  i = 0
  n = 200000
  while i < n:
    s = 'echo *.[ch] *.?'
    #s = '*'
    BackslashEscape(s, GLOB_META_CHARS)
    i = i + 1


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
