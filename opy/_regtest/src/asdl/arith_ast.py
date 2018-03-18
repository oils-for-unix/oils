#!/usr/bin/env python
"""
arith_ast.py
"""

import os
import sys

from asdl import asdl_ as asdl
from asdl import py_meta

this_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
schema_path = os.path.join(this_dir, 'arith.asdl')

with open(schema_path) as f:
  module = asdl.parse(f)
type_lookup = asdl.ResolveTypes(module)
root = sys.modules[__name__]
py_meta.MakeTypes(module, root, type_lookup)
