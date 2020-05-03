#!/usr/bin/env python2
"""
osh_parse.py
"""
from __future__ import print_function

import sys

from _devbuild.gen.option_asdl import builtin_i
from _devbuild.gen.syntax_asdl import (
    source, source_t, command, command_e, command_t, command_str,
    command__Simple, command__DParen,
)
from asdl import format as fmt
from core import alloc
from core import dev
from core import error
from core import main_loop
from core import meta
from core import pyutil
from core.util import log
from core import util
from core import state
from core import ui
from core.vm import _Executor  # reordered by mycpp
from frontend import consts
from frontend import parse_lib
from frontend import reader
from mycpp import mylib
from mycpp.mylib import tagswitch, NewStr
from osh import braces
from osh import split

# Evaluators
# This causes errors in oil_lang/{objects,regex_translate}, builtin_pure, etc.
# builtin_pure.Command maybe shouldn't be hard-coded?
from osh import cmd_eval
from osh import sh_expr_eval
from osh import word_eval

from typing import List, Dict, Tuple, Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import command__ShFunction
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from core.state import MutableOpts
  from core.vm import _AssignBuiltin
  from osh.cmd_parse import CommandParser
  from pgen2.grammar import Grammar


if mylib.PYTHON:
  unused1 = log
  unused2 = cmd_eval  # lint ignore
  unused3 = dev
  unused4 = main_loop


class TestEvaluator(object):
  def __init__(self, arith_ev, word_ev):
    # type: (sh_expr_eval.ArithEvaluator, word_eval.NormalWordEvaluator) -> None
    self.arith_ev = arith_ev
    self.word_ev = word_ev

  def Eval(self, node):
    # type: (command_t) -> None

    UP_node = node
    with tagswitch(node) as case:
      if case(command_e.Simple):
        node = cast(command__Simple, UP_node)

        # Need splitter for this.
        if 0:
          cmd_val = self.word_ev.EvalWordSequence2(node.words, allow_assign=True)
          for arg in cmd_val.argv:
            log('arg %s', arg)
        words = braces.BraceExpandWords(node.words)
        for w in words:
          val = self.word_ev.EvalWordToString(w)
          log('arg %r', val.s)

      elif case(command_e.DParen):
        node = cast(command__DParen, UP_node)

        a = self.arith_ev.Eval(node.child)
        # TODO: how to print repr() in C++?
        log('arith val %d', a.tag_())

      else:
        log('Unhandled node %s', NewStr(command_str(node.tag_())))


def Parse(argv):
  # type: (List[str]) -> Tuple[int, bool, Optional[str], bool]
  """
  returns the -n and -c value
  """
  i = 0  

  flag_a = True
  flag_c = None  # type: str
  flag_n = False

  n = len(argv)

  while i < n:
    if argv[i] == '-n':
      flag_n = True

    elif argv[i] == '-a':
      if i >= n:
        raise AssertionError(argv)

      i += 1
      if argv[i] == "none":
        flag_a = False

    elif argv[i] == '-c':
      if i >= n:
        raise AssertionError(argv)

      i += 1
      flag_c = argv[i]

    else:
      break

    i += 1

  return i, flag_a, flag_c, flag_n


