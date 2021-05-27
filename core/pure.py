#!/usr/bin/env python2
"""
core/pure.py -- Pure shell interpreter without I/O.

Note that this is a modified version of core/shell.py.  Maybe consolidate
them.
"""
from __future__ import print_function

import time as time_

from _devbuild.gen import arg_types
from _devbuild.gen.option_asdl import builtin_i
from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import source

from asdl import format as fmt
from asdl import runtime

from core import alloc
from core import dev
from core import error
from core import executor
from core import main_loop
from core import process
from core.pyerror import e_usage
from core import pyos
from core import pyutil
from core.pyutil import stderr_line
from core import state
from core import ui
from core import util
from core.pyerror import log, e_die
from core import vm

from frontend import args
from frontend import consts
from frontend import flag_def  # side effect: flags are defined!
_ = flag_def
from frontend import flag_spec
from frontend import reader
from frontend import parse_lib

from osh import builtin_assign
from osh import builtin_bracket
from osh import builtin_meta
from osh import builtin_misc
from osh import builtin_printf
#from osh import builtin_process
from osh import builtin_pure
from osh import cmd_eval
from osh import prompt
from osh import sh_expr_eval
from osh import split
from osh import word_eval

from mycpp import mylib
from pylib import os_path

import posix_ as posix

from typing import List, Dict, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv, Proc
  from core import optview
  from oil_lang import expr_eval
  from pgen2 import grammar


def MakeBuiltinArgv(argv1):
  # type: (List[str]) -> cmd_value__Argv
  argv = ['']  # dummy for argv[0]
  argv.extend(argv1)
  # no location info
  return cmd_value.Argv(argv, [runtime.NO_SPID] * len(argv), None)


def AddPure(b, mem, procs, modules, mutable_opts, aliases, search_path, errfmt):
  # type: (Dict[int, vm._Builtin], state.Mem, Dict[str, Proc], Dict[str, bool], state.MutableOpts, Dict[str, str], state.SearchPath, ui.ErrorFormatter) -> None
  b[builtin_i.set] = builtin_pure.Set(mutable_opts, mem)

  b[builtin_i.alias] = builtin_pure.Alias(aliases, errfmt)
  b[builtin_i.unalias] = builtin_pure.UnAlias(aliases, errfmt)

  b[builtin_i.hash] = builtin_pure.Hash(search_path)
  b[builtin_i.getopts] = builtin_pure.GetOpts(mem, errfmt)

  true_ = builtin_pure.Boolean(0)
  b[builtin_i.colon] = true_  # a "special" builtin 
  b[builtin_i.true_] = true_
  b[builtin_i.false_] = builtin_pure.Boolean(1)

  b[builtin_i.shift] = builtin_assign.Shift(mem)

  b[builtin_i.type] = builtin_meta.Type(procs, aliases, search_path, errfmt)
  b[builtin_i.module] = builtin_pure.Module(modules, mem.exec_opts, errfmt)


def AddIO(b, mem, dir_stack, exec_opts, splitter, parse_ctx, errfmt):
  # type: (Dict[int, vm._Builtin], state.Mem, state.DirStack, optview.Exec, split.SplitContext, parse_lib.ParseContext, ui.ErrorFormatter) -> None
  mapfile = builtin_misc.MapFile(mem, errfmt)

  b[builtin_i.echo] = builtin_pure.Echo(exec_opts)
  b[builtin_i.mapfile] = mapfile
  b[builtin_i.readarray] = mapfile

  b[builtin_i.read] = builtin_misc.Read(splitter, mem, parse_ctx)
  b[builtin_i.cat] = builtin_misc.Cat()  # for $(<file)

  # test / [ differ by need_right_bracket
  b[builtin_i.test] = builtin_bracket.Test(False, exec_opts, mem, errfmt)
  b[builtin_i.bracket] = builtin_bracket.Test(True, exec_opts, mem, errfmt)

  b[builtin_i.pushd] = builtin_misc.Pushd(mem, dir_stack, errfmt)
  b[builtin_i.popd] = builtin_misc.Popd(mem, dir_stack, errfmt)
  b[builtin_i.dirs] = builtin_misc.Dirs(mem, dir_stack, errfmt)
  b[builtin_i.pwd] = builtin_misc.Pwd(mem, errfmt)

  b[builtin_i.times] = builtin_misc.Times()


