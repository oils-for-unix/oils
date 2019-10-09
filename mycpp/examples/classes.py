#!/usr/bin/python
"""
classes.py - Test out inheritance.  Based on asdl/format.py.
"""
from __future__ import print_function

import cStringIO
import os
import sys

import mylib
from mylib import log

from typing import IO


class ColorOutput(object):
  """Abstract base class for plain text, ANSI color, and HTML color."""

  def __init__(self, f):
    # type: (mylib.File) -> None
    self.f = f
    self.num_chars = 0

  def write(self, s):
    # type: (str) -> None
    self.f.write(s)
    self.num_chars += len(s)  # Only count visible characters!


class TextOutput(ColorOutput):
  """TextOutput put obeys the color interface, but outputs nothing."""

  def __init__(self, f):
    # type: (mylib.File) -> None
    """
    This docstring used to interfere with __init__ detection
    """
    # Note: translated into an initializer list.
    ColorOutput.__init__(self, f)
    print('TextOutput constructor')


def run_tests():
  # type: () -> None
  stdout = mylib.StdOut()
  out = TextOutput(stdout)
  out.write('foo\n')
  out.write('bar\n')
  log('Wrote %d bytes', out.num_chars)


def run_benchmarks():
  # type: () -> None
  n = 500000

  x = 33
  result = -1

  f = mylib.Buf()
  out = TextOutput(f)

  i = 0
  while i < n:
    out.write('foo\n')
    i += 1
  log('Ran %d iterations', n)
  log('Wrote %d bytes', out.num_chars)


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
