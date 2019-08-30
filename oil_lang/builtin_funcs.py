#!/usr/bin/env python2
"""
builtin_funcs.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, scope_e
from _devbuild.gen.syntax_asdl import lhs_expr


def SetGlobalFunc(mem, name, func):
  """Used by bin/oil.py to set split(), etc."""
  assert callable(func), func
  mem.SetVar(lhs_expr.LhsName(name), value.Obj(func), (), scope_e.GlobalOnly)


def _Join(array, delim=''):
  """
  func join(items Array[Str]) Str ...
  """
  # default is not ' '?
  return delim.join(array)


def Init(mem):
  """Populate the top level namespace with some builtin functions."""

  SetGlobalFunc(mem, 'len', len)
  SetGlobalFunc(mem, 'max', max)
  SetGlobalFunc(mem, 'min', min)

  SetGlobalFunc(mem, 'abs', abs)

  SetGlobalFunc(mem, 'any', any)
  SetGlobalFunc(mem, 'all', all)

  # Return an iterable like Python 3.
  SetGlobalFunc(mem, 'range', xrange)

  SetGlobalFunc(mem, 'join', _Join)

  # NOTE: split() is set in main(), since it depends on the Splitter() object /
  # $IFS.

