#!/usr/bin/env python2
"""
objects.py

Python types under value.Obj.  See the invariant in osh/runtime.asdl.
"""
from __future__ import print_function

# These are for data frames?

class BoolArray(list):
  """
  var b = @[true false false]
  var b = @[T F F]
  """
  pass

class IntArray(list):
  """
  var b = @[1 2 3 -42]
  """
  pass


class FloatArray(list):
  """
  var b = @[1.1 2.2 3.9]
  """
  pass


class StrArray(list):
  """
  local oldarray=(a b c)  # only strings, but deprecated

  var array = @(a b c)  # only strings, PARSED like shell
  var oilarray = @[a b c]  # can be integers

  TODO: value.MaybeStrArray should be renamed LooseArray?
    Because it can have holes!
    StrNoneArray?  MaybeMaybeStrArray?

  In C, do both of them have the same physical representation?
  """
  pass


class Function(object):
  """An Oil function or a wrapped shell function.

  Put under value.Obj()

  objects.Function
  """
  def __init__(self, node, ex):
    self.node = node
    self.ex = ex

  def __call__(self, *args, **kwargs):
    return self.ex.RunOilFunc(self.node, args, kwargs)


class Module(object):
  """An Oil module.

  The 'use' keyword creates an object of this type in the current namespace.

  It holds both variables and functions.

  But it doesn't have "$@" or anything else that Mem has?
  Mem also has introspection.  For function calls and such.
  Maybe that only applies to 'proc' and not 'func'.
  """
  def __init__(self, name):
    self.name = name
    self.docstring = ''
    # items
    self.attrs = {}
