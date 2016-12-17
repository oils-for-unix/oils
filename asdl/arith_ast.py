#!/usr/bin/env python3
"""
arith_ast.py
"""

import os
import sys

from asdl import asdl_parse
from asdl import py_meta

this_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
schema_path = os.path.join(this_dir, 'arith.asdl')

module = asdl_parse.parse(schema_path)
root = sys.modules[__name__]
py_meta.MakeTypes(module, root)
