#!/usr/bin/env python3
"""
mypy_shim.py

Convert stdlib ast nodes into MyPy nodes
"""

from mypy.nodes import MypyFile


def CreateMyPyFile(path: str) -> MypyFile:
    stub = MypyFile([], [])
    # fullname is a property, backed by _fullname
    stub._fullname = path
    return stub
