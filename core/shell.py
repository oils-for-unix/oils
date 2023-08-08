"""
core/shell.py -- Entry point for the shell interpreter.
"""
from __future__ import print_function

from errno import ENOENT
import time

from _devbuild.gen import arg_types
from _devbuild.gen.option_asdl import option_i, builtin_i
from _devbuild.gen.runtime_asdl import cmd_value, value, value_e
from _devbuild.gen.syntax_asdl import (loc, source, source_t, IntParamBox,
                                       CompoundWord)

from core import alloc
from core import comp_ui
from core import dev
from core import error
from core import executor
from core import completion
from core import main_loop
from core import pyos
from core import process
from core import pyutil
from core import state
from core import ui
from core import util
from mycpp.mylib import log

unused1 = log
from core import vm

from frontend import args
from frontend import flag_def  # side effect: flags are defined!

unused2 = flag_def
from frontend import flag_spec
from frontend import reader
from frontend import parse_lib

from library import func_cpython
from library import func_hay
from library import func_init
from library import func_misc

from ysh import expr_eval
from ysh import builtin_json
from ysh import builtin_oil

from osh import builtin_assign
from osh import builtin_bracket
from osh import builtin_comp
from osh import builtin_meta
from osh import builtin_misc
from osh import builtin_lib
from osh import builtin_printf
from osh import builtin_process
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
from tools import deps
from tools import ysh_ify

import libc

import posix_ as posix

from typing import List, Dict, Optional, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import Proc
    from core import optview
    from frontend.py_readline import Readline

if mylib.PYTHON:
    try:
        from _devbuild.gen import help_meta  # type: ignore
    except ImportError:
        help_meta = None


def MakeBuiltinArgv(argv1):
    # type: (List[str]) -> cmd_value.Argv
    argv = ['']  # dummy for argv[0]
    argv.extend(argv1)
    missing = None  # type: CompoundWord
    return cmd_value.Argv(argv, [missing] * len(argv), None)


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
        A1 = completion.TestAction(['foo.py', 'foo', 'bar.py'], 0.0)
        l = []  # type: List[str]
        for i in xrange(0, 5):
            l.append('m%d' % i)

        A2 = completion.TestAction(l, 0.1)
        C1 = completion.UserSpec([A1, A2], [], [],
                                 completion.DefaultPredicate(), '', '')
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

    with alloc.ctx_Location(arena, source.SourcedFile(rc_path, loc.Missing)):
        # TODO: handle status, e.g. 2 for ParseError
        unused = main_loop.Batch(cmd_ev, rc_c_parser, errfmt)

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
                self.readline.parse_and_bind("set editing-mode " + opt_name)
            else:
                print_stderr(
                    "Warning: Can't set option %r because shell wasn't compiled with GNU readline"
                    % opt_name)
                return False

            # Invert: they are mutually exclusive!
            if opt_name == 'vi':
                opt0_array[option_i.emacs] = not b
            elif opt_name == 'emacs':
                opt0_array[option_i.vi] = not b

        return True


def AddOil(b, mem, search_path, cmd_ev, expr_ev, errfmt, procs, arena):
    # type: (Dict[int, vm._Builtin], state.Mem, state.SearchPath, cmd_eval.CommandEvaluator, expr_eval.ExprEvaluator, ui.ErrorFormatter, Dict[str, Proc], alloc.Arena) -> None

    b[builtin_i.shvar] = builtin_pure.Shvar(mem, search_path, cmd_ev)
    b[builtin_i.push_registers] = builtin_pure.PushRegisters(mem, cmd_ev)
    b[builtin_i.fopen] = builtin_pure.Fopen(mem, cmd_ev)
    b[builtin_i.use] = builtin_pure.Use(mem, errfmt)

    b[builtin_i.append] = builtin_oil.Append(mem, errfmt)
    b[builtin_i.write] = builtin_oil.Write(mem, errfmt)
    b[builtin_i.pp] = builtin_oil.Pp(mem, errfmt, procs, arena)
    b[builtin_i.error] = builtin_meta.Error(expr_ev)


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
    b[builtin_i.echo] = builtin_pure.Echo(exec_opts)

    b[builtin_i.cat] = builtin_misc.Cat()  # for $(<file)

    # test / [ differ by need_right_bracket
    b[builtin_i.test] = builtin_bracket.Test(False, exec_opts, mem, errfmt)
    b[builtin_i.bracket] = builtin_bracket.Test(True, exec_opts, mem, errfmt)

    b[builtin_i.pushd] = builtin_misc.Pushd(mem, dir_stack, errfmt)
    b[builtin_i.popd] = builtin_misc.Popd(mem, dir_stack, errfmt)
    b[builtin_i.dirs] = builtin_misc.Dirs(mem, dir_stack, errfmt)
    b[builtin_i.pwd] = builtin_misc.Pwd(mem, errfmt)

    b[builtin_i.times] = builtin_misc.Times()


