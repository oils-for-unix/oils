#!/usr/bin/env python2
"""
pyj8_test.py: Tests for pyj8.py
"""
from __future__ import print_function

import unittest

from data_lang import pyj8  # module under test
from mycpp import mylib


def _EncodeString(s, options):
    # type: (str, int) -> str
    buf = mylib.BufWriter()
    pyj8.WriteString(s, options, buf)
    return buf.getvalue()


class PyJ8Test(unittest.TestCase):

    def testEncode(self):
        en = _EncodeString('hello', 0)
        print(en)

        en = _EncodeString('\xff-\xfe-\xff-\xfe', 0)
        print(en)

        # multiple errrors
        en = _EncodeString('hello\xffthere \xfe\xff gah', 0)
        print(en)

        # valid mu
        en = _EncodeString('hello \xce\xbc there', 0)
        print(en)

        # two first bytes - invalid
        en = _EncodeString('hello \xce\xce there', 0)
        print(en)

        # two cont bytes - invalid
        en = _EncodeString('hello \xbc\xbc there', 0)
        print(en)

        en = _EncodeString('hello \xbc\xbc there', pyj8.LOSSY_JSON_STRINGS)
        print(en)


if __name__ == '__main__':
    unittest.main()

# vim: sw=4
