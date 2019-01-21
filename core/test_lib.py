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
from core import completion
from core import dev
from core import main_loop
from core import process
from core import util
from core.meta import Id, runtime_asdl
from frontend import lexer
from frontend import match
from frontend import parse_lib
from frontend import reader
from osh import builtin
from osh import builtin_comp
from osh import cmd_exec
from osh import expr_eval
from osh import split
from osh import state
from osh import word_eval

builtin_e = runtime_asdl.builtin_e


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
  line_lexer = lexer.LineLexer(match.MATCHER, '', arena)
  line_reader = reader.StringLineReader(s, arena)
  lx = lexer.Lexer(line_lexer, line_reader)
  return line_reader, lx


def MakeTestEvaluator():
  arena = alloc.SideArena('<MakeTestEvaluator>')
  mem = state.Mem('', [], {}, arena)
  exec_opts = state.ExecOpts(mem, None)

  exec_deps = cmd_exec.Deps()
  exec_deps.splitter = split.SplitContext(mem)

  ev = word_eval.CompletionWordEvaluator(mem, exec_opts, exec_deps, arena)
  return ev


def InitExecutor(comp_state=None, arena=None, mem=None):
  arena = arena or MakeArena('<InitExecutor>')

  mem = mem or state.Mem('', [], {}, arena)
  fd_state = process.FdState()
  funcs = {}

  comp_state = comp_state or completion.State()
  readline = None  # simulate not having it
  builtins = {  # Lookup
      builtin_e.HISTORY: builtin.History(readline),

      builtin_e.COMPOPT: builtin_comp.CompOpt(comp_state),
      builtin_e.COMPADJUST: builtin_comp.CompAdjust(mem),
  }

  # For the tests, we do not use 'readline'.
  exec_opts = state.ExecOpts(mem, None)
  parse_ctx = parse_lib.ParseContext(arena, {})

  debug_f = util.DebugFile(sys.stderr)
  exec_deps = cmd_exec.Deps()
  exec_deps.dumper = dev.CrashDumper('')
  exec_deps.debug_f = debug_f
  exec_deps.trace_f = debug_f

  splitter = split.SplitContext(mem)
  exec_deps.splitter = splitter

  word_ev = word_eval.NormalWordEvaluator(mem, exec_opts, exec_deps, arena)
  exec_deps.word_ev = word_ev

  arith_ev = expr_eval.ArithEvaluator(mem, exec_opts, word_ev, arena)
  exec_deps.arith_ev = arith_ev

  bool_ev = expr_eval.BoolEvaluator(mem, exec_opts, word_ev, arena)
  exec_deps.bool_ev = bool_ev

  tracer = cmd_exec.Tracer(parse_ctx, exec_opts, mem, word_ev, debug_f)
  exec_deps.tracer = tracer

  ex = cmd_exec.Executor(mem, fd_state, funcs, builtins, exec_opts,
                         parse_ctx, exec_deps)

  # Add some builtins that depend on the executor!
  complete_builtin = builtin_comp.Complete(ex, comp_state)  # used later
  builtins[builtin_e.COMPLETE] = complete_builtin
  builtins[builtin_e.COMPGEN] = builtin_comp.CompGen(ex, splitter, word_ev)

  return ex


def EvalCode(code_str, comp_state=None, arena=None, mem=None):
  """
  This allows unit tests to write code strings and have functions appear in the
  executor.
  """
  comp_state = comp_state or completion.State()
  arena = arena or MakeArena('<test_lib>')
  mem = mem or state.Mem('', [], {}, arena)

  c_parser = InitCommandParser(code_str, arena=arena)
  ex = InitExecutor(comp_state=comp_state, arena=arena, mem=mem)
  # Parse and execute!
  main_loop.Batch(ex, c_parser, arena)
  return ex


def InitWordParser(code_str, arena=None):
  arena = arena or MakeArena('<test_lib>')
  parse_ctx = parse_lib.ParseContext(arena, {})
  line_reader, _ = InitLexer(code_str, arena)
  c_parser = parse_ctx.MakeOshParser(line_reader)
  # Hack
  return c_parser.w_parser


def InitCommandParser(code_str, arena=None):
  arena = arena or MakeArena('<test_lib>')
  parse_ctx = parse_lib.ParseContext(arena, {})
  line_reader, _ = InitLexer(code_str, arena)
  c_parser = parse_ctx.MakeOshParser(line_reader)
  return c_parser


def InitOilParser(code_str, arena=None):
  # NOTE: aliases don't exist in the Oil parser?
  arena = arena or MakeArena('<cmd_exec_test.py>')
  parse_ctx = parse_lib.ParseContext(arena, {})
  line_reader, _ = InitLexer(code_str, arena)
  c_parser = parse_ctx.MakeOilParser(line_reader)
  return arena, c_parser
