#!/usr/bin/env python2
"""
posix_test.py: Tests for our posix_ module subset.

NOTE: There are more tests in Python-2.7.13/Lib/test/test_posix.py.
"""
from __future__ import print_function

import unittest

import posix_  # module under test


# Taken from build/oil-defs/.../posix_methods.def

FUNCS = [
    "access",
    "chdir",
    "getcwd",
    "listdir",
    "lstat",
    "readlink",
    "stat",
    "umask",
    "uname",
    "_exit",
    "execv",
    "execve",
    "fork",
    "geteuid",
    "getpid",
    "getuid",
    "wait",
    "open",
    "close",
    "dup2",
    "read",
    "write",
    "fdopen",
    "isatty",
    "pipe",
    "strerror",
    "WIFSIGNALED",
    "WIFEXITED",
    "WEXITSTATUS",
    "WTERMSIG",

    # Additional names found by grepping
    'X_OK',
    'R_OK',
    'W_OK',

    'O_APPEND',
    'O_CREAT',
    'O_RDONLY',
    'O_RDWR',
    'O_TRUNC',
    'O_WRONLY',
]

class FooTest(unittest.TestCase):

  def testFoo(self):
    print(posix_.getcwd())

  def testFunctionsExist(self):
    for name in FUNCS:
      func = getattr(posix_, name)
      print(func)


if __name__ == '__main__':
  unittest.main()
