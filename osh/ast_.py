#!/usr/bin/env python3
"""
osh/ast.py

We parse osh.asdl and dynamically create classes on this module.
"""

import os
import sys

from asdl import py_meta
from asdl import asdl_parse

from core.id_kind import Id

bin_dir = os.path.dirname(os.path.abspath(sys.argv[0]))  # ~/git/oil/bin
schema_path = os.path.join(bin_dir, '../osh/osh.asdl')  # ~/git/oil/osh

# TODO: A better syntax for this might be:
# id = external   # in osh.asdl.  provided by the application.
app_types = {'id': Id}

module = asdl_parse.parse(schema_path)
# Check for type errors
if not asdl_parse.check(module, app_types):
  raise AssertionError('ASDL file is invalid')

root = sys.modules[__name__]
py_meta.MakeTypes(module, root, app_types)
