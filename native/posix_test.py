#!/usr/bin/env python2
"""
posix_test.py: Tests for our posix_ module subset.

NOTE: There are more tests in Python-2.7.13/Lib/test/test_posix.py.

Notes on stripping posixmodule.c:

I left in:

  - putenv, unsetenv: Isn't it simpler to use these than os.environ?  I'm not
    sure how it works.
  - tcgetpgrp, tcsetpgrp, setsid, getsid: is this for job control?

  - times: This is a builtin!  It's like 'time' for the shell prosecs itself.
  - symlink - useful for writing tools?
  - waitpid - because we're using wait

  - set*uid, etc. - for container tools?
  - kill, killpg - would the kill builtin need these?
  - getppid - I think for $PPID
  - setpgrp, getpgrp

  - fork1() -- what is this for?
  - mkdir, rmdir() -- might be useful for tools


Other notes:

  - The shell uses dup2 but not dup?
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
    # Testing this because I removed a lot of #ifdef
    entries = posix_.listdir('.')
    self.assert_('doc' in entries)

  def testFunctionsExist(self):
    for name in FUNCS:
      func = getattr(posix_, name)
      print(func)


if __name__ == '__main__':
  unittest.main()
