"""
util.py
"""
from __future__ import print_function

import sys

from typing import Any, Sequence

# Used by cppgen_pass and const_pass

# mycpp/examples/small_str.py sorta works with this!
#SMALL_STR = True

SMALL_STR = False

SymbolPath = Sequence[str]


def log(msg: str, *args: Any) -> None:
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)

def join_name(parts: SymbolPath, strip_package: bool = False, delim: str = '::') -> str:
    """
    Join the given name path into a string with the given delimiter.
    Use strip_package to remove the top-level directory (e.g. `core`, `ysh`)
    when dealing with C++ namespaces.
    """
    if not strip_package:
        return delim.join(parts)

    if len(parts) > 1:
        return delim.join(('',) + parts[1:])

    return parts[0]

def split_py_name(name: str) -> SymbolPath:
    ret = tuple(name.split('.'))
    if len(ret) and ret[0] == 'mycpp':
        # Drop the prefix 'mycpp.' if present. This makes names compatible with
        # the examples that use testpkg.
        return ret[1:]

    return ret
