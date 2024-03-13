#!/usr/bin/env python3
from __future__ import print_function

import re
import sys


def ReplaceFunc(m):
    return '[' + m.group(1) + ']'


def ReplaceFuncDict(m):
    return {'key': '[' + m.group(1) + ']'}


def main(argv):
    pat = re.compile(r'(\d+)')

    #s = pat.sub(ReplaceFunc, 'foo 123 bar 456', ReplaceFunc)

    s = pat.sub(ReplaceFunc, 'foo 123 bar 456')
    print(s)

    d = pat.sub(ReplaceFuncDict, 'foo 123 bar 456')
    print(d)


main(sys.argv)