def AddMeta(builtins, shell_ex, mutable_opts, mem, procs, aliases, search_path,
            errfmt):
  # type: (Dict[int, vm._Builtin], vm._Executor, state.MutableOpts, state.Mem, Dict[str, Proc], Dict[str, str], state.SearchPath, ui.ErrorFormatter) -> None
  """Builtins that run more code."""

  builtins[builtin_i.builtin] = builtin_meta.Builtin(shell_ex, errfmt)
  builtins[builtin_i.command] = builtin_meta.Command(shell_ex, procs, aliases,
                                                     search_path)
  builtins[builtin_i.try_] = builtin_meta.Try(mutable_opts, mem, shell_ex, errfmt)


def AddBlock(builtins, mem, mutable_opts, dir_stack, cmd_ev, errfmt):
  # type: (Dict[int, vm._Builtin], state.Mem, state.MutableOpts, state.DirStack, cmd_eval.CommandEvaluator, ui.ErrorFormatter) -> None
  # These builtins take blocks, and thus need cmd_ev.
  builtins[builtin_i.cd] = builtin_misc.Cd(mem, dir_stack, cmd_ev, errfmt)
  builtins[builtin_i.shopt] = builtin_pure.Shopt(mutable_opts, cmd_ev)


def InitAssignmentBuiltins(mem, procs, errfmt):
  # type: (state.Mem, Dict[str, Proc], ui.ErrorFormatter) -> Dict[int, vm._AssignBuiltin]

  assign_b = {}  # type: Dict[int, vm._AssignBuiltin]

  new_var = builtin_assign.NewVar(mem, procs, errfmt)
  assign_b[builtin_i.declare] = new_var
  assign_b[builtin_i.typeset] = new_var
  assign_b[builtin_i.local] = new_var

  assign_b[builtin_i.export_] = builtin_assign.Export(mem, errfmt)
  assign_b[builtin_i.readonly] = builtin_assign.Readonly(mem, errfmt)

  return assign_b


