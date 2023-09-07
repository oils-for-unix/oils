#!/usr/bin/env python2
"""
classes.py - Test out inheritance.
"""
from __future__ import print_function

import cStringIO
import os
import sys

from mycpp import mylib
from mycpp.mylib import log

from typing import IO, cast


# Based on asdl/format.py

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


#
# Heterogeneous linked list to test field masks, inheritance, virtual dispatch,
# constructors, etc.
#

class Abstract(object):

  # empty constructor required by mycpp
  def __init__(self):
    # type: () -> None
    pass

  def TypeString(self):
    # type: () -> str

    # TODO: could be translated to TypeString() = 0; in C++
    raise NotImplementedError()


class Base(Abstract):

  def __init__(self, n):
    # type: (Base) -> None
    Abstract.__init__(self)
    self.next = n

  def TypeString(self):
    # type: () -> str
    return "Base(%s)" % ('next' if self.next else 'null')


class DerivedI(Base):

  def __init__(self, n, i):
    # type: (Base, int) -> None
    Base.__init__(self, n)
    self.i = i

  def Integer(self):
    # type: () -> int
    return self.i

  def TypeString(self):
    # type: () -> str
    return "DerivedI(%s, %d)" % ('next' if self.next else 'null', self.i)


class DerivedSS(Base):

  def __init__(self, n, t, u):
    # type: (Base, str, str) -> None
    Base.__init__(self, n)
    self.t = t
    self.u = u

  def TypeString(self):
    # type: () -> str
    return "DerivedSS(%s, %s, %s)" % (
        'next' if self.next else 'null', self.t, self.u)

#
# Homogeneous Node
#

class Node(object):
  """No vtable pointer."""
  def __init__(self, n, i):
    # type: (Node, int) -> None
    self.next = n
    self.i = i


def TestMethods():
  # type: () -> None

  stdout_ = mylib.Stdout()
  out = TextOutput(stdout_)
  out.write('foo\n')
  out.write('bar\n')
  log('Wrote %d bytes', out.num_chars)

  out.MutateFields()
  out.PrintFields()


def f(obj):
  # type: (Base) -> str
  return obj.TypeString()


def TestInheritance():
  # type: () -> None

  b = Base(None)
  di = DerivedI(None, 1)
  dss = DerivedSS(None, 'left', 'right')

  log('Integer() = %d', di.Integer())

  log("b.TypeString()   %s", b.TypeString())
  log("di.TypeString()  %s", di.TypeString())
  log("dss.TypeString() %s", dss.TypeString())

  log("f(b)           %s", f(b))
  log("f(di)          %s", f(di))
  log("f(dss)         %s", f(dss))


def run_tests():
  # type: () -> None
  TestMethods()
  TestInheritance()


def BenchmarkWriter(n):
  # type: (int) -> None

  log('BenchmarkWriter')
  log('')

  f = mylib.BufWriter()
  out = TextOutput(f)

  i = 0
  while i < n:
    out.write('foo\n')
    i += 1
  log('  Ran %d iterations', n)
  log('  Wrote %d bytes', out.num_chars)
  log('')


def PrintLength(node):
  # type: (Node) -> None

  current = node
  linked_list_len = 0
  while True:
    if linked_list_len < 10:
      log('  -> %d', current.i)

    current = current.next

    if current is None:
      break

    linked_list_len += 1

  log('')
  log("  linked list len = %d", linked_list_len)
  log('')


def BenchmarkSimpleNode(n):
  # type: (int) -> None

  log('BenchmarkSimpleNode')
  log('')

  next_ = Node(None, -1)
  for i in xrange(n):
    node = Node(next_, i)
    next_ = node

  PrintLength(node)


def PrintLengthBase(current):
  # type: (Base) -> None

  linked_list_len = 0
  while True:
    if linked_list_len < 10:
      log('  -> %s', current.TypeString())

    current = current.next

    if current is None:
      break
    linked_list_len += 1

  log('')
  log("  linked list len = %d", linked_list_len)
  log('')


def BenchmarkVirtualNodes(n):
  # type: (int) -> None
  """With virtual function pointers"""

  log('BenchmarkVirtualNodes')
  log('')

  next_ = Base(None)
  for i in xrange(n):
    node1 = DerivedI(next_, i)

    # Allocate some children
    s1 = str(i)
    s2 = '+%d' % i
    node2 = DerivedSS(node1, s1, s2)

    node3 = Base(node2)
    next_ = node3

  # do this separately because of type
  current = None  # type: Base
  current = node3

  PrintLengthBase(current)


def run_benchmarks():
  # type: () -> None

  # NOTE: Raising this exposes quadratic behavior
  #  30,000 iterations:  1.4 seconds in cxx-opt mode
  #  60,000 iterations:  5.0 seconds in cxx-opt mode
  if 1:
    BenchmarkWriter(30000)

  if 1:
    BenchmarkSimpleNode(10000)

  # Hits Collect() and ASAN finds bugs above 500 and before 1000
  #BenchmarkNodes(750)
  if 1:
    BenchmarkVirtualNodes(1000)


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()

# vim: sw=2
