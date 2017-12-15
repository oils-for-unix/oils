#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
test_lib.py - Functions for testing.
"""

from core import alloc


def TokensEqual(left, right):
  # Ignoring location in CompoundObj.__eq__ now, but we might want this later.
  return left.id == right.id and left.val == right.val
  #return left == right


def TokenWordsEqual(left, right):
  # Ignoring location in CompoundObj.__eq__ now, but we might want this later.
  return TokensEqual(left.token, right.token)
  #return left == right


def AsdlEqual(left, right):
  """Check if generated ASDL instances are equal.

  We don't use equality in the actual code, so this is relegated to test_lib.
  """
  if isinstance(left, (int, str, bool)):
    return left == right

  if isinstance(left, list):
    if len(left) != len(right):
      return False
    for a, b in zip(left, right):
      if not AsdlEqual(a, b):
        return False
    return True

  if isinstance(other, asdl.CompoundObj):
    if left.tag != right.tag:
      return False

    for name in left.FIELDS:
      # Special case: we are not testing locations right now.
      #if name == 'span_id':
      #  continue
      a = getattr(left, name)
      b = getattr(right, name)
      if not AsdlEqual(left, right):
        return False

    return True

  raise AssertionError


def AssertAsdlEqual(test, left, right):
  test.assertTrue(left, right)


def MakeArena(source_name):
  pool = alloc.Pool()
  arena = pool.NewArena()
  arena.PushSource('<lex_test.py>')
  return arena