def main(argv):
  # type: (List[str]) -> int
  arena = alloc.Arena()

  dollar0 = argv[0]
  debug_stack = []  # type: List[state.DebugFrame]
  mem = state.Mem(dollar0, argv, arena, debug_stack)
  opt_hook = state.OptHook()
  parse_opts, exec_opts, mutable_opts = state.MakeOpts(mem, opt_hook)
  # Dummy value; not respecting aliases!
  aliases = {}  # type: Dict[str, str]
  # parse `` and a[x+1]=bar differently

  state.SetGlobalString(mem, 'SHELLOPTS', '')

  oil_grammar = None  # type: Grammar
  if mylib.PYTHON:
    loader = pyutil.GetResourceLoader()
    oil_grammar = meta.LoadOilGrammar(loader)

  parse_ctx = parse_lib.ParseContext(arena, parse_opts, aliases, oil_grammar)

  argv = argv[1:]  # remove binary name
  i, flag_a, flag_c, flag_n = Parse(argv)

  argv = argv[i:]  # truncate

  if flag_c:
    # This path is easier to run through GDB
    line_reader = reader.StringLineReader(flag_c, arena)
    src = source.CFlag()  # type: source_t

  elif len(argv) == 0:
    line_reader = reader.FileLineReader(mylib.Stdin(), arena)
    src = source.Stdin('')

  elif len(argv) == 1:
    path = argv[0]
    f = mylib.open(path)
    line_reader = reader.FileLineReader(f, arena)
    src = source.MainFile(path)

  else:
    raise AssertionError(argv)

  arena.PushSource(src)
  c_parser = parse_ctx.MakeOshParser(line_reader)

  # C++ doesn't have the abbreviations yet (though there are some differences
  # like omitting spids)
  #tree = node.AbbreviatedTree()
  if flag_n:
    try:
      node = main_loop.ParseWholeFile(c_parser)
    except error.Parse as e:
      ui.PrettyPrintError(e, arena)
      return 2
    assert node is not None

    if flag_a:
      tree = node.PrettyTree()

      ast_f = fmt.DetectConsoleOutput(mylib.Stdout())
      fmt.PrintTree(tree, ast_f)
      ast_f.write('\n')
    return 0

  # New osh_eval.py instantiations

  errfmt = ui.ErrorFormatter(arena)

  splitter = split.SplitContext(mem)
  arith_ev = sh_expr_eval.ArithEvaluator(mem, exec_opts, parse_ctx, errfmt)
  bool_ev = sh_expr_eval.BoolEvaluator(mem, exec_opts, parse_ctx, errfmt)
  word_ev = word_eval.NormalWordEvaluator(mem, exec_opts, splitter, errfmt)

  arith_ev.word_ev = word_ev
  word_ev.arith_ev = arith_ev

  #test_ev = TestEvaluator(arith_ev, word_ev)
  #test_ev.Eval(node)

  procs = {}  # type: Dict[str, command__ShFunction]

  assign_builtins = {}  # type: Dict[int, _AssignBuiltin]

  cmd_deps = cmd_eval.Deps()
  cmd_deps.mutable_opts = mutable_opts
  cmd_deps.traps = {}
  cmd_deps.trap_nodes = []  # TODO: Clear on fork() to avoid duplicates

  cmd_deps.dumper = dev.CrashDumper('')

  builtins = {}  # type: Dict[int, _Builtin]
  builtins[builtin_i.echo] = Echo()
  builtins[builtin_i.shopt] = Shopt(mutable_opts)
  builtins[builtin_i.set] = Set(mutable_opts)
  ex = NullExecutor(builtins)

  trace_f = util.DebugFile(mylib.Stderr())
  tracer = dev.Tracer(parse_ctx, exec_opts, mutable_opts, mem, word_ev, trace_f)

  cmd_ev = cmd_eval.CommandEvaluator(mem, exec_opts, errfmt, procs,
                                     assign_builtins, arena, cmd_deps)

  # vm.InitCircularDeps
  cmd_ev.arith_ev = arith_ev
  cmd_ev.bool_ev = bool_ev
  cmd_ev.word_ev = word_ev
  cmd_ev.tracer = tracer
  cmd_ev.shell_ex = ex

  bool_ev.word_ev = word_ev

  status = main_loop.Batch(cmd_ev, c_parser, arena, is_main=True)
  return status


class _Builtin(object):

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    raise NotImplementedError()


class Echo(_Builtin):
  """Simple echo builtin.
  """
  def __init__(self):
    # type: () -> None
    self.f = mylib.Stdout()

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    for i, a in enumerate(cmd_val.argv[1:]):
      if i != 0:
        self.f.write(' ')  # arg separator
      self.f.write(a)

    self.f.write('\n')
    return 0


class Set(_Builtin):
  def __init__(self, mutable_opts):
    # type: (MutableOpts) -> None
    self.mutable_opts = mutable_opts

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    argv = cmd_val.argv

    if len(argv) != 3:
      #log('shopt %s', argv)
      log('set %d', len(argv))
      return 1

    b = (argv[1] == '-o')
    opt_name = argv[2]
    self.mutable_opts.SetOption(opt_name, b)

    return 0


class Shopt(_Builtin):
  def __init__(self, mutable_opts):
    # type: (MutableOpts) -> None
    self.mutable_opts = mutable_opts

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    argv = cmd_val.argv

    if len(argv) != 3:
      #log('shopt %s', argv)
      log('shopt %d', len(argv))
      return 1

    b = (argv[1] == '-s')
    for opt_name in cmd_val.argv[2:]:
      #log('opt_name %s', opt_name)
      self.mutable_opts.SetShoptOption(opt_name, b)
    return 0


class NullExecutor(_Executor):
  def __init__(self, builtins):
    # type: (Dict[int, _Builtin]) -> None
    self.builtins = builtins

  def RunBuiltin(self, builtin_id, cmd_val):
    # type: (int, cmd_value__Argv) -> int
    """Run a builtin.  Also called by the 'builtin' builtin."""

    builtin_func = self.builtins[builtin_id]

    try:
      status = builtin_func.Run(cmd_val)
    finally:
      pass
    return status

  def RunSimpleCommand(self, cmd_val, do_fork, call_procs=True):
    # type: (cmd_value__Argv, bool, bool) -> int

    arg0 = cmd_val.argv[0]

    builtin_id = consts.LookupSpecialBuiltin(arg0)
    if builtin_id != consts.NO_INDEX:
      return self.RunBuiltin(builtin_id, cmd_val)

    builtin_id = consts.LookupNormalBuiltin(arg0)
    if builtin_id != consts.NO_INDEX:
      return self.RunBuiltin(builtin_id, cmd_val)

    log('Unhandled SimpleCommand')

    f = mylib.Stdout()
    #ast_f = fmt.DetectConsoleOutput(f)
    # Stupid Eclipse debugger doesn't display ANSI
    ast_f = fmt.TextOutput(f)
    tree = cmd_val.PrettyTree()

    ast_f.FileHeader()
    fmt.PrintTree(tree, ast_f)
    ast_f.FileFooter()
    ast_f.write('\n')

    return 0


if __name__ == '__main__':
  try:
    status = main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    status = 1
  sys.exit(status)
