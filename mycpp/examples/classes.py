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
    # type: (mylib.Writer) -> None
    self.f = f
    self.num_chars = 0

  def write(self, s):
    # type: (str) -> None
    self.f.write(s)
    self.num_chars += len(s)  # Only count visible characters!


class TextOutput(ColorOutput):
  """TextOutput put obeys the color interface, but outputs nothing."""

  def __init__(self, f):
    # type: (mylib.Writer) -> None
    """
    This docstring used to interfere with __init__ detection
    """
    # Note: translated into an initializer list.
    ColorOutput.__init__(self, f)
    print('TextOutput constructor')


class Base(object):
  def method(self):
    # type: () -> str
    return "Base"

  def x(self):
    # type: () -> int
    return 42


class Derived(Base):
  def method(self):
    # type: () -> str
    return "Derived"

  def y(self):
    # type: () -> int
    return 43


def f(obj):
  # type: (Base) -> str
  return obj.method()


def run_tests():
  # type: () -> None
  stdout = mylib.Stdout()
  out = TextOutput(stdout)
  out.write('foo\n')
  out.write('bar\n')
  log('Wrote %d bytes', out.num_chars)

  #b = Base()
  d = Derived()
  #log(b.method())
  print(d.method())
  print(f(d))


def run_benchmarks():
  # type: () -> None
  n = 500000

  x = 33
  result = -1

  f = mylib.BufWriter()
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