def AddProcess(
        b,  # type: Dict[int, vm._Builtin]
        mem,  # type: state.Mem
        shell_ex,  # type: vm._Executor
        ext_prog,  # type: process.ExternalProgram
        fd_state,  # type: process.FdState
        job_control,  # type: process.JobControl
        job_list,  # type: process.JobList
        waiter,  # type: process.Waiter
        tracer,  # type: dev.Tracer
        search_path,  # type: state.SearchPath
        errfmt  # type: ui.ErrorFormatter
):
    # type: (...) -> None

    # Process
    b[builtin_i.exec_] = builtin_process.Exec(mem, ext_prog, fd_state,
                                              search_path, errfmt)
    b[builtin_i.umask] = builtin_process.Umask()
    b[builtin_i.wait] = builtin_process.Wait(waiter, job_list, mem, tracer,
                                             errfmt)

    b[builtin_i.jobs] = builtin_process.Jobs(job_list)
    b[builtin_i.fg] = builtin_process.Fg(job_control, job_list, waiter)
    b[builtin_i.bg] = builtin_process.Bg(job_list)

    b[builtin_i.fork] = builtin_process.Fork(shell_ex)
    b[builtin_i.forkwait] = builtin_process.ForkWait(shell_ex)


def AddMeta(builtins, shell_ex, mutable_opts, mem, procs, aliases, search_path,
            errfmt):
    # type: (Dict[int, vm._Builtin], vm._Executor, state.MutableOpts, state.Mem, Dict[str, Proc], Dict[str, str], state.SearchPath, ui.ErrorFormatter) -> None
    """Builtins that run more code."""

    builtins[builtin_i.builtin] = builtin_meta.Builtin(shell_ex, errfmt)
    builtins[builtin_i.command] = builtin_meta.Command(shell_ex, procs, aliases,
                                                       search_path)
    builtins[builtin_i.runproc] = builtin_meta.RunProc(shell_ex, procs, errfmt)
    builtins[builtin_i.boolstatus] = builtin_meta.BoolStatus(shell_ex, errfmt)


def AddBlock(builtins, mem, mutable_opts, dir_stack, cmd_ev, shell_ex,
             hay_state, errfmt):
    # type: (Dict[int, vm._Builtin], state.Mem, state.MutableOpts, state.DirStack, cmd_eval.CommandEvaluator, vm._Executor, state.Hay, ui.ErrorFormatter) -> None
    # These builtins take blocks, and thus need cmd_ev.
    builtins[builtin_i.cd] = builtin_misc.Cd(mem, dir_stack, cmd_ev, errfmt)
    builtins[builtin_i.shopt] = builtin_pure.Shopt(mutable_opts, cmd_ev)
    builtins[builtin_i.try_] = builtin_meta.Try(mutable_opts, mem, cmd_ev,
                                                shell_ex, errfmt)
    builtins[builtin_i.hay] = builtin_pure.Hay(hay_state, mutable_opts, mem,
                                               cmd_ev)
    builtins[builtin_i.haynode] = builtin_pure.HayNode(hay_state, mem, cmd_ev)


