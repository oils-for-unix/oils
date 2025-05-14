"""
bin/hello_mylib.py
"""
from __future__ import print_function

from typing import List

from mycpp.mylib import print_stderr


def main(argv):
    # type: (List[str]) -> int
    print('hi')
    print_stderr('stderr')
    if len(argv):
        return 1
    else:
        return 0
