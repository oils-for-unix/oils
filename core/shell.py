"""
core/shell.py -- Entry point for the shell interpreter.
"""
from __future__ import print_function

from errno import ENOENT
import time as time_

from _devbuild.gen import arg_types
from _devbuild.gen.option_asdl import option_i, builtin_i
from _devbuild.gen.syntax_asdl import (loc, source, source_t, IntParamBox,
                                       debug_frame, debug_frame_t)
from _devbuild.gen.value_asdl import (value, value_e, value_t, value_str, Obj)
from core import alloc
from core import comp_ui
from core import dev
from core import error
from core import executor
from core import completion
from core import main_loop
from core import optview
from core import process
from core import pyutil
from core import sh_init
from core import state
from display import ui
from core import util
from core import vm

from frontend import args
from frontend import flag_def  # side effect: flags are defined!

unused1 = flag_def
from frontend import flag_util
from frontend import reader
from frontend import parse_lib

from builtin import assign_osh
from builtin import bracket_osh
from builtin import completion_osh
from builtin import completion_ysh
from builtin import dirs_osh
from builtin import error_ysh
from builtin import hay_ysh
from builtin import io_osh
from builtin import io_ysh
from builtin import json_ysh
from builtin import meta_oils
from builtin import misc_osh
from builtin import module_ysh
from builtin import printf_osh
from builtin import process_osh
from builtin import pure_osh
from builtin import pure_ysh
from builtin import readline_osh
from builtin import read_osh
from builtin import trap_osh

from builtin import func_eggex
from builtin import func_hay
from builtin import func_misc
from builtin import func_reflect

from builtin import method_dict
from builtin import method_io
from builtin import method_list
from builtin import method_other
from builtin import method_str
from builtin import method_type

from osh import cmd_eval
from osh import glob_
from osh import history
from osh import prompt
from osh import sh_expr_eval
from osh import split
from osh import word_eval

from mycpp import iolib
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import NewDict, print_stderr, log
from pylib import os_path
from tools import deps
from tools import fmt
from tools import ysh_ify
from ysh import expr_eval

unused2 = log

import libc
import posix_ as posix

from typing import List, Dict, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from frontend.py_readline import Readline

if mylib.PYTHON:
    try:
        from _devbuild.gen import help_meta  # type: ignore
    except ImportError:
        help_meta = None


def _InitDefaultCompletions(cmd_ev, complete_builtin, comp_lookup):
    # type: (cmd_eval.CommandEvaluator, completion_osh.Complete, completion.Lookup) -> None

    # register builtins and words
    complete_builtin.Run(cmd_eval.MakeBuiltinArgv(['-E', '-A', 'command']))
    # register path completion
    # Add -o filenames?  Or should that be automatic?
    complete_builtin.Run(cmd_eval.MakeBuiltinArgv(['-D', '-A', 'file']))


def _CompletionDemo(comp_lookup):
    # type: (completion.Lookup) -> None

    # Something for fun, to show off.  Also: test that you don't repeatedly hit
    # the file system / network / coprocess.
    A1 = completion.TestAction(['foo.py', 'foo', 'bar.py'], 0.0)
    l = []  # type: List[str]
    for i in xrange(0, 5):
        l.append('m%d' % i)

    A2 = completion.TestAction(l, 0.1)
    C1 = completion.UserSpec([A1, A2], [], [], completion.DefaultPredicate(),
                             '', '')
    comp_lookup.RegisterName('slowc', {}, C1)


def SourceStartupFile(
        fd_state,  # type: process.FdState
        rc_path,  # type: str
        lang,  # type: str
        parse_ctx,  # type: parse_lib.ParseContext
        cmd_ev,  # type: cmd_eval.CommandEvaluator
        errfmt,  # type: ui.ErrorFormatter
):
    # type: (...) -> None

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

    with alloc.ctx_SourceCode(arena, source.MainFile(rc_path)):
        # Note: bash keep going after parse error in startup file.  Should we
        # have a strict mode for this?
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


def _AddBuiltinFunc(mem, name, func):
    # type: (state.Mem, str, vm._Callable) -> None
    assert isinstance(func, vm._Callable), func
    mem.AddBuiltin(name, value.BuiltinFunc(func))


def InitAssignmentBuiltins(
        mem,  # type: state.Mem
        procs,  # type: state.Procs
        exec_opts,  # type: optview.Exec
        arith_ev,  # type: sh_expr_eval.ArithEvaluator
        errfmt,  # type: ui.ErrorFormatter
):
    # type: (...) -> Dict[int, vm._AssignBuiltin]

    assign_b = {}  # type: Dict[int, vm._AssignBuiltin]

    new_var = assign_osh.NewVar(mem, procs, exec_opts, arith_ev, errfmt)
    assign_b[builtin_i.declare] = new_var
    assign_b[builtin_i.typeset] = new_var
    assign_b[builtin_i.local] = new_var

    assign_b[builtin_i.export_] = assign_osh.Export(mem, arith_ev, errfmt)
    assign_b[builtin_i.readonly] = assign_osh.Readonly(mem, arith_ev, errfmt)

    return assign_b


