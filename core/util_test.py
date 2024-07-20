#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""util_test.py: Tests for util.py."""

import unittest
import sys

from core import util  # module under test

# guard some tests that fail on Darwin
IS_DARWIN = sys.platform == 'darwin'


class UtilTest(unittest.TestCase):

    def testDebugFile(self):
        n = util.NullDebugFile()
        n.write('foo')

    def testRegexSearch(self):
        cases = [
            ('([a-z]+)([0-9]+)', 'foo123', ['foo123', 'foo', '123']),
            (r'.*\.py', 'foo.py', ['foo.py']),
            (r'.*\.py', 'abcd', None),
            # The match is unanchored
            (r'bc', 'abcd', ['bc']),
            # The match is unanchored
            (r'.c', 'abcd', ['bc']),
            # Empty matches empty
            None if IS_DARWIN else (r'', '', ['']),
            (r'^$', '', ['']),
            (r'^.$', '', None),
            (r'(a*)(b*)', '', ['', '', '']),
            (r'(a*)(b*)', 'aa', ['aa', 'aa', '']),
            (r'(a*)(b*)', 'bb', ['bb', '', 'bb']),
            (r'(a*)(b*)', 'aabb', ['aabb', 'aa', 'bb']),
            (r'(a*(z)?)|(b*)', 'aaz', ['aaz', 'aaz', 'z', '']),
            (r'(a*(z)?)|(b*)', 'bb', ['bb', '', '', 'bb']),
        ]

        # TODO:
        #
        # return a single list of length 2*(1 + nsub)
        # 2 is for start and end, +1 is for 0
        #
        # indices = regex_search(...)
        # indices[2*group] is start
        # indices[2*group+1] is end
        # group is from 0 ... n

        for pat, s, expected in filter(None, cases):
            #print('CASE %s' % pat)
            actual = util.RegexSearch(pat, s)
            #print('actual %r' % actual)
            self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
