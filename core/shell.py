"""
core/shell.py -- Entry point for the shell interpreter.
"""
from __future__ import print_function

from errno import ENOENT
import time

from _devbuild.gen import arg_types
from _devbuild.gen.option_asdl import option_i, builtin_i
from _devbuild.gen.syntax_asdl import source, source_t

from asdl import runtime

from core import alloc
from core import comp_ui
from core import dev
from core import error
from core import executor
from core import completion
from core import main_loop
from core import pyos
from core import process
from core import shell_native
from core import pyutil
from core import state
from core import ui
from core import util
from core.pyerror import log
unused = log
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
from oil_lang import funcs
from oil_lang import funcs_builtin

from osh import builtin_assign
from osh import builtin_comp
from osh import builtin_meta
from osh import builtin_misc
from osh import builtin_lib
from osh import builtin_printf
from osh import builtin_pure
from osh import builtin_trap
from osh import cmd_eval
from osh import glob_
from osh import history
from osh import prompt
from osh import sh_expr_eval
from osh import split
from osh import word_eval

from mycpp import mylib
from mycpp.mylib import print_stderr
from pylib import os_path

import libc

import posix_ as posix

from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import Proc
  from frontend.py_readline import Readline


def _InitDefaultCompletions(cmd_ev, complete_builtin, comp_lookup):
  # type: (cmd_eval.CommandEvaluator, builtin_comp.Complete, completion.Lookup) -> None

  # register builtins and words
  complete_builtin.Run(shell_native.MakeBuiltinArgv(['-E', '-A', 'command']))
  # register path completion
  # Add -o filenames?  Or should that be automatic?
  complete_builtin.Run(shell_native.MakeBuiltinArgv(['-D', '-A', 'file']))

  # TODO: Move this into demo/slow-completion.sh
  if 1:
    # Something for fun, to show off.  Also: test that you don't repeatedly hit
    # the file system / network / coprocess.
    A1 = completion.TestAction(['foo.py', 'foo', 'bar.py'], 0.0)
    l = [] # type: List[str]
    for i in xrange(0, 5):
        l.append('m%d' % i)

    A2 = completion.TestAction(l, 0.1)
    C1 = completion.UserSpec([A1, A2], [], [], completion.DefaultPredicate(), '', '')
    comp_lookup.RegisterName('slowc', {}, C1)


def SourceStartupFile(fd_state, rc_path, lang, parse_ctx, cmd_ev, errfmt):
  # type: (process.FdState, str, str, parse_lib.ParseContext, cmd_eval.CommandEvaluator, ui.ErrorFormatter) -> None

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
    f = fd_state.Open(rc_path)
  except (IOError, OSError) as e:
    # TODO: Could warn about nonexistent explicit --rcfile?
    if e.errno != ENOENT:
      raise  # Goes to top level.  Handle this better?
    return

  arena = parse_ctx.arena
  rc_line_reader = reader.FileLineReader(f, arena)
  rc_c_parser = parse_ctx.MakeOshParser(rc_line_reader)

  with alloc.ctx_Location(arena, source.SourcedFile(rc_path, runtime.NO_SPID)):
    # TODO: handle status, e.g. 2 for ParseError
    status = main_loop.Batch(cmd_ev, rc_c_parser, errfmt)

  f.close()


class ShellOptHook(state.OptHook):

  def __init__(self, readline):
    # type: (Optional[Readline]) -> None
    self.readline = readline

  def OnChange(self, opt0_array, opt_name, b):
    # type: (List[bool], str, bool) -> bool
    """This method is called whenever an option is changed.

    Returns success or failure.
    """
    if opt_name == 'vi' or opt_name == 'emacs':
      # TODO: Replace with a hook?  Just like setting LANG= can have a hook.
      if self.readline:
        self.readline.parse_and_bind("set editing-mode " + opt_name);
      else:
        print_stderr(
            "Warning: Can't set option %r because shell wasn't compiled with GNU readline" % opt_name)
        return False

      # Invert: they are mutually exclusive!
      if opt_name == 'vi':
        opt0_array[option_i.emacs] = not b
      elif opt_name == 'emacs':
        opt0_array[option_i.vi] = not b

    return True


