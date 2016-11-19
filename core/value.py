#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
"""
value.py - Representation of runtime values.
"""

__all__ = ['TValue', 'Value']


class TValue(object):
  STRING = 0
  ARRAY = 1
  EMPTY_UNQUOTED = 2


class Value(object):
  """
  Words evaluate to Value.  Almost all words evaluate to strings, but
  """
  def __init__(self):
    self.type = TValue.STRING  # default value is empty string
    self.s = ''  
    self.a = []

  def __repr__(self):
    if self.type == TValue.STRING:
      return '<Value String %r>' % self.s
    elif self.type == TValue.ARRAY:
      return '<Value Array %r>' % self.a
    elif self.type == TValue.EMPTY_UNQUOTED:
      return '<Value EmptyUnquoted>' % self.a
    else:
      raise AssertionError

  @staticmethod
  def FromString(s):
    assert isinstance(s, str), s
    v = Value()
    v.s = s
    return v

  @staticmethod
  def FromArray(a):
    v = Value()
    v.type = TValue.ARRAY
    v.a = a
    return v

  @staticmethod
  def EmptyUnquoted():
    v = Value()
    v.type = TValue.EMPTY_UNQUOTED
    return v

  def IsEmptyString(self):
    """Return whether the value is an empty string.

    Not sure I want this EMPTY_UNQUOTED.  Maybe I need a flag on raw strings:
    "elide if whole word" and probably "do glob".
    """
    if self.type == TValue.EMPTY_UNQUOTED:
      return True
    if self.type == TValue.STRING:
      return self.s == ''
    return False

  def AsString(self):
    """Return the value as a string, or false.

    Returns:
      is_string: bool
      s: string (or None)
    """
    if self.type == TValue.STRING:
      assert isinstance(self.s, str), self.s
      return True, self.s
    else:
      return False, None

  def AsArray(self):
    """Return the value as an array, or false.

    Returns:
      is_array: bool
      a: array (or None)
    """
    if self.type == TValue.ARRAY:
      assert isinstance(self.a, list), self.a
      return True, self.a
    else:
      return False, None

  def IsArray(self):
    """Used when indexing like a[@] or a[*]."""
    return self.type == TValue.ARRAY

  def EvalToFirst(self):
    """Implement bash semantics, where $a evaluates to $a[0]."""
    if self.type == TValue.ARRAY:
      if len(self.a) == 0:
        # empty=() interpolates to no args
        return Value.EmptyUnquoted()
      else:
        return Value.FromString(self.a[0])
    else:  # STRING
      return self

  def AppendTo(self, argv):
    """Append the string value or the list values to an argv array."""
    if self.type == TValue.STRING:
      argv.append(self.s)
    elif self.type == TValue.ARRAY:
      argv.extend(self.a)
    elif self.type == TValue.EMPTY_UNQUOTED:
      pass
    else:
      raise AssertionError
