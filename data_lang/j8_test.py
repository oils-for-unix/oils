#!/usr/bin/env python2
from __future__ import print_function
"""
Old tests for YAJL, could probably be deleted.

Differences

- It decoded to Python 2 str() type, not unicode()
- Bug in emitting \\xff literally, which is not valid JSON
"""

import unittest

import json
from mycpp import mylib
from mycpp.mylib import log

try:
    import yajl
except ImportError:
    yajl = None

yajl = None  # no longer using this module

from data_lang import j8


if yajl:
    def dumps(obj):
        return yajl.dumps(obj)


    def loads(s):
        return yajl.loads(s)

else:
    dumps = json.dumps
    loads = json.loads

    # This doesn't work, we would need the old ysh/cpython.py to do value_t
    # conversion
    def BAD_dumps(obj):
        p = j8.Printer()

        buf = mylib.BufWriter()
        p.PrintJsonMessage(obj, buf, -1)
        return buf.getvalue()

    def BAD_loads(s):
        p = j8.Parser(s)
        return p.ParseJson()


class YajlTest(unittest.TestCase):

    def testMisc(self):
        print(dumps({'foo': 42}))

        # Gives us unicode back
        print(loads('{"bar": 43}'))

    def testIntOverflow(self):
        log('OVERFLOW')
        CASES = [
            0,
            2**31,
            2**32,
            2**64 - 1,
            2**64,
            2**128,
        ]
        for i in CASES:
            print('--')

            # This raises Overflow?  I guess the problem is that yajl takes an
            # integer.
            #print(dumps(i))
            s = str(i)
            print(s)

            print(loads('{"k": %d}' % i))

            # Why doesn't it parse raw integers?
            #print(loads(s))

        log('')

    def testParseError(self):
        if 0:
            loads('[')

    def testBool(self):
        log('BOOL')
        print(dumps(True))
        print(loads('false'))
        log('')

    def testInt(self):
        log('INT')
        encoded = dumps(123)
        print('encoded = %r' % encoded)
        self.assertEqual('123', encoded)

        # Bug fix over latest version of py-yajl: a lone int decodes
        decoded = loads('123\n')
        print('decoded = %r' % decoded)
        self.assertEqual(123, decoded)

        decoded = loads('{"a":123}\n')
        print('decoded = %r' % decoded)
        log('')

    def testFloat(self):
        log('FLOAT')
        print(dumps(123.4))

        # Bug fix over latest version of py-yajl: a lone float decodes
        decoded = loads('123.4')
        self.assertEqual(123.4, decoded)
        log('')

    def testList(self):
        log('LIST')
        print(dumps([4, "foo", False]))
        print(loads('[4, "foo", false]'))
        log('')

    def testDict(self):
        log('DICT')
        d = {"bool": False, "int": 42, "float": 3.14, "string": "s"}
        print(dumps(d))

        s = '{"bool": false, "int": 42, "float": 3.14, "string": "s"}'
        print(loads(s))
        log('')

    def testStringEncoding(self):
        log('STRING ENCODE')

        # It should just raise with Unicode instance
        #print(dumps(u'abc\u0100def'))

        # yajl inserts \xff literally -- this is a BUG because JSON messages
        # must be valid UTF-8.
        if yajl:
            print(dumps('\x00\xff'))

        # mu character
        print(dumps('\xCE\xBC'))

    def testStringDecoding(self):
        log('STRING DECODE')

        # This should decode to a utf-8 str()!
        # Not a unicode instance!

        s = loads('"abc"')
        print(repr(s))

        obj = loads('"\u03bc"')
        if yajl:
            assert isinstance(obj, str), repr(obj)
            self.assertEqual(obj, '\xce\xbc')

        obj = loads('"\xce\xbc"')
        if yajl:
            assert isinstance(obj, str), repr(obj)
            self.assertEqual(obj, '\xce\xbc')

        # Invalid utf-8.  Doesn't give a good parse error!
        if 0:
            u = loads('"\xFF"')
            print(repr(u))

    def testOrdered(self):
        from collections import OrderedDict

        # Order is lost
        d1 = OrderedDict({'a': 1, 'b': 2, 'c': 3})

        # Preserved
        d = OrderedDict([('a', 1), ('b', 2), ('c', 3)])
        d['a'] = 42
        d['d'] = 50

        #d = OrderedDict([('z', 1), ('y', 2), ('x', 3)])
        #d['a'] = 42
        #d['z'] = 50

        actual = dumps(d)
        if yajl:
            self.assertEqual('{"a":42,"b":2,"c":3,"d":50}', actual)
        else:
            self.assertEqual('{"a": 42, "b": 2, "c": 3, "d": 50}', actual)

        #
        # More tests in py-yajl/tests/unit.py
        #


if __name__ == '__main__':
    unittest.main()
