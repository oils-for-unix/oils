#!/usr/bin/env python2
from __future__ import print_function

import unittest

from builtin import read_osh  # module under test
from osh import split


class BuiltinTest(unittest.TestCase):

    def testAppendParts(self):
        # allow_escape is True by default, but False when the user passes -r.
        CASES = [
            (['Aa', 'b', ' a b'], 100, 'Aa b \\ a\\ b'),
            (['a', 'b', 'c'], 3, 'a b c '),
        ]

        for expected_parts, max_results, line in CASES:
            sp = split.IfsSplitter(split.DEFAULT_IFS, '')
            spans = sp.Split(line, True)
            print('--- %r' % line)
            for span in spans:
                print('  %s %s' % span)

            parts = []
            read_osh._AppendParts(line, spans, max_results, False, parts)
            strs = [buf.getvalue() for buf in parts]
            self.assertEqual(expected_parts, strs)

            print('---')


if __name__ == '__main__':
    unittest.main()
