#!/usr/bin/env python2
"""
strings.py
"""
from __future__ import print_function

import os
from mycpp import mylib
from mycpp.mylib import log

from typing import List


def banner(s):
    # type: (str) -> None
    print('')
    print('=== %s ===' % s)
    print('')


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

    # find(s, start, end) can be used to implement TokenStartsWith() and
    # TokenEndsWith(), TokenEquals(), IsPlusEquals(), TokenContains(), etc.

    s = 'aaa-bb-cc'
    substrs = [
        'aa',
        'b',
        'z',
        'aaaa',  # too long
        '',
    ]
    for substr in substrs:
        for start in xrange(0, len(s)):
            pos = s.find(substr, start)
            print('%s find %s start:%d => %d' % (s, substr, start, pos))

    print('---')

    for substr in substrs:
        for end in xrange(0, len(s)):
            pos = s.find(substr, 0, end)
            print('%s find %s end:%d => %d' % (s, substr, end, pos))

    print('---')

    # empty string test
    for start in xrange(0, 3):
        for end in xrange(0, 3):
            pos = s.find('', start, end)
            print('%s find empty [%d, %d) => %d' % (s, start, end, pos))


def TestFormat():
    # type: () -> None

    banner('TestFormat')

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


def TestByteOperations():
    # type: () -> None
    banner('TestByteOperations')

    s = 'foo' * 10

    i = 0
    n = len(s)
    total = 0
    total2 = 0
    while i < n:
        byte = ord(s[i])
        byte2 = mylib.ByteAt(s, i)

        total += byte
        total2 += byte2

        i += 1

    if total != total2:
        raise AssertionError()

    print('total = %d' % total)
    print('total2 = %d' % total2)


def TestBytes2():
    # type: () -> None

    banner('TestBytes2')

    b = []  # type: List[int]
    ch = []  # type: List[str]
    for i in xrange(256):
        # Shuffle it a bit, make it a better test
        j = 255 - i
        if j == 2:
            j = 0

        b.append(j)
        ch.append(chr(j))

    print('len(b) = %d' % len(b))
    print('len(ch) = %d' % len(ch))

    all_bytes = ''.join(ch)

    b2 = mylib.JoinBytes(b)
    if all_bytes == b2:
        print('EQUAL ==')
    else:
        raise AssertionError('should be equal')

    n = len(all_bytes)
    print('len(all_bytes) = %d' % n)
    print('')
    #print('[%s]' % all_bytes)

    i = 0
    while i < n:
        byte = mylib.ByteAt(all_bytes, i)
        #log('byte = %d', byte)

        if mylib.ByteEquals(byte, '['):
            print('LEFT')
        if mylib.ByteEquals(byte, ']'):
            print('RIGHT')
        if mylib.ByteEquals(byte, '\\'):
            print('BACKSLASH')

        # TODO: get rid of JSON crap
        #if mylib.ByteEqualsStr(byte, '\xff'):
        #    print('0xff')

        if mylib.ByteEquals(byte, chr(255)):
            print('0xff')

        if mylib.ByteInSet(byte, 'abcXYZ'):
            print('abcXYZ')

        i += 1

    print('')


def run_tests():
    # type: () -> None

    TestFormat()
    TestMethods()
    TestByteOperations()
    TestBytes2()


def run_benchmarks():
    # type: () -> None
    pass


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
