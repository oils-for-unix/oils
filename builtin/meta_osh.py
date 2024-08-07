#!/usr/bin/env python2
"""
meta_osh.py - Builtins that call back into the interpreter.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value, CommandStatus
from _devbuild.gen.syntax_asdl import source, loc
from core import alloc
from core import dev
from core import error
from core import executor
from core import main_loop
from core import process
from core.error import e_usage
from core import pyutil  # strerror
from core import state
from core import vm
from data_lang import j8_lite
from frontend import flag_util
from frontend import consts
from frontend import reader
from frontend import typed_args
from mycpp.mylib import log, print_stderr
from pylib import os_path
from osh import cmd_eval

import posix_ as posix
from posix_ import X_OK  # translated directly to C macro

_ = log

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from frontend import args
    from frontend.parse_lib import ParseContext
    from core import optview
    from display import ui
    from osh.cmd_eval import CommandEvaluator
    from osh.cmd_parse import CommandParser


class Eval(vm._Builtin):

    def __init__(
            self,
            parse_ctx,  # type: ParseContext
            exec_opts,  # type: optview.Exec
            cmd_ev,  # type: CommandEvaluator
            tracer,  # type: dev.Tracer
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.parse_ctx = parse_ctx
        self.arena = parse_ctx.arena
        self.exec_opts = exec_opts
        self.cmd_ev = cmd_ev
        self.tracer = tracer
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        if cmd_val.typed_args:  # eval (mycmd)
            rd = typed_args.ReaderForProc(cmd_val)
            cmd = rd.PosCommand()
            rd.Done()
            return self.cmd_ev.EvalCommand(cmd)

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

        src = source.ArgvWord('eval', eval_loc)
        with dev.ctx_Tracer(self.tracer, 'eval', None):
            with alloc.ctx_SourceCode(self.arena, src):
                return main_loop.Batch(self.cmd_ev,
                                       c_parser,
                                       self.errfmt,
                                       cmd_flags=cmd_eval.RaiseControlFlow)


class Source(vm._Builtin):

    def __init__(
            self,
            parse_ctx,  # type: ParseContext
            search_path,  # type: state.SearchPath
            cmd_ev,  # type: CommandEvaluator
            fd_state,  # type: process.FdState
            tracer,  # type: dev.Tracer
            errfmt,  # type: ui.ErrorFormatter
            loader,  # type: pyutil._ResourceLoader
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

        self.mem = cmd_ev.mem

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('source', cmd_val)
        arg = arg_types.source(attrs.attrs)

        path_arg = arg_r.Peek()
        if path_arg is None:
            e_usage('missing required argument', loc.Missing)
        arg_r.Next()

        # Old:
        #     source --builtin two.sh  # looks up stdlib/two.sh
        # New:
        #     source $LIB_OSH/two.sh  # looks up stdlib/osh/two.sh
        #     source ///osh/two.sh  # looks up stdlib/osh/two.sh
        builtin_path = None  # type: Optional[str]
        if arg.builtin:
            builtin_path = path_arg
        elif path_arg.startswith('///'):
            builtin_path = path_arg[3:]

        if builtin_path is not None:
            try:
                load_path = os_path.join("stdlib", builtin_path)
                contents = self.loader.Get(load_path)
            except (IOError, OSError):
                self.errfmt.Print_('source failed: No builtin file %r' %
                                   load_path,
                                   blame_loc=cmd_val.arg_locs[2])
                return 2

            line_reader = reader.StringLineReader(contents, self.arena)
            c_parser = self.parse_ctx.MakeOshParser(line_reader)
            return self._Exec(cmd_val, arg_r, load_path, c_parser)

        else:
            # 'source' respects $PATH
            resolved = self.search_path.LookupOne(path_arg,
                                                  exec_required=False)
            if resolved is None:
                resolved = path_arg

            try:
                # Shell can't use descriptors 3-9
                f = self.fd_state.Open(resolved)
            except (IOError, OSError) as e:
                self.errfmt.Print_('source %r failed: %s' %
                                   (path_arg, pyutil.strerror(e)),
                                   blame_loc=cmd_val.arg_locs[1])
                return 1

            line_reader = reader.FileLineReader(f, self.arena)
            c_parser = self.parse_ctx.MakeOshParser(line_reader)

            with process.ctx_FileCloser(f):
                return self._Exec(cmd_val, arg_r, path_arg, c_parser)

    def _Exec(self, cmd_val, arg_r, path, c_parser):
        # type: (cmd_value.Argv, args.Reader, str, CommandParser) -> int
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


def _PrintFreeForm(row):
    # type: (Tuple[str, str, Optional[str]]) -> None
    name, kind, resolved = row

    if kind == 'file':
        what = resolved
    elif kind == 'alias':
        what = ('an alias for %s' %
                j8_lite.EncodeString(resolved, unquoted_ok=True))
    else:  # builtin, function, keyword
        what = 'a shell %s' % kind

    # TODO: Should also print haynode

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
                                  cmd_val.typed_args, cmd_val.pos_args,
                                  cmd_val.named_args, cmd_val.block_arg)

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
                          cmd_val.is_last_cmd, cmd_val.typed_args,
                          cmd_val.pos_args, cmd_val.named_args,
                          cmd_val.block_arg)


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
        if not self.procs.Get(name):
            self.errfmt.PrintMessage('runproc: no proc named %r' % name)
            return 1

        cmd_val2 = cmd_value.Argv(argv, locs, cmd_val.is_last_cmd,
                                  cmd_val.typed_args, cmd_val.pos_args,
                                  cmd_val.named_args, cmd_val.block_arg)

        cmd_st = CommandStatus.CreateNull(alloc_lists=True)
        run_flags = executor.IS_LAST_CMD if cmd_val.is_last_cmd else 0
        return self.shell_ex.RunSimpleCommand(cmd_val2, cmd_st, run_flags)


def _ResolveName(
        name,  # type: str
        funcs,  # type: state.Procs
        aliases,  # type: Dict[str, str]
        search_path,  # type: state.SearchPath
        do_all,  # type: bool
):
    # type: (...) -> List[Tuple[str, str, Optional[str]]]

    # MyPy tuple type
    no_str = None  # type: Optional[str]

    results = []  # type: List[Tuple[str, str, Optional[str]]]

    if funcs and funcs.Get(name):
        results.append((name, 'function', no_str))

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
