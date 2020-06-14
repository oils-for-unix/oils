#!/usr/bin/env python2
"""
core/main.py -- Entry point for the shell interpreter.
"""
from __future__ import print_function

import errno
import time

from _devbuild.gen.option_asdl import option_i, builtin_i
from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import source
# Hack because we don't want libcmark.so dependency for build/dev.sh minimal
try:
  from _devbuild.gen import help_index  # generated file
except ImportError:
  help_index = None

from asdl import runtime

from core import alloc
from core import comp_ui
from core import dev
from core import error
from core import executor
from core import completion
from core import main_loop
from core import meta
from core import passwd
from core import process
from core import pyutil
from core.pyutil import stderr_line
from core import state
from core import ui
from core import util
from core.util import log
from core import vm

from frontend import args
from frontend import flag_def  # side effect: flags are defined!
_ = flag_def
from frontend import flag_spec
from frontend import reader
from frontend import py_reader
from frontend import parse_lib

from oil_lang import expr_eval
from oil_lang import builtin_oil
from oil_lang import builtin_funcs

from osh import builtin_assign
from osh import builtin_bracket
from osh import builtin_comp
from osh import builtin_meta
from osh import builtin_misc
from osh import builtin_lib
from osh import builtin_printf
from osh import builtin_process
from osh import builtin_pure
from osh import cmd_eval
from osh import glob_
from osh import history
from osh import prompt
from osh import sh_expr_eval
from osh import split
from osh import word_eval

from mycpp import mylib
from pylib import os_path

import libc

import posix_ as posix

from typing import List, Dict, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from _devbuild.gen.syntax_asdl import command__ShFunction


def MakeBuiltinArgv(argv):
  # type: (List[str]) -> cmd_value__Argv
  argv = [''] + argv  # add dummy for argv[0]
  # no location info
  return cmd_value.Argv(argv, [runtime.NO_SPID] * len(argv))


def _InitDefaultCompletions(cmd_ev, complete_builtin, comp_lookup):
  # type: (cmd_eval.CommandEvaluator, builtin_comp.Complete, completion.Lookup) -> None

  # register builtins and words
  complete_builtin.Run(MakeBuiltinArgv(['-E', '-A', 'command']))
  # register path completion
  # Add -o filenames?  Or should that be automatic?
  complete_builtin.Run(MakeBuiltinArgv(['-D', '-A', 'file']))

  # TODO: Move this into demo/slow-completion.sh
  if 1:
    # Something for fun, to show off.  Also: test that you don't repeatedly hit
    # the file system / network / coprocess.
    A1 = completion.TestAction(['foo.py', 'foo', 'bar.py'])
    A2 = completion.TestAction(['m%d' % i for i in xrange(5)], delay=0.1)
    C1 = completion.UserSpec([A1, A2], [], [], lambda candidate: True)
    comp_lookup.RegisterName('slowc', {}, C1)


def ShowVersion(version_str):
  # type: (str) -> None
  pyutil.ShowAppVersion('Oil', version_str)


def SourceStartupFile(rc_path, lang, parse_ctx, cmd_ev):
  # type: (str, str, parse_lib.ParseContext, cmd_eval.CommandEvaluator) -> None

  # Right now this is called when the shell is interactive.  (Maybe it should
  # be called on login_shel too.)
  #
  # Terms:
  # - interactive shell: Roughly speaking, no args or -c, and isatty() is true
  #   for stdin and stdout.
  # - login shell: Started from the top level, e.g. from init or ssh.
  #
  # We're not going to copy everything bash does because it's too complex, but
  # for reference:
  # https://www.gnu.org/software/bash/manual/bash.html#Bash-Startup-Files
  # Bash also has --login.

  try:
    arena = parse_ctx.arena
    with open(rc_path) as f:
      rc_line_reader = reader.FileLineReader(f, arena)
      rc_c_parser = parse_ctx.MakeOshParser(rc_line_reader)

      arena.PushSource(source.SourcedFile(rc_path))
      try:
        # TODO: don't ignore status, e.g. status == 2 when there's a parse error.
        status = main_loop.Batch(cmd_ev, rc_c_parser, arena)
      finally:
        arena.PopSource()
  except IOError as e:
    if e.errno != errno.ENOENT:
      raise


