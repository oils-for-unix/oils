#!/usr/bin/env python2
"""target_lang_test.py: test out MyPy-compatible code we generated

Similar to mycpp/demo/target_lang.cc
"""

from typing import List, Dict


class word_t(object):
    pass

#class CompoundWord('List[int]'):
#class CompoundWord(word_t, 'List[int]'):

#class CompoundWord(List[int]):
class CompoundWord(word_t, List[int]):
    pass

class value_t(object):
    pass

class Dict_(value_t, Dict[str, value_t]):
    pass

class List_(value_t, List[value_t]):
    pass


def main():
    # type: () -> None

    #print(dir(collections))

    # Wow this works
    c = CompoundWord()

    c.append(42)
    print(c)
    print('len %d' % len(c))

    d = Dict_()

    d['key'] = d
    print(d)
    print(len(d))

    mylist = List_()
    print(mylist)
    print(len(mylist))


if __name__ == '__main__':
    main()
