#!/usr/bin/env python2
"""
builtin_oil_test.py: Tests for builtin_oil.py
"""
from __future__ import print_function

import unittest

from core.util import log
#from oil_lang import builtin_oil  # module under test

import yajl  # test this too


class YajlTest(unittest.TestCase):

  def testMisc(self):
    print(yajl.dumps({'foo': 42}))

    # Gives us unicode back
    print(yajl.loads('{"bar": 43}'))

  def testIntOverflow(self):
    log('OVERFLOW')
    CASES = [
        0,
        2 ** 31,
        2 ** 32, 
        2 ** 64 -1,
        2 ** 64, 
        2 ** 128, 
    ]
    for i in CASES:
      print('--')

      # This raises Overflow?  I guess the problem is that yajl takes an
      # integer.
      #print(yajl.dumps(i))
      s = str(i)
      print(s)

      print(yajl.loads('{"k": %d}' % i))

      # Why doesn't it parse raw integers?
      #print(yajl.loads(s))

    log('')

  def testParseError(self):
    if 0:
      yajl.loads('[')

  def testBool(self):
    log('BOOL')
    print(yajl.dumps(True))
    print(yajl.loads('false'))
    log('')

  def testInt(self):
    log('INT')
    encoded = yajl.dumps(123)
    print('encoded = %r' % encoded)
    self.assertEqual('123', encoded)

    # Bug fix over latest version of py-yajl: a lone int decodes
    decoded = yajl.loads('123\n')
    print('decoded = %r' % decoded)
    self.assertEqual(123, decoded)

    decoded = yajl.loads('{"a":123}\n')
    print('decoded = %r' % decoded)
    log('')

  def testFloat(self):
    log('FLOAT')
    print(yajl.dumps(123.4))

    # Bug fix over latest version of py-yajl: a lone float decodes
    decoded = yajl.loads('123.4')
    self.assertEqual(123.4, decoded)
    log('')

  def testList(self):
    log('LIST')
    print(yajl.dumps([4, "foo", False]))
    print(yajl.loads('[4, "foo", false]'))
    log('')

  def testDict(self):
    log('DICT')
    d = {"bool": False, "int": 42, "float": 3.14, "string": "s"}
    print(yajl.dumps(d))

    s = '{"bool": false, "int": 42, "float": 3.14, "string": "s"}'
    print(yajl.loads(s))
    log('')

  def testStringEncoding(self):
    log('STRING ENCODE')

    # It should just raise with Unicode instance
    #print(yajl.dumps(u'abc\u0100def'))

    # It inserts \xff literally, OK I guess that's fine.  It's not valid utf-8
    print(yajl.dumps('\x00\xff'))

    # mu character
    print(yajl.dumps('\xCE\xBC'))

  def testStringDecoding(self):
    log('STRING DECODE')

    # This should decode to a utf-8 str()!
    # Not a unicode instance!

    s = yajl.loads('"abc"')
    print(repr(s))

    obj = yajl.loads('"\u03bc"')
    assert isinstance(obj, str), repr(obj)
    self.assertEqual(obj, '\xce\xbc')

    obj = yajl.loads('"\xce\xbc"')
    assert isinstance(obj, str), repr(obj)
    self.assertEqual(obj, '\xce\xbc')


    # Invalid utf-8.  Doesn't give a good parse error!
    if 0:
      u = yajl.loads('"\xFF"')
      print(repr(u))


if __name__ == '__main__':
  unittest.main()