class ShellOptHook(state.OptHook):

  def __init__(self, line_input):
    # type: (Any) -> None
    self.line_input = line_input

  def OnChange(self, opt_array, opt_name, b):
    # type: (List[bool], str, bool) -> bool
    """This method is called whenever an option is changed.

    Returns success or failure.
    """
    if opt_name == 'vi' or opt_name == 'emacs':
      # TODO: Replace with a hook?  Just like setting LANG= can have a hook.
      if self.line_input:
        self.line_input.parse_and_bind("set editing-mode " + opt_name);
      else:
        stderr_line(
            "Warning: Can't set option %r because Oil wasn't built with line editing (e.g. GNU readline)", opt_name)
        return False

      # Invert: they are mutually exclusive!
      if opt_name == 'vi':
        opt_array[option_i.emacs] = not b
      elif opt_name == 'emacs':
        opt_array[option_i.vi] = not b

    return True


def ShellMain(lang, argv0, arg_r, environ, login_shell, line_input):
  # type: (str, str, args.Reader, Dict[str, str], bool, Any) -> int
  """Used by bin/osh and bin/oil.

  Args:
    lang: 'osh' or 'oil'
    argv0, argv: So we can also invoke bin/osh as 'oil.ovm osh'.  Like busybox.
    login_shell: Was - on the front?

  Dependencies for a pure interpreter:
    loader: to get help, version, grammar, etc.
    environ: environment
  Optional:
    line_input: optional GNU readline
    process.{ExternalProgram,Waiter,FdState,JobState,SignalState} -- we want
      to evaluate config files without any of these

  Modules not translated yet: completion, comp_ui, builtin_comp, process
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

  assert lang in ('osh', 'oil'), lang

  try:
    flag = flag_spec.ParseMore('osh', arg_r)
  except error.Usage as e:
    ui.Stderr('osh usage error: %s', e.msg)
    return 2

  # NOTE: This has a side effect of deleting _OVM_* from the environment!
  # TODO: Thread this throughout the program, and get rid of the global
  # variable in core/util.py.  Rename to InitResourceLaoder().  It's now only
  # used for the 'help' builtin and --version.
  loader = pyutil.GetResourceLoader()
  arena = alloc.Arena()
  errfmt = ui.ErrorFormatter(arena)

  help_builtin = builtin_misc.Help(loader, help_index, errfmt)
  if flag.help:
    help_builtin.Run(MakeBuiltinArgv(['%s-usage' % lang]))
    return 0
  version_str = pyutil.GetVersion()
  if flag.version:
    # OSH version is the only binary in Oil right now, so it's all one version.
    ShowVersion(version_str)
    return 0

  no_str = None  # type: str

  debug_stack = []
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
  state.InitMem(mem, environ, version_str)

  builtin_funcs.Init(mem)

  procs = {}  # type: Dict[str, command__ShFunction]

  job_state = process.JobState()
  fd_state = process.FdState(errfmt, job_state, mem)

  opt_hook = ShellOptHook(line_input)
  parse_opts, exec_opts, mutable_opts = state.MakeOpts(mem, opt_hook)
  # TODO: only MutableOpts needs mem, so it's not a true circular dep.
  mem.exec_opts = exec_opts  # circular dep

  if flag.show_options:  # special case: sh -o
    mutable_opts.ShowOptions([])
    return 0

  # Set these BEFORE processing flags, so they can be overridden.
  if lang == 'oil':
    mutable_opts.SetShoptOption('oil:all', True)

  builtin_pure.SetShellOpts(mutable_opts, flag.opt_changes, flag.shopt_changes)
  aliases = {}  # feedback between runtime and parser

  oil_grammar = meta.LoadOilGrammar(loader)

  if flag.one_pass_parse and not exec_opts.noexec():
    raise error.Usage('--one-pass-parse requires noexec (-n)')
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

  waiter = process.Waiter(job_state, exec_opts)

  my_pid = posix.getpid()

  debug_path = ''
  debug_dir = environ.get('OSH_DEBUG_DIR')
  if flag.debug_file:  # --debug-file takes precedence over OSH_DEBUG_DIR
    debug_path = flag.debug_file
  elif debug_dir:
    debug_path = os_path.join(debug_dir, '%d-osh.log' % my_pid)

  if debug_path:
    # This will be created as an empty file if it doesn't exist, or it could be
    # a pipe.
    try:
      debug_f = util.DebugFile(fd_state.Open(debug_path, mode='w'))
    except OSError as e:
      ui.Stderr("osh: Couldn't open %r: %s", debug_path,
                posix.strerror(e.errno))
      return 2
  else:
    debug_f = util.NullDebugFile()

  cmd_deps.debug_f = debug_f

  # Not using datetime for dependency reasons.  TODO: maybe show the date at
  # the beginning of the log, and then only show time afterward?  To save
  # space, and make space for microseconds.  (datetime supports microseconds
  # but time.strftime doesn't).
  iso_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
  debug_f.log('%s [%d] OSH started with argv %s', iso_stamp, my_pid, arg_r.argv)
  if debug_path:
    debug_f.log('Writing logs to %r', debug_path)

  interp = environ.get('OSH_HIJACK_SHEBANG', '')
  search_path = state.SearchPath(mem)
  ext_prog = process.ExternalProgram(interp, fd_state, errfmt, debug_f)

  splitter = split.SplitContext(mem)

  # split() builtin
  # TODO: Accept IFS as a named arg?  split('a b', IFS=' ')
  builtin_funcs.SetGlobalFunc(
      mem, 'split', lambda s, ifs=None: splitter.SplitForWordEval(s, ifs=ifs))

  # glob() builtin
  # TODO: This is instantiation is duplicated in osh/word_eval.py
  globber = glob_.Globber(exec_opts)
  builtin_funcs.SetGlobalFunc(
      mem, 'glob', lambda s: globber.OilFuncCall(s))

  # This could just be OSH_DEBUG_STREAMS='debug crash' ?  That might be
  # stuffing too much into one, since a .json crash dump isn't a stream.
  crash_dump_dir = environ.get('OSH_CRASH_DUMP_DIR', '')
  cmd_deps.dumper = dev.CrashDumper(crash_dump_dir)

  if flag.xtrace_to_debug_file:
    trace_f = debug_f
  else:
    trace_f = util.DebugFile(mylib.Stderr())

  comp_lookup = completion.Lookup()

  # Various Global State objects to work around readline interfaces
  compopt_state = completion.OptionState()
  comp_ui_state = comp_ui.State()
  prompt_state = comp_ui.PromptState()

  dir_stack = state.DirStack()

  new_var = builtin_assign.NewVar(mem, procs, errfmt)
  assign_builtins = {
      # ShAssignment (which are pure)
      builtin_i.declare: new_var,
      builtin_i.typeset: new_var,
      builtin_i.local: new_var,

      builtin_i.export_: builtin_assign.Export(mem, errfmt),
      builtin_i.readonly: builtin_assign.Readonly(mem, errfmt),
  }

  true_ = builtin_pure.Boolean(0)
  mapfile = builtin_misc.MapFile(mem, errfmt)

  builtins = {
      builtin_i.echo: builtin_pure.Echo(exec_opts),
      builtin_i.printf: builtin_printf.Printf(mem, parse_ctx, errfmt),
      builtin_i.mapfile: mapfile,
      builtin_i.readarray: mapfile,

      builtin_i.pushd: builtin_misc.Pushd(mem, dir_stack, errfmt),
      builtin_i.popd: builtin_misc.Popd(mem, dir_stack, errfmt),
      builtin_i.dirs: builtin_misc.Dirs(mem, dir_stack, errfmt),
      builtin_i.pwd: builtin_misc.Pwd(mem, errfmt),

      builtin_i.times: builtin_misc.Times(),
      builtin_i.read: builtin_misc.Read(splitter, mem),
      builtin_i.help: help_builtin,

      builtin_i.cat: builtin_misc.Cat(),  # for $(<file)

      # Completion (more added below)
      builtin_i.compopt: builtin_comp.CompOpt(compopt_state, errfmt),
      builtin_i.compadjust: builtin_comp.CompAdjust(mem),

      # interactive
      builtin_i.bind: builtin_lib.Bind(line_input, errfmt),
      builtin_i.history: builtin_lib.History(line_input, mylib.Stdout()),

      # test / [ differ by need_right_bracket
      builtin_i.test: builtin_bracket.Test(False, exec_opts, mem, errfmt),
      builtin_i.bracket: builtin_bracket.Test(True, exec_opts, mem, errfmt),

      # assign
      builtin_i.shift: builtin_assign.Shift(mem),

      # meta
      builtin_i.type: builtin_meta.Type(procs, aliases, search_path, errfmt),

      # Pure
      builtin_i.set: builtin_pure.Set(mutable_opts, mem),
      builtin_i.shopt: builtin_pure.Shopt(mutable_opts),

      builtin_i.alias: builtin_pure.Alias(aliases, errfmt),
      builtin_i.unalias: builtin_pure.UnAlias(aliases, errfmt),

      builtin_i.hash: builtin_pure.Hash(search_path),
      builtin_i.getopts: builtin_pure.GetOpts(mem, errfmt),

      builtin_i.colon: true_,  # a "special" builtin 
      builtin_i.true_: true_,
      builtin_i.false_: builtin_pure.Boolean(1),

      # Process
      builtin_i.exec_: builtin_process.Exec(mem, ext_prog,
                                            fd_state, search_path,
                                            errfmt),
      builtin_i.wait: builtin_process.Wait(waiter,
                                           job_state, mem, errfmt),
      builtin_i.jobs: builtin_process.Jobs(job_state),
      builtin_i.fg: builtin_process.Fg(job_state, waiter),
      builtin_i.bg: builtin_process.Bg(job_state),
      builtin_i.umask: builtin_process.Umask(),

      # Oil
      builtin_i.push: builtin_oil.Push(mem, errfmt),
      builtin_i.append: builtin_oil.Append(mem, errfmt),

      builtin_i.write: builtin_oil.Write(mem, errfmt),
      builtin_i.getline: builtin_oil.Getline(mem, errfmt),

      builtin_i.repr: builtin_oil.Repr(mem, errfmt),
      builtin_i.use: builtin_oil.Use(mem, errfmt),
      builtin_i.opts: builtin_oil.Opts(mem, errfmt),
  }

  arith_ev = sh_expr_eval.ArithEvaluator(mem, exec_opts, parse_ctx, errfmt)
  bool_ev = sh_expr_eval.BoolEvaluator(mem, exec_opts, parse_ctx, errfmt)
  expr_ev = expr_eval.OilEvaluator(mem, procs, errfmt)
  word_ev = word_eval.NormalWordEvaluator(mem, exec_opts, splitter, errfmt)
  cmd_ev = cmd_eval.CommandEvaluator(mem, exec_opts, errfmt, procs,
                                     assign_builtins, arena, cmd_deps)

  shell_ex = executor.ShellExecutor(
      mem, exec_opts, mutable_opts, procs, builtins, search_path,
      ext_prog, waiter, job_state, fd_state, errfmt)

  # PromptEvaluator rendering is needed in non-interactive shells for @P.
  prompt_ev = prompt.Evaluator(lang, parse_ctx, mem)
  tracer = dev.Tracer(parse_ctx, exec_opts, mutable_opts, mem, word_ev, trace_f)

  # Wire up circular dependencies.
  vm.InitCircularDeps(arith_ev, bool_ev, expr_ev, word_ev, cmd_ev, shell_ex,
                      prompt_ev, tracer)

  #
  # Add builtins that depend on various evaluators
  #

  builtins[builtin_i.unset] = builtin_assign.Unset(mem, exec_opts, procs,
                                                   parse_ctx, arith_ev, errfmt)
  builtins[builtin_i.eval] = builtin_meta.Eval(parse_ctx, exec_opts, cmd_ev)

  source_builtin = builtin_meta.Source(
      parse_ctx, search_path, cmd_ev, fd_state, errfmt)
  builtins[builtin_i.source] = source_builtin
  builtins[builtin_i.dot] = source_builtin

  builtins[builtin_i.builtin] = builtin_meta.Builtin(shell_ex, errfmt)
  builtins[builtin_i.command] = builtin_meta.Command(shell_ex, procs, aliases,
                                                      search_path)

  spec_builder = builtin_comp.SpecBuilder(cmd_ev, parse_ctx, word_ev, splitter,
                                          comp_lookup)
  complete_builtin = builtin_comp.Complete(spec_builder, comp_lookup)
  builtins[builtin_i.complete] = complete_builtin
  builtins[builtin_i.compgen] = builtin_comp.CompGen(spec_builder)

  # These builtins take blocks, and thus need cmd_ev.
  builtins[builtin_i.cd] = builtin_misc.Cd(mem, dir_stack, cmd_ev, errfmt)
  builtins[builtin_i.json] = builtin_oil.Json(mem, cmd_ev, errfmt)

  sig_state = process.SignalState()
  sig_state.InitShell()

  builtins[builtin_i.trap] = builtin_process.Trap(sig_state, cmd_deps.traps,
                                                  cmd_deps.trap_nodes,
                                                  parse_ctx, errfmt)

  # History evaluation is a no-op if line_input is None.
  hist_ev = history.Evaluator(line_input, hist_ctx, debug_f)

  if flag.c is not None:
    arena.PushSource(source.CFlag())
    line_reader = reader.StringLineReader(flag.c, arena)
    if flag.i:  # -c and -i can be combined
      mutable_opts.set_interactive()

  elif flag.i:  # force interactive
    arena.PushSource(source.Stdin(' -i'))
    line_reader = py_reader.InteractiveLineReader(
        arena, prompt_ev, hist_ev, line_input, prompt_state)
    mutable_opts.set_interactive()

  else:
    if script_name is None:
      stdin = mylib.Stdin()
      if stdin.isatty():
        arena.PushSource(source.Interactive())
        line_reader = py_reader.InteractiveLineReader(
            arena, prompt_ev, hist_ev, line_input, prompt_state)
        mutable_opts.set_interactive()
      else:
        arena.PushSource(source.Stdin(''))
        line_reader = reader.FileLineReader(stdin, arena)
    else:
      arena.PushSource(source.MainFile(script_name))
      try:
        f = fd_state.Open(script_name)
      except OSError as e:
        ui.Stderr("osh: Couldn't open %r: %s", script_name,
                  posix.strerror(e.errno))
        return 1
      line_reader = reader.FileLineReader(f, arena)

  # TODO: assert arena.NumSourcePaths() == 1
  # TODO: .rc file needs its own arena.
  c_parser = parse_ctx.MakeOshParser(line_reader)

  if exec_opts.interactive():
    # bash: 'set -o emacs' is the default only in the interactive shell
    mutable_opts.set_emacs()

    # Calculate ~/.config/oil/oshrc or oilrc
    # Use ~/.config/oil to avoid cluttering the user's home directory.  Some
    # users may want to ln -s ~/.config/oil/oshrc ~/oshrc or ~/.oshrc.

    # https://unix.stackexchange.com/questions/24347/why-do-some-applications-use-config-appname-for-their-config-data-while-other
    home_dir = passwd.GetMyHomeDir()
    assert home_dir is not None
    rc_path = flag.rcfile or os_path.join(home_dir, '.config/oil', lang + 'rc')

    history_filename = os_path.join(home_dir, '.config/oil', 'history_' + lang)

    if line_input:
      # NOTE: We're using a different WordEvaluator here.
      ev = word_eval.CompletionWordEvaluator(mem, exec_opts, splitter, errfmt)

      ev.arith_ev = arith_ev
      ev.expr_ev = expr_ev
      ev.prompt_ev = prompt_ev
      ev.CheckCircularDeps()

      root_comp = completion.RootCompleter(ev, mem, comp_lookup, compopt_state,
                                           comp_ui_state, comp_ctx, debug_f)

      term_width = 0
      if flag.completion_display == 'nice':
        try:
          term_width = libc.get_terminal_width()
        except IOError:  # stdin not a terminal
          pass

      if term_width != 0:
        display = comp_ui.NiceDisplay(term_width, comp_ui_state, prompt_state,
                                      debug_f, line_input)
      else:
        display = comp_ui.MinimalDisplay(comp_ui_state, prompt_state, debug_f)

      comp_ui.InitReadline(line_input, history_filename, root_comp, display,
                           debug_f)
      _InitDefaultCompletions(cmd_ev, complete_builtin, comp_lookup)

    else:  # Without readline module
      display = comp_ui.MinimalDisplay(comp_ui_state, prompt_state, debug_f)

    sig_state.InitInteractiveShell(display)

    # NOTE: Call this AFTER _InitDefaultCompletions.
    try:
      SourceStartupFile(rc_path, lang, parse_ctx, cmd_ev)
    except util.UserExit as e:
      return e.status

    line_reader.Reset()  # After sourcing startup file, render $PS1

    prompt_plugin = prompt.UserPlugin(mem, parse_ctx, cmd_ev)
    try:
      status = main_loop.Interactive(flag, cmd_ev, c_parser, display,
                                     prompt_plugin, errfmt)
      if cmd_ev.MaybeRunExitTrap():
        status = cmd_ev.LastStatus()
    except util.UserExit as e:
      status = e.status
    return status

  if exec_opts.noexec():
    status = 0
    try:
      node = main_loop.ParseWholeFile(c_parser)
    except error.Parse as e:
      ui.PrettyPrintError(e, arena)
      status = 2

    if status == 0 :
      if flag.parser_mem_dump:  # only valid in -n mode
        # This might be superstition, but we want to let the value stabilize
        # after parsing.  bash -c 'cat /proc/$$/status' gives different results
        # with a sleep.
        time.sleep(0.001)
        input_path = '/proc/%d/status' % posix.getpid()
        with open(input_path) as f, open(flag.parser_mem_dump, 'w') as f2:
          contents = f.read()
          f2.write(contents)
          log('Wrote %s to %s (--parser-mem-dump)', input_path,
              flag.parser_mem_dump)

      ui.PrintAst(node, flag)
  else:
    if flag.parser_mem_dump:
      raise error.Usage('--parser-mem-dump can only be used with -n')

    try:
      status = main_loop.Batch(cmd_ev, c_parser, arena,
                               cmd_flags=cmd_eval.IsMainProgram)
      if cmd_ev.MaybeRunExitTrap():
        status = cmd_ev.LastStatus()
    except util.UserExit as e:
      status = e.status

  # NOTE: 'exit 1' is ControlFlow and gets here, but subshell/commandsub
  # don't because they call sys.exit().
  if flag.runtime_mem_dump:
    # This might be superstition, but we want to let the value stabilize
    # after parsing.  bash -c 'cat /proc/$$/status' gives different results
    # with a sleep.
    time.sleep(0.001)
    input_path = '/proc/%d/status' % posix.getpid()
    with open(input_path) as f, open(flag.runtime_mem_dump, 'w') as f2:
      contents = f.read()
      f2.write(contents)
      log('Wrote %s to %s (--runtime-mem-dump)', input_path,
          flag.runtime_mem_dump)

  # NOTE: We haven't closed the file opened with fd_state.Open
  return status
