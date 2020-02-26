#!/usr/bin/env python2
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

from _devbuild.gen.option_asdl import builtin_i, option_i
from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import source, Token
from asdl import pybase
from asdl import runtime
from core import alloc
from core import completion
from core import dev
from core import main_loop
from core import meta
from core import optview
from core import process
from core import pyutil
from core import ui
from core import util
from core import vm
from frontend import lexer
from frontend import parse_lib
from frontend import reader
from osh import builtin_assign
from osh import builtin_comp
from osh import builtin_misc
from osh import builtin_pure
from osh import cmd_exec
from osh import prompt
from osh import sh_expr_eval
from osh import split
from core import state
from osh import word_eval
from oil_lang import expr_eval


def MakeBuiltinArgv(argv):
  return cmd_value.Argv(argv, [0] * len(argv))


def Tok(id_, val):
  return Token(id_, runtime.NO_SPID, val)


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
  if left is None and right is None:
    return True

  if isinstance(left, (int, str, bool, pybase.SimpleObj)):
    return left == right

  if isinstance(left, list):
    if len(left) != len(right):
      return False
    for a, b in zip(left, right):
      if not AsdlEqual(a, b):
        return False
    return True

  if isinstance(left, pybase.CompoundObj):
    if left.tag != right.tag:
      return False

    field_names = left.__slots__  # hack for now
    for name in field_names:
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
  arena = alloc.Arena()
  arena.PushSource(source.MainFile(source_name))
  return arena


def InitLexer(s, arena):
  """For tests only."""
  line_lexer = lexer.LineLexer('', arena)
  line_reader = reader.StringLineReader(s, arena)
  lx = lexer.Lexer(line_lexer, line_reader)
  return line_reader, lx


def InitWordEvaluator():
  arena = MakeArena('<InitWordEvaluator>')
  mem = state.Mem('', [], arena, [])
  state.InitMem(mem, {})

  opt_array = [False] * option_i.ARRAY_SIZE
  errexit = state._ErrExit()
  parse_opts = optview.Parse(opt_array)
  exec_opts = optview.Exec(opt_array, errexit)
  mem.exec_opts = exec_opts  # circular dep

  exec_deps = cmd_exec.Deps()
  exec_deps.trap_nodes = []

  splitter = split.SplitContext(mem)
  errfmt = ui.ErrorFormatter(arena)

  ev = word_eval.CompletionWordEvaluator(mem, exec_opts, splitter, errfmt)
  return ev


