#!/usr/bin/env python2
"""
builtin_oil_test.py: Tests for builtin_oil.py
"""
from __future__ import print_function

import unittest

import yajl  # test thi stoo

#from oil_lang import builtin_oil  # module under test


class JsonTest(unittest.TestCase):

  def testYajl(self):
    print(yajl.dumps({'foo': 42}))

    # Gives us unicode back
    print(yajl.loads('{"bar": 43}'))

    # TODO: Test 

    CASES = [
        0,
        2 ** 31,
        2 ** 32, 
        #2 ** 64 -1,
        #2 ** 64, 
        #2 ** 128, 
    ]
    for i in CASES:
      print('--')
      print(yajl.dumps(i))
      s = str(i)
      print(s)

      print(yajl.loads('{"k": %d}' % i))

      # Why doesn't it parse raw integers?
      #print(yajl.loads(s))



if __name__ == '__main__':
  unittest.main()
