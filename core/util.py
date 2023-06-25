#t!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
util.py - Common infrastructure.
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_e, value_str, value_t
from _devbuild.gen.syntax_asdl import loc
from core import error
from mycpp import mylib

from typing import cast


class UserExit(Exception):
    """For explicit 'exit'."""

    def __init__(self, status):
        # type: (int) -> None
        self.status = status


class HistoryError(Exception):
    def __init__(self, msg):
        # type: (str) -> None
        self.msg = msg

    def UserErrorString(self):
        # type: () -> str
        return 'history: %s' % self.msg


class _DebugFile(object):
    def __init__(self):
        # type: () -> None
        pass

    def write(self, s):
        # type: (str) -> None
        pass

    def writeln(self, s):
        # type: (str) -> None
        pass

    def isatty(self):
        # type: () -> bool
        return False


class NullDebugFile(_DebugFile):
    def __init__(self):
        # type: () -> None
        """Empty constructor for mycpp."""
        _DebugFile.__init__(self)


class DebugFile(_DebugFile):
    def __init__(self, f):
        # type: (mylib.Writer) -> None
        _DebugFile.__init__(self)
        self.f = f

    def write(self, s):
        # type: (str) -> None
        """Used by dev::Tracer and ASDL node.PrettyPrint()."""
        self.f.write(s)

    def writeln(self, s):
        # type: (str) -> None
        self.write(s + '\n')

    def isatty(self):
        # type: () -> bool
        """Used by node.PrettyPrint()."""
        return self.f.isatty()


def MustBeInt(val):
    # type: (value_t) -> value.Int
    UP_val = val
    if val.tag() == value_e.Int:
        val = cast(value.Int, UP_val)
        return val

    raise error.InvalidType(
        'expected value.Int, but got %s' % value_str(val.tag()), loc.Missing)


def MustBeStr(val):
    # type: (value_t) -> value.Str
    UP_val = val
    if val.tag() == value_e.Str:
        val = cast(value.Str, UP_val)
        return val

    raise error.InvalidType(
        'expected value.Str, but got %s' % value_str(val.tag()), loc.Missing)


def MustBeList(val):
    # type: (value_t) -> value.List
    UP_val = val
    if val.tag() == value_e.List:
        val = cast(value.List, UP_val)
        return val

    raise error.InvalidType(
        'expected value.List, but got %s' % value_str(val.tag()), loc.Missing)


def MustBeFunc(val):
    # type: (value_t) -> value.Func
    UP_val = val
    if val.tag() == value_e.Func:
        val = cast(value.Func, UP_val)
        return val

    raise error.InvalidType(
        'expected value.Func, but got %s' % value_str(val.tag()), loc.Missing)
