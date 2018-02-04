#!/usr/bin/env python
"""
core/runtime.py 

Parse runtime.asdl and dynamically create classes on this module.  Similar to
osh/ast_.py.
"""

import sys

from asdl import py_meta
from asdl import asdl_ as asdl
from core import util
from core.id_kind import Id


def _LoadSchema(f):
  module = asdl.parse(f)

  app_types = {'id': asdl.UserType(Id)}
  type_lookup = asdl.ResolveTypes(module, app_types)

  # Check for type errors
  if not asdl.check(module, app_types):
    raise AssertionError('ASDL file is invalid')
  return module, type_lookup


f = util.GetResourceLoader().open('core/runtime.asdl')
root = sys.modules[__name__]
module, type_lookup = _LoadSchema(f)

if 0:
  py_meta.MakeTypes(module, root, type_lookup)
else:
  # Exported for the generated code to use
  TYPE_LOOKUP = type_lookup

  # Get the types from elsewhere
  from _devbuild.gen import runtime_asdl
  py_meta.AssignTypes(runtime_asdl, root)

f.close()
