#!/usr/bin/env python3
"""
osh/ast.py

We parse osh.asdl and dynamically create classes on this module.
"""

import os
import sys

from asdl import py_meta
from asdl import asdl_parse

bin_dir = os.path.dirname(os.path.abspath(sys.argv[0]))  # ~/git/oil/bin
schema_path = os.path.join(bin_dir, '../osh/osh.asdl')  # ~/git/oil/osh

module = asdl_parse.parse(schema_path)
root = sys.modules[__name__]
py_meta.MakeTypes(module, root)
