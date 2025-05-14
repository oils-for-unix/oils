"""
bin/hello.py
"""
from __future__ import print_function

from typing import List


def main(argv):
    # type: (List[str]) -> int
    print('hi')
    if len(argv):
        return 1
    else:
        return 0
