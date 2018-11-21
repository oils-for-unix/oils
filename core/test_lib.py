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

from asdl import runtime
from core import alloc
from core import dev
from core import process
from core import util
from core.meta import Id
from frontend import lexer
from frontend import match
from frontend import parse_lib
from frontend import reader
from osh import cmd_exec
from osh import split
from osh import state
from osh import word_eval


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

  if isinstance(left, runtime.CompoundObj):
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


def InitLexer(s, arena):
  """For tests only."""
  match_func = match.MATCHER
  line_lexer = lexer.LineLexer(match_func, '', arena)
  line_reader = reader.StringLineReader(s, arena)
  lx = lexer.Lexer(line_lexer, line_reader)
  return line_reader, lx


def MakeTestEvaluator():
  arena = alloc.SideArena('<MakeTestEvaluator>')
  mem = state.Mem('', [], {}, arena)
  exec_opts = state.ExecOpts(mem, None)
  splitter = split.SplitContext(mem)
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


def InitCommandParser(code_str, arena=None):
  arena = arena or MakeArena('<cmd_exec_test.py>')
  parse_ctx = parse_lib.ParseContext(arena, {})
  line_reader, _ = InitLexer(code_str, arena)
  w_parser, c_parser = parse_ctx.MakeOshParser(line_reader)
  return arena, c_parser


def InitOilParser(code_str, arena=None):
  # NOTE: aliases don't exist in the Oil parser?
  arena = arena or MakeArena('<cmd_exec_test.py>')
  parse_ctx = parse_lib.ParseContext(arena, {})
  line_reader, _ = InitLexer(code_str, arena)
  c_parser = parse_ctx.MakeOilParser(line_reader)
  return arena, c_parser
