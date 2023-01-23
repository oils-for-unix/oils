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


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
