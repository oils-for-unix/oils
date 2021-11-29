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
    self.i = 0  # field only in derived class

  def MutateField(self):
    # type: () -> None
    self.num_chars = 42
    self.i = 43

  def PrintFields(self):
    # type: () -> None
    print("num_chars = %d" % self.num_chars)  # field from base
    print("i = %d" % self.i)  # field from derived


class Base(object):

  # empty constructor required by mycpp
  def __init__(self):
    # type: () -> None
    pass

  def method(self):
    # type: () -> str
    return "Base"

  def x(self):
    # type: () -> int
    return 42


class Derived(Base):

  def __init__(self):
    # type: () -> None
    Base.__init__(self)

  def method(self):
    # type: () -> str
    return "Derived"

  def y(self):
    # type: () -> int
    return 43


GLOBAL = Derived()

# TODO: Test GC masks for fields.  Do subtypes re-initialize it?


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

  out.MutateField()
  out.PrintFields()

  #b = Base()
  d = Derived()
  #log(b.method())
  print(d.method())
  print(f(d))

  print(GLOBAL.method())


def run_benchmarks():
  # type: () -> None

  # NOTE: Raising this exposes quadratic behavior
  n = 50000

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
