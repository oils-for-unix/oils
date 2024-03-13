#!/usr/bin/env python2
"""
exceptions.py
"""
from __future__ import print_function

#from errno import EISDIR
import os
from mycpp.mylib import log, print_stderr

from typing import List, Any
#import posix_ as posix


def Close(fd):
    # type: (int) -> None

    #raise OSError(EISDIR)
    raise OSError(0)


def Pop(fd):
    # type: (int) -> None

    try:
        #posix.close(fd)
        Close(fd)
    except (IOError, OSError) as e:
        #log('Error closing descriptor %d: %s', rf.orig_fd, pyutil.strerror(e))
        log('Error closing descriptor %d', fd)
        raise


def AppBundleMain(argv):
    # type: (List[str]) -> int

    Pop(3)

    return 0


def TestRethrow():
    # type: () -> int
    """
  This is fine, the problem was throwing an exceptinon in a DESTRUCTOR
  """
    argv = []  # type: List[str]

    try:
        return AppBundleMain(argv)

    except ValueError as e:
        return 2
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


class ctx_TerminalControl(object):

    def __init__(self):
        # type: () -> None

        log('TerminalControl init')

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        log('TerminalControl exit')

        TestRethrow()

        # https://akrzemi1.wordpress.com/2011/09/21/destructors-that-throw/

        # Quote: Until any exception gets out from the destructor we can throw at
        # will inside, even from other destructors, and this does not account for
        # double-exception situation or "throwing from destructor during stack
        # unwinding." Let's illustrate it with an example.
        log('Throw and Catch within destructor seems OK')


def TestDestructor():
    # type: () -> None

    with ctx_TerminalControl():
        log('hi')


def run_tests():
    # type: () -> int

    TestRethrow()

    log('')
    log('TestDestructor')
    log('')

    TestDestructor()

    return 0


def run_benchmarks():
    # type: () -> None
    raise NotImplementedError()


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
