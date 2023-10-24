"""
util.py
"""
from __future__ import print_function

import sys

from typing import Any

# Used by cppgen_pass and const_pass

# mycpp/examples/small_str.py sorta works with this!
SMALL_STR = True

#SMALL_STR = False


def log(msg: str, *args: Any) -> None:
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)
