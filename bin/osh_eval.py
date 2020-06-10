#!/usr/bin/env python2
"""
osh_parse.py
"""
from __future__ import print_function

import sys

from _devbuild.gen.option_asdl import builtin_i
from _devbuild.gen.syntax_asdl import (source, source_t)
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
from core import vm
from frontend import args
from frontend import consts
from frontend import flag_def  # side effect: flags are defined!
_ = flag_def
from frontend import parse_lib
from frontend import reader
from mycpp import mylib
from osh import split
from osh import builtin_assign
from osh import builtin_meta

# translation: has 'set' builtin
from osh import builtin_pure
from osh import builtin_printf
from osh import builtin_bracket
from osh import builtin_process

# Depends on core/completion.py
# _FlagSpecAndMore needs translating
#from osh import builtin_comp

# - note: history has readline_mod argument
from osh import builtin_misc

# Evaluators
from osh import cmd_eval
from osh import sh_expr_eval
from osh import word_eval
from osh import prompt

import posix_ as posix

from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import command__ShFunction
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from core.state import MutableOpts
  from core.vm import _AssignBuiltin
  from pgen2.grammar import Grammar


if mylib.PYTHON:
  unused1 = log
  unused2 = args
  unused3 = builtin_process


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

  argv = argv[1:]  # remove binary name
  i, flag_a, flag_c, flag_n = Parse(argv)
  argv = argv[i:]  # truncate

  mem = state.Mem(dollar0, argv, arena, debug_stack)

  # TODO: look at extern char** environ;

  environ = {}  # type: Dict[str, str]
  environ['PWD'] = posix.getcwd()
  state.InitMem(mem, environ, 'VERSION')

  opt_hook = state.OptHook()
  parse_opts, exec_opts, mutable_opts = state.MakeOpts(mem, opt_hook)
  # Dummy value; not respecting aliases!
  aliases = {}  # type: Dict[str, str]
  # parse `` and a[x+1]=bar differently

  oil_grammar = None  # type: Grammar
  if mylib.PYTHON:
    loader = pyutil.GetResourceLoader()
    oil_grammar = meta.LoadOilGrammar(loader)

  parse_ctx = parse_lib.ParseContext(arena, parse_opts, aliases, oil_grammar)

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
  prompt_ev = prompt.Evaluator('osh', parse_ctx, mem)

  arith_ev.word_ev = word_ev
  word_ev.arith_ev = arith_ev
  word_ev.prompt_ev = prompt_ev

  prompt_ev.word_ev = word_ev

  procs = {}  # type: Dict[str, command__ShFunction]

  assign_builtins = {}  # type: Dict[int, _AssignBuiltin]

  new_var = builtin_assign.NewVar(mem, procs, errfmt)
  assign_builtins[builtin_i.declare] = new_var
  assign_builtins[builtin_i.typeset] = new_var
  assign_builtins[builtin_i.local] = new_var
  assign_builtins[builtin_i.export_] = builtin_assign.Export(mem, errfmt)
  assign_builtins[builtin_i.readonly] = builtin_assign.Readonly(mem, errfmt)

  #assign_builtins = {
  #    # ShAssignment (which are pure)
  #    builtin_i.declare: new_var,
  #    builtin_i.typeset: new_var,
  #    builtin_i.local: new_var,

  #    builtin_i.export_: builtin_assign.Export(mem, errfmt),
  #    builtin_i.readonly: builtin_assign.Readonly(mem, errfmt),
  #}

  cmd_deps = cmd_eval.Deps()
  cmd_deps.mutable_opts = mutable_opts
  cmd_deps.traps = {}
  cmd_deps.trap_nodes = []  # TODO: Clear on fork() to avoid duplicates

  cmd_deps.dumper = dev.CrashDumper('')

  search_path = state.SearchPath(mem)

  builtins = {}  # type: Dict[int, vm._Builtin]
  builtins[builtin_i.echo] = builtin_pure.Echo(exec_opts)

  # DUMMY VERSIONS
  builtins[builtin_i.shopt] = Shopt(mutable_opts)
  builtins[builtin_i.set] = Set(mutable_opts)

  #builtins[builtin_i.set] = builtin_pure.Set(mutable_opts, mem)
  #builtins[builtin_i.shopt] = builtin_pure.Shopt(mutable_opts)

  builtins[builtin_i.alias] = builtin_pure.Alias(aliases, errfmt)
  builtins[builtin_i.unalias] = builtin_pure.UnAlias(aliases, errfmt)

  builtins[builtin_i.hash] = builtin_pure.Hash(search_path)
  builtins[builtin_i.getopts] = builtin_pure.GetOpts(mem, errfmt)

  builtins[builtin_i.shift] = builtin_assign.Shift(mem)
  builtins[builtin_i.unset] = builtin_assign.Unset(
      mem, exec_opts, procs, parse_ctx, arith_ev, errfmt)

  true_ = builtin_pure.Boolean(0)
  builtins[builtin_i.colon] = true_  # a "special" builtin 
  builtins[builtin_i.true_] = true_
  builtins[builtin_i.false_] = builtin_pure.Boolean(1)

  # builtin_meta
  builtins[builtin_i.type] = builtin_meta.Type(procs, aliases, search_path, errfmt)

  shell_ex = NullExecutor(builtins)

  trace_f = util.DebugFile(mylib.Stderr())
  tracer = dev.Tracer(parse_ctx, exec_opts, mutable_opts, mem, word_ev, trace_f)

  cmd_ev = cmd_eval.CommandEvaluator(mem, exec_opts, errfmt, procs,
                                     assign_builtins, arena, cmd_deps)

  # TODO: can't instantiate this yet
  #fd_state = None

  # needs cmd_ev
  builtins[builtin_i.eval] = builtin_meta.Eval(parse_ctx, exec_opts, cmd_ev)
  #source_builtin = builtin_meta.Source(
  #    parse_ctx, search_path, cmd_ev, fd_state, errfmt)
  #builtins[builtin_i.source] = source_builtin
  #builtins[builtin_i.dot] = source_builtin

  builtins[builtin_i.builtin] = builtin_meta.Builtin(shell_ex, errfmt)
  builtins[builtin_i.command] = builtin_meta.Command(shell_ex, procs, aliases,
                                                     search_path)

  builtins[builtin_i.printf] = builtin_printf.Printf(mem, parse_ctx, errfmt)

  builtins[builtin_i.test] = builtin_bracket.Test(False, exec_opts, mem, errfmt)
  builtins[builtin_i.bracket] = builtin_bracket.Test(True, exec_opts, mem, errfmt)

  dir_stack = state.DirStack()
  builtins[builtin_i.pushd] = builtin_misc.Pushd(mem, dir_stack, errfmt)
  builtins[builtin_i.popd] = builtin_misc.Popd(mem, dir_stack, errfmt)
  builtins[builtin_i.dirs] = builtin_misc.Dirs(mem, dir_stack, errfmt)
  builtins[builtin_i.pwd] = builtin_misc.Pwd(mem, errfmt)

  builtins[builtin_i.times] = builtin_misc.Times()
  builtins[builtin_i.read] = builtin_misc.Read(splitter, mem)

  builtins[builtin_i.cat] = builtin_misc.Cat()  # for $(<file)
  builtins[builtin_i.cd] = builtin_misc.Cd(mem, dir_stack, cmd_ev, errfmt)

  # vm.InitCircularDeps
  cmd_ev.arith_ev = arith_ev
  cmd_ev.bool_ev = bool_ev
  cmd_ev.word_ev = word_ev
  cmd_ev.tracer = tracer
  cmd_ev.shell_ex = shell_ex

  bool_ev.word_ev = word_ev

  status = main_loop.Batch(cmd_ev, c_parser, arena, is_main=True)
  return status


class Set(vm._Builtin):
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


class Shopt(vm._Builtin):
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


class NullExecutor(vm._Executor):
  def __init__(self, builtins):
    # type: (Dict[int, vm._Builtin]) -> None
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

    # See how many tests will pass
    if mylib.PYTHON:
      import subprocess
      status = subprocess.call(cmd_val.argv)
      return status

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
