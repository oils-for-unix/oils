"""
Wrapper for Python.asdl.
"""

import os
import sys

from asdl import py_meta
from asdl import asdl_ as asdl

# Dummy types for now
class Identifier:
  pass

class Bytes:
  pass

class PyObject:
  pass

class Constant:
  pass

class Singleton:
  pass


  # TODO: Fill these in:
  #
  # Num(object n) -- a number as a PyObject.
  # Bytes(bytes s)
  # Constant(constant value)
  # NameConstant(singleton value)
  #
  # singleton: None, True or False
  # constant can be None, whereas None means "no value" for object.
  #
  # Hm do I want an LST?  Then it shouldn't have these typed values?  That
  # comes later?
  #
  # identifier: this one is used a lot.  Why not string?

def _ParseAndMakeTypes(schema_path, root):
  module = asdl.parse(schema_path)

  app_types = {
      'identifier': asdl.UserType(Identifier),
      'bytes': asdl.UserType(Bytes),
      'object': asdl.UserType(PyObject),
      'constant': asdl.UserType(Constant),
      'singleton': asdl.UserType(Singleton),
  }

  # Check for type errors
  if not asdl.check(module, app_types):
    raise AssertionError('ASDL file is invalid')
  py_meta.MakeTypes(module, root, app_types)


bin_dir = os.path.dirname(os.path.abspath(sys.argv[0]))  # ~/git/oil/bin
schema_path = os.path.join(bin_dir, '../foil/Python.asdl')  # ~/git/oil/osh

root = sys.modules[__name__]

_ParseAndMakeTypes(schema_path, root)
