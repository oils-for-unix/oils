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

from core import ansi
from core import pyutil
from mycpp import mylib

import libc

from typing import List


def RegexGroups(s, indices):
    # type: (str, List[int]) -> List[str]
    groups = []  # type: List[str]
    n = len(indices)
    for i in xrange(n / 2):
        start = indices[2 * i]
        end = indices[2 * i + 1]
        if start == -1:
            groups.append(None)
        else:
            groups.append(s[start:end])
    return groups


def simple_regex_search(pat, s):
    # type: (str, str) -> List[str]
    """Convenience wrapper around libc."""
    indices = libc.regex_search(pat, 0, s, 0)
    if indices is None:
        return None
    return RegexGroups(s, indices)


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
        self.f.flush()

    def isatty(self):
        # type: () -> bool
        """Used by node.PrettyPrint()."""
        return self.f.isatty()


def PrintTopicHeader(topic_id, f):
    # type: (str, mylib.Writer) -> None
    if f.isatty():
        f.write('%s %s %s\n' % (ansi.REVERSE, topic_id, ansi.RESET))
    else:
        f.write('~~~ %s ~~~\n' % topic_id)

    f.write('\n')


def PrintEmbeddedHelp(loader, topic_id, f):
    # type: (pyutil._ResourceLoader, str, mylib.Writer) -> bool
    try:
        contents = loader.Get('_devbuild/help/%s' % topic_id)
    except (IOError, OSError):
        return False

    PrintTopicHeader(topic_id, f)
    f.write(contents)
    f.write('\n')
    return True  # found


def _PrintVersionLine(loader, f):
    # type: (pyutil._ResourceLoader, mylib.Writer) -> None
    v = pyutil.GetVersion(loader)
    f.write('Oils %s\t\thttps://www.oilshell.org/\n' % v)


def HelpFlag(loader, topic_id, f):
    # type: (pyutil._ResourceLoader, str, mylib.Writer) -> None
    _PrintVersionLine(loader, f)
    f.write('\n')
    found = PrintEmbeddedHelp(loader, topic_id, f)
    # Note: could assert this in C++ too
    assert found, 'Missing %s' % topic_id


def VersionFlag(loader, f):
    # type: (pyutil._ResourceLoader, mylib.Writer) -> None
    _PrintVersionLine(loader, f)
    f.write('\n')
    pyutil.PrintVersionDetails(loader)
