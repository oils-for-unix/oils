#!/usr/bin/env python2
"""
strings.py
"""
from __future__ import print_function

import os
from mycpp.mylib import log


class Foo(object):
  def __init__(self):
    # type: () -> None
    self.s = 'mystr'


def TestMethods():
    # type: () -> None

    s = 'a1bc'

    if s.startswith(''):
        print('empty yes')

    if s.startswith('a1'):
        print('a1 yes')

    if not s.startswith('zz'):
        print('zz no')

    if s.endswith(''):
        print('empty yes')

    if s.endswith('bc'):
        print('bc yes')

    if s.endswith('c'):
        print('bc yes')

    if not s.endswith('zzzzzz'):
        print('zzzzzz no')

    # This file is out of date!  It thinks it happens in Python 3, but we have
    # it in Python 2.7

    # /home/andy/wedge/oils-for-unix.org/pkg/mypy/0.780/mypy/typeshed/stdlib/2/__builtin__.pyi:509: note: "startswith" of "str" defined here

    # Fixed here - https://github.com/python/typeshed/blob/main/stdlib/builtins.pyi
    #
    # It can be fixed by patching, gah

    # start pos
    #if s.startswith('bc', start=2):
    #    print('bc YES')


def run_tests():
  # type: () -> None

  print('foo' + 'bar')
  print('foo' * 3)
  obj = Foo()
  print('foo' + obj.s)

  s = 'mystr'
  print('[%s]' % s)

  s = 'mystr'
  print('[%s, %s]' % (s, 'abc'))

  print('%s: 5%%-100%%' % 'abc')

  print('<a href="foo.html">%s</a>' % 'anchor')

  print("foo? %d" % ('f' in s))
  print("str? %d" % ('s' in s))

  print("int 5d %5d" % 35)

  print("'single'")
  print('"double"')

  # test escape codes
  print("a\tb\nc\td\n")

  x = 'x'
  print("%s\tb\n%s\td\n" % (x, x))

  fmt = "%dfoo"
  print(fmt % 10)

  fmts = ["foo%d"]
  print(fmts[0] % 10)

  print(("foo " + "%s") % "bar")

  # NUL bytes
  s = "spam\0%s" % "eggs"

  # TODO: There's a bug here -- we get len == 4 in C++, but it should be 9.
  # It's either StrFormat() or the bad JSON literals \u0000
  if 0:
    print("len(s) = %d" % len(s))
    print(s)

  s = "foo%s" % "\0bar"
  print("len(s) = %d" % len(s))

  print("%o" % 12345)
  print("%17o" % 12345)
  print("%017o" % 12345)

  print("%%%d%%%%" % 12345)

  print("%r" % "tab\tline\nline\r\n")

  s = 'a1b2c3d4e5'
  # Disable step support
  # print(s[0:10:2])
  # print(s[1:10:2])
  print(s.upper())

  TestMethods()


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
