#!/usr/bin/env python2
"""
pyj8_test.py: Tests for pyj8.py
"""
from __future__ import print_function

import unittest

from data_lang import pyj8  # module under test


class J8Test(unittest.TestCase):

    def testEncode(self):
        en = pyj8.EncodeString('hello', 0)
        print(en)

        en = pyj8.EncodeString('\xff-\xfe-\xff-\xfe', 0)
        print(en)

        # multiple errrors
        en = pyj8.EncodeString('hello\xffthere \xfe\xff gah', 0)
        print(en)

        # valid mu
        en = pyj8.EncodeString('hello \xce\xbc there', 0)
        print(en)

        # two first bytes - invalid
        en = pyj8.EncodeString('hello \xce\xce there', 0)
        print(en)

        # two cont bytes - invalid
        en = pyj8.EncodeString('hello \xbc\xbc there', 0)
        print(en)


if __name__ == '__main__':
    unittest.main()

# vim: sw=4
