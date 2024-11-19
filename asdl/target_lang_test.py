#!/usr/bin/env python2
"""target_lang_test.py: test out MyPy-compatible code we generated

Similar to mycpp/demo/target_lang.cc
"""

#import collections
#import unittest

from typing import List


class word_t(object):
    pass

#class CompoundWord('List[int]'):
#class CompoundWord(word_t, 'List[int]'):

#class CompoundWord(List[int]):
class CompoundWord(word_t, List[int]):
    pass


def main():
    # type: () -> None

    #print(dir(collections))

    # Wow this works
    c = CompoundWord()

    c.append(42)
    print(c)
    print('len %d' % len(c))


if __name__ == '__main__':
    main()
