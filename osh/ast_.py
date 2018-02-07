#!/usr/bin/env python
"""
osh/ast_.py -- Parse osh.asdl and dynamically create classes on this module.
"""

import sys

from asdl import asdl_ as asdl
from asdl import py_meta

from core import util
from osh.meta import Id


def LoadSchema(f):
  app_types = {'id': asdl.UserType(Id)}

  asdl_module = asdl.parse(f)

  if not asdl.check(asdl_module, app_types):
    raise AssertionError('ASDL file is invalid')

  type_lookup = asdl.ResolveTypes(asdl_module, app_types)
  return asdl_module, type_lookup


f = util.GetResourceLoader().open('osh/osh.asdl')
asdl_module, type_lookup = LoadSchema(f)

root = sys.modules[__name__]
if 0:
  py_meta.MakeTypes(asdl_module, root, type_lookup)
else:
  # Exported for the generated code to use
  TYPE_LOOKUP = type_lookup

  # Get the types from elsewhere
  from _devbuild.gen import osh_asdl
  py_meta.AssignTypes(osh_asdl, root)

f.close()
