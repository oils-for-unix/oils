#!/usr/bin/env python
"""
osh/ast_.py -- Parse osh.asdl and dynamically create classes on this module.
"""

from asdl import asdl_ as asdl


def LoadSchema(Id, f):
  """Parse an ASDL schema.  Used for code gen and metaprogramming."""
  app_types = {'id': asdl.UserType(Id)}

  asdl_module = asdl.parse(f)

  if not asdl.check(asdl_module, app_types):
    raise AssertionError('ASDL file is invalid')

  type_lookup = asdl.ResolveTypes(asdl_module, app_types)
  return asdl_module, type_lookup
