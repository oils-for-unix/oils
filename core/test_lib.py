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
from _devbuild.gen.runtime_asdl import cmd_value, scope_e
from _devbuild.gen.syntax_asdl import loc, source, SourceLine, Token
from _devbuild.gen.value_asdl import value
from asdl import pybase
from asdl import runtime
from builtin import assign_osh
from builtin import completion_osh
from builtin import hay_ysh
from builtin import io_osh
from builtin import pure_osh
from builtin import readline_osh
from builtin import trap_osh
from core import alloc
from core import completion
from core import dev
from core import executor
from core import main_loop
from core import optview
from core import process
from core import pyos
from core import pyutil
from core import state
from core import ui
from core import util
from core import vm
from frontend import lexer
from frontend import location
from frontend import parse_lib
from frontend import reader
from osh import cmd_eval
from osh import prompt
from osh import sh_expr_eval
from osh import split
from osh import word_eval
from ysh import expr_eval
from mycpp import mylib

import posix_ as posix


def MakeBuiltinArgv(argv):
    return cmd_value.Argv(argv, [loc.Missing] * len(argv), None, None, None)


def FakeTok(id_, val):
    # type: (int, str) -> Token
    src = source.Interactive
    line = SourceLine(1, val, src)
    return Token(id_, 0, len(val), runtime.NO_SPID, line, None)


def PrintableString(s):
    """For pretty-printing in tests."""
    if all(c in string.printable for c in s):
        return s
    return repr(s)


def TokensEqual(left, right):
    # Ignoring location in CompoundObj.__eq__ now, but we might want this later.

    if left.id != right.id:
        return False

    if left.line is not None:
        left_str = lexer.TokenVal(left)
    else:
        left_str = None

    if right.line is not None:
        right_str = lexer.TokenVal(right)
    else:
        right_str = None

    # Better error message sometimes:
    #assert left_str == right_str, '%r != %r' % (left_str, right_str)
    return left_str == right_str


def TokenWordsEqual(left, right):
    # Ignoring location in CompoundObj.__eq__ now, but we might want this later.
    return TokensEqual(left.token, right.token)
    #return left == right