def InitExecutor(parse_ctx=None, comp_lookup=None, arena=None, mem=None,
                 aliases=None, ext_prog=None):
  opt_array = [False] * option_i.ARRAY_SIZE
  if parse_ctx:
    arena = parse_ctx.arena
    parse_opts = parse_ctx.parse_opts
  else:
    parse_ctx = InitParseContext()

  mem = mem or state.Mem('', [], arena, [])
  state.InitMem(mem, {})
  errexit = state._ErrExit()
  exec_opts = optview.Exec(opt_array, errexit)
  mutable_opts = state.MutableOpts(mem, opt_array, errexit, None)
  # No 'readline' in the tests.

  errfmt = ui.ErrorFormatter(arena)
  job_state = process.JobState()
  fd_state = process.FdState(errfmt, job_state)
  funcs = {}
  aliases = {} if aliases is None else aliases

  compopt_state = completion.OptionState()
  comp_lookup = comp_lookup or completion.Lookup()

  readline = None  # simulate not having it
  new_var = builtin_assign.NewVar(mem, funcs, errfmt)
  builtins = {  # Lookup
      builtin_i.echo: builtin_pure.Echo(exec_opts),
      builtin_i.shift: builtin_assign.Shift(mem),

      builtin_i.history: builtin_misc.History(readline),

      builtin_i.compopt: builtin_comp.CompOpt(compopt_state, errfmt),
      builtin_i.compadjust: builtin_comp.CompAdjust(mem),

      builtin_i.alias: builtin_pure.Alias(aliases, errfmt),
      builtin_i.unalias: builtin_pure.UnAlias(aliases, errfmt),

      builtin_i.declare: new_var,
      builtin_i.typeset: new_var,
      builtin_i.local: new_var,

      builtin_i.export_: builtin_assign.Export(mem, errfmt),
      builtin_i.readonly: builtin_assign.Readonly(mem, errfmt),
  }

  debug_f = util.DebugFile(sys.stderr)
  exec_deps = cmd_exec.Deps()
  exec_deps.mutable_opts = state.MutableOpts(mem, opt_array, errexit, None)
  exec_deps.search_path = state.SearchPath(mem)
  exec_deps.errfmt = errfmt
  exec_deps.trap_nodes = []
  exec_deps.job_state = job_state
  exec_deps.waiter = process.Waiter(exec_deps.job_state, exec_opts)

  exec_deps.ext_prog = \
      ext_prog or process.ExternalProgram('', fd_state,
                                          exec_deps.search_path, errfmt,
                                          debug_f)

  exec_deps.dumper = dev.CrashDumper('')
  exec_deps.debug_f = debug_f
  exec_deps.trace_f = debug_f

  splitter = split.SplitContext(mem)

  procs = {}

  arith_ev = sh_expr_eval.ArithEvaluator(mem, exec_opts, errfmt)
  bool_ev = sh_expr_eval.BoolEvaluator(mem, exec_opts, errfmt)
  expr_ev = expr_eval.OilEvaluator(mem, procs, errfmt)
  word_ev = word_eval.NormalWordEvaluator(mem, exec_opts, splitter, errfmt)
  ex = cmd_exec.Executor(mem, fd_state, funcs, builtins, exec_opts,
                         parse_ctx, exec_deps)
  assert ex.mutable_opts is not None, ex
  prompt_ev = prompt.Evaluator('osh', parse_ctx, mem)
  tracer = dev.Tracer(parse_ctx, exec_opts, mutable_opts, mem, word_ev,
                      debug_f)

  vm.InitCircularDeps(arith_ev, bool_ev, expr_ev, word_ev, ex, prompt_ev, tracer)

  spec_builder = builtin_comp.SpecBuilder(ex, parse_ctx, word_ev, splitter,
                                          comp_lookup)
  # Add some builtins that depend on the executor!
  complete_builtin = builtin_comp.Complete(spec_builder, comp_lookup)
  builtins[builtin_i.complete] = complete_builtin
  builtins[builtin_i.compgen] = builtin_comp.CompGen(spec_builder)

  return ex


def EvalCode(code_str, parse_ctx, comp_lookup=None, mem=None, aliases=None):
  """
  Unit tests can evaluate code strings and then use the resulting Executor.
  """
  arena = parse_ctx.arena

  comp_lookup = comp_lookup or completion.Lookup()
  mem = mem or state.Mem('', [], arena, [])
  state.InitMem(mem, {})

  line_reader, _ = InitLexer(code_str, arena)
  c_parser = parse_ctx.MakeOshParser(line_reader)

  ex = InitExecutor(parse_ctx=parse_ctx, comp_lookup=comp_lookup, arena=arena,
                    mem=mem, aliases=aliases)

  main_loop.Batch(ex, c_parser, arena)  # Parse and execute!
  return ex


def InitParseContext(arena=None, oil_grammar=None, aliases=None):
  arena = arena or MakeArena('<test_lib>')
  if aliases is None:
    aliases = {}
  opt_array = [False] * option_i.ARRAY_SIZE
  parse_opts = optview.Parse(opt_array)
  parse_ctx = parse_lib.ParseContext(arena, parse_opts, aliases, oil_grammar)
  return parse_ctx


def InitWordParser(word_str, oil_at=False, arena=None):
  arena = arena or MakeArena('<test_lib>')
  opt_array = [False] * option_i.ARRAY_SIZE
  parse_opts = optview.Parse(opt_array)
  opt_array[option_i.parse_at] = oil_at
  loader = pyutil.GetResourceLoader()
  oil_grammar = meta.LoadOilGrammar(loader)
  parse_ctx = parse_lib.ParseContext(arena, parse_opts, {}, oil_grammar)
  line_reader, _ = InitLexer(word_str, arena)
  c_parser = parse_ctx.MakeOshParser(line_reader)
  # Hack
  return c_parser.w_parser


def InitCommandParser(code_str, arena=None):
  arena = arena or MakeArena('<test_lib>')
  parse_ctx = InitParseContext(arena=arena)
  line_reader, _ = InitLexer(code_str, arena)
  c_parser = parse_ctx.MakeOshParser(line_reader)
  return c_parser
