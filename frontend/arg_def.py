#!/usr/bin/env python2
"""
arg_def.py -- Flag and arg defs for builtins.
"""
from __future__ import print_function

import sys

from frontend import args

# Similar to frontend/{option,builtin}_def.py
_ARG_DEF = {}


def FlagSpec(builtin_name, typed=False):
  # type: (str, bool) -> args.FlagSpec
  """
  """
  arg_spec = args.FlagSpec(typed=typed)
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


def Parse(spec_name, arg_r):
  # type: (str, args.Reader) -> args._Attributes
  """Parse argv using a given FlagSpec / FlagSpecAndMore."""
  spec = _ARG_DEF[spec_name]
  return spec.Parse(arg_r)


def All():
  return _ARG_DEF


# TODO:
# spec = FlagSpec(builtin_i.export)
#
# And then later:
# 
# attrs = args.Parse(builtin_i.export, arg_r)
# arg = arg_types.export(attrs)
#
# Does this mean that builtins should take:
# Run(attrs, arg_r) ?
# I think that makes more sense...
# Yeah _Builtin should define Run(cmd_val) to parse it and call
# _Run(attrs, arg_reader)
#   

# It will look up the spec dynamically and then call Parse() on it I think.

EXPORT_SPEC = FlagSpec('export', typed=True)
EXPORT_SPEC.ShortFlag('-n')
EXPORT_SPEC.ShortFlag('-f')  # stubbed
EXPORT_SPEC.ShortFlag('-p')


READONLY_SPEC = FlagSpec('readonly', typed=True)

# TODO: Check the consistency of -a and -A against values, here and below.
READONLY_SPEC.ShortFlag('-a')
READONLY_SPEC.ShortFlag('-A')
READONLY_SPEC.ShortFlag('-p')


NEW_VAR_SPEC = FlagSpec('new_var', typed=True)

# print stuff
NEW_VAR_SPEC.ShortFlag('-f')
NEW_VAR_SPEC.ShortFlag('-F')
NEW_VAR_SPEC.ShortFlag('-p')

NEW_VAR_SPEC.ShortFlag('-g')  # Look up in global scope

# Options +r +x +n
NEW_VAR_SPEC.ShortOption('x')  # export
NEW_VAR_SPEC.ShortOption('r')  # readonly
NEW_VAR_SPEC.ShortOption('n')  # named ref

# Common between readonly/declare
NEW_VAR_SPEC.ShortFlag('-a')
NEW_VAR_SPEC.ShortFlag('-A')


UNSET_SPEC = FlagSpec('unset', typed=True)
UNSET_SPEC.ShortFlag('-v')
UNSET_SPEC.ShortFlag('-f')