def Main(lang, arg_r, environ, login_shell, loader, line_input):
  # type: (str, args.Reader, Dict[str, str], bool, pyutil._ResourceLoader, Any) -> int
  """The full shell lifecycle.  Used by bin/osh and bin/oil.

  Args:
    lang: 'osh' or 'oil'
    argv0, arg_r: command line arguments
    environ: environment
    login_shell: Was - on the front?
    loader: to get help, version, grammar, etc.
    line_input: optional GNU readline
  """
  # Differences between osh and oil:
  # - --help?  I guess Oil has a SUPERSET of OSH options.
  # - oshrc vs oilrc
  # - shopt -s oil:all
  # - Change the prompt in the interactive shell?

  # osh-pure:
  # - no oil grammar
  # - no expression evaluator
  # - no interactive shell, or line_input
  # - no process.*
  #   process.{ExternalProgram,Waiter,FdState,JobState,SignalState} -- we want
  #   to evaluate config files without any of these
  # Modules not translated yet: completion, comp_ui, builtin_comp, process
  # - word evaluator
  #   - shouldn't glob?  set -o noglob?  or hard failure?
  #   - ~ shouldn't read from the file system
  #     - I guess it can just be the HOME=HOME?
  # Builtin:
  #   shellvm -c 'echo hi'
  #   shellvm <<< 'echo hi'

  argv0 = arg_r.Peek()
  assert argv0 is not None
  arg_r.Next()

  assert lang in ('osh', 'oil'), lang

  try:
    attrs = flag_spec.ParseMore('main', arg_r)
  except error.Usage as e:
    stderr_line('osh usage error: %s', e.msg)
    return 2
  flag = arg_types.main(attrs.attrs)

  arena = alloc.Arena()
  errfmt = ui.ErrorFormatter(arena)

  help_builtin = builtin_misc.Help(loader, errfmt)
  if flag.help:
    help_builtin.Run(MakeBuiltinArgv(['%s-usage' % lang]))
    return 0
  if flag.version:
    # OSH version is the only binary in Oil right now, so it's all one version.
    pyutil.ShowAppVersion('Oil', loader)
    return 0

  no_str = None  # type: str

  debug_stack = []  # type: List[state.DebugFrame]
  if arg_r.AtEnd():
    dollar0 = argv0
  else:
    dollar0 = arg_r.Peek()  # the script name, or the arg after -c

    # Copy quirky bash behavior.
    frame0 = state.DebugFrame(dollar0, 'main', no_str, state.LINE_ZERO, 0, 0)
    debug_stack.append(frame0)

  # Copy quirky bash behavior.
  frame1 = state.DebugFrame(no_str, no_str, no_str, runtime.NO_SPID, 0, 0)
  debug_stack.append(frame1)

  script_name = arg_r.Peek()  # type: Optional[str]
  arg_r.Next()
  mem = state.Mem(dollar0, arg_r.Rest(), arena, debug_stack)

  opt_hook = state.OptHook()
  parse_opts, exec_opts, mutable_opts = state.MakeOpts(mem, opt_hook)
  # Note: only MutableOpts needs mem, so it's not a true circular dep.
  mem.exec_opts = exec_opts  # circular dep
  mutable_opts.Init()

  version_str = pyutil.GetVersion(loader)
  state.InitMem(mem, environ, version_str)

  procs = {}  # type: Dict[str, Proc]

  if attrs.show_options:  # special case: sh -o
    mutable_opts.ShowOptions([])
    return 0

  # Set these BEFORE processing flags, so they can be overridden.
  if lang == 'oil':
    mutable_opts.SetShoptOption('oil:all', True)

  builtin_pure.SetShellOpts(mutable_opts, attrs.opt_changes, attrs.shopt_changes)
  # feedback between runtime and parser
  aliases = {}  # type: Dict[str, str]

  oil_grammar = None  # type: grammar.Grammar
  #oil_grammar = pyutil.LoadOilGrammar(loader)

  if flag.one_pass_parse and not exec_opts.noexec():
    e_usage('--one-pass-parse requires noexec (-n)')
  parse_ctx = parse_lib.ParseContext(arena, parse_opts, aliases, oil_grammar)
  parse_ctx.Init_OnePassParse(flag.one_pass_parse)

  # Three ParseContext instances SHARE aliases.
  comp_arena = alloc.Arena()
  comp_arena.PushSource(source.Unused('completion'))
  trail1 = parse_lib.Trail()
  # one_pass_parse needs to be turned on to complete inside backticks.  TODO:
  # fix the issue where ` gets erased because it's not part of
  # set_completer_delims().
  comp_ctx = parse_lib.ParseContext(comp_arena, parse_opts, aliases,
                                    oil_grammar)
  comp_ctx.Init_Trail(trail1)
  comp_ctx.Init_OnePassParse(True)

  hist_arena = alloc.Arena()
  hist_arena.PushSource(source.Unused('history'))
  trail2 = parse_lib.Trail()
  hist_ctx = parse_lib.ParseContext(hist_arena, parse_opts, aliases,
                                    oil_grammar)
  hist_ctx.Init_Trail(trail2)

  # Deps helps manages dependencies.  These dependencies are circular:
  # - cmd_ev and word_ev, arith_ev -- for command sub, arith sub
  # - arith_ev and word_ev -- for $(( ${a} )) and $x$(( 1 )) 
  # - cmd_ev and builtins (which execute code, like eval)
  # - prompt_ev needs word_ev for $PS1, which needs prompt_ev for @P
  cmd_deps = cmd_eval.Deps()
  cmd_deps.mutable_opts = mutable_opts

  # TODO: In general, cmd_deps are shared between the mutually recursive
  # evaluators.  Some of the four below are only shared between a builtin and
  # the CommandEvaluator, so we could put them somewhere else.
  cmd_deps.traps = {}
  cmd_deps.trap_nodes = []  # TODO: Clear on fork() to avoid duplicates

  my_pid = posix.getpid()

  debug_path = ''
  debug_dir = environ.get('OSH_DEBUG_DIR')
  if flag.debug_file is not None:
    # --debug-file takes precedence over OSH_DEBUG_DIR
    debug_path = flag.debug_file
  elif debug_dir is not None:
    debug_path = os_path.join(debug_dir, '%d-osh.log' % my_pid)

  if len(debug_path):
    raise NotImplementedError()
  else:
    debug_f = util.NullDebugFile()  # type: util._DebugFile

  cmd_deps.debug_f = debug_f

  # Not using datetime for dependency reasons.  TODO: maybe show the date at
  # the beginning of the log, and then only show time afterward?  To save
  # space, and make space for microseconds.  (datetime supports microseconds
  # but time.strftime doesn't).
  if mylib.PYTHON:
    iso_stamp = time_.strftime("%Y-%m-%d %H:%M:%S")
    debug_f.log('%s [%d] OSH started with argv %s', iso_stamp, my_pid, arg_r.argv)
  if len(debug_path):
    debug_f.log('Writing logs to %r', debug_path)

  if flag.xtrace_to_debug_file:
    trace_f = debug_f
  else:
    trace_f = util.DebugFile(mylib.Stderr())
  tracer = dev.Tracer(parse_ctx, exec_opts, mutable_opts, mem, trace_f)

  # TODO: We shouldn't have SignalState?
  sig_state = pyos.SignalState()
  sig_state.InitShell()

  job_state = process.JobState()
  fd_state = process.FdState(errfmt, job_state, mem, tracer, None)
  waiter = process.Waiter(job_state, exec_opts, sig_state, tracer)
  fd_state.waiter = waiter  # circular dep

  interp = environ.get('OSH_HIJACK_SHEBANG', '')
  search_path = state.SearchPath(mem)
  ext_prog = process.ExternalProgram(interp, fd_state, errfmt, debug_f)

  splitter = split.SplitContext(mem)

  # This could just be OSH_DEBUG_STREAMS='debug crash' ?  That might be
  # stuffing too much into one, since a .json crash dump isn't a stream.
  crash_dump_dir = environ.get('OSH_CRASH_DUMP_DIR', '')
  cmd_deps.dumper = dev.CrashDumper(crash_dump_dir)

  #comp_lookup = completion.Lookup()

  # Various Global State objects to work around readline interfaces
  #compopt_state = completion.OptionState()
  #comp_ui_state = comp_ui.State()
  #prompt_state = comp_ui.PromptState()

  dir_stack = state.DirStack()

  #
  # Initialize builtins that don't depend on evaluators
  #

  builtins = {}  # type: Dict[int, vm._Builtin]
  modules = {}  # type: Dict[str, bool]

  AddPure(builtins, mem, procs, modules, mutable_opts, aliases, search_path, errfmt)
  AddIO(builtins, mem, dir_stack, exec_opts, splitter, parse_ctx, errfmt)

  builtins[builtin_i.help] = help_builtin

  #
  # Initialize Evaluators
  #

  arith_ev = sh_expr_eval.ArithEvaluator(mem, exec_opts, parse_ctx, errfmt)
  bool_ev = sh_expr_eval.BoolEvaluator(mem, exec_opts, parse_ctx, errfmt)
  expr_ev = None  # type: expr_eval.OilEvaluator
  word_ev = word_eval.NormalWordEvaluator(mem, exec_opts, mutable_opts,
                                          splitter, errfmt)

  assign_b = InitAssignmentBuiltins(mem, procs, errfmt)
  cmd_ev = cmd_eval.CommandEvaluator(mem, exec_opts, errfmt, procs,
                                     assign_b, arena, cmd_deps)

  shell_ex = executor.ShellExecutor(
      mem, exec_opts, mutable_opts, procs, builtins, search_path,
      ext_prog, waiter, tracer, job_state, fd_state, errfmt)
  #shell_ex = NullExecutor(exec_opts, mutable_opts, procs, builtins)

  # PromptEvaluator rendering is needed in non-interactive shells for @P.
  prompt_ev = prompt.Evaluator(lang, parse_ctx, mem)

  # Wire up circular dependencies.
  vm.InitCircularDeps(arith_ev, bool_ev, expr_ev, word_ev, cmd_ev, shell_ex,
                      prompt_ev, tracer)

  #
  # Initialize builtins that depend on evaluators
  #

  # note: 'printf -v a[i]' and 'unset a[i]' require same deps
  builtins[builtin_i.printf] = builtin_printf.Printf(mem, exec_opts, parse_ctx,
                                                     arith_ev, errfmt)

  builtins[builtin_i.unset] = builtin_assign.Unset(mem, exec_opts, procs,
                                                   parse_ctx, arith_ev, errfmt)
  builtins[builtin_i.eval] = builtin_meta.Eval(parse_ctx, exec_opts, cmd_ev,
                                               tracer)

  #source_builtin = builtin_meta.Source(parse_ctx, search_path, cmd_ev,
                                       #fd_state, tracer, errfmt)
  #builtins[builtin_i.source] = source_builtin
  #builtins[builtin_i.dot] = source_builtin

  AddMeta(builtins, shell_ex, mutable_opts, mem, procs, aliases, search_path,
          errfmt)
  AddBlock(builtins, mem, mutable_opts, dir_stack, cmd_ev, errfmt)

  #builtins[builtin_i.trap] = builtin_process.Trap(sig_state, cmd_deps.traps,
  #                                                cmd_deps.trap_nodes,
  #                                                parse_ctx, errfmt)

  if flag.c is not None:
    arena.PushSource(source.CFlag())
    line_reader = reader.StringLineReader(flag.c, arena)  # type: reader._Reader
    if flag.i:  # -c and -i can be combined
      mutable_opts.set_interactive()

  elif flag.i:  # force interactive
    raise NotImplementedError()

  else:
    if script_name is None:
      stdin = mylib.Stdin()
      arena.PushSource(source.Stdin(''))
      line_reader = reader.FileLineReader(stdin, arena)
    else:
      arena.PushSource(source.MainFile(script_name))
      try:
        f = fd_state.Open(script_name)
        #f = mylib.open(script_name)
      except OSError as e:
        stderr_line("osh: Couldn't open %r: %s", script_name,
                    pyutil.strerror(e))
        return 1
      line_reader = reader.FileLineReader(f, arena)

  # TODO: assert arena.NumSourcePaths() == 1
  # TODO: .rc file needs its own arena.
  c_parser = parse_ctx.MakeOshParser(line_reader)

  if exec_opts.interactive():
    raise NotImplementedError()

  if exec_opts.noexec():
    status = 0
    try:
      node = main_loop.ParseWholeFile(c_parser)
    except error.Parse as e:
      ui.PrettyPrintError(e, arena)
      status = 2

    if status == 0 :
      if flag.parser_mem_dump is not None:  # only valid in -n mode
        input_path = '/proc/%d/status' % posix.getpid()
        pyutil.CopyFile(input_path, flag.parser_mem_dump)

      ui.PrintAst(node, flag)
  else:
    if flag.parser_mem_dump is not None:
      e_usage('--parser-mem-dump can only be used with -n')

    try:
      status = main_loop.Batch(cmd_ev, c_parser, arena,
                               cmd_flags=cmd_eval.IsMainProgram)
    except util.UserExit as e:
      status = e.status
    box = [status]
    cmd_ev.MaybeRunExitTrap(box)
    status = box[0]

  # NOTE: 'exit 1' is ControlFlow and gets here, but subshell/commandsub
  # don't because they call sys.exit().
  if flag.runtime_mem_dump is not None:
    input_path = '/proc/%d/status' % posix.getpid()
    pyutil.CopyFile(input_path, flag.runtime_mem_dump)

  # NOTE: We haven't closed the file opened with fd_state.Open
  return status


