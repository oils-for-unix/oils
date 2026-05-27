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
from _devbuild.gen.syntax_asdl import source, loc, loc_t, CompoundWord
from _devbuild.gen.value_asdl import Obj, value, value_t
from core import alloc
from core import dev
from core import error
from core.error import e_usage
from core import executor
from core import main_loop
from core import process
from core import pyutil  # strerror
from core import state
from core import vm
from data_lang import j8_lite
from display import ui
from frontend import consts
from frontend import flag_util
from frontend import reader
from mycpp.mylib import log, print_stderr, NewDict
from pylib import os_path
from osh import cmd_eval

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
            with state.ctx_CompoundWordDebugFrame(self.mem, eval_loc):
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
    #return basename.replace('-', '_')
    return basename


class ShellFile(vm._Builtin):
    """
    These share code:
    - 'source' builtin for OSH
    - 'use' builtin for YSH
    """

    def __init__(
            self,
            parse_ctx,  # type: ParseContext
            search_path,  # type: executor.SearchPath
            cmd_ev,  # type: CommandEvaluator
            fd_state,  # type: process.FdState
            tracer,  # type: dev.Tracer
            errfmt,  # type: ui.ErrorFormatter
            loader,  # type: pyutil._ResourceLoader
            module_invoke=None,  # type: vm._Builtin
    ):
        # type: (...) -> None
        """
        If module_invoke is passed, this class behaves like 'use'.  Otherwise
        it behaves like 'source'.
        """
        self.parse_ctx = parse_ctx
        self.arena = parse_ctx.arena
        self.search_path = search_path
        self.cmd_ev = cmd_ev
        self.fd_state = fd_state
        self.tracer = tracer
        self.errfmt = errfmt
        self.loader = loader
        self.module_invoke = module_invoke

        self.builtin_name = 'use' if module_invoke else 'source'
        self.mem = cmd_ev.mem

        # Don't load modules more than once
        # keyed by libc.realpath(arg)
        self._disk_cache = {}  # type: Dict[str, Obj]

        # keyed by ///
        self._embed_cache = {}  # type: Dict[str, Obj]

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        if self.module_invoke:
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
            # The file being sourced needs to be open across several commands
            # that can potentially move its fd, so open it persistently
            f, fd = self.fd_state.Open(fs_path, persistent=True)
        except (IOError, OSError) as e:
            self.errfmt.Print_(
                '%s %r failed: %s' %
                (self.builtin_name, fs_path, pyutil.strerror(e)),
                blame_loc=blame_loc)
            return None, None

        file_line_reader = reader.FileLineReader(f, self.arena)
        line_reader = file_line_reader
        self.fd_state.SetCallback(fd, file_line_reader)
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
            with state.ctx_Source(self.mem, path, source_argv, call_loc):
                with state.ctx_ThisDir(self.mem, path):
                    src = source.OtherFile(path, call_loc)
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

    def _NewModule(self):
        # type: () -> Obj
        # Builtin proc that serves as __invoke__ - it looks up procs in 'self'
        methods = Obj(None,
                      {'__invoke__': value.BuiltinProc(self.module_invoke)})
        props = NewDict()  # type: Dict[str, value_t]
        module_obj = Obj(methods, props)
        return module_obj

    def _UseExec(
            self,
            cmd_val,  # type: cmd_value.Argv
            path,  # type: str
            path_loc,  # type: loc_t
            c_parser,  # type: cmd_parse.CommandParser
            props,  # type: Dict[str, value_t]
    ):
        # type: (...) -> int
        """
        Args:
          props: is mutated, and will contain module properties
        """
        error_strs = []  # type: List[str]

        with dev.ctx_Tracer(self.tracer, 'use', cmd_val.argv):
            with state.ctx_ModuleEval(self.mem, cmd_val.arg_locs[0], props,
                                      error_strs):
                with state.ctx_ThisDir(self.mem, path):
                    src = source.OtherFile(path, path_loc)
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
                        if status != 0:
                            return status
                        #e_die("'use' failed 2", path_loc)

        if len(error_strs):
            for s in error_strs:
                self.errfmt.PrintMessage('Error: %s' % s, path_loc)
            return 1

        return 0

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

    def _BindNames(self, module_obj, module_name, pick_names, pick_locs):
        # type: (Obj, str, Optional[List[str]], Optional[List[CompoundWord]]) -> int
        state.SetGlobalValue(self.mem, module_name, module_obj)

        if pick_names is None:
            return 0

        for i, name in enumerate(pick_names):
            val = module_obj.d.get(name)
            # ctx_ModuleEval ensures this
            if val is None:
                # note: could be more precise
                self.errfmt.Print_("use: module doesn't provide name %r" %
                                   name,
                                   blame_loc=pick_locs[i])
                return 1
            state.SetGlobalValue(self.mem, name, val)
        return 0

    def _Use(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        """
        Module system with all the power of Python, but still a proc

        use util.ysh  # util is a value.Obj

        # Importing a bunch of words
        use dialect-ninja.ysh --all-provided
        use dialect-github.ysh --all-provided

        # This declares some names
        use --extern grep sed

        # Renaming
        use util.ysh (&myutil)

        # Ignore
        use util.ysh (&_)

        # Picking specifics
        use util.ysh --names log die

        # Rename
        var mylog = log
        """
        attrs, arg_r = flag_util.ParseCmdVal('use', cmd_val)
        arg = arg_types.use(attrs.attrs)

        # Accepts any args
        if arg.extern_:  # use --extern grep  # no-op for static analysis
            return 0

        path_arg, path_loc = arg_r.ReadRequired2('requires a module path')

        pick_names = None  # type: Optional[List[str]]
        pick_locs = None  # type: Optional[List[CompoundWord]]

        # There is only one flag
        flag, flag_loc = arg_r.Peek2()
        if flag is not None:
            if flag == '--pick':
                arg_r.Next()
                p = arg_r.Peek()
                if p is None:
                    raise error.Usage('with --pick expects one or more names',
                                      flag_loc)
                pick_names, pick_locs = arg_r.Rest2()

            elif flag == '--all-provided':
                arg_r.Next()
                arg_r.Done()
                print('TODO: --all-provided not implemented')

            elif flag == '--all-for-testing':
                arg_r.Next()
                arg_r.Done()
                print('TODO: --all-for testing not implemented')

            else:
                raise error.Usage(
                    'expected flag like --pick after module path', flag_loc)

        # Similar logic as 'source'
        if path_arg.startswith('///'):
            embed_path = path_arg[3:]
        else:
            embed_path = None

        if self.mem.InsideFunction():
            raise error.Usage("may only be used at the top level", path_loc)

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
                return self._BindNames(cached_obj, var_name, pick_names,
                                       pick_locs)

            load_path, c_parser = self.LoadEmbeddedFile(embed_path, path_loc)
            if c_parser is None:
                return 1  # error was already shown

            module_obj = self._NewModule()

            # Cache BEFORE executing, to prevent circular import
            self._embed_cache[embed_path] = module_obj

            status = self._UseExec(cmd_val, load_path, path_loc, c_parser,
                                   module_obj.d)
            if status != 0:
                return status

            return self._BindNames(module_obj, var_name, pick_names, pick_locs)

        else:
            normalized = libc.realpath(path_arg)
            if normalized is None:
                self.errfmt.Print_("use: couldn't find %r" % path_arg,
                                   blame_loc=path_loc)
                return 1

            # Disk modules are cached using normalized path as cache key
            cached_obj = self._disk_cache.get(normalized)
            if cached_obj:
                return self._BindNames(cached_obj, var_name, pick_names,
                                       pick_locs)

            f, c_parser = self._LoadDiskFile(normalized, path_loc)
            if c_parser is None:
                return 1  # error was already shown

            module_obj = self._NewModule()

            # Cache BEFORE executing, to prevent circular import
            self._disk_cache[normalized] = module_obj

            with process.ctx_FileCloser(f):
                status = self._UseExec(cmd_val, path_arg, path_loc, c_parser,
                                       module_obj.d)
            if status != 0:
                return status

            return self._BindNames(module_obj, var_name, pick_names, pick_locs)

        return 0


def _PrintFreeForm(row):
    # type: (Tuple[str, str, Optional[str]]) -> None
    """For type builtin and command builtin"""

    name, kind, detail = row

    if kind == 'file':
        what = detail  # file path
    elif kind == 'alias':
        what = ('an alias for %s' %
                j8_lite.EncodeString(detail, unquoted_ok=True))
    elif kind == 'proc':
        # "a YSH proc" - for regular procs
        # "a YSH invokable" (object)
        what = 'a YSH %s' % (detail if detail is not None else kind)
    elif kind == 'builtin':
        if detail is None:
            prefix = ''
        else:
            prefix = detail + ' '
        what = 'a %sshell %s' % (prefix, kind)
    elif kind in ('keyword', 'function'):
        # OSH prints 'shell function' instead of 'function', to distinguish
        # from YSH func
        what = 'a shell %s' % kind
    else:
        raise AssertionError()

    print('%s is %s' % (name, what))


#  8 space gutter column
# 12 spaces for name
# 12 for 'kind' - builtin proc extern
_TABLE_ROW_FMT = '%-8s%-12s%-12s%s'


def _PrintTableRow(row):
    # type: (Tuple[str, str, Optional[str]]) -> None
    name, kind, detail = row

    # Ideas for printing
    #
    # I guess the path always s
    #
    # time alias
    # time 'special builtin'
    # time /usr/bin/time
    # time '/home/dir with spaces/time'
    #
    # TODO: Might want to create an enum:
    # first_word =
    #   Alias(str body)
    # | Keyword
    # | Extern(str path)
    # | Builtin(kind k)
    # | ShellFunction
    # | Proc
    # | Invokable

    name_row = j8_lite.EncodeString(name, unquoted_ok=True)

    kind_row = kind
    if kind == 'function':
        # Consistent with --sh-func
        kind_row = 'sh-func'
    elif kind == 'file':
        # Consistent with --extern
        kind_row = 'extern'

    detail_row = (j8_lite.EncodeString(detail, unquoted_ok=True)
                  if detail is not None else '-')

    # 20 cols for "private builtin"
    print(_TABLE_ROW_FMT % ('', name_row, kind_row, detail_row))


class Command(vm._Builtin):
    """'command ls' suppresses function lookup."""

    def __init__(
            self,
            shell_ex,  # type: vm._Executor
            procs,  # type: state.Procs
            aliases,  # type: Dict[str, str]
            search_path,  # type: executor.SearchPath
    ):
        # type: (...) -> None
        self.shell_ex = shell_ex
        self.procs = procs
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
                r = _ResolveName(argument, self.procs, self.aliases,
                                 self.search_path, False)
                if len(r):
                    # Print only the first occurrence.
                    # TODO: it would be nice to short-circuit the lookups
                    row = r[0]
                    if arg.v:
                        name, kind, detail = row
                        if kind == 'file':
                            print(detail)  # /usr/bin/awk
                        else:
                            print(name)  # myfunc
                    else:
                        _PrintFreeForm(row)
                else:
                    # match bash behavior by printing to stderr
                    print_stderr('%s: not found' % argument)
                    status = 1  # nothing printed, but we fail

            return status

        cmd_val2 = cmd_value.Argv(argv, locs, cmd_val.is_last_cmd,
                                  cmd_val.self_obj, cmd_val.proc_args)

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
                          cmd_val.is_last_cmd, cmd_val.self_obj,
                          cmd_val.proc_args)


