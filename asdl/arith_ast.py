#!/usr/bin/env python
"""
arith_ast.py
"""

import sys

from asdl import asdl_ as asdl
from asdl import py_meta
from core import util

f = util.GetResourceLoader().open('asdl/arith.asdl')
_asdl_module, _type_lookup = asdl.LoadSchema(f, {})  # no app_types
f.close()

root = sys.modules[__name__]
py_meta.MakeTypes(_asdl_module, root, _type_lookup)
