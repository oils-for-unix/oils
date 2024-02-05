#!/usr/bin/env python2
from __future__ import print_function

import unittest

from data_lang import j8


class J8Test(unittest.TestCase):

    def testJ8(self):
        s = '{}'
        p = j8.Parser(s, True)
        obj = p.ParseValue()
        print(obj)

    def testNil8(self):
        cases = [
            '()',
            '(42)',
            '[]',

            '[42]',
            '[42 43]',
            '[42 ["a" "b"]]',

            '42',
            '"hi"',
            ]
        for s in cases:
            p = j8.Nil8Parser(s, True)
            obj = p.ParseNil8()
            print(s)
            print('    %s' % obj)
            print()


class YajlTest(unittest.TestCase):
    """
    Note on old tests for YAJL.  Differences

    - It decoded to Python 2 str() type, not unicode()
    - Bug in emitting \\xff literally, which is not valid JSON
      - turns out there is a C level option for this
    """
    pass


if __name__ == '__main__':
    unittest.main()