def AsdlEqual(left, right):
    """Check if generated ASDL instances are equal.

    We don't use equality in the actual code, so this is relegated to
    test_lib.
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
        if left.tag() != right.tag():
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
    test.assertTrue(AsdlEqual(left, right),
                    'Expected %s, got %s' % (left, right))


def MakeArena(source_name):
    arena = alloc.Arena(save_tokens=True)
    arena.PushSource(source.MainFile(source_name))
    return arena


def InitLineLexer(s, arena):
    line_lexer = lexer.LineLexer(arena)
    src = source.Interactive
    line_lexer.Reset(SourceLine(1, s, src), 0)
    return line_lexer


def InitLexer(s, arena):
    """For tests only."""
    line_lexer = lexer.LineLexer(arena)
    line_reader = reader.StringLineReader(s, arena)
    lx = lexer.Lexer(line_lexer, line_reader)
    return line_reader, lx


def InitWordEvaluator(exec_opts=None):
    arena = MakeArena('<InitWordEvaluator>')
    mem = state.Mem('', [], arena, [])

    if exec_opts is None:
        parse_opts, exec_opts, mutable_opts = state.MakeOpts(mem, None)
        mem.exec_opts = exec_opts  # circular dep
        state.InitMem(mem, {}, '0.1')
        mutable_opts.Init()
    else:
        mutable_opts = None

    cmd_deps = cmd_eval.Deps()
    cmd_deps.trap_nodes = []

    splitter = split.SplitContext(mem)
    errfmt = ui.ErrorFormatter()

    tilde_ev = word_eval.TildeEvaluator(mem, exec_opts)
    ev = word_eval.CompletionWordEvaluator(mem, exec_opts, mutable_opts,
                                           tilde_ev, splitter, errfmt)
    return ev


def InitCommandEvaluator(parse_ctx=None,
                         comp_lookup=None,
                         arena=None,
                         mem=None,
                         aliases=None,
                         ext_prog=None):

    opt0_array = state.InitOpts()
    opt_stacks = [None] * option_i.ARRAY_SIZE
    if parse_ctx:
        arena = parse_ctx.arena
    else:
        parse_ctx = InitParseContext()

    mem = mem or state.Mem('', [], arena, [])
    exec_opts = optview.Exec(opt0_array, opt_stacks)
    mutable_opts = state.MutableOpts(mem, opt0_array, opt_stacks, None)
    mem.exec_opts = exec_opts
    state.InitMem(mem, {}, '0.1')
    mutable_opts.Init()

    # No 'readline' in the tests.

    errfmt = ui.ErrorFormatter()
    job_control = process.JobControl()
    job_list = process.JobList()
    fd_state = process.FdState(errfmt, job_control, job_list, None, None, None)
    aliases = {} if aliases is None else aliases
    procs = {}
    methods = {}

    compopt_state = completion.OptionState()
    comp_lookup = comp_lookup or completion.Lookup()

    readline = None  # simulate not having it

    new_var = assign_osh.NewVar(mem, procs, errfmt)
    assign_builtins = {
        builtin_i.declare: new_var,
        builtin_i.typeset: new_var,
        builtin_i.local: new_var,
        builtin_i.export_: assign_osh.Export(mem, errfmt),
        builtin_i.readonly: assign_osh.Readonly(mem, errfmt),
    }
    builtins = {  # Lookup
        builtin_i.echo: io_osh.Echo(exec_opts),
        builtin_i.shift: assign_osh.Shift(mem),

        builtin_i.history: readline_osh.History(
          readline,
          mem,
          errfmt,
          mylib.Stdout(),
        ),

        builtin_i.compopt: completion_osh.CompOpt(compopt_state, errfmt),
        builtin_i.compadjust: completion_osh.CompAdjust(mem),

        builtin_i.alias: pure_osh.Alias(aliases, errfmt),
        builtin_i.unalias: pure_osh.UnAlias(aliases, errfmt),
    }

    debug_f = util.DebugFile(sys.stderr)
    cmd_deps = cmd_eval.Deps()
    cmd_deps.mutable_opts = mutable_opts

    search_path = state.SearchPath(mem)

    ext_prog = \
        ext_prog or process.ExternalProgram('', fd_state, errfmt, debug_f)

    cmd_deps.dumper = dev.CrashDumper('', fd_state)
    cmd_deps.debug_f = debug_f

    splitter = split.SplitContext(mem)

    arith_ev = sh_expr_eval.ArithEvaluator(mem, exec_opts, mutable_opts,
                                           parse_ctx, errfmt)
    bool_ev = sh_expr_eval.BoolEvaluator(mem, exec_opts, mutable_opts,
                                         parse_ctx, errfmt)
    expr_ev = expr_eval.ExprEvaluator(mem, mutable_opts, methods, splitter,
                                      errfmt)
    tilde_ev = word_eval.TildeEvaluator(mem, exec_opts)
    word_ev = word_eval.NormalWordEvaluator(mem, exec_opts, mutable_opts,
                                            tilde_ev, splitter, errfmt)
    signal_safe = pyos.InitSignalSafe()
    trap_state = trap_osh.TrapState(signal_safe)
    cmd_ev = cmd_eval.CommandEvaluator(mem, exec_opts, errfmt, procs,
                                       assign_builtins, arena, cmd_deps,
                                       trap_state, signal_safe)

    multi_trace = dev.MultiTracer(posix.getpid(), '', '', '', fd_state)
    tracer = dev.Tracer(parse_ctx, exec_opts, mutable_opts, mem, debug_f,
                        multi_trace)
    waiter = process.Waiter(job_list, exec_opts, trap_state, tracer)

    hay_state = hay_ysh.HayState()
    shell_ex = executor.ShellExecutor(mem, exec_opts, mutable_opts, procs,
                                      hay_state, builtins, search_path,
                                      ext_prog, waiter, tracer, job_control,
                                      job_list, fd_state, trap_state, errfmt)

    assert cmd_ev.mutable_opts is not None, cmd_ev
    prompt_ev = prompt.Evaluator('osh', '0.0.0', parse_ctx, mem)

    global_io = value.IO(cmd_ev, prompt_ev)
    vm.InitCircularDeps(arith_ev, bool_ev, expr_ev, word_ev, cmd_ev, shell_ex,
                        prompt_ev, global_io, tracer)

    try:
        from _devbuild.gen.help_meta import TOPICS
    except ImportError:
        TOPICS = None  # minimal dev build
    spec_builder = completion_osh.SpecBuilder(cmd_ev, parse_ctx, word_ev,
                                              splitter, comp_lookup, TOPICS,
                                              errfmt)

    # Add some builtins that depend on the executor!
    complete_builtin = completion_osh.Complete(spec_builder, comp_lookup)
    builtins[builtin_i.complete] = complete_builtin
    builtins[builtin_i.compgen] = completion_osh.CompGen(spec_builder)

    return cmd_ev


def EvalCode(code_str, parse_ctx, comp_lookup=None, mem=None, aliases=None):
    """Unit tests can evaluate code strings and then use the resulting
    CommandEvaluator."""
    arena = parse_ctx.arena
    errfmt = ui.ErrorFormatter()

    comp_lookup = comp_lookup or completion.Lookup()
    mem = mem or state.Mem('', [], arena, [])
    parse_opts, exec_opts, mutable_opts = state.MakeOpts(mem, None)
    mem.exec_opts = exec_opts

    state.InitMem(mem, {}, '0.1')
    mutable_opts.Init()

    line_reader, _ = InitLexer(code_str, arena)
    c_parser = parse_ctx.MakeOshParser(line_reader)

    cmd_ev = InitCommandEvaluator(parse_ctx=parse_ctx,
                                  comp_lookup=comp_lookup,
                                  arena=arena,
                                  mem=mem,
                                  aliases=aliases)

    main_loop.Batch(cmd_ev, c_parser, errfmt)  # Parse and execute!
    return cmd_ev


def InitParseContext(arena=None,
                     ysh_grammar=None,
                     aliases=None,
                     parse_opts=None,
                     do_lossless=False):
    arena = arena or MakeArena('<test_lib>')

    if aliases is None:
        aliases = {}

    mem = state.Mem('', [], arena, [])
    if parse_opts is None:
        parse_opts, exec_opts, mutable_opts = state.MakeOpts(mem, None)

    parse_ctx = parse_lib.ParseContext(arena,
                                       parse_opts,
                                       aliases,
                                       ysh_grammar,
                                       do_lossless=do_lossless)

    return parse_ctx


def InitWordParser(word_str, oil_at=False, arena=None):
    arena = arena or MakeArena('<test_lib>')

    mem = state.Mem('', [], arena, [])
    parse_opts, exec_opts, mutable_opts = state.MakeOpts(mem, None)

    # CUSTOM SETTING
    mutable_opts.opt0_array[option_i.parse_at] = oil_at

    loader = pyutil.GetResourceLoader()
    ysh_grammar = pyutil.LoadYshGrammar(loader)
    parse_ctx = parse_lib.ParseContext(arena, parse_opts, {}, ysh_grammar)
    line_reader, _ = InitLexer(word_str, arena)
    c_parser = parse_ctx.MakeOshParser(line_reader)
    # Hack
    return c_parser.w_parser


def InitCommandParser(code_str, arena=None):
    arena = arena or MakeArena('<test_lib>')

    loader = pyutil.GetResourceLoader()
    ysh_grammar = pyutil.LoadYshGrammar(loader)

    parse_ctx = InitParseContext(arena=arena, ysh_grammar=ysh_grammar)
    line_reader, _ = InitLexer(code_str, arena)
    c_parser = parse_ctx.MakeOshParser(line_reader)
    return c_parser


def SetLocalString(mem, name, s):
    # type: (state.Mem, str, str) -> None
    """Bind a local string."""
    assert isinstance(s, str)
    mem.SetNamed(location.LName(name), value.Str(s), scope_e.LocalOnly)
