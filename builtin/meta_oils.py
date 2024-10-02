#!/usr/bin/env python2
"""
meta_oils.py - Builtins that call back into the interpreter, or reflect on it.

OSH builtins:
  builtin command type       
  source eval

YSH builtins:
  invoke extern
  use
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value, CommandStatus
from _devbuild.gen.syntax_asdl import source, loc, loc_t
from _devbuild.gen.value_asdl import Obj, value, value_t
from builtin import module_ysh
from core import alloc
from core import dev
from core import error
from core.error import e_usage, e_die
from core import executor
from core import main_loop
from core import process
from core import pyutil  # strerror
from core import state
from core import vm
from data_lang import j8_lite
from frontend import consts
from frontend import flag_util
from frontend import reader
from mycpp.mylib import log, print_stderr, NewDict
from pylib import os_path
from osh import cmd_eval

import posix_ as posix
from posix_ import X_OK  # translated directly to C macro

import libc

_ = log

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from frontend import args
    from frontend.parse_lib import ParseContext
    from core import optview
    from display import ui
    from mycpp import mylib
    from osh.cmd_eval import CommandEvaluator
    from osh import cmd_parse


class Eval(vm._Builtin):

    def __init__(
            self,
            parse_ctx,  # type: ParseContext
            exec_opts,  # type: optview.Exec
            cmd_ev,  # type: CommandEvaluator
            tracer,  # type: dev.Tracer
            errfmt,  # type: ui.ErrorFormatter
            mem,  # type: state.Mem
    ):
        # type: (...) -> None
        self.parse_ctx = parse_ctx
        self.arena = parse_ctx.arena
        self.exec_opts = exec_opts
        self.cmd_ev = cmd_ev
        self.tracer = tracer
        self.errfmt = errfmt
        self.mem = mem

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        # There are no flags, but we need it to respect --
        _, arg_r = flag_util.ParseCmdVal('eval', cmd_val)

        if self.exec_opts.simple_eval_builtin():
            code_str, eval_loc = arg_r.ReadRequired2('requires code string')
            if not arg_r.AtEnd():
                e_usage('requires exactly 1 argument', loc.Missing)
        else:
            code_str = ' '.join(arg_r.Rest())
            # code_str could be EMPTY, so just use the first one
            eval_loc = cmd_val.arg_locs[0]

        line_reader = reader.StringLineReader(code_str, self.arena)
        c_parser = self.parse_ctx.MakeOshParser(line_reader)

        src = source.Dynamic('eval arg', eval_loc)
        with dev.ctx_Tracer(self.tracer, 'eval', None):
            with alloc.ctx_SourceCode(self.arena, src):
                return main_loop.Batch(self.cmd_ev,
                                       c_parser,
                                       self.errfmt,
                                       cmd_flags=cmd_eval.RaiseControlFlow)


def _VarName(module_path):
    # type: (str) -> str
    """Convert ///path/foo-bar.ysh -> foo_bar

    Design issue: proc vs. func naming conventinos imply treating hyphens
    differently.

      foo-bar myproc
      var x = `foo-bar`.myproc

    I guess use this for now:

      foo_bar myproc
      var x = foo_bar.myproc

    The user can also choose this:

      fooBar myproc
      var x = fooBar.myproc
    """
    basename = os_path.basename(module_path)
    i = basename.rfind('.')
    if i != -1:
        basename = basename[:i]
    return basename.replace('-', '_')


class ShellFile(vm._Builtin):
    """
    These share code:
    - 'source' builtin for OSH
    - 'use' builtin for YSH
    """

    def __init__(
            self,
            parse_ctx,  # type: ParseContext
            search_path,  # type: state.SearchPath
            cmd_ev,  # type: CommandEvaluator
            fd_state,  # type: process.FdState
            tracer,  # type: dev.Tracer
            errfmt,  # type: ui.ErrorFormatter
            loader,  # type: pyutil._ResourceLoader
            ysh_use=False,  # type: bool
    ):
        # type: (...) -> None
        self.parse_ctx = parse_ctx
        self.arena = parse_ctx.arena
        self.search_path = search_path
        self.cmd_ev = cmd_ev
        self.fd_state = fd_state
        self.tracer = tracer
        self.errfmt = errfmt
        self.loader = loader
        self.ysh_use = ysh_use

        self.builtin_name = 'use' if ysh_use else 'source'
        self.mem = cmd_ev.mem

        # Don't load modules more than once
        # keyed by libc.realpath(arg)
        self._disk_cache = {}  # type: Dict[str, Obj]

        # keyed by ///
        self._embed_cache = {}  # type: Dict[str, Obj]

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        if self.ysh_use:
            return self._Use(cmd_val)
        else:
            return self._Source(cmd_val)

    def LoadEmbeddedFile(self, embed_path, blame_loc):
        # type: (str, loc_t) -> Tuple[str, cmd_parse.CommandParser]
        try:
            load_path = os_path.join("stdlib", embed_path)
            contents = self.loader.Get(load_path)
        except (IOError, OSError):
            self.errfmt.Print_('%r failed: No builtin file %r' %
                               (self.builtin_name, load_path),
                               blame_loc=blame_loc)
            return None, None  # error

        line_reader = reader.StringLineReader(contents, self.arena)
        c_parser = self.parse_ctx.MakeOshParser(line_reader)
        return load_path, c_parser

    def _LoadDiskFile(self, fs_path, blame_loc):
        # type: (str, loc_t) -> Tuple[mylib.LineReader, cmd_parse.CommandParser]
        try:
            # Shell can't use descriptors 3-9
            f = self.fd_state.Open(fs_path)
        except (IOError, OSError) as e:
            self.errfmt.Print_(
                '%s %r failed: %s' %
                (self.builtin_name, fs_path, pyutil.strerror(e)),
                blame_loc=blame_loc)
            return None, None

        line_reader = reader.FileLineReader(f, self.arena)
        c_parser = self.parse_ctx.MakeOshParser(line_reader)
        return f, c_parser

    def _SourceExec(self, cmd_val, arg_r, path, c_parser):
        # type: (cmd_value.Argv, args.Reader, str, cmd_parse.CommandParser) -> int
        call_loc = cmd_val.arg_locs[0]

        # A sourced module CAN have a new arguments array, but it always shares
        # the same variable scope as the caller.  The caller could be at either a
        # global or a local scope.

        # TODO: I wonder if we compose the enter/exit methods more easily.

        with dev.ctx_Tracer(self.tracer, 'source', cmd_val.argv):
            source_argv = arg_r.Rest()
            with state.ctx_Source(self.mem, path, source_argv):
                with state.ctx_ThisDir(self.mem, path):
                    src = source.SourcedFile(path, call_loc)
                    with alloc.ctx_SourceCode(self.arena, src):
                        try:
                            status = main_loop.Batch(
                                self.cmd_ev,
                                c_parser,
                                self.errfmt,
                                cmd_flags=cmd_eval.RaiseControlFlow)
                        except vm.IntControlFlow as e:
                            if e.IsReturn():
                                status = e.StatusCode()
                            else:
                                raise

        return status

    def _UseExec(self, path, path_loc, c_parser):
        # type: (str, loc_t, cmd_parse.CommandParser) -> Obj

        attrs = NewDict()  # type: Dict[str, value_t]
        error_strs = []  # type: List[str]

        with state.ctx_ModuleEval(self.mem, attrs, error_strs):
            with dev.ctx_Tracer(self.tracer, 'use', None):
                with state.ctx_ThisDir(self.mem, path):

                    # TODO: change the src to source.ShellFile

                    src = source.SourcedFile(path, path_loc)
                    with alloc.ctx_SourceCode(self.arena, src):
                        try:
                            unused_status = main_loop.Batch(
                                self.cmd_ev,
                                c_parser,
                                self.errfmt,
                                cmd_flags=cmd_eval.RaiseControlFlow)
                        except vm.IntControlFlow as e:
                            if e.IsReturn():
                                status = e.StatusCode()
                            else:
                                raise

        if len(error_strs):
            # TODO: show 'export' location, not the 'import' location
            for s in error_strs:
                self.errfmt.PrintMessage('Error: %s' % s, path_loc)
            e_die("Import failed", path_loc)

        # Builtin proc that serves as __invoke__ - it looks up procs in 'self'
        inv = module_ysh.InvokeModule()
        methods = Obj(None, {'__invoke__': value.BuiltinProc(inv)})
        module_obj = Obj(methods, attrs)
        return module_obj

    def _Source(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('source', cmd_val)
        arg = arg_types.source(attrs.attrs)

        path_arg, path_loc = arg_r.ReadRequired2('requires a file path')

        # Old:
        #     source --builtin two.sh  # looks up stdlib/two.sh
        # New:
        #     source $LIB_OSH/two.sh  # looks up stdlib/osh/two.sh
        #     source ///osh/two.sh  # looks up stdlib/osh/two.sh
        embed_path = None  # type: Optional[str]
        if arg.builtin:
            embed_path = path_arg
        elif path_arg.startswith('///'):
            embed_path = path_arg[3:]

        if embed_path is not None:
            load_path, c_parser = self.LoadEmbeddedFile(embed_path, path_loc)
            if c_parser is None:
                return 1  # error was already shown

            return self._SourceExec(cmd_val, arg_r, load_path, c_parser)

        else:
            # 'source' respects $PATH
            resolved = self.search_path.LookupOne(path_arg,
                                                  exec_required=False)
            if resolved is None:
                resolved = path_arg

            f, c_parser = self._LoadDiskFile(resolved, path_loc)
            if c_parser is None:
                return 1  # error was already shown

            with process.ctx_FileCloser(f):
                return self._SourceExec(cmd_val, arg_r, path_arg, c_parser)

        raise AssertionError()

    def _Use(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        """
        Module system with all the power of Python, but still a proc

        use util.ysh  # util is a value.Obj

        # Importing a bunch of words
        use dialect-ninja.ysh { all }  # requires 'provide' in dialect-ninja
        use dialect-github.ysh { all }

        # This declares some names
        use --extern grep sed

        # Renaming
        use util.ysh (&myutil)

        # Ignore
        use util.ysh (&_)

        # Picking specifics
        use util.ysh {
          pick log die
          pick foo (&myfoo)
        }

        # A long way to write this is:

        use util.ysh
        const log = util.log
        const die = util.die
        const myfoo = util.foo

        Another way is:
        for name in log die {
          call setVar(name, util[name])

          # value.Obj may not support [] though
          # get(propView(util), name, null) is a long way of writing it
        }

        Other considerations:

        - Statically parseable subset?  For fine-grained static tree-shaking
          - We're doing coarse dynamic tree-shaking first though

        - if TYPE_CHECKING is an issue
          - that can create circular dependencies, especially with gradual typing,
            when you go dynamic to static (like Oils did)
          - I guess you can have
            - use --static parse_lib.ysh { pick ParseContext } 

        # Crazy idea - pure ysh

        use $LIB_YSH/pick.ysh
        pick $LIB_YSH/table.ysh {
          names foo bar
          name x (&alias)

          all
          names *  # perhaps, if you turn off globbing
        }

        import $LIB_YSH/stdlib

        """
        attrs, arg_r = flag_util.ParseCmdVal('use', cmd_val)
        arg = arg_types.use(attrs.attrs)

        # Accepts any args
        if arg.extern_:  # use --extern grep  # no-op for static analysis
            return 0

        path_arg, path_loc = arg_r.ReadRequired2('requires a module path')
        # TODO on usage:
        # - typed arg is value.Place
        # - block arg binds 'pick' and 'all'
        # Although ALL these 3 mechanisms can be done with 'const' assignments.
        # Hm.
        arg_r.Done()

        # I wonder if modules should be FROZEN value.Obj, not mutable?

        # Similar logic as 'source'
        if path_arg.startswith('///'):
            embed_path = path_arg[3:]
        else:
            embed_path = None

        # Important, consider:
        #     use symlink.ysh  # where symlink.ysh -> realfile.ysh
        #
        # Then the cache key would be '/some/path/realfile.ysh'
        # But the variable name bound is 'symlink'
        var_name = _VarName(path_arg)
        #log('var %s', var_name)

        if embed_path is not None:
            # Embedded modules are cached using /// path as cache key
            cached_obj = self._embed_cache.get(embed_path)
            if cached_obj:
                state.SetLocalValue(self.mem, var_name, cached_obj)
                return 0

            load_path, c_parser = self.LoadEmbeddedFile(embed_path, path_loc)
            if c_parser is None:
                return 1  # error was already shown

            obj = self._UseExec(load_path, path_loc, c_parser)
            state.SetLocalValue(self.mem, var_name, obj)
            self._embed_cache[embed_path] = obj

        else:
            normalized = libc.realpath(path_arg)
            if normalized is None:
                self.errfmt.Print_("use: couldn't find %r" % path_arg,
                                   blame_loc=path_loc)
                return 1

            # Disk modules are cached using normalized path as cache key
            cached_obj = self._disk_cache.get(normalized)
            if cached_obj:
                var_name = _VarName(path_arg)
                state.SetLocalValue(self.mem, var_name, cached_obj)
                return 0

            f, c_parser = self._LoadDiskFile(normalized, path_loc)
            if c_parser is None:
                return 1  # error was already shown

            with process.ctx_FileCloser(f):
                obj = self._UseExec(path_arg, path_loc, c_parser)
            state.SetLocalValue(self.mem, var_name, obj)
            self._disk_cache[normalized] = obj

        return 0


def _PrintFreeForm(row):
    # type: (Tuple[str, str, Optional[str]]) -> None
    name, kind, resolved = row

    if kind == 'file':
        what = resolved
    elif kind == 'alias':
        what = ('an alias for %s' %
                j8_lite.EncodeString(resolved, unquoted_ok=True))
    elif kind in ('proc', 'invokable'):
        # Note: haynode should be an invokable
        what = 'a YSH %s' % kind
    else:  # builtin, function, keyword
        what = 'a shell %s' % kind

    print('%s is %s' % (name, what))

    # if kind == 'function':
    #   bash is the only shell that prints the function


def _PrintEntry(arg, row):
    # type: (arg_types.type, Tuple[str, str, Optional[str]]) -> None

    _, kind, resolved = row
    assert kind is not None

    if arg.t:  # short string
        print(kind)

    elif arg.p:
        #log('%s %s %s', name, kind, resolved)
        if kind == 'file':
            print(resolved)

    else:  # free-form text
        _PrintFreeForm(row)


class Command(vm._Builtin):
    """'command ls' suppresses function lookup."""

    def __init__(
            self,
            shell_ex,  # type: vm._Executor
            funcs,  # type: state.Procs
            aliases,  # type: Dict[str, str]
            search_path,  # type: state.SearchPath
    ):
        # type: (...) -> None
        self.shell_ex = shell_ex
        self.funcs = funcs
        self.aliases = aliases
        self.search_path = search_path

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        # accept_typed_args=True because we invoke other builtins
        attrs, arg_r = flag_util.ParseCmdVal('command',
                                             cmd_val,
                                             accept_typed_args=True)
        arg = arg_types.command(attrs.attrs)

        argv, locs = arg_r.Rest2()

        if arg.v or arg.V:
            status = 0
            for argument in argv:
                r = _ResolveName(argument, self.funcs, self.aliases,
                                 self.search_path, False)
                if len(r):
                    # command -v prints the name (-V is more detailed)
                    # Print it only once.
                    row = r[0]
                    name, _, _ = row
                    if arg.v:
                        print(name)
                    else:
                        _PrintFreeForm(row)
                else:
                    # match bash behavior by printing to stderr
                    print_stderr('%s: not found' % argument)
                    status = 1  # nothing printed, but we fail

            return status

        cmd_val2 = cmd_value.Argv(argv, locs, cmd_val.is_last_cmd,
                                  cmd_val.proc_args)

        cmd_st = CommandStatus.CreateNull(alloc_lists=True)

        # If we respected do_fork here instead of passing DO_FORK
        # unconditionally, the case 'command date | wc -l' would take 2
        # processes instead of 3.  See test/syscall
        run_flags = executor.NO_CALL_PROCS
        if cmd_val.is_last_cmd:
            run_flags |= executor.IS_LAST_CMD
        if arg.p:
            run_flags |= executor.USE_DEFAULT_PATH

        return self.shell_ex.RunSimpleCommand(cmd_val2, cmd_st, run_flags)


def _ShiftArgv(cmd_val):
    # type: (cmd_value.Argv) -> cmd_value.Argv
    return cmd_value.Argv(cmd_val.argv[1:], cmd_val.arg_locs[1:],
                          cmd_val.is_last_cmd, cmd_val.proc_args)


class Builtin(vm._Builtin):

    def __init__(self, shell_ex, errfmt):
        # type: (vm._Executor, ui.ErrorFormatter) -> None
        self.shell_ex = shell_ex
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        if len(cmd_val.argv) == 1:
            return 0  # this could be an error in strict mode?

        name = cmd_val.argv[1]

        # Run regular builtin or special builtin
        to_run = consts.LookupNormalBuiltin(name)
        if to_run == consts.NO_INDEX:
            to_run = consts.LookupSpecialBuiltin(name)
        if to_run == consts.NO_INDEX:
            location = cmd_val.arg_locs[1]
            if consts.LookupAssignBuiltin(name) != consts.NO_INDEX:
                # NOTE: There's a similar restriction for 'command'
                self.errfmt.Print_("Can't run assignment builtin recursively",
                                   blame_loc=location)
            else:
                self.errfmt.Print_("%r isn't a shell builtin" % name,
                                   blame_loc=location)
            return 1

        cmd_val2 = _ShiftArgv(cmd_val)
        return self.shell_ex.RunBuiltin(to_run, cmd_val2)


class RunProc(vm._Builtin):

    def __init__(self, shell_ex, procs, errfmt):
        # type: (vm._Executor, state.Procs, ui.ErrorFormatter) -> None
        self.shell_ex = shell_ex
        self.procs = procs
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('runproc',
                                         cmd_val,
                                         accept_typed_args=True)
        argv, locs = arg_r.Rest2()

        if len(argv) == 0:
            raise error.Usage('requires arguments', loc.Missing)

        name = argv[0]
        proc, _ = self.procs.GetInvokable(name)
        if not proc:
            # note: should runproc be invoke?
            self.errfmt.PrintMessage('runproc: no invokable named %r' % name)
            return 1

        cmd_val2 = cmd_value.Argv(argv, locs, cmd_val.is_last_cmd,
                                  cmd_val.proc_args)

        cmd_st = CommandStatus.CreateNull(alloc_lists=True)
        run_flags = executor.IS_LAST_CMD if cmd_val.is_last_cmd else 0
        return self.shell_ex.RunSimpleCommand(cmd_val2, cmd_st, run_flags)


class Invoke(vm._Builtin):
    """
    Introspection:

    invoke     - YSH introspection on first word
    type --all - introspection on variables too?
               - different than = type(x)

    3 Coarsed-grained categories
    - invoke --builtin     aka builtin
      - including special builtins
    - invoke --proc-like   aka runproc
      - myproc (42)
      - sh-func
      - invokable-obj
    - invoke --extern      aka extern

    Note: If you don't distinguish between proc, sh-func, and invokable-obj,
    then 'runproc' suffices.

    invoke --proc-like reads more nicely though, and it also combines.

        invoke --builtin --extern  # this is like 'command'

    You can also negate:

        invoke --no-proc-like --no-builtin --no-extern

    - type -t also has 'keyword' and 'assign builtin'

    With no args, print a table of what's available

       invoke --builtin
       invoke --builtin true
    """

    def __init__(self, shell_ex, procs, errfmt):
        # type: (vm._Executor, state.Procs, ui.ErrorFormatter) -> None
        self.shell_ex = shell_ex
        self.procs = procs
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('invoke',
                                         cmd_val,
                                         accept_typed_args=True)
        #argv, locs = arg_r.Rest2()

        print('TODO: invoke')
        # TODO
        return 0


class Extern(vm._Builtin):

    def __init__(self, shell_ex, procs, errfmt):
        # type: (vm._Executor, state.Procs, ui.ErrorFormatter) -> None
        self.shell_ex = shell_ex
        self.procs = procs
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('extern',
                                         cmd_val,
                                         accept_typed_args=True)
        #argv, locs = arg_r.Rest2()

        print('TODO: extern')

        return 0


def _ResolveName(
        name,  # type: str
        procs,  # type: state.Procs
        aliases,  # type: Dict[str, str]
        search_path,  # type: state.SearchPath
        do_all,  # type: bool
):
    # type: (...) -> List[Tuple[str, str, Optional[str]]]
    """
    TODO: Can this be moved to pure YSH?

    All of these could be in YSH:

    type, type -t, type -a
    pp proc

    We would have primitive isShellFunc() and isInvokableObj() functions
    """

    # MyPy tuple type
    no_str = None  # type: Optional[str]

    results = []  # type: List[Tuple[str, str, Optional[str]]]

    if procs:
        if procs.IsShellFunc(name):
            results.append((name, 'function', no_str))

        if procs.IsProc(name):
            results.append((name, 'proc', no_str))
        elif procs.IsInvokableObj(name):  # can't be both proc and obj
            results.append((name, 'invokable', no_str))

    if name in aliases:
        results.append((name, 'alias', aliases[name]))

    # See if it's a builtin
    if consts.LookupNormalBuiltin(name) != 0:
        results.append((name, 'builtin', no_str))
    elif consts.LookupSpecialBuiltin(name) != 0:
        results.append((name, 'builtin', no_str))
    elif consts.LookupAssignBuiltin(name) != 0:
        results.append((name, 'builtin', no_str))

    # See if it's a keyword
    if consts.IsControlFlow(name):  # continue, etc.
        results.append((name, 'keyword', no_str))
    elif consts.IsKeyword(name):
        results.append((name, 'keyword', no_str))

    # See if it's external
    for path in search_path.LookupReflect(name, do_all):
        if posix.access(path, X_OK):
            results.append((name, 'file', path))

    return results


class Type(vm._Builtin):

    def __init__(
            self,
            funcs,  # type: state.Procs
            aliases,  # type: Dict[str, str]
            search_path,  # type: state.SearchPath
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.funcs = funcs
        self.aliases = aliases
        self.search_path = search_path
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('type', cmd_val)
        arg = arg_types.type(attrs.attrs)

        if arg.f:  # suppress function lookup
            funcs = None  # type: state.Procs
        else:
            funcs = self.funcs

        status = 0
        names = arg_r.Rest()

        if arg.P:  # -P should forces PATH search, regardless of builtin/alias/function/etc.
            for name in names:
                paths = self.search_path.LookupReflect(name, arg.a)
                if len(paths):
                    for path in paths:
                        print(path)
                else:
                    status = 1
            return status

        for argument in names:
            r = _ResolveName(argument, funcs, self.aliases, self.search_path,
                             arg.a)
            if arg.a:
                for row in r:
                    _PrintEntry(arg, row)
            else:
                if len(r):  # Just print the first one
                    _PrintEntry(arg, r[0])

            # Error case
            if len(r) == 0:
                if not arg.t:  # 'type -t' is silent in this case
                    # match bash behavior by printing to stderr
                    print_stderr('%s: not found' % argument)
                status = 1  # nothing printed, but we fail

        return status
