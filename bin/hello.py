"""
bin/hello.py
"""
from __future__ import print_function

from typing import List


def main(argv):
    # type: (List[str]) -> int

    #print('hi')
    if len(argv) == 1:
        return 0  # no args, success
    else:
        return 42
