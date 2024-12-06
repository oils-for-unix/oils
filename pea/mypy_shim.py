#!/usr/bin/env python3
"""
mypy_shim.py

Convert stdlib ast nodes into MyPy nodes
"""

import os

from mypy.nodes import MypyFile


def CreateMyPyFile(path: str) -> MypyFile:
    stub = MypyFile([], [])
    # fullname is a property, backed by _fullname
    #
    # mycpp/examples/pea_hello.py -> mycpp

    name = os.path.basename(path)
    mod_name, _ = os.path.splitext(name)

    stub._fullname = mod_name
    return stub