def Main(
        lang,  # type: str
        arg_r,  # type: args.Reader
        environ,  # type: Dict[str, str]
        login_shell,  # type: bool
        loader,  # type: pyutil._ResourceLoader
        readline,  # type: Optional[Readline]
):
    # type: (...) -> int
    """The full shell lifecycle.  Used by bin/osh and bin/ysh.

    Args:
      lang: 'osh' or 'ysh'
      login_shell: Was - on argv[0]?
      loader: to get help, version, grammar, etc.
      readline: optional GNU readline
    """
    # Differences between osh and ysh:
    # - oshrc vs yshrc
    # - shopt -s ysh:all
    # - Prompt
    # - --help

    argv0 = arg_r.Peek()
    assert argv0 is not None
    arg_r.Next()

    assert lang in ('osh', 'ysh'), lang

    try:
        attrs = flag_util.ParseMore('main', arg_r)
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

    if flag.tool == 'cat-em':
        paths = arg_r.Rest()

        status = 0
        for p in paths:
            try:
                contents = loader.Get(p)
                print(contents)
            except (OSError, IOError):
                print_stderr("cat-em: %r not found" % p)
                status = 1
        return status

    script_name = arg_r.Peek()  # type: Optional[str]
    arg_r.Next()

    if script_name is None:
        dollar0 = argv0
        # placeholder for -c or stdin (depending on flag.c)
        frame0 = debug_frame.Dummy  # type: debug_frame_t
    else:
        dollar0 = script_name
        frame0 = debug_frame.MainFile(script_name)

    debug_stack = [frame0]

    argv = arg_r.Rest()
    env_dict = NewDict()  # type: Dict[str, value_t]
    defaults = NewDict()  # type: Dict[str, value_t]
    mem = state.Mem(dollar0,
                    argv,
                    arena,
                    debug_stack,
                    env_dict,
                    defaults=defaults)

    opt_hook = ShellOptHook(readline)
    # Note: only MutableOpts needs mem, so it's not a true circular dep.
    parse_opts, exec_opts, mutable_opts = state.MakeOpts(
        mem, environ, opt_hook)
    mem.exec_opts = exec_opts  # circular dep

    # Set these BEFORE processing flags, so they can be overridden.
    if lang == 'ysh':
        mutable_opts.SetAnyOption('ysh:all', True)

    pure_osh.SetOptionsFromFlags(mutable_opts, attrs.opt_changes,
                                 attrs.shopt_changes)

    version_str = pyutil.GetVersion(loader)
    sh_init.InitBuiltins(mem, version_str, defaults)
    sh_init.InitDefaultVars(mem, argv)

    sh_init.CopyVarsFromEnv(exec_opts, environ, mem)

    # PATH PWD, etc. must be set after CopyVarsFromEnv()
    # Also mutate options from SHELLOPTS, if set
    sh_init.InitVarsAfterEnv(mem, mutable_opts)

    if attrs.show_options:  # special case: sh -o
        pure_osh.ShowOptions(mutable_opts, [])
        return 0

    # feedback between runtime and parser
    aliases = NewDict()  # type: Dict[str, str]

    ysh_grammar = pyutil.LoadYshGrammar(loader)

    if flag.do_lossless and not exec_opts.noexec():
        raise error.Usage('--one-pass-parse requires noexec (-n)', loc.Missing)

    # Tools always use one pass parse
    # Note: osh --tool syntax-tree is like osh -n --one-pass-parse
    do_lossless = True if len(flag.tool) else flag.do_lossless

    parse_ctx = parse_lib.ParseContext(arena,
                                       parse_opts,
                                       aliases,
                                       ysh_grammar,
                                       do_lossless=do_lossless)

    # Three ParseContext instances SHARE aliases.
    comp_arena = alloc.Arena()
    comp_arena.PushSource(source.Unused('completion'))
    trail1 = parse_lib.Trail()
    # do_lossless needs to be turned on to complete inside backticks.  TODO:
    # fix the issue where ` gets erased because it's not part of
    # set_completer_delims().
    comp_ctx = parse_lib.ParseContext(comp_arena,
                                      parse_opts,
                                      aliases,
                                      ysh_grammar,
                                      do_lossless=True)
    comp_ctx.Init_Trail(trail1)

    hist_arena = alloc.Arena()
    hist_arena.PushSource(source.Unused('history'))
    trail2 = parse_lib.Trail()
    hist_ctx = parse_lib.ParseContext(hist_arena, parse_opts, aliases,
                                      ysh_grammar)
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
    fd_state = process.FdState(errfmt, job_control, job_list, mem, None, None,
                               exec_opts)

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

    trace_dir = environ.get('OILS_TRACE_DIR', '')
    dumps = environ.get('OILS_TRACE_DUMPS', '')
    streams = environ.get('OILS_TRACE_STREAMS', '')
    multi_trace = dev.MultiTracer(my_pid, trace_dir, dumps, streams, fd_state)

    tracer = dev.Tracer(parse_ctx, exec_opts, mutable_opts, mem, trace_f,
                        multi_trace)
    fd_state.tracer = tracer  # circular dep

    signal_safe = iolib.InitSignalSafe()
    trap_state = trap_osh.TrapState(signal_safe)

    waiter = process.Waiter(job_list, exec_opts, signal_safe, tracer)
    fd_state.waiter = waiter

    cmd_deps.debug_f = debug_f

    cflow_builtin = cmd_eval.ControlFlowBuiltin(mem, exec_opts, tracer, errfmt)
    cmd_deps.cflow_builtin = cflow_builtin

    now = time_.time()
    iso_stamp = time_.strftime("%Y-%m-%d %H:%M:%S", time_.localtime(now))

    argv_buf = mylib.BufWriter()
    dev.PrintShellArgv(arg_r.argv, argv_buf)

    debug_f.writeln('%s [%d] Oils started with argv %s' %
                    (iso_stamp, my_pid, argv_buf.getvalue()))
    if len(debug_path):
        debug_f.writeln('Writing logs to %r' % debug_path)

    interp = environ.get('OILS_HIJACK_SHEBANG', '')
    search_path = executor.SearchPath(mem, exec_opts)
    ext_prog = process.ExternalProgram(interp, fd_state, errfmt, debug_f)

    splitter = split.SplitContext(mem)
    # TODO: This is instantiation is duplicated in osh/word_eval.py
    globber = glob_.Globber(exec_opts)

    # This could just be OILS_TRACE_DUMPS='crash:argv0'
    crash_dump_dir = environ.get('OILS_CRASH_DUMP_DIR', '')
    cmd_deps.dumper = dev.CrashDumper(crash_dump_dir, fd_state)

    comp_lookup = completion.Lookup()

    # Various Global State objects to work around readline interfaces
    compopt_state = completion.OptionState()

    comp_ui_state = comp_ui.State()
    prompt_state = comp_ui.PromptState()

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

    sh_files = sh_init.ShellFiles(lang, home_dir, mem, flag)

    #
    # Executor and Evaluators (are circularly dependent)
    #

    # Global proc namespace.  Funcs are defined in the common variable
    # namespace.
    procs = state.Procs(mem)  # type: state.Procs

    builtins = {}  # type: Dict[int, vm._Builtin]

    # e.g. s.startswith()
    methods = {}  # type: Dict[int, Dict[str, vm._Callable]]

    hay_state = hay_ysh.HayState()

    shell_ex = executor.ShellExecutor(mem, exec_opts, mutable_opts, procs,
                                      hay_state, builtins, tracer, errfmt,
                                      search_path, ext_prog, waiter,
                                      job_control, job_list, fd_state,
                                      trap_state)

    pure_ex = executor.PureExecutor(mem, exec_opts, mutable_opts, procs,
                                    hay_state, builtins, tracer, errfmt)

    arith_ev = sh_expr_eval.ArithEvaluator(mem, exec_opts, mutable_opts,
                                           parse_ctx, errfmt)
    bool_ev = sh_expr_eval.BoolEvaluator(mem, exec_opts, mutable_opts,
                                         parse_ctx, errfmt)
    expr_ev = expr_eval.ExprEvaluator(mem, mutable_opts, methods, splitter,
                                      errfmt)
    word_ev = word_eval.NormalWordEvaluator(mem, exec_opts, mutable_opts,
                                            tilde_ev, splitter, errfmt)

    assign_b = InitAssignmentBuiltins(mem, procs, exec_opts, arith_ev, errfmt)
    cmd_ev = cmd_eval.CommandEvaluator(mem, exec_opts, errfmt, procs, assign_b,
                                       arena, cmd_deps, trap_state,
                                       signal_safe)

    # PromptEvaluator rendering is needed in non-interactive shells for @P.
    prompt_ev = prompt.Evaluator(lang, version_str, parse_ctx, mem)

    io_methods = NewDict()  # type: Dict[str, value_t]
    io_methods['promptVal'] = value.BuiltinFunc(method_io.PromptVal(prompt_ev))

    # The M/ prefix means it's io->eval()
    io_methods['M/eval'] = value.BuiltinFunc(
        method_io.Eval(mem, cmd_ev, None, method_io.EVAL_NULL))
    io_methods['M/evalExpr'] = value.BuiltinFunc(
        method_io.EvalExpr(expr_ev, None, None))

    # Identical to command sub
    io_methods['captureStdout'] = value.BuiltinFunc(
        method_io.CaptureStdout(mem, shell_ex))

    # TODO: remove these 2 deprecated methods
    io_methods['M/evalToDict'] = value.BuiltinFunc(
        method_io.Eval(mem, cmd_ev, None, method_io.EVAL_DICT))
    io_methods['M/evalInFrame'] = value.BuiltinFunc(
        method_io.EvalInFrame(mem, cmd_ev))

    # TODO:
    io_methods['time'] = value.BuiltinFunc(method_io.Time())
    io_methods['strftime'] = value.BuiltinFunc(method_io.Strftime())
    io_methods['glob'] = value.BuiltinFunc(method_io.Glob())

    io_props = {'stdin': value.Stdin}  # type: Dict[str, value_t]
    io_obj = Obj(Obj(None, io_methods), io_props)

    vm_methods = NewDict()  # type: Dict[str, value_t]
    # These are methods, not free functions, because they reflect VM state
    vm_methods['getFrame'] = value.BuiltinFunc(func_reflect.GetFrame(mem))
    vm_methods['getDebugStack'] = value.BuiltinFunc(
        func_reflect.GetDebugStack(mem))
    vm_methods['id'] = value.BuiltinFunc(func_reflect.Id())

    vm_props = NewDict()  # type: Dict[str, value_t]
    vm_obj = Obj(Obj(None, vm_methods), vm_props)

    # Add basic type objects for flag parser
    # flag -v --verbose (Bool, help='foo')
    #
    # TODO:
    # - Add other types like Dict, CommandFlag
    #   - Obj(first, rest)
    #   - List() Dict() Obj() can do shallow copy with __call__

    # - type(x) should return these Obj, or perhaps typeObj(x)
    #   - __str__ method for echo $[type(x)] ?

    # TODO: List and Dict could be the only ones with __index__?
    i_func = method_type.Index__()
    type_m = NewDict()  # type: Dict[str, value_t]
    type_m['__index__'] = value.BuiltinFunc(i_func)
    type_obj_methods = Obj(None, type_m)

    # Note: Func[Int -> Int] is something we should do?
    for tag in [
            value_e.Bool,
            value_e.Int,
            value_e.Float,
            value_e.Str,
            value_e.List,
            value_e.Dict,
    ]:
        type_name = value_str(tag, dot=False)
        #log('%s %s' , type_name, tag)
        type_obj = Obj(type_obj_methods, {'name': value.Str(type_name)})
        mem.AddBuiltin(type_name, type_obj)

    # Initialize Obj
    tag = value_e.Obj
    type_name = value_str(tag, dot=False)

    # TODO: change Obj.new to __call__
    type_props = NewDict()  # type: Dict[str, value_t]
    type_props['name'] = value.Str(type_name)
    type_props['new'] = value.BuiltinFunc(func_misc.Obj_call())
    type_obj = Obj(type_obj_methods, type_props)

    mem.AddBuiltin(type_name, type_obj)

    # Wire up circular dependencies.
    vm.InitCircularDeps(arith_ev, bool_ev, expr_ev, word_ev, cmd_ev, shell_ex,
                        pure_ex, prompt_ev, io_obj, tracer)

    unsafe_arith = sh_expr_eval.UnsafeArith(mem, exec_opts, mutable_opts,
                                            parse_ctx, arith_ev, errfmt)
    vm.InitUnsafeArith(mem, word_ev, unsafe_arith)

    #
    # Initialize Built-in Procs
    #

    b = builtins  # short alias for initialization

    if mylib.PYTHON:
        if help_meta:
            help_data = help_meta.TopicMetadata()
        else:
            help_data = NewDict()  # minimal build
    else:
        help_data = help_meta.TopicMetadata()
    b[builtin_i.help] = misc_osh.Help(lang, loader, help_data, errfmt)

    # Control flow
    b[builtin_i.break_] = cflow_builtin
    b[builtin_i.continue_] = cflow_builtin
    b[builtin_i.return_] = cflow_builtin
    b[builtin_i.exit] = cflow_builtin

    # Interpreter state
    b[builtin_i.set] = pure_osh.Set(mutable_opts, mem)
    b[builtin_i.shopt] = pure_osh.Shopt(exec_opts, mutable_opts, cmd_ev, mem,
                                        environ)

    b[builtin_i.hash] = pure_osh.Hash(search_path)  # not really pure
    b[builtin_i.trap] = trap_osh.Trap(trap_state, parse_ctx, tracer, errfmt)

    b[builtin_i.shvar] = pure_ysh.Shvar(mem, search_path, cmd_ev)
    b[builtin_i.ctx] = pure_ysh.Ctx(mem, cmd_ev)
    b[builtin_i.push_registers] = pure_ysh.PushRegisters(mem, cmd_ev)

    # Hay
    b[builtin_i.hay] = hay_ysh.Hay(hay_state, mutable_opts, mem, cmd_ev)
    b[builtin_i.haynode] = hay_ysh.HayNode_(hay_state, mem, cmd_ev)

    # Interpreter introspection
    b[builtin_i.type] = meta_oils.Type(procs, aliases, search_path, errfmt)
    b[builtin_i.builtin] = meta_oils.Builtin(shell_ex, errfmt)
    b[builtin_i.command] = meta_oils.Command(shell_ex, procs, aliases,
                                             search_path)
    # Part of YSH, but similar to builtin/command
    b[builtin_i.runproc] = meta_oils.RunProc(shell_ex, procs, errfmt)
    b[builtin_i.invoke] = meta_oils.Invoke(shell_ex, procs, errfmt)
    b[builtin_i.extern_] = meta_oils.Extern(shell_ex, procs, errfmt)

    # Meta builtins
    module_invoke = module_ysh.ModuleInvoke(cmd_ev, tracer, errfmt)
    b[builtin_i.use] = meta_oils.ShellFile(parse_ctx,
                                           search_path,
                                           cmd_ev,
                                           fd_state,
                                           tracer,
                                           errfmt,
                                           loader,
                                           module_invoke=module_invoke)
    source_builtin = meta_oils.ShellFile(parse_ctx, search_path, cmd_ev,
                                         fd_state, tracer, errfmt, loader)
    b[builtin_i.source] = source_builtin
    b[builtin_i.dot] = source_builtin
    eval_builtin = meta_oils.Eval(parse_ctx, exec_opts, cmd_ev, tracer, errfmt,
                                  mem)
    b[builtin_i.eval] = eval_builtin

    # Module builtins
    guards = NewDict()  # type: Dict[str, bool]
    b[builtin_i.source_guard] = module_ysh.SourceGuard(guards, exec_opts,
                                                       errfmt)
    b[builtin_i.is_main] = module_ysh.IsMain(mem)

    # Errors
    b[builtin_i.error] = error_ysh.Error()
    b[builtin_i.failed] = error_ysh.Failed(mem)
    b[builtin_i.boolstatus] = error_ysh.BoolStatus(shell_ex, errfmt)
    b[builtin_i.try_] = error_ysh.Try(mutable_opts, mem, cmd_ev, shell_ex,
                                      errfmt)
    b[builtin_i.assert_] = error_ysh.Assert(expr_ev, errfmt)

    # Pure builtins
    true_ = pure_osh.Boolean(0)
    b[builtin_i.colon] = true_  # a "special" builtin
    b[builtin_i.true_] = true_
    b[builtin_i.false_] = pure_osh.Boolean(1)

    b[builtin_i.alias] = pure_osh.Alias(aliases, errfmt)
    b[builtin_i.unalias] = pure_osh.UnAlias(aliases, errfmt)

    b[builtin_i.getopts] = pure_osh.GetOpts(mem, errfmt)

    b[builtin_i.shift] = assign_osh.Shift(mem)
    b[builtin_i.unset] = assign_osh.Unset(mem, procs, unsafe_arith, errfmt)

    b[builtin_i.append] = pure_ysh.Append(mem, errfmt)

    # test / [ differ by need_right_bracket
    b[builtin_i.test] = bracket_osh.Test(False, exec_opts, mem, errfmt)
    b[builtin_i.bracket] = bracket_osh.Test(True, exec_opts, mem, errfmt)

    # Output
    b[builtin_i.echo] = io_osh.Echo(exec_opts)
    b[builtin_i.printf] = printf_osh.Printf(mem, parse_ctx, unsafe_arith,
                                            errfmt)
    b[builtin_i.write] = io_ysh.Write(mem, errfmt)
    redir_builtin = io_ysh.RunBlock(mem, cmd_ev)  # used only for redirects
    b[builtin_i.redir] = redir_builtin
    b[builtin_i.fopen] = redir_builtin  # alias for backward compatibility

    # (pp output format isn't stable)
    b[builtin_i.pp] = io_ysh.Pp(expr_ev, mem, errfmt, procs, arena)

    # Input
    b[builtin_i.cat] = io_osh.Cat()  # for $(<file)
    b[builtin_i.read] = read_osh.Read(splitter, mem, parse_ctx, cmd_ev, errfmt)

    mapfile = io_osh.MapFile(mem, errfmt, cmd_ev)
    b[builtin_i.mapfile] = mapfile
    b[builtin_i.readarray] = mapfile

    # Dirs
    dir_stack = dirs_osh.DirStack()
    b[builtin_i.cd] = dirs_osh.Cd(mem, dir_stack, cmd_ev, errfmt)
    b[builtin_i.pushd] = dirs_osh.Pushd(mem, dir_stack, errfmt)
    b[builtin_i.popd] = dirs_osh.Popd(mem, dir_stack, errfmt)
    b[builtin_i.dirs] = dirs_osh.Dirs(mem, dir_stack, errfmt)
    b[builtin_i.pwd] = dirs_osh.Pwd(mem, errfmt)

    b[builtin_i.times] = misc_osh.Times()

    b[builtin_i.json] = json_ysh.Json(mem, errfmt, False)
    b[builtin_i.json8] = json_ysh.Json(mem, errfmt, True)

    ### Process builtins
    b[builtin_i.exec_] = process_osh.Exec(mem, ext_prog, fd_state, search_path,
                                          errfmt)
    b[builtin_i.umask] = process_osh.Umask()
    b[builtin_i.ulimit] = process_osh.Ulimit()
    b[builtin_i.wait] = process_osh.Wait(waiter, job_list, mem, tracer, errfmt)

    b[builtin_i.jobs] = process_osh.Jobs(job_list)
    b[builtin_i.fg] = process_osh.Fg(job_control, job_list, waiter)
    b[builtin_i.bg] = process_osh.Bg(job_list)

    # Could be in process_ysh
    b[builtin_i.fork] = process_osh.Fork(shell_ex)
    b[builtin_i.forkwait] = process_osh.ForkWait(shell_ex)

    # Interactive builtins depend on readline
    bindx_cb = readline_osh.BindXCallback(eval_builtin)
    b[builtin_i.bind] = readline_osh.Bind(readline, errfmt, mem, bindx_cb)
    b[builtin_i.history] = readline_osh.History(readline, sh_files, errfmt,
                                                mylib.Stdout())

    # Completion
    spec_builder = completion_osh.SpecBuilder(cmd_ev, parse_ctx, word_ev,
                                              splitter, comp_lookup, help_data,
                                              errfmt)
    complete_builtin = completion_osh.Complete(spec_builder, comp_lookup)
    b[builtin_i.complete] = complete_builtin
    b[builtin_i.compgen] = completion_osh.CompGen(spec_builder)
    b[builtin_i.compopt] = completion_osh.CompOpt(compopt_state, errfmt)
    b[builtin_i.compadjust] = completion_osh.CompAdjust(mem)

    comp_ev = word_eval.CompletionWordEvaluator(mem, exec_opts, mutable_opts,
                                                tilde_ev, splitter, errfmt)

    comp_ev.arith_ev = arith_ev
    comp_ev.expr_ev = expr_ev
    comp_ev.prompt_ev = prompt_ev
    comp_ev.CheckCircularDeps()

    root_comp = completion.RootCompleter(comp_ev, mem, comp_lookup,
                                         compopt_state, comp_ui_state,
                                         comp_ctx, debug_f)
    b[builtin_i.compexport] = completion_ysh.CompExport(root_comp)

    #
    # Initialize Builtin-in Methods
    #

    methods[value_e.Str] = {
        'startsWith': method_str.HasAffix(method_str.START),
        'endsWith': method_str.HasAffix(method_str.END),
        'trim': method_str.Trim(method_str.START | method_str.END),
        'trimStart': method_str.Trim(method_str.START),
        'trimEnd': method_str.Trim(method_str.END),
        'upper': method_str.Upper(),
        'lower': method_str.Lower(),
        'split': method_str.Split(),
        'lines': method_str.Lines(),

        # finds a substring, optional position to start at
        'find': None,

        # replace substring, OR an eggex
        # takes count=3, the max number of replacements to do.
        'replace': method_str.Replace(mem, expr_ev),

        # Like Python's re.search, except we put it on the string object
        # It's more consistent with Str->find(substring, pos=0)
        # It returns value.Match() rather than an integer
        'search': method_str.SearchMatch(method_str.SEARCH),

        # like Python's re.match()
        'leftMatch': method_str.SearchMatch(method_str.LEFT_MATCH),

        # like Python's re.fullmatch(), not sure if we really need it
        'fullMatch': None,
    }
    methods[value_e.Dict] = {
        # keys() values() get() are FREE functions, not methods
        # I think items() isn't as necessary because dicts are ordered?  YSH
        # code shouldn't use the List of Lists representation.
        'M/erase': method_dict.Erase(),
        # could be d->tally() or d->increment(), but inc() is short
        #
        # call d->inc('mycounter')
        # call d->inc('mycounter', 3)
        'M/inc': None,

        # call d->accum('mygroup', 'value')
        'M/accum': None,

        # DEPRECATED - use free functions
        'get': method_dict.Get(),
        'keys': method_dict.Keys(),
        'values': method_dict.Values(),
    }
    methods[value_e.List] = {
        'M/reverse': method_list.Reverse(),
        'M/append': method_list.Append(),
        'M/clear': method_list.Clear(),
        'M/extend': method_list.Extend(),
        'M/pop': method_list.Pop(),
        'M/insert': method_list.Insert(),
        'M/remove': method_list.Remove(),
        'indexOf': method_list.IndexOf(),  # return first index of value, or -1
        # Python list() has index(), which raises ValueError
        # But this is consistent with Str->find(), and doesn't
        # use exceptions
        'lastIndexOf': method_list.LastIndexOf(),
        'join': func_misc.Join(),  # both a method and a func
    }

    methods[value_e.Match] = {
        'group': func_eggex.MatchMethod(func_eggex.G, expr_ev),
        'start': func_eggex.MatchMethod(func_eggex.S, None),
        'end': func_eggex.MatchMethod(func_eggex.E, None),
    }

    methods[value_e.Place] = {
        # __mut_setValue()

        # instead of setplace keyword
        'M/setValue': method_other.SetValue(mem),
    }

    methods[value_e.Command] = {
        # var x = ^(echo hi)
        # p { echo hi }
        # Export source code and location
        # Useful for test frameworks, built systems and so forth
        'sourceCode': method_other.SourceCode(),
    }

    methods[value_e.DebugFrame] = {
        'toString': func_reflect.DebugFrameToString(),
    }

    #
    # Initialize Built-in Funcs
    #

    # Pure functions
    _AddBuiltinFunc(mem, 'eval',
                    method_io.Eval(mem, cmd_ev, pure_ex, method_io.EVAL_NULL))
    _AddBuiltinFunc(mem, 'evalExpr',
                    method_io.EvalExpr(expr_ev, pure_ex, cmd_ev))

    parse_hay = func_hay.ParseHay(fd_state, parse_ctx, mem, errfmt)
    eval_hay = func_hay.EvalHay(hay_state, mutable_opts, mem, cmd_ev)
    hay_func = func_hay.HayFunc(hay_state)

    _AddBuiltinFunc(mem, 'parseHay', parse_hay)
    _AddBuiltinFunc(mem, 'evalHay', eval_hay)
    _AddBuiltinFunc(mem, '_hay', hay_func)

    _AddBuiltinFunc(mem, 'len', func_misc.Len())
    _AddBuiltinFunc(mem, 'type', func_misc.Type())

    g = func_eggex.MatchFunc(func_eggex.G, expr_ev, mem)
    _AddBuiltinFunc(mem, '_group', g)
    _AddBuiltinFunc(mem, '_match',
                    g)  # TODO: remove this backward compat alias
    _AddBuiltinFunc(mem, '_start',
                    func_eggex.MatchFunc(func_eggex.S, None, mem))
    _AddBuiltinFunc(mem, '_end', func_eggex.MatchFunc(func_eggex.E, None, mem))

    # TODO: should this be parseCommandStr() vs. parseFile() for Hay?
    _AddBuiltinFunc(mem, 'parseCommand',
                    func_reflect.ParseCommand(parse_ctx, mem, errfmt))
    _AddBuiltinFunc(mem, 'parseExpr',
                    func_reflect.ParseExpr(parse_ctx, errfmt))

    _AddBuiltinFunc(mem, 'shvarGet', func_reflect.Shvar_get(mem))
    _AddBuiltinFunc(mem, 'getVar', func_reflect.GetVar(mem))
    _AddBuiltinFunc(mem, 'setVar', func_reflect.SetVar(mem))

    # TODO: implement bindFrame() to turn CommandFrag -> Command
    # Then parseCommand() and parseHay() will not depend on mem; they will not
    # bind a frame yet
    #
    # what about newFrame() and globalFrame()?
    _AddBuiltinFunc(mem, 'bindFrame', func_reflect.BindFrame())

    _AddBuiltinFunc(mem, 'Object', func_misc.Object())

    _AddBuiltinFunc(mem, 'rest', func_misc.Prototype())
    _AddBuiltinFunc(mem, 'first', func_misc.PropView())

    # TODO: remove these aliases
    _AddBuiltinFunc(mem, 'prototype', func_misc.Prototype())
    _AddBuiltinFunc(mem, 'propView', func_misc.PropView())

    # type conversions
    _AddBuiltinFunc(mem, 'bool', func_misc.Bool())
    _AddBuiltinFunc(mem, 'int', func_misc.Int())
    _AddBuiltinFunc(mem, 'float', func_misc.Float())
    _AddBuiltinFunc(mem, 'str', func_misc.Str_())
    _AddBuiltinFunc(mem, 'list', func_misc.List_())
    _AddBuiltinFunc(mem, 'dict', func_misc.DictFunc())

    # Dict functions
    _AddBuiltinFunc(mem, 'get', method_dict.Get())
    _AddBuiltinFunc(mem, 'keys', method_dict.Keys())
    _AddBuiltinFunc(mem, 'values', method_dict.Values())

    _AddBuiltinFunc(mem, 'runes', func_misc.Runes())
    _AddBuiltinFunc(mem, 'encodeRunes', func_misc.EncodeRunes())
    _AddBuiltinFunc(mem, 'bytes', func_misc.Bytes())
    _AddBuiltinFunc(mem, 'encodeBytes', func_misc.EncodeBytes())

    # Str
    #_AddBuiltinFunc(mem, 'strcmp', None)
    # TODO: This should be Python style splitting
    _AddBuiltinFunc(mem, 'split', func_misc.Split(splitter))
    _AddBuiltinFunc(mem, 'shSplit', func_misc.Split(splitter))

    # Float
    _AddBuiltinFunc(mem, 'floatsEqual', func_misc.FloatsEqual())

    # List
    _AddBuiltinFunc(mem, 'join', func_misc.Join())
    _AddBuiltinFunc(mem, 'maybe', func_misc.Maybe())
    _AddBuiltinFunc(mem, 'glob', func_misc.Glob(globber))

    # Serialize
    _AddBuiltinFunc(mem, 'toJson8', func_misc.ToJson8(True))
    _AddBuiltinFunc(mem, 'toJson', func_misc.ToJson8(False))

    _AddBuiltinFunc(mem, 'fromJson8', func_misc.FromJson8(True))
    _AddBuiltinFunc(mem, 'fromJson', func_misc.FromJson8(False))

    mem.AddBuiltin('io', io_obj)
    mem.AddBuiltin('vm', vm_obj)

    # Special case for testing
    mem.AddBuiltin('module-invoke', value.BuiltinProc(module_invoke))

    # First, process --eval flags.  In interactive mode, this comes before --rcfile.
    # (It could be used for the headless shell.  Although terminals have a bootstrap process.)
    # Note that --eval

    for path, is_pure in attrs.eval_flags:
        ex = pure_ex if is_pure else None
        with vm.ctx_MaybePure(ex, cmd_ev):
            try:
                ok, status = main_loop.EvalFile(path, fd_state, parse_ctx,
                                                cmd_ev, lang)
            except util.UserExit as e:
                # Doesn't seem like we need this, and verbose_errexit isn't the right option
                #if exec_opts.verbose_errexit():
                #    print-stderr('oils: --eval exit')
                return e.status

        # I/O error opening file, parse error.  Message was # already printed.
        if not ok:
            return 1

        # YSH will stop on errors.  OSH keep going, a bit like 'source'.
        if status != 0 and exec_opts.errexit():
            return status

    #
    # Is the shell interactive?
    #

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
        location_start_line = mops.BigTruncate(flag.location_start_line)
        if location_start_line != -1:
            line_reader.SetLineOffset(location_start_line)

    arena.PushSource(src)

    # Calculate ~/.config/oils/oshrc or yshrc.  Used for both -i and --headless
    # We avoid cluttering the user's home directory.  Some users may want to ln
    # -s ~/.config/oils/oshrc ~/oshrc or ~/.oshrc.

    # https://unix.stackexchange.com/questions/24347/why-do-some-applications-use-config-appname-for-their-config-data-while-other

    config_dir = '.config/oils'
    rc_paths = []  # type: List[str]
    if flag.headless or exec_opts.interactive():
        if flag.norc:
            # bash doesn't have this warning, but it's useful
            if flag.rcfile is not None:
                print_stderr('%s warning: --rcfile ignored with --norc' % lang)
            if flag.rcdir is not None:
                print_stderr('%s warning: --rcdir ignored with --norc' % lang)
        else:
            # User's rcfile comes FIRST.  Later we can add an 'after-rcdir' hook
            rc_path = flag.rcfile
            if rc_path is None:
                rc_paths.append(
                    os_path.join(home_dir, '%s/%src' % (config_dir, lang)))
            else:
                rc_paths.append(rc_path)

            # Load all files in ~/.config/oils/oshrc.d or oilrc.d
            # This way "installers" can avoid mutating oshrc directly

            rc_dir = flag.rcdir
            if rc_dir is None:
                rc_dir = os_path.join(home_dir,
                                      '%s/%src.d' % (config_dir, lang))

            rc_paths.extend(libc.glob(os_path.join(rc_dir, '*'), 0))

    # Initialize even in non-interactive shell, for 'compexport'
    _InitDefaultCompletions(cmd_ev, complete_builtin, comp_lookup)

    if flag.headless:
        sh_init.InitInteractive(mem, sh_files, lang)
        mutable_opts.set_redefine_const()
        mutable_opts.set_redefine_source()

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
        cmd_ev.RunTrapsOnExit(mut_status)
        status = mut_status.i

        return status

    # Note: headless mode above doesn't use c_parser
    assert line_reader is not None
    c_parser = parse_ctx.MakeOshParser(line_reader)

    if exec_opts.interactive():
        sh_init.InitInteractive(mem, sh_files, lang)
        # bash: 'set -o emacs' is the default only in the interactive shell
        mutable_opts.set_emacs()
        mutable_opts.set_redefine_const()
        mutable_opts.set_redefine_source()

        # NOTE: rc files loaded AFTER _InitDefaultCompletions.
        for rc_path in rc_paths:
            with state.ctx_ThisDir(mem, rc_path):
                try:
                    SourceStartupFile(fd_state, rc_path, lang, parse_ctx,
                                      cmd_ev, errfmt)
                except util.UserExit as e:
                    return e.status

        completion_display = state.MaybeString(mem, 'OILS_COMP_UI')
        if completion_display is None:
            completion_display = flag.completion_display

        if readline:
            if completion_display == 'nice':
                display = comp_ui.NiceDisplay(
                    comp_ui_state, prompt_state, debug_f, readline,
                    signal_safe)  # type: comp_ui._IDisplay
            else:
                display = comp_ui.MinimalDisplay(comp_ui_state, prompt_state,
                                                 debug_f, signal_safe)

            comp_ui.InitReadline(readline, sh_files.HistoryFile(), root_comp,
                                 display, debug_f)

            if flag.completion_demo:
                _CompletionDemo(comp_lookup)

        else:  # Without readline module
            display = comp_ui.MinimalDisplay(comp_ui_state, prompt_state,
                                             debug_f, signal_safe)

        process.InitInteractiveShell(signal_safe)  # Set signal handlers
        # The interactive shell leads a process group which controls the terminal.
        # It MUST give up the terminal afterward, otherwise we get SIGTTIN /
        # SIGTTOU bugs.
        with process.ctx_TerminalControl(job_control, errfmt):

            assert line_reader is not None
            line_reader.Reset()  # After sourcing startup file, render $PS1

            prompt_plugin = prompt.UserPlugin(mem, parse_ctx, cmd_ev, errfmt)
            try:
                status = main_loop.Interactive(flag, cmd_ev, c_parser, display,
                                               prompt_plugin, waiter, errfmt)
            except util.UserExit as e:
                status = e.status

            mut_status = IntParamBox(status)
            cmd_ev.RunTrapsOnExit(mut_status)
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
        # Don't save tokens because it's slow
        if tool_name != 'syntax-tree':
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

        elif tool_name == 'find-lhs-array':
            ysh_ify.TreeFind(arena, node, errfmt)

        elif tool_name == 'lossless-cat':  # for test/lossless.sh
            ysh_ify.LosslessCat(arena)

        elif tool_name == 'fmt':
            fmt.Format(arena, node)

        elif tool_name == 'test':
            # Do we need this?  Couldn't this just be a YSH script?
            raise AssertionError('TODO')

        elif tool_name == 'ysh-ify':
            ysh_ify.Ysh_ify(arena, node)

        elif tool_name == 'deps':
            if mylib.PYTHON:
                deps.Deps(node)

        else:
            raise AssertionError(tool_name)  # flag parser validated it

        return 0

    #
    # Batch mode: shell script or -c
    #

    with state.ctx_ThisDir(mem, script_name):
        try:
            status = main_loop.Batch(cmd_ev,
                                     c_parser,
                                     errfmt,
                                     cmd_flags=cmd_eval.IsMainProgram)
        except util.UserExit as e:
            status = e.status
        except KeyboardInterrupt:
            # The interactive shell handles this in main_loop.Interactive
            status = 130  # 128 + 2
    mut_status = IntParamBox(status)
    cmd_ev.RunTrapsOnExit(mut_status)

    multi_trace.WriteDumps()

    # NOTE: We haven't closed the file opened with fd_state.Open
    return mut_status.i
