#!/usr/bin/env python2
"""
builtin_funcs.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, scope_e
from _devbuild.gen.syntax_asdl import lhs_expr


def SetGlobalFunc(mem, name, func):
  """Helper for completion."""
  assert callable(func), func
  mem.SetVar(lhs_expr.LhsName(name), value.Obj(func), (), scope_e.GlobalOnly)


def _Join(array, delim=''):
  """
  func join(items Array[Str]) Str ...
  """
  # default is not ' '?
  return delim.join(array)


def _Split(s):
  """
  func split(s Str) Array[Str] { ... }
  """
  # TODO: self.splitter for ifs
  return s.split()


def Init(mem):
  SetGlobalFunc(mem, 'len', len)
  SetGlobalFunc(mem, 'join', _Join)
  SetGlobalFunc(mem, 'split', _Split)