def AddMethods(methods):
    # type: (Dict[int, Dict[str, vm._Callable]]) -> None
    """Initialize methods table."""
    methods[value_e.Str] = {
        'startswith': func_misc.StartsWith(),
        'strip': func_misc.Strip(),
        'upper': func_misc.Upper(),
    }
    methods[value_e.Dict] = {'keys': func_misc.Keys()}


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


class ShellFiles(object):
    def __init__(self, lang, home_dir, mem, flag):
        # type: (str, str, state.Mem, arg_types.main) -> None
        assert lang in ('osh', 'ysh'), lang
        self.lang = lang
        self.home_dir = home_dir
        self.mem = mem
        self.flag = flag

    def _HistVar(self):
        # type: () -> str
        return 'HISTFILE' if self.lang == 'osh' else 'YSH_HISTFILE'

    def _DefaultHistoryFile(self):
        # type: () -> str
        return os_path.join(self.home_dir,
                            '.local/share/oils/%s_history' % self.lang)

    def InitAfterLoadingEnv(self):
        # type: () -> None

        hist_var = self._HistVar()
        if self.mem.GetValue(hist_var).tag() == value_e.Undef:
            # Note: if the directory doesn't exist, GNU readline ignores
            state.SetGlobalString(self.mem, hist_var,
                                  self._DefaultHistoryFile())

    def HistoryFile(self):
        # type: () -> Optional[str]
        # TODO: In non-strict mode we should try to cast the HISTFILE value to a
        # string following bash's rules

        UP_val = self.mem.GetValue(self._HistVar())
        if UP_val.tag() == value_e.Str:
            val = cast(value.Str, UP_val)
            return val.s
        else:
            # Note: if HISTFILE is an array, bash will return ${HISTFILE[0]}
            return None
            #return self._DefaultHistoryFile()

            # TODO: can we recover line information here?
            #       might be useful to show where HISTFILE was set
            #raise error.Strict("$HISTFILE should only ever be a string", loc.Missing)


