#!/usr/bin/env python2
from __future__ import print_function

import cgi
import unittest


class FuncsTest(unittest.TestCase):

    def testHtmlEscape(self):
        s = '<script>"This" isn\'t right</script>'
        print(cgi.escape(s))

        # Hm I think you're supposed to escape ' too
        print(cgi.escape(s, quote=True))

        # Python 3 enhanced this to take a dict
        # https://docs.python.org/3.3/library/stdtypes.html?highlight=maketrans#str.maketrans
        # We should write our own

        d = {'<': '&lt;'}
        #t = string.maketrans(['a', 'b'], ['aa', 'bb'])
        #print(t)


if __name__ == '__main__':
    unittest.main()
