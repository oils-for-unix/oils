#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
"""
util.py -- Common infrastructure.

In some cases, we're using C++ idioms in Python, so the code translates more
easily to C++.
"""

import cStringIO
import os
import pwd
import sys

if not os.getenv('_OVM_DEPS'):
  import inspect
  import types

from asdl import const

Buffer = cStringIO.StringIO  # used by asdl/format.py


class _ErrorWithLocation(Exception):
  """A parse error that can be formatted.

  Formatting is in ui.PrintError.
  """
  def __init__(self, msg, *args, **kwargs):
    Exception.__init__(self)
    self.msg = msg
    self.args = args
    # NOTE: We use a kwargs dict because Python 2 doesn't have keyword-only
    # args.
    self.span_id = kwargs.pop('span_id', const.NO_INTEGER)
    self.token = kwargs.pop('token', None)
    self.part = kwargs.pop('part', None)
    self.word = kwargs.pop('word', None)
    self.exit_status = kwargs.pop('status', None)
    if kwargs:
      raise AssertionError('Invalid keyword args %s' % kwargs)

  def __repr__(self):
    return '<%s %s %r %r %s>' % (
        self.msg, self.args, self.token, self.word, self.exit_status)

  def __str__(self):
    # The default doesn't work very well?
    return repr(self)

  def UserErrorString(self):
    return self.msg % self.args


class ParseError(_ErrorWithLocation):
  """Used in the parsers.

  TODO:
  - This could just be FatalError?
  - You might want to catch this and add multiple locations?
    try:
      foo
    except ParseError as e:
      e.AddErrorInfo('hi', token=t)
      raise
  """
  pass


class FatalRuntimeError(_ErrorWithLocation):
  """Used in the evaluators.

  Also used in test builtin for invalid argument.
  """
  pass


class ErrExitFailure(FatalRuntimeError):
  """For set -e.
  
  Travels between WordEvaluator and Executor.
  """
  pass


def p_die(msg, *args, **kwargs):
  """Convenience wrapper for parse errors."""
  raise ParseError(msg, *args, **kwargs)


def e_die(msg, *args, **kwargs):
  """Convenience wrapper for runtime errors."""
  raise FatalRuntimeError(msg, *args, **kwargs)


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def warn(msg, *args):
  if args:
    msg = msg % args
  print('osh warning: ' + msg, file=sys.stderr)


def error(msg, *args):
  if args:
    msg = msg % args
  print('osh error: ' + msg, file=sys.stderr)


def usage(msg, *args):
  if args:
    msg = msg % args
  print('usage error: ' + msg, file=sys.stderr)


def GetHomeDir():
  """Get the user's home directory from the /etc/passwd.

  Used by tilde expansion in word_eval.py and readline initialization in
  completion.py.
  """
  uid = os.getuid()
  try:
    e = pwd.getpwuid(uid)
  except KeyError:
    return None
  else:
    return e.pw_dir


class _EnumValue(object):
  """A unique name."""
  def __init__(self, namespace, name, value):
    self.namespace = namespace
    self.name = name
    self.value = value

  def __repr__(self):
    return '<%s.%s %s>' % (self.namespace, self.name, self.value)

  # I think this is not needed?
  def __hash__(self):
    # Needed for the LEXER_DEF dictionary
    return hash(self.name)

  # Why is this needed?  For ASDL serialization?  But we're not using it like
  # that.
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


# Mutate the class after defining it:
#
# http://stackoverflow.com/questions/3467526/attaching-a-decorator-to-all-functions-within-a-class

# Other more complicated ways:
#
# http://code.activestate.com/recipes/366254-generic-proxy-object-with-beforeafter-method-hooks/
# http://stackoverflow.com/questions/3467526/attaching-a-decorator-to-all-functions-within-a-class


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


class _FileResourceLoader:
  """Open resources relative to argv[0]."""

  def __init__(self, argv0):
    bin_dir = os.path.dirname(os.path.abspath(argv0))  # ~/git/oil/bin
    self.root_dir = os.path.join(bin_dir, '..')  # ~/git/oil/osh

  # TODO: Make this a context manager?
  def open(self, rel_path):
    return open(os.path.join(self.root_dir, rel_path))


import zipimport  # NOT the zipfile module.

class _ZipResourceLoader:
  """Open resources INSIDE argv[0] as a zip file."""

  def __init__(self, argv0):
    self.z = zipimport.zipimporter(argv0)

  def open(self, rel_path):
    contents = self.z.get_data(rel_path)
    return cStringIO.StringIO(contents)


_loader = None

def GetResourceLoader():
  global _loader
  if _loader:
    return _loader

  # Ovm_Main in main.c sets this.
  if os.getenv('_OVM_IS_BUNDLE') == '1':
    ovm_path = os.getenv('_OVM_PATH')
    #log('! OVM_PATH = %s', ovm_path)
    _loader = _ZipResourceLoader(ovm_path)
  else:
    _loader = _FileResourceLoader(sys.argv[0])

  return _loader
