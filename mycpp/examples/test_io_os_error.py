#!/usr/bin/env python2
"""
exceptions.py
"""
from __future__ import print_function

#from errno import EISDIR
import os
from mycpp.mylib import log, print_stderr

from typing import List


def Close(fd):
  # type: (int) -> None

  #raise OSError(EISDIR)
  raise OSError(0)


def Pop(fd):
  # type: (int) -> None
  #log('Close %d', orig)
  try:
    #posix.close(rf.orig_fd)
    Close(fd)
  except (IOError, OSError) as e:
    #log('Error closing descriptor %d: %s', rf.orig_fd, pyutil.strerror(e))
    log('Error closing descriptor %d', fd)
    raise


def AppBundleMain(argv):
  # type: (List[str]) -> int

  Pop(3)

  return 0


def run_tests():
  # type: () -> int

  argv = []  # type: List[str]

  try:
    return AppBundleMain(argv)

  #except error.Usage as e:
  #  #builtin.Help(['oil-usage'], util.GetResourceLoader())
  #  log('oil: %s', e.msg)
  #  return 2

  except KeyboardInterrupt:
    print('')
    return 130  # 128 + 2

  except (IOError, OSError) as e:
    if 0:
      import traceback
      traceback.print_exc()

    # test this with prlimit --nproc=1 --pid=$$
    #print_stderr('osh I/O error (main): %s' % posix.strerror(e.errno))
    print_stderr('osh I/O error (main)')
    return 2  # dash gives status 2


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