class NullExecutor(vm._Executor):
  def __init__(self, exec_opts, mutable_opts, procs, builtins):
    # type: (optview.Exec, state.MutableOpts, Dict[str, Proc], Dict[int, vm._Builtin]) -> None
    vm._Executor.__init__(self)
    self.exec_opts = exec_opts
    self.mutable_opts = mutable_opts
    self.procs = procs
    self.builtins = builtins

  def RunBuiltin(self, builtin_id, cmd_val):
    # type: (int, cmd_value__Argv) -> int
    """Run a builtin.  Also called by the 'builtin' builtin."""

    builtin_func = self.builtins[builtin_id]

    try:
      status = builtin_func.Run(cmd_val)
    except error.Usage as e:
      status = 2
    finally:
      pass
    return status

  def RunSimpleCommand(self, cmd_val, do_fork, call_procs=True):
    # type: (cmd_value__Argv, bool, bool) -> int
    argv = cmd_val.argv
    span_id = cmd_val.arg_spids[0] if len(cmd_val.arg_spids) else runtime.NO_SPID

    arg0 = argv[0]

    builtin_id = consts.LookupSpecialBuiltin(arg0)
    if builtin_id != consts.NO_INDEX:
      return self.RunBuiltin(builtin_id, cmd_val)

    # Copied from core/executor.py
    if call_procs:
      proc_node = self.procs.get(arg0)
      if proc_node is not None:
        if (self.exec_opts.strict_errexit() and 
            self.mutable_opts.ErrExitIsDisabled()):
          # TODO: make errfmt a member
          #self.errfmt.Print_('errexit was disabled for this construct',
          #                   span_id=self.mutable_opts.errexit.spid_stack[0])
          #stderr_line('')
          e_die("Can't run a proc while errexit is disabled. "
                "Use 'catch' or wrap it in a process with $0 myproc",
                span_id=span_id)

        # NOTE: Functions could call 'exit 42' directly, etc.
        status = self.cmd_ev.RunProc(proc_node, argv[1:])
        return status

    builtin_id = consts.LookupNormalBuiltin(arg0)
    if builtin_id != consts.NO_INDEX:
      return self.RunBuiltin(builtin_id, cmd_val)

    # See how many tests will pass
    #if mylib.PYTHON:
    if 0:  # osh_eval.cc will pass 1078 rather than 872 by enabling
      import subprocess
      try:
        status = subprocess.call(cmd_val.argv)
      except OSError as e:
        log('Error running %s: %s', cmd_val.argv, e)
        return 1
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
