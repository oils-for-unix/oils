#!/usr/bin/env python2
"""spelling_test.py: Tests for spelling.py."""
from __future__ import print_function

import unittest

import spelling  # module under test


class SpellingTest(unittest.TestCase):

    def testSplitWords(self):
        # type: () -> None

        docs = [
            r'''
        a b c   # single chars left out
        foo bar
        http://google.com   # url stripped
        spam

        https://google.com/?q=foo 
        file:///home/andy/git

        aren't
        can't

        array[r'\']

        ''',

            # real test case from lynx -dump
            '''
        hi
        9. file:///home/andy/git/oilshell/oil/_release/VERSION/doc/oil-language-faq.html#why-doesnt-a-raw-string-work-here-arrayr

        bye

        aren'tzzz
        '''

            # turns into "aren't", "zzz" which I guess is right
        ]

        for doc in docs:
            print(list(spelling.SplitWords(doc)))


if __name__ == '__main__':
    unittest.main()
