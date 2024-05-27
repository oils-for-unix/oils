"""
util.py
"""
from __future__ import print_function

import sys

from typing import Any

# Used by cppgen_pass and const_pass

# mycpp/examples/small_str.py sorta works with this!
#SMALL_STR = True

SMALL_STR = False


def log(msg: str, *args: Any) -> None:
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)

def join_name_cpp(parts: tuple[str], strip_package:bool=False) -> str:
    if not strip_package:
        return '::'.join(parts)

    if len(parts) > 1:
        return '::'.join(('',) + parts[1:])

    return parts[0]

def split_py_name(name: str) -> tuple[str]:
    ret = tuple(name.split('.'))
    if len(ret) and ret[0] == 'mycpp':
        # Drop the prefix 'mycpp.' if present. This makes names compatible with
        # the examples that use testpkg.
        return ret[1:]

    return ret