def Main(lang, arg_r, environ, login_shell, loader, readline):
    # type: (str, args.Reader, Dict[str, str], bool, pyutil._ResourceLoader, Optional[Readline]) -> int
    """The full shell lifecycle.  Used by bin/osh and bin/oil.

    Args:
      lang: 'osh' or 'ysh'
      argv0, arg_r: command line arguments
      environ: environment
      login_shell: Was - on the front?
      loader: to get help, version, grammar, etc.
      readline: optional GNU readline
    """
    # Differences between osh and ysh:
    # - oshrc vs yshrc
    # - shopt -s ysh:all
    # - Default prompt
    # - --help

    argv0 = arg_r.Peek()
    assert argv0 is not None
    arg_r.Next()

    assert lang in ('osh', 'ysh'), lang

    try:
        attrs = flag_spec.ParseMore('main', arg_r)
    except error.Usage as e:
        print_stderr('%s usage error: %s' % (lang, e.msg))
        return 2
    flag = arg_types.main(attrs.attrs)

    arena = alloc.Arena()
    errfmt = ui.ErrorFormatter()

    if flag.help:
        util.HelpFlag(loader, '%s-usage' % lang, mylib.Stdout())
        return 0
    if flag.version:
        util.VersionFlag(loader, mylib.Stdout())
        return 0

    no_str = None  # type: str

    debug_stack = []  # type: List[state.DebugFrame]
    if arg_r.AtEnd():
        dollar0 = argv0
    else:
        dollar0 = arg_r.Peek()  # the script name, or the arg after -c

        # Copy quirky bash behavior.
        frame0 = state.DebugFrame(dollar0, 'main', no_str, state.LINE_ZERO, 0,
                                  0)
        debug_stack.append(frame0)

    # Copy quirky bash behavior.
    frame1 = state.DebugFrame(no_str, no_str, no_str, None, 0, 0)
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
        func_cpython.Init(mem)

    procs = {}  # type: Dict[str, Proc]

    # TODO: rename funcs module
    # e.g. max() sum() etc.
    funcs = {}  # type: Dict[str, vm._Callable]

    # e.g. s->startswith()
    methods = {}  # type: Dict[int, Dict[str, vm._Callable]]
    AddMethods(methods)

    hay_state = state.Hay()

    if attrs.show_options:  # special case: sh -o
        mutable_opts.ShowOptions([])
        return 0

    # Set these BEFORE processing flags, so they can be overridden.
    if lang == 'ysh':
        mutable_opts.SetAnyOption('ysh:all', True)

    builtin_pure.SetOptionsFromFlags(mutable_opts, attrs.opt_changes,
                                     attrs.shopt_changes)

    # feedback between runtime and parser
    aliases = {}  # type: Dict[str, str]

    oil_grammar = pyutil.LoadOilGrammar(loader)

    if flag.one_pass_parse and not exec_opts.noexec():
        raise error.Usage('--one-pass-parse requires noexec (-n)', loc.Missing)

    # Tools always use one pass parse
    # Note: osh --tool syntax-tree is like osh -n --one-pass-parse
    one_pass_parse = True if len(flag.tool) else flag.one_pass_parse

    parse_ctx = parse_lib.ParseContext(arena,
                                       parse_opts,
                                       aliases,
                                       oil_grammar,
                                       one_pass_parse=one_pass_parse)

    # Three ParseContext instances SHARE aliases.
    comp_arena = alloc.Arena()
    comp_arena.PushSource(source.Unused('completion'))
    trail1 = parse_lib.Trail()
    # one_pass_parse needs to be turned on to complete inside backticks.  TODO:
    # fix the issue where ` gets erased because it's not part of
    # set_completer_delims().
    comp_ctx = parse_lib.ParseContext(comp_arena,
                                      parse_opts,
                                      aliases,
                                      oil_grammar,
                                      one_pass_parse=True)
    comp_ctx.Init_Trail(trail1)

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

    job_control = process.JobControl()
    job_list = process.JobList()
    fd_state = process.FdState(errfmt, job_control, job_list, mem, None, None)

    my_pid = posix.getpid()

    debug_path = ''
    debug_dir = environ.get('OILS_DEBUG_DIR')
    if flag.debug_file is not None:
        # --debug-file takes precedence over OSH_DEBUG_DIR
        debug_path = flag.debug_file
    elif debug_dir is not None:
        debug_path = os_path.join(debug_dir, '%d-osh.log' % my_pid)

    if len(debug_path):
        # This will be created as an empty file if it doesn't exist, or it could be
        # a pipe.
        try:
            debug_f = util.DebugFile(
                fd_state.OpenForWrite(debug_path))  # type: util._DebugFile
        except (IOError, OSError) as e:
            print_stderr("%s: Couldn't open %r: %s" %
                         (lang, debug_path, posix.strerror(e.errno)))
            return 2
    else:
        debug_f = util.NullDebugFile()

    if flag.xtrace_to_debug_file:
        trace_f = debug_f
    else:
        trace_f = util.DebugFile(mylib.Stderr())
    tracer = dev.Tracer(parse_ctx, exec_opts, mutable_opts, mem, trace_f)
    fd_state.tracer = tracer  # circular dep

    signal_safe = pyos.InitSignalSafe()
    trap_state = builtin_trap.TrapState(signal_safe)

    waiter = process.Waiter(job_list, exec_opts, signal_safe, tracer)
    fd_state.waiter = waiter

    cmd_deps.debug_f = debug_f

    # Not using datetime for dependency reasons.  TODO: maybe show the date at
    # the beginning of the log, and then only show time afterward?  To save
    # space, and make space for microseconds.  (datetime supports microseconds
    # but time.strftime doesn't).
    if mylib.PYTHON:
        iso_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        debug_f.writeln('%s [%d] OSH started with argv %s' %
                        (iso_stamp, my_pid, arg_r.argv))
    if len(debug_path):
        debug_f.writeln('Writing logs to %r' % debug_path)

    interp = environ.get('OILS_HIJACK_SHEBANG', '')
    search_path = state.SearchPath(mem)
    ext_prog = process.ExternalProgram(interp, fd_state, errfmt, debug_f)

    splitter = split.SplitContext(mem)
    # TODO: This is instantiation is duplicated in osh/word_eval.py
    globber = glob_.Globber(exec_opts)

    if mylib.PYTHON:
        func_cpython.Init2(mem, splitter, globber)

    # This could just be OILS_DEBUG_STREAMS='debug crash' ?  That might be
    # stuffing too much into one, since a .json crash dump isn't a stream.
    crash_dump_dir = environ.get('OILS_CRASH_DUMP_DIR', '')
    cmd_deps.dumper = dev.CrashDumper(crash_dump_dir)

    comp_lookup = completion.Lookup()

    # Various Global State objects to work around readline interfaces
    compopt_state = completion.OptionState()

    comp_ui_state = comp_ui.State()
    prompt_state = comp_ui.PromptState()

    dir_stack = state.DirStack()

    # The login program is supposed to set $HOME
    # https://superuser.com/questions/271925/where-is-the-home-environment-variable-set
    # state.InitMem(mem) must happen first
    tilde_ev = word_eval.TildeEvaluator(mem, exec_opts)
    home_dir = tilde_ev.GetMyHomeDir()
    if home_dir is None:
        # TODO: print errno from getpwuid()
        print_stderr("%s: Failed to get home dir from $HOME or getpwuid()" %
                     lang)
        return 1

    sh_files = ShellFiles(lang, home_dir, mem, flag)
    sh_files.InitAfterLoadingEnv()

    #
    # Initialize builtins that don't depend on evaluators
    #

    builtins = {}  # type: Dict[int, vm._Builtin]
    modules = {}  # type: Dict[str, bool]

    shell_ex = executor.ShellExecutor(mem, exec_opts, mutable_opts, procs,
                                      hay_state, builtins, search_path,
                                      ext_prog, waiter, tracer, job_control,
                                      job_list, fd_state, trap_state, errfmt)

    AddPure(builtins, mem, procs, modules, mutable_opts, aliases, search_path,
            errfmt)
    AddIO(builtins, mem, dir_stack, exec_opts, splitter, parse_ctx, errfmt)
    AddProcess(builtins, mem, shell_ex, ext_prog, fd_state, job_control,
               job_list, waiter, tracer, search_path, errfmt)

    if mylib.PYTHON:
        if help_meta:
            help_data = help_meta.TopicMetadata()
        else:
            help_data = {}  # minimal build
    else:
        help_data = help_meta.TopicMetadata()
    builtins[builtin_i.help] = builtin_misc.Help(lang, loader, help_data,
                                                 errfmt)

    # Interactive, depend on readline
    builtins[builtin_i.bind] = builtin_lib.Bind(readline, errfmt)
    builtins[builtin_i.history] = builtin_lib.History(readline, sh_files,
                                                      errfmt, mylib.Stdout())

    #
    # Initialize Evaluators
    #

    arith_ev = sh_expr_eval.ArithEvaluator(mem, exec_opts, mutable_opts,
                                           parse_ctx, errfmt)
    bool_ev = sh_expr_eval.BoolEvaluator(mem, exec_opts, mutable_opts,
                                         parse_ctx, errfmt)
    expr_ev = expr_eval.ExprEvaluator(mem, mutable_opts, funcs, methods,
                                     splitter, errfmt)
    word_ev = word_eval.NormalWordEvaluator(mem, exec_opts, mutable_opts,
                                            tilde_ev, splitter, errfmt)

    assign_b = InitAssignmentBuiltins(mem, procs, errfmt)
    cmd_ev = cmd_eval.CommandEvaluator(mem, exec_opts, errfmt, procs, funcs,
                                       assign_b, arena, cmd_deps, trap_state, signal_safe)

    AddOil(builtins, mem, search_path, cmd_ev, expr_ev, errfmt, procs, arena)

    parse_hay = func_hay.ParseHay(fd_state, parse_ctx, errfmt)
    eval_hay = func_hay.EvalHay(hay_state, mutable_opts, mem, cmd_ev)
    block_as_str = func_hay.BlockAsStr(arena)
    hay_func = func_hay.HayFunc(hay_state)

    func_init.SetGlobalFunc(mem, 'parse_hay', parse_hay)
    func_init.SetGlobalFunc(mem, 'eval_hay', eval_hay)
    func_init.SetGlobalFunc(mem, 'block_as_str', block_as_str)
    func_init.SetGlobalFunc(mem, '_hay', hay_func)

    # PromptEvaluator rendering is needed in non-interactive shells for @P.
    prompt_ev = prompt.Evaluator(lang, version_str, parse_ctx, mem)

    # Wire up circular dependencies.
    vm.InitCircularDeps(arith_ev, bool_ev, expr_ev, word_ev, cmd_ev, shell_ex,
                        prompt_ev, tracer)

    #
    # Initialize builtins that depend on evaluators
    #

    unsafe_arith = sh_expr_eval.UnsafeArith(mem, exec_opts, mutable_opts,
                                            parse_ctx, arith_ev, errfmt)
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

    AddMeta(builtins, shell_ex, mutable_opts, mem, procs, aliases, search_path,
            errfmt)
    AddBlock(builtins, mem, mutable_opts, dir_stack, cmd_ev, shell_ex,
             hay_state, errfmt)

    spec_builder = builtin_comp.SpecBuilder(cmd_ev, parse_ctx, word_ev,
                                            splitter, comp_lookup,
                                            help_data, errfmt)
    complete_builtin = builtin_comp.Complete(spec_builder, comp_lookup)
    builtins[builtin_i.complete] = complete_builtin
    builtins[builtin_i.compgen] = builtin_comp.CompGen(spec_builder)
    builtins[builtin_i.compopt] = builtin_comp.CompOpt(compopt_state, errfmt)
    builtins[builtin_i.compadjust] = builtin_comp.CompAdjust(mem)

    builtins[builtin_i.json] = builtin_json.Json(mem, expr_ev, errfmt, False)
    builtins[builtin_i.j8] = builtin_json.Json(mem, expr_ev, errfmt, True)

    builtins[builtin_i.trap] = builtin_trap.Trap(trap_state, parse_ctx, tracer,
                                                 errfmt)

    # History evaluation is a no-op if readline is None.
    hist_ev = history.Evaluator(readline, hist_ctx, debug_f)

    if flag.c is not None:
        src = source.CFlag  # type: source_t
        line_reader = reader.StringLineReader(flag.c,
                                              arena)  # type: reader._Reader
        if flag.i:  # -c and -i can be combined
            mutable_opts.set_interactive()

    elif flag.i:  # force interactive
        src = source.Stdin(' -i')
        line_reader = reader.InteractiveLineReader(arena, prompt_ev, hist_ev,
                                                   readline, prompt_state)
        mutable_opts.set_interactive()

    else:
        if script_name is None:
            if flag.headless:
                src = source.Headless
                line_reader = None  # unused!
                # Not setting '-i' flag for now.  Some people's bashrc may want it?
            else:
                stdin_ = mylib.Stdin()
                # --tool never starts a prompt
                if len(flag.tool) == 0 and stdin_.isatty():
                    src = source.Interactive
                    line_reader = reader.InteractiveLineReader(
                        arena, prompt_ev, hist_ev, readline, prompt_state)
                    mutable_opts.set_interactive()
                else:
                    src = source.Stdin('')
                    line_reader = reader.FileLineReader(stdin_, arena)
        else:
            src = source.MainFile(script_name)
            try:
                f = fd_state.Open(script_name)
            except (IOError, OSError) as e:
                print_stderr("%s: Couldn't open %r: %s" %
                             (lang, script_name, posix.strerror(e.errno)))
                return 1
            line_reader = reader.FileLineReader(f, arena)

    # Pretend it came from somewhere else
    if flag.location_str is not None:
        src = source.Synthetic(flag.location_str)
        assert line_reader is not None
        if flag.location_start_line != -1:
            line_reader.SetLineOffset(flag.location_start_line)

    arena.PushSource(src)

    # Calculate ~/.config/oils/oshrc or yshrc.  Used for both -i and --headless
    # We avoid cluttering the user's home directory.  Some users may want to ln
    # -s ~/.config/oils/oshrc ~/oshrc or ~/.oshrc.

    # https://unix.stackexchange.com/questions/24347/why-do-some-applications-use-config-appname-for-their-config-data-while-other

    config_dir = '.config/oils'
    rc_paths = []  # type: List[str]
    if not flag.norc and (flag.headless or exec_opts.interactive()):
        # User's rcfile comes FIRST.  Later we can add an 'after-rcdir' hook
        rc_path = flag.rcfile
        if rc_path is None:
            rc_paths.append(
                os_path.join(home_dir, '%s/%src' % (config_dir, lang)))
        else:
            rc_paths.append(rc_path)

        # Load all files in ~/.config/oil/oshrc.d or oilrc.d
        # This way "installers" can avoid mutating oshrc directly

        rc_dir = flag.rcdir
        if rc_dir is None:
            rc_dir = os_path.join(home_dir, '%s/%src.d' % (config_dir, lang))

        rc_paths.extend(libc.glob(os_path.join(rc_dir, '*')))
    else:
        if flag.rcfile is not None:  # bash doesn't have this warning, but it's useful
            print_stderr('%s warning: --rcfile ignored with --norc' % lang)
        if flag.rcdir is not None:
            print_stderr('%s warning: --rcdir ignored with --norc' % lang)

    if flag.headless:
        state.InitInteractive(mem)
        mutable_opts.set_redefine_proc_func()
        mutable_opts.set_redefine_module()

        # This is like an interactive shell, so we copy some initialization from
        # below.  Note: this may need to be tweaked.
        _InitDefaultCompletions(cmd_ev, complete_builtin, comp_lookup)

        # NOTE: rc files loaded AFTER _InitDefaultCompletions.
        for rc_path in rc_paths:
            with state.ctx_ThisDir(mem, rc_path):
                try:
                    SourceStartupFile(fd_state, rc_path, lang, parse_ctx,
                                      cmd_ev, errfmt)
                except util.UserExit as e:
                    return e.status

        loop = main_loop.Headless(cmd_ev, parse_ctx, errfmt)
        try:
            # TODO: What other exceptions happen here?
            status = loop.Loop()
        except util.UserExit as e:
            status = e.status

        # Same logic as interactive shell
        mut_status = IntParamBox(status)
        cmd_ev.MaybeRunExitTrap(mut_status)
        status = mut_status.i

        return status

    # Note: headless mode above doesn't use c_parser
    assert line_reader is not None
    c_parser = parse_ctx.MakeOshParser(line_reader)

    if exec_opts.interactive():
        state.InitInteractive(mem)
        # bash: 'set -o emacs' is the default only in the interactive shell
        mutable_opts.set_emacs()
        mutable_opts.set_redefine_proc_func()
        mutable_opts.set_redefine_module()

        if readline:
            # NOTE: We're using a different WordEvaluator here.
            ev = word_eval.CompletionWordEvaluator(mem, exec_opts, mutable_opts,
                                                   tilde_ev, splitter, errfmt)

            ev.arith_ev = arith_ev
            ev.expr_ev = expr_ev
            ev.prompt_ev = prompt_ev
            ev.CheckCircularDeps()

            root_comp = completion.RootCompleter(ev, mem, comp_lookup,
                                                 compopt_state, comp_ui_state,
                                                 comp_ctx, debug_f)

            term_width = 0
            if flag.completion_display == 'nice':
                try:
                    term_width = libc.get_terminal_width()
                except (IOError, OSError):  # stdin not a terminal
                    pass

            if term_width != 0:
                display = comp_ui.NiceDisplay(
                    term_width, comp_ui_state, prompt_state, debug_f, readline,
                    signal_safe)  # type: comp_ui._IDisplay
            else:
                display = comp_ui.MinimalDisplay(comp_ui_state, prompt_state,
                                                 debug_f)

            comp_ui.InitReadline(readline, sh_files.HistoryFile(), root_comp,
                                 display, debug_f)

            _InitDefaultCompletions(cmd_ev, complete_builtin, comp_lookup)

        else:  # Without readline module
            display = comp_ui.MinimalDisplay(comp_ui_state, prompt_state,
                                             debug_f)

        process.InitInteractiveShell()  # Set signal handlers

        # The interactive shell leads a process group which controls the terminal.
        # It MUST give up the terminal afterward, otherwise we get SIGTTIN /
        # SIGTTOU bugs.
        with process.ctx_TerminalControl(job_control, errfmt):

            # NOTE: rc files loaded AFTER _InitDefaultCompletions.
            for rc_path in rc_paths:
                with state.ctx_ThisDir(mem, rc_path):
                    try:
                        SourceStartupFile(fd_state, rc_path, lang, parse_ctx,
                                          cmd_ev, errfmt)
                    except util.UserExit as e:
                        return e.status

            assert line_reader is not None
            line_reader.Reset()  # After sourcing startup file, render $PS1

            prompt_plugin = prompt.UserPlugin(mem, parse_ctx, cmd_ev, errfmt)
            try:
                status = main_loop.Interactive(flag, cmd_ev, c_parser, display,
                                               prompt_plugin, waiter, errfmt)
            except util.UserExit as e:
                status = e.status

            mut_status = IntParamBox(status)
            cmd_ev.MaybeRunExitTrap(mut_status)
            status = mut_status.i

        if readline:
            hist_file = sh_files.HistoryFile()
            if hist_file is not None:
                try:
                    readline.write_history_file(hist_file)
                except (IOError, OSError):
                    pass

        return status

    if flag.rcfile is not None:  # bash doesn't have this warning, but it's useful
        print_stderr('%s warning: --rcfile ignored in non-interactive shell' %
                     lang)
    if flag.rcdir is not None:
        print_stderr('%s warning: --rcdir ignored in non-interactive shell' %
                     lang)

    #
    # Tools that use the OSH/YSH parsing mode, etc.
    #

    # flag.tool is '' if nothing is passed
    # osh --tool syntax-tree is equivalent to osh -n --one-pass-parse
    tool_name = 'syntax-tree' if exec_opts.noexec() else flag.tool

    if len(tool_name):
        arena.SaveTokens()

        try:
            node = main_loop.ParseWholeFile(c_parser)
        except error.Parse as e:
            errfmt.PrettyPrintError(e)
            return 2

        if tool_name == 'syntax-tree':
            ui.PrintAst(node, flag)

        elif tool_name == 'tokens':
            ysh_ify.PrintTokens(arena)

        elif tool_name == 'arena':  # for test/arena.sh
            ysh_ify.PrintArena(arena)

        elif tool_name == 'ysh-ify':
            ysh_ify.PrintAsOil(arena, node)

        elif tool_name == 'deps':
            if mylib.PYTHON:
                deps.Deps(node)

        else:
            raise AssertionError(tool_name)  # flag parser validated it

        return 0

    # 
    # Run a shell script
    # 

    with state.ctx_ThisDir(mem, script_name):
        try:
            status = main_loop.Batch(cmd_ev,
                                     c_parser,
                                     errfmt,
                                     cmd_flags=cmd_eval.IsMainProgram)
        except util.UserExit as e:
            status = e.status
    mut_status = IntParamBox(status)
    cmd_ev.MaybeRunExitTrap(mut_status)

    # NOTE: We haven't closed the file opened with fd_state.Open
    return mut_status.i
