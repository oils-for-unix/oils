#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
"""
util.py -- Common infrastructure.

In some cases, we're using C++ idioms in Python, so the code translates more
easily to C++.
"""

# Mutate the class after defining it:
#
# http://stackoverflow.com/questions/3467526/attaching-a-decorator-to-all-functions-within-a-class

# Other more complicated ways:
#
# http://code.activestate.com/recipes/366254-generic-proxy-object-with-beforeafter-method-hooks/
#
# http://stackoverflow.com/questions/3467526/attaching-a-decorator-to-all-functions-within-a-class

import inspect
import sys
import types


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


class _EnumValue(object):
  """A unique name."""
  def __init__(self, namespace, name, value):
    self.namespace = namespace
    self.name = name
    self.value = value

  def __repr__(self):
    return '<%s.%s %s>' % (self.namespace, self.name, self.value)

  def __hash__(self):
    # Needed for the LEXER_DEF dictionary
    return hash(self.name)

  def __eq__(self, other):
    if isinstance(other, int):
      return self.value == other
    elif isinstance(other, _EnumValue):
      return self is other
    else:
      raise ValueError('%r is not comparable with %r' % (self, other))


class Enum(object):
  def __init__(self, enum_name, spec):
    self._values = []
    self._lookup = {}

    counter = 0
    for item in spec:
      if isinstance(item, tuple):
        name, i = item
        v = _EnumValue(enum_name, name, i)
        counter = i + 1
      else:
        name = item
        v = _EnumValue(enum_name, name, counter)
        counter += 1
      self._values.append(v)
      self._lookup[name] = v

  def __getattr__(self, name):
    """Get a value by name, e.g. Color.red."""
    val = self._lookup.get(name)
    if val is None:
      raise AttributeError(name)
    return val


def TracedFunc(func, cls_name, state):
  def traced(*args, **kwargs):
    name_str = '%s.%s' % (cls_name, func.__name__)
    print(state.indent + '>', name_str)  #, args[1:] #, kwargs
    state.Push()
    ret = func(*args, **kwargs)
    state.Pop()
    print(state.indent + '<', name_str, ret)
    return ret
  return traced


def WrapMethods(cls, state):
  for name, func in inspect.getmembers(cls):
    # NOTE: This doesn't work in python 3?  Types module is different
    if isinstance(func, types.UnboundMethodType):
      setattr(cls, name, TracedFunc(func, cls.__name__, state))


class TraceState(object):

  def __init__(self):
    self.indent = ''
    self.num_spaces = 4

  def Push(self):
    self.indent += self.num_spaces * ' '

  def Pop(self):
    self.indent = self.indent[:-self.num_spaces]
