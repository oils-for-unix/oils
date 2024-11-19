#!/usr/bin/env python2
"""target_lang_test.py: test out MyPy-compatible code we generated

Similar to mycpp/demo/target_lang.cc
"""

import collections
import unittest

from typing import List


class word_t(object):
    pass

#class CompoundWord('List[int]'):
#class CompoundWord(word_t, 'List[int]'):

#class CompoundWord(List[int]):
class CompoundWord(word_t, List[int]):
    pass


class TargetLangTest(unittest.TestCase):

    def testFoo(self):
        # type: () -> None

        print(dir(collections))

        # Wow this works
        c = CompoundWord()

        c.append(42)
        print(c)

        pass


if __name__ == '__main__':
    unittest.main()
