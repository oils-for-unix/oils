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

import string
import sys

from asdl import py_meta

from core import alloc
from core import cmd_exec
from core import dev
from core import legacy
from core import process
from core import state
from core import word_eval
from core import util

from osh import parse_lib
from osh.meta import Id


def PrintableString(s):
  """For pretty-printing in tests."""
  if all(c in string.printable for c in s):
    return s
  return repr(s)


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
  if isinstance(left, (int, str, bool, Id)):  # little hack for Id
    return left == right

  if isinstance(left, list):
    if len(left) != len(right):
      return False
    for a, b in zip(left, right):
      if not AsdlEqual(a, b):
        return False
    return True

  if isinstance(left, py_meta.CompoundObj):
    if left.tag != right.tag:
      return False

    for name in left.ASDL_TYPE.GetFieldNames():
      # Special case: we are not testing locations right now.
      if name == 'span_id':
        continue
      a = getattr(left, name)
      b = getattr(right, name)
      if not AsdlEqual(a, b):
        return False

    return True

  raise AssertionError(left)


def AssertAsdlEqual(test, left, right):
  test.assertTrue(AsdlEqual(left, right), 'Expected %s, got %s' % (left, right))


def MakeArena(source_name):
  pool = alloc.Pool()
  arena = pool.NewArena()
  arena.PushSource(source_name)
  return arena


def MakeTestEvaluator():
  arena = alloc.SideArena('<MakeTestEvaluator>')
  mem = state.Mem('', [], {}, arena)
  exec_opts = state.ExecOpts(mem, None)
  splitter = legacy.SplitContext(mem)
  ev = word_eval.CompletionWordEvaluator(mem, exec_opts, splitter, arena)
  return ev


def InitExecutor(arena=None):
  arena = arena or MakeArena('<InitExecutor>')

  mem = state.Mem('', [], {}, arena)
  fd_state = process.FdState()
  funcs = {}
  comp_funcs = {}
  # For the tests, we do not use 'readline'.
  exec_opts = state.ExecOpts(mem, None)
  parse_ctx = parse_lib.ParseContext(arena, {})

  debug_f = util.DebugFile(sys.stderr)
  devtools = dev.DevTools(dev.CrashDumper(''), debug_f, debug_f)

  return cmd_exec.Executor(mem, fd_state, funcs, comp_funcs, exec_opts,
                           parse_ctx, devtools)
