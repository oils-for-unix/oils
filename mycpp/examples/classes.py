#!/usr/bin/env python2
"""
classes.py - Test out inheritance.  Based on asdl/format.py.
"""
from __future__ import print_function

import cStringIO
import os
import sys

from mycpp import mylib
from mycpp.mylib import log

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

  def MutateFields(self):
    # type: () -> None
    self.num_chars = 42
    self.i = 43

  def PrintFields(self):
    # type: () -> None
    print("num_chars = %d" % self.num_chars)  # field from base
    print("i = %d" % self.i)  # field from derived


class Abstract(object):
  def __init__(self):
    # type: () -> None
    pass

  def TypeString(self):
    # type: () -> str

    # TODO: could be translated to TypeString() = 0; in C++
    raise NotImplementedError()


class Base(Abstract):

  # empty constructor required by mycpp
  def __init__(self, s):
    # type: (str) -> None
    self.s = s

  def TypeString(self):
    # type: () -> str
    return "Base with %s" % self.s


class Derived(Base):

  def __init__(self, s):
    # type: (str) -> None
    Base.__init__(self, s)

  def TypeString(self):
    # type: () -> str
    return "Derived with %s" % self.s


def TestMethods():
  # type: () -> None

  stdout = mylib.Stdout()
  out = TextOutput(stdout)
  out.write('foo\n')
  out.write('bar\n')
  log('Wrote %d bytes', out.num_chars)

  out.MutateFields()
  out.PrintFields()


def f(obj):
  # type: (Base) -> str
  return obj.TypeString()


# Note: this happsns to work, but globals should probably be disallowed
GLOBAL = Derived('goo')

def TestInheritance():
  # type: () -> None

  b = Base('bee')
  d = Derived('dog')
  log("b.TypeString() %s", b.TypeString())
  log("d.TypeString() %s", d.TypeString())
  log("f(b)           %s", f(b))
  log("f(d)           %s", f(d))
  log("f(GLOBAL)      %s", f(GLOBAL))


def run_tests():
  # type: () -> None
  TestMethods()
  TestInheritance()


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
