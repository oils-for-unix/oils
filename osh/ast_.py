#!/usr/bin/env python3
"""
osh/ast_.py -- Parse osh.asdl and dynamically create classes on this module.
"""

import json
import re
import os
import sys

from asdl import py_meta
from asdl import asdl_ as asdl

from core.id_kind import Id

# This is word characters, - and _, as well as path name characters . and /.
_PLAIN_RE = re.compile(r'^[a-zA-Z0-9\-_./]+$')

def EncodeTokenVal(s):
  if '\n' in s:
    return json.dumps(s)  # account for the fact that $ matches the newline
  if _PLAIN_RE.match(s):
    return s
  else:
    return json.dumps(s)


def PrintAst(node, out_f, do_abbrev=False):
  """
  """
  pass


def _ParseAndMakeTypes(schema_path, root):
  # TODO: A better syntax for this might be:
  # id = external in osh.asdl.  provided by the application.
  app_types = {'id': asdl.UserType(Id)}

  module = asdl.parse(schema_path)

  # Check for type errors
  if not asdl.check(module, app_types):
    raise AssertionError('ASDL file is invalid')
  py_meta.MakeTypes(module, root, app_types)


bin_dir = os.path.dirname(os.path.abspath(sys.argv[0]))  # ~/git/oil/bin
schema_path = os.path.join(bin_dir, '../osh/osh.asdl')  # ~/git/oil/osh

root = sys.modules[__name__]

_ParseAndMakeTypes(schema_path, root)
