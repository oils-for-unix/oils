#!/usr/bin/env python2
"""
arg_def.py
"""
from __future__ import print_function

import sys

from frontend import args

# Similar to frontend/{option,builtin}_def.py
_ARG_DEF = {}


def Register(builtin_name):
  # type: (str) -> args.BuiltinFlags
  """
  """
  arg_spec = args.BuiltinFlags()
  _ARG_DEF[builtin_name] = arg_spec
  return arg_spec


def All():
  return _ARG_DEF