class Builtin(vm._Builtin):

    def __init__(self, shell_ex, errfmt):
        # type: (vm._Executor, ui.ErrorFormatter) -> None
        self.shell_ex = shell_ex
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('builtin',
                                             cmd_val,
                                             accept_typed_args=True)
        argv, locs = arg_r.Rest2()

        if len(argv) == 0:
            return 0  # this could be an error in strict mode?

        name = argv[0]

        to_run = _LookupAnyBuiltin(name)

        if to_run == consts.NO_INDEX:  # error
            location = locs[0]
            if consts.LookupAssignBuiltin(name) != consts.NO_INDEX:
                # NOTE: core/executor.py has a similar restriction for 'command'
                self.errfmt.Print_("'builtin' can't run assignment builtin",
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
            raise error.Usage('requires arguments', cmd_val.arg_locs[0])

        name = argv[0]
        proc, _ = self.procs.GetInvokable(name)
        if not proc:
            self.errfmt.Print_('runproc: no invokable named %r' % name,
                               locs[0])
            return 1

        cmd_val2 = cmd_value.Argv(argv, locs, cmd_val.is_last_cmd,
                                  cmd_val.self_obj, cmd_val.proc_args)

        # NOTE: Don't need cmd_st?
        cmd_st = CommandStatus.CreateNull(alloc_lists=True)
        run_flags = executor.IS_LAST_CMD if cmd_val.is_last_cmd else 0
        return self.shell_ex.RunSimpleCommand(cmd_val2, cmd_st, run_flags)


def _LookupAnyBuiltin(name):
    # type: (str) -> int
    to_run = consts.LookupNormalBuiltin(name)  # builtin true

    if to_run == consts.NO_INDEX:  # builtin eval
        to_run = consts.LookupSpecialBuiltin(name)

    if to_run == consts.NO_INDEX:  # builtin sleep
        # Note that plain 'sleep' doesn't work
        to_run = consts.LookupPrivateBuiltin(name)

    return to_run


class Invoke(vm._Builtin):
    """Invoke a command, controlling the resolution of the first word."""

    def __init__(
            self,
            shell_ex,  # type: vm._Executor
            procs,  # type: state.Procs
            aliases,  # type: Dict[str, str]
            search_path,  # type: executor.SearchPath
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.shell_ex = shell_ex
        self.procs = procs
        self.aliases = aliases
        self.search_path = search_path
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('invoke',
                                             cmd_val,
                                             accept_typed_args=True)
        arg = arg_types.invoke(attrs.attrs)
        argv, locs = arg_r.Rest2()

        if len(argv) == 0:
            raise error.Usage('expected arguments', cmd_val.arg_locs[0])

        if arg.show:
            # she-dot of .qtt8
            print(_TABLE_ROW_FMT % ('#.qtt8', 'name', 'kind', 'detail'))
            for name in argv:
                r = _ResolveName(name,
                                 self.procs,
                                 self.aliases,
                                 self.search_path,
                                 True,
                                 do_private=True)
                if len(r):
                    for row in r:
                        _PrintTableRow(row)
                else:
                    # - means not found
                    _PrintTableRow((name, '-', '-'))
            return 0

        cmd_val2 = cmd_value.Argv(argv, locs, cmd_val.is_last_cmd,
                                  cmd_val.self_obj, cmd_val.proc_args)

        name = argv[0]
        location = locs[0]

        tried = []  # type: List[str]

        # Look it up
        if arg.proc:
            tried.append('--proc')
            proc_val, self_obj = self.procs.GetProc(name)
            if proc_val is not None:
                return self.shell_ex._RunInvokable(proc_val, self_obj,
                                                   location, cmd_val2)

        if arg.sh_func:
            tried.append('--sh-func')
            sh_func = self.procs.GetShellFunc(name)
            if sh_func:
                return self.shell_ex._RunInvokable(sh_func, None, location,
                                                   cmd_val2)

        if arg.builtin:
            tried.append('--builtin')
            # Look up any builtin

            to_run = _LookupAnyBuiltin(name)
            if to_run != consts.NO_INDEX:
                # early return
                return self.shell_ex.RunBuiltin(to_run, cmd_val2)

        # Special considerations:
        # - set PATH for lookup
        # - set ENV for external process with a DICT
        #   - I think these are better for the 'extern' builtin
        if arg.extern_:
            tried.append('--extern')
            # cmd_st is None - should we get rid of it?  See 'runproc' too
            return self.shell_ex.RunExternal(name, location, cmd_val2, None, 0)

        if len(tried) == 0:
            raise error.Usage(
                'expected one or more flags like --proc --sh-func --builtin --extern',
                cmd_val.arg_locs[0])

        # Command not found
        self.errfmt.Print_("'invoke' couldn't find command %r (tried %s)" %
                           (name, ' '.join(tried)),
                           blame_loc=location)
        return 127


class Extern(vm._Builtin):
    """
    Why does this exist?  
    - Run with ENV in a dict, similar to env -i, but possibly easier
    - Run with $PATH
    """

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
        search_path,  # type: executor.SearchPath
        do_all,  # type: bool
        do_private=False,  # type: bool
):
    # type: (...) -> List[Tuple[str, str, Optional[str]]]
    """
    Returns:
      A list of (name, type, optional arg)

    When type == 'alias',   arg is the expansion text
    When type == 'file',    arg is the path
    When type == 'builtin', arg is 'special', 'private', or None
    When type == 'proc',    arg is 'invokable' or None

    POSIX has these rules:
      https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_09_01_01

      a. special builtins (eval :)
      b. undefined builtins (complete whence)
      c. shell function
      d. list of builtins (alias command) - could include th undefined ones
      e. external

    Our ShellExecutor uses this order, wich is compatible:
      1. special builtins
      2. shell functions
      3. normal builtins
      4. external
    """
    # MyPy tuple type
    no_str = None  # type: Optional[str]

    results = []  # type: List[Tuple[str, str, Optional[str]]]

    # Aliases can redefine keywords
    if name in aliases:
        results.append((name, 'alias', aliases[name]))

    # Keywords come before simple commands
    if consts.IsControlFlow(name):  # continue, etc.
        results.append((name, 'keyword', no_str))
    elif consts.IsKeyword(name):
        results.append((name, 'keyword', no_str))

    # Simple commands are looked up in this order by ShellExecutor:
    #
    #   1. special builtins
    #   2. procs
    #   3. shell functions - see state.Procs, shell functions come second
    #   4. normal builtins
    #   5. external commands
    #
    # These require the 'builtin' prefix:
    #   6. private builtins

    # Special builtins are looked up FIRST
    if consts.LookupSpecialBuiltin(name) != 0:
        results.append((name, 'builtin', 'special'))

    if procs:
        if procs.IsProc(name):
            results.append((name, 'proc', no_str))
        elif procs.IsInvokableObj(name):  # can't be both proc and obj
            results.append((name, 'proc', 'invokable'))

        if procs.IsShellFunc(name):  # shell functions AFTER procs
            results.append((name, 'function', no_str))

    # See if it's a builtin
    if consts.LookupNormalBuiltin(name) != 0:
        results.append((name, 'builtin', no_str))
    elif consts.LookupAssignBuiltin(name) != 0:
        results.append((name, 'builtin', 'special'))

    # See if it's external
    for path in search_path.LookupReflect(name, do_all):
        results.append((name, 'file', path))

    # Private builtins after externals
    if do_private and consts.LookupPrivateBuiltin(name) != 0:
        results.append((name, 'builtin', 'private'))

    return results


class Type(vm._Builtin):

    def __init__(
            self,
            procs,  # type: state.Procs
            aliases,  # type: Dict[str, str]
            search_path,  # type: executor.SearchPath
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.procs = procs
        self.aliases = aliases
        self.search_path = search_path
        self.errfmt = errfmt

    def _PrintEntry(self, arg, row):
        # type: (arg_types.type, Tuple[str, str, Optional[str]]) -> None
        """For type builtin"""

        name, kind, detail = row
        assert kind is not None

        if arg.t:  # short string
            print(kind)

        elif arg.p:
            #log('%s %s %s', name, kind, resolved)
            if kind == 'file':
                print(detail)  # print the file path

        else:  # free-form text
            _PrintFreeForm(row)
            if kind == 'function':
                #self._PrintShellFuncSource(name)
                sh_func = self.procs.GetShellFunc(name)
                assert sh_func is not None  # we already looked it up
                ui.PrintShFunction(sh_func)

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('type', cmd_val)
        arg = arg_types.type(attrs.attrs)

        if arg.f:  # suppress function lookup
            procs = None  # type: state.Procs
        else:
            procs = self.procs

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
            r = _ResolveName(argument, procs, self.aliases, self.search_path,
                             arg.a)

            if arg.a:
                for row in r:
                    self._PrintEntry(arg, row)
            else:
                # Just print the first one.
                # TODO: it would be nice to short-circuit the lookups.
                # It would be nice if 'yield' worked.
                if len(r):
                    self._PrintEntry(arg, r[0])

            # Error case
            if len(r) == 0:
                if not arg.t:  # 'type -t' is silent in this case
                    # match bash behavior by printing to stderr
                    print_stderr('%s: not found' % argument)
                status = 1  # nothing printed, but we fail

        return status
