#!/usr/bin/env python2
"""
pyvm2_test.py: Tests for pyvm2.py
"""

import unittest

import pyvm2  # module under test
import pyobj


def dummy():
    return 1 + 2


class TestGuestException(unittest.TestCase):

    def testGuestException(self):
        co = dummy.__code__
        back = None  # Frame pointer

        locals_ = globals()
        globals_ = globals()

        frames = [pyobj.Frame(co, globals_, locals_, back)]
        g = pyvm2.GuestException(RuntimeError, 1, frames)
        print(g)


if __name__ == '__main__':
  unittest.main()
