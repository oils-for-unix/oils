#!/usr/bin/python
"""
core/runtime.py -- Parse runtime.asdl and dynamically create classes on this module.

Similar to osh/ast_.py.
"""

import sys

from asdl import py_meta
from asdl import asdl_ as asdl
from core import util


def _ParseAndMakeTypes(f, root):
  module = asdl.parse(f)

  app_types = {}

  # Check for type errors
  if not asdl.check(module, app_types):
    raise AssertionError('ASDL file is invalid')
  py_meta.MakeTypes(module, root, app_types)


f = util.GetResourceLoader().open('core/runtime.asdl')
root = sys.modules[__name__]
_ParseAndMakeTypes(f, root)
