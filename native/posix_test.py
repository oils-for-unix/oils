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

  - mkdir, rmdir() -- might be useful for tools

Other notes:

  - The shell uses dup2 but not dup?
"""
from __future__ import print_function

import signal
import subprocess
import unittest

import posix_  # module under test
from core.util import log


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
    'X_OK_',
    'R_OK_',
    'W_OK_',

    'O_APPEND',
    'O_CREAT',
    'O_RDONLY',
    'O_RDWR',
    'O_TRUNC',
    'O_WRONLY',
]

class PosixTest(unittest.TestCase):

  def testFoo(self):
    print(posix_.getcwd())
    # Testing this because I removed a lot of #ifdef
    entries = posix_.listdir('.')
    self.assert_('doc' in entries)

  def testFunctionsExist(self):
    for name in FUNCS:
      func = getattr(posix_, name)
      print(func)

  def testEmptyReadAndWrite(self):
    # Regression for bug where this would hang
    posix_.read(0, 0)
    posix_.write(1, '')

  def testRead(self):
    if posix_.environ.get('EINTR_TEST'):
      # Now we can do kill -TERM PID can get EINTR.
      # Or Ctrl-C for KeyboardInterrupt

      signal.signal(signal.SIGTERM, _Handler)
      log('Hanging on read in pid %d', posix_.getpid())
      posix_.read(0, 1)

  def testWait(self):
    if posix_.environ.get('EINTR_TEST'):
      # Now we can do kill -TERM PID can get EINTR.
      signal.signal(signal.SIGTERM, _Handler)

      p = subprocess.Popen(['sleep', '5'])
      log('started sleep pid %d', p.pid)

      log('Hanging on wait in pid %d', posix_.getpid())
      posix_.wait()

  def testWaitpid(self):
    if posix_.environ.get('EINTR_TEST'):
      # Now we can do kill -TERM PID can get EINTR.
      signal.signal(signal.SIGTERM, _Handler)

      p = subprocess.Popen(['sleep', '5'])
      log('started sleep pid %d', p.pid)

      log('Hanging on waitpid in pid %d', posix_.getpid())
      posix_.waitpid(-1, 0)

  def testWrite(self):
    if posix_.environ.get('EINTR_TEST'):

      signal.signal(signal.SIGTERM, _Handler)
      r, w = posix_.pipe()
      log('Hanging on write in pid %d', posix_.getpid())

      # 1 byte bigger than pipe size
      n = posix_.write(w, 'x'*65537)
      log('1: Wrote %d bytes', n)

      # write returns early when a signal interrupts it, and we read at least
      # one byte!  We do NOT get EINTR>

      # On the second try, it didn't write anything, and we get EINTR!

      log('Second try (pid %d)', posix_.getpid())
      n = posix_.write(w, 'x'*65537)
      log('2: Wrote %d bytes', n)

  def testPrint(self):
    # Conclusion: print CAN raise IOError with EINTR.

    if posix_.environ.get('EINTR_TEST'):

      signal.signal(signal.SIGTERM, _Handler)
      r, w = posix_.pipe()
      log('Hanging on write in pid %d', posix_.getpid())
      f = posix_.fdopen(w, 'w')

      # 1 byte bigger than pipe size
      print('x'*65537, file=f)
      log('1: done')

      # write returns early when a signal interrupts it, and we read at least
      # one byte!  We do NOT get EINTR>

      # On the second try, it didn't write anything, and we get EINTR!

      log('Second try (pid %d)', posix_.getpid())
      print('x'*65537, file=f)
      log('2: done')


def _Handler(x, y):
  log('Got signal %s %s', x, y)


if __name__ == '__main__':
  unittest.main()