def AddOil(b, mem, search_path, cmd_ev, errfmt, procs, arena):
  # type: (Dict[int, vm._Builtin], state.Mem, state.SearchPath, cmd_eval.CommandEvaluator, ui.ErrorFormatter, Dict[str, Proc], alloc.Arena) -> None

  b[builtin_i.shvar] = builtin_pure.Shvar(mem, search_path, cmd_ev)
  b[builtin_i.push_registers] = builtin_pure.PushRegisters(mem, cmd_ev)
  b[builtin_i.fopen] = builtin_pure.Fopen(mem, cmd_ev)
  b[builtin_i.use] = builtin_pure.Use(mem, errfmt)

  if mylib.PYTHON:
    b[builtin_i.append] = builtin_oil.Append(mem, errfmt)
    b[builtin_i.write] = builtin_oil.Write(mem, errfmt)
    b[builtin_i.pp] = builtin_oil.Pp(mem, errfmt, procs, arena)
    b[builtin_i.argparse] = builtin_oil.ArgParse(mem, errfmt)
    b[builtin_i.describe] = builtin_oil.Describe(mem, errfmt)


def Main(lang, arg_r, environ, login_shell, loader, readline):
  # type: (str, args.Reader, Dict[str, str], bool, pyutil._ResourceLoader, Optional[Readline]) -> int
  """The full shell lifecycle.  Used by bin/osh and bin/oil.

  Args:
    lang: 'osh' or 'oil'
    argv0, arg_r: command line arguments
    environ: environment
    login_shell: Was - on the front?
    loader: to get help, version, grammar, etc.
    readline: optional GNU readline
  """
  # Differences between osh and oil:
  # - --help?  I guess Oil has a SUPERSET of OSH options.
  # - oshrc vs oilrc
  # - shopt -s oil:all
  # - Change the prompt in the interactive shell?

  # osh-pure:
  # - no oil grammar
  # - no expression evaluator
  # - no interactive shell, or readline
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
    print_stderr('osh usage error: %s' % e.msg)
    return 2
  flag = arg_types.main(attrs.attrs)

  arena = alloc.Arena()
  errfmt = ui.ErrorFormatter(arena)

  help_builtin = builtin_misc.Help(loader, errfmt)
  if flag.help:
    help_builtin.Run(shell_native.MakeBuiltinArgv(['%s-usage' % lang]))
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

  opt_hook = ShellOptHook(readline)
  # Note: only MutableOpts needs mem, so it's not a true circular dep.
  parse_opts, exec_opts, mutable_opts = state.MakeOpts(mem, opt_hook)
  mem.exec_opts = exec_opts  # circular dep
  mutable_opts.Init()

  version_str = pyutil.GetVersion(loader)
  state.InitMem(mem, environ, version_str)

  if mylib.PYTHON:
    funcs_builtin.Init(mem)

  procs = {}  # type: Dict[str, Proc]
  hay_state = state.Hay()

  if attrs.show_options:  # special case: sh -o
    mutable_opts.ShowOptions([])
    return 0

  # Set these BEFORE processing flags, so they can be overridden.
  if lang == 'oil':
    mutable_opts.SetAnyOption('oil:all', True)

  builtin_pure.SetOptionsFromFlags(mutable_opts, attrs.opt_changes,
                                   attrs.shopt_changes)

  # feedback between runtime and parser
  aliases = {}  # type: Dict[str, str]

  oil_grammar = pyutil.LoadOilGrammar(loader)

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

  job_state = process.JobState()
  fd_state = process.FdState(errfmt, job_state, mem, None, None)

  my_pid = posix.getpid()

  debug_path = ''
  debug_dir = environ.get('OSH_DEBUG_DIR')
  if flag.debug_file is not None:
    # --debug-file takes precedence over OSH_DEBUG_DIR
    debug_path = flag.debug_file
  elif debug_dir is not None:
    debug_path = os_path.join(debug_dir, '%d-osh.log' % my_pid)

  if len(debug_path):
    # This will be created as an empty file if it doesn't exist, or it could be
    # a pipe.
    try:
      debug_f = util.DebugFile(fd_state.OpenForWrite(debug_path))  # type: util._DebugFile
    except OSError as e:
      print_stderr("osh: Couldn't open %r: %s" %
                   (debug_path, posix.strerror(e.errno)))
      return 2
  else:
    debug_f = util.NullDebugFile()

  if flag.xtrace_to_debug_file:
    trace_f = debug_f
  else:
    trace_f = util.DebugFile(mylib.Stderr())
  tracer = dev.Tracer(parse_ctx, exec_opts, mutable_opts, mem, trace_f)
  fd_state.tracer = tracer  # circular dep

  trap_state = builtin_trap.TrapState()
  trap_state.InitShell()
  waiter = process.Waiter(job_state, exec_opts, trap_state, tracer)
  fd_state.waiter = waiter

  cmd_deps.debug_f = debug_f

  # Not using datetime for dependency reasons.  TODO: maybe show the date at
  # the beginning of the log, and then only show time afterward?  To save
  # space, and make space for microseconds.  (datetime supports microseconds
  # but time.strftime doesn't).
  if mylib.PYTHON:
    iso_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    debug_f.log('%s [%d] OSH started with argv %s', iso_stamp, my_pid, arg_r.argv)
  if len(debug_path):
    debug_f.log('Writing logs to %r', debug_path)

  interp = environ.get('OSH_HIJACK_SHEBANG', '')
  search_path = state.SearchPath(mem)
  ext_prog = process.ExternalProgram(interp, fd_state, errfmt, debug_f)

  splitter = split.SplitContext(mem)
  # TODO: This is instantiation is duplicated in osh/word_eval.py
  globber = glob_.Globber(exec_opts)

  if mylib.PYTHON:
    funcs_builtin.Init2(mem, splitter, globber)

  # This could just be OSH_DEBUG_STREAMS='debug crash' ?  That might be
  # stuffing too much into one, since a .json crash dump isn't a stream.
  crash_dump_dir = environ.get('OSH_CRASH_DUMP_DIR', '')
  cmd_deps.dumper = dev.CrashDumper(crash_dump_dir)

  comp_lookup = completion.Lookup()

  # Various Global State objects to work around readline interfaces
  compopt_state = completion.OptionState()

  comp_ui_state = comp_ui.State()
  prompt_state = comp_ui.PromptState()

  dir_stack = state.DirStack()

  #
  # Initialize builtins that don't depend on evaluators
  #

  builtins = {}  # type: Dict[int, vm._Builtin]
  modules = {}  # type: Dict[str, bool]

  shell_ex = executor.ShellExecutor(
      mem, exec_opts, mutable_opts, procs, hay_state, builtins, search_path,
      ext_prog, waiter, tracer, job_state, fd_state, errfmt)

  shell_native.AddPure(builtins, mem, procs, modules, mutable_opts, aliases,
                       search_path, errfmt)
  shell_native.AddIO(builtins, mem, dir_stack, exec_opts, splitter, parse_ctx,
                     errfmt)
  shell_native.AddProcess(builtins, mem, shell_ex, ext_prog, fd_state,
                          job_state, waiter, tracer, search_path, errfmt)

  builtins[builtin_i.help] = help_builtin

  # Interactive, depend on readline
  builtins[builtin_i.bind] = builtin_lib.Bind(readline, errfmt)
  builtins[builtin_i.history] = builtin_lib.History(readline, mylib.Stdout())

  #
  # Initialize Evaluators
  #

  arith_ev = sh_expr_eval.ArithEvaluator(mem, exec_opts, parse_ctx, errfmt)
  bool_ev = sh_expr_eval.BoolEvaluator(mem, exec_opts, parse_ctx, errfmt)

  if mylib.PYTHON:
    expr_ev = expr_eval.OilEvaluator(mem, mutable_opts, procs, splitter, errfmt)
  else:
    expr_ev = None

  word_ev = word_eval.NormalWordEvaluator(mem, exec_opts, mutable_opts,
                                          splitter, errfmt)

  assign_b = shell_native.InitAssignmentBuiltins(mem, procs, errfmt)
  cmd_ev = cmd_eval.CommandEvaluator(mem, exec_opts, errfmt, procs,
                                     assign_b, arena, cmd_deps, trap_state)

  AddOil(builtins, mem, search_path, cmd_ev, errfmt, procs, arena)

  if mylib.PYTHON:
    parse_config = funcs.ParseHay(fd_state, parse_ctx, errfmt)
    eval_to_dict = funcs.EvalHay(hay_state, mutable_opts, mem, cmd_ev)
    block_as_str = funcs.BlockAsStr(arena)

    hay_func = funcs.HayFunc(hay_state)
    funcs_builtin.Init3(mem, parse_config, eval_to_dict, block_as_str, hay_func)


  # PromptEvaluator rendering is needed in non-interactive shells for @P.
  prompt_ev = prompt.Evaluator(lang, version_str, parse_ctx, mem)

  # Wire up circular dependencies.
  vm.InitCircularDeps(arith_ev, bool_ev, expr_ev, word_ev, cmd_ev, shell_ex,
                      prompt_ev, tracer)

  #
  # Initialize builtins that depend on evaluators
  #

  unsafe_arith = sh_expr_eval.UnsafeArith(mem, exec_opts, parse_ctx, arith_ev,
                                          errfmt)
  vm.InitUnsafeArith(mem, word_ev, unsafe_arith)

  builtins[builtin_i.printf] = builtin_printf.Printf(mem, parse_ctx,
                                                     unsafe_arith, errfmt)
  builtins[builtin_i.unset] = builtin_assign.Unset(mem, procs, unsafe_arith,
                                                   errfmt)
  builtins[builtin_i.eval] = builtin_meta.Eval(parse_ctx, exec_opts, cmd_ev,
                                               tracer, errfmt)
  builtins[builtin_i.read] = builtin_misc.Read(splitter, mem, parse_ctx,
                                               cmd_ev, errfmt)
  mapfile = builtin_misc.MapFile(mem, errfmt, cmd_ev)
  builtins[builtin_i.mapfile] = mapfile
  builtins[builtin_i.readarray] = mapfile

  source_builtin = builtin_meta.Source(parse_ctx, search_path, cmd_ev,
                                       fd_state, tracer, errfmt)
  builtins[builtin_i.source] = source_builtin
  builtins[builtin_i.dot] = source_builtin

  shell_native.AddMeta(builtins, shell_ex, mutable_opts, mem, procs, aliases,
                       search_path, errfmt)
  shell_native.AddBlock(builtins, mem, mutable_opts, dir_stack, cmd_ev,
                        shell_ex, hay_state, errfmt)

  spec_builder = builtin_comp.SpecBuilder(cmd_ev, parse_ctx, word_ev, splitter,
                                          comp_lookup, errfmt)
  complete_builtin = builtin_comp.Complete(spec_builder, comp_lookup)
  builtins[builtin_i.complete] = complete_builtin
  builtins[builtin_i.compgen] = builtin_comp.CompGen(spec_builder)
  builtins[builtin_i.compopt] = builtin_comp.CompOpt(compopt_state, errfmt)
  builtins[builtin_i.compadjust] = builtin_comp.CompAdjust(mem)

  if mylib.PYTHON:
    builtins[builtin_i.json] = builtin_oil.Json(mem, expr_ev, errfmt)

  builtins[builtin_i.trap] = builtin_trap.Trap(trap_state, parse_ctx, tracer, errfmt)

  # History evaluation is a no-op if readline is None.
  hist_ev = history.Evaluator(readline, hist_ctx, debug_f)

  if flag.c is not None:
    src = source.CFlag()  # type: source_t
    line_reader = reader.StringLineReader(flag.c, arena)  # type: reader._Reader
    if flag.i:  # -c and -i can be combined
      mutable_opts.set_interactive()

  elif flag.i:  # force interactive
    src = source.Stdin(' -i')
    if mylib.PYTHON:
      line_reader = py_reader.InteractiveLineReader(
          arena, prompt_ev, hist_ev, readline, prompt_state)
    else:
      line_reader = None
    mutable_opts.set_interactive()

  else:
    if script_name is None:
      if flag.headless:
        src = source.Headless()
        line_reader = None  # unused!
        # Not setting '-i' flag for now.  Some people's bashrc may want it?
      else:
        stdin = mylib.Stdin()
        if stdin.isatty():
          src = source.Interactive()
          if mylib.PYTHON:
            line_reader = py_reader.InteractiveLineReader(
                arena, prompt_ev, hist_ev, readline, prompt_state)
          else:
            line_reader = None
          mutable_opts.set_interactive()
        else:
          src = source.Stdin('')
          line_reader = reader.FileLineReader(stdin, arena)
    else:
      src = source.MainFile(script_name)
      try:
        f = fd_state.Open(script_name)
      except (IOError, OSError) as e:
        print_stderr("osh: Couldn't open %r: %s" %
                     (script_name, posix.strerror(e.errno)))
        return 1
      line_reader = reader.FileLineReader(f, arena)

  # Pretend it came from somewhere else
  if flag.location_str is not None:
    src = source.Synthetic(flag.location_str)
    assert line_reader is not None
    if flag.location_start_line != -1:
      line_reader.SetLineOffset(flag.location_start_line)

  arena.PushSource(src)

  # TODO: assert arena.NumSourcePaths() == 1
  # TODO: .rc file needs its own arena.
  assert line_reader is not None
  c_parser = parse_ctx.MakeOshParser(line_reader)

  # Calculate ~/.config/oil/oshrc or oilrc.  Used for both -i and --headless
  # We avoid cluttering the user's home directory.  Some users may want to ln
  # -s ~/.config/oil/oshrc ~/oshrc or ~/.oshrc.

  # https://unix.stackexchange.com/questions/24347/why-do-some-applications-use-config-appname-for-their-config-data-while-other

  home_dir = pyos.GetMyHomeDir()
  assert home_dir is not None
  rc_path = flag.rcfile
  # mycpp: rewrite of or
  if rc_path is None:
    rc_path = os_path.join(home_dir, '.config/oil/%src' % lang)

  if flag.headless:
    state.InitInteractive(mem)
    mutable_opts.set_redefine_proc()
    mutable_opts.set_redefine_module()

    # This is like an interactive shell, so we copy some initialization from
    # below.  Note: this may need to be tweaked.
    _InitDefaultCompletions(cmd_ev, complete_builtin, comp_lookup)

    # NOTE: called AFTER _InitDefaultCompletions.
    with state.ctx_ThisDir(mem, rc_path):
      try:
        SourceStartupFile(fd_state, rc_path, lang, parse_ctx, cmd_ev, errfmt)
      except util.UserExit as e:
        return e.status

    loop = main_loop.Headless(cmd_ev, parse_ctx, errfmt)
    try:
      # TODO: What other exceptions happen here?
      status = loop.Loop()
    except util.UserExit as e:
      status = e.status

    # Same logic as interactive shell
    box = [status]
    cmd_ev.MaybeRunExitTrap(box)
    status = box[0]

    return status

  if exec_opts.interactive():
    state.InitInteractive(mem)
    # bash: 'set -o emacs' is the default only in the interactive shell
    mutable_opts.set_emacs()
    mutable_opts.set_redefine_proc()
    mutable_opts.set_redefine_module()

    if readline:
      if mylib.PYTHON:
        # NOTE: We're using a different WordEvaluator here.
        ev = word_eval.CompletionWordEvaluator(mem, exec_opts, mutable_opts,
                                               splitter, errfmt)

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
                                        debug_f, readline)  # type: comp_ui._IDisplay
        else:
          display = comp_ui.MinimalDisplay(comp_ui_state, prompt_state, debug_f)

        history_filename = os_path.join(home_dir, '.config/oil/history_%s' % lang)
        comp_ui.InitReadline(readline, history_filename, root_comp, display,
                             debug_f)

        _InitDefaultCompletions(cmd_ev, complete_builtin, comp_lookup)

    else:  # Without readline module
      display = comp_ui.MinimalDisplay(comp_ui_state, prompt_state, debug_f)

    trap_state.InitInteractiveShell(display, my_pid)

    # NOTE: called AFTER _InitDefaultCompletions.
    with state.ctx_ThisDir(mem, rc_path):
      try:
        SourceStartupFile(fd_state, rc_path, lang, parse_ctx, cmd_ev, errfmt)
      except util.UserExit as e:
        return e.status

    assert line_reader is not None
    line_reader.Reset()  # After sourcing startup file, render $PS1

    prompt_plugin = prompt.UserPlugin(mem, parse_ctx, cmd_ev, errfmt)
    try:
      status = main_loop.Interactive(flag, cmd_ev, c_parser, display,
                                     prompt_plugin, errfmt)
    except util.UserExit as e:
      status = e.status

    box = [status]
    cmd_ev.MaybeRunExitTrap(box)
    status = box[0]

    return status

  if flag.rcfile is not None:  # bash doesn't have this warning, but it's useful
    print_stderr('osh warning: --rcfile ignored in non-interactive shell')

  if exec_opts.noexec():
    status = 0
    try:
      node = main_loop.ParseWholeFile(c_parser)
    except error.Parse as e:
      errfmt.PrettyPrintError(e)
      status = 2

    if status == 0 :
      ui.PrintAst(node, flag)
  else:
    with state.ctx_ThisDir(mem, script_name):
      try:
        status = main_loop.Batch(cmd_ev, c_parser, errfmt,
                                 cmd_flags=cmd_eval.IsMainProgram)
      except util.UserExit as e:
        status = e.status
    box = [status]
    cmd_ev.MaybeRunExitTrap(box)
    status = box[0]

  # NOTE: We haven't closed the file opened with fd_state.Open
  return status
