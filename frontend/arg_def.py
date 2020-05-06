#!/usr/bin/env python2
"""
arg_def.py
"""
from __future__ import print_function

import sys

from frontend import args

# Similar to frontend/{option,builtin}_def.py
_ARG_DEF = {}


def FlagSpec(builtin_name):
  # type: (str) -> args.FlagSpec
  """
  """
  arg_spec = args.FlagSpec()
  _ARG_DEF[builtin_name] = arg_spec
  return arg_spec


def FlagSpecAndMore(name):
  # type: (str) -> args.FlagSpecAndMore
  """
  For set, bin/oil.py ("main"), compgen -A, complete -A, etc.
  """
  arg_spec = args.FlagSpecAndMore()
  _ARG_DEF[name] = arg_spec
  return arg_spec


def All():
  return _ARG_DEF
