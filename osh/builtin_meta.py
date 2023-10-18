#!/usr/bin/env python2
"""
builtin_meta.py - Builtins that call back into the interpreter.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value, CommandStatus, value
from _devbuild.gen.syntax_asdl import source, loc
from core import alloc
from core import dev
from core import error
from core import main_loop
from core import process
from core.error import e_die, e_die_status, e_usage
from core import pyutil  # strerror
from core import state
from core import vm
from frontend import flag_spec
from frontend import consts
from frontend import reader
from frontend import typed_args
from mycpp.mylib import log
from pylib import os_path
from osh import cmd_eval

_ = log

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from frontend import args
    from frontend.parse_lib import ParseContext
    from core import optview
    from core import ui
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

        if cmd_val.typed_args:  # eval (myblock)
            rd = typed_args.ReaderForProc(cmd_val)
            block = rd.PosCommand()
            rd.Done()
            return self.cmd_ev.EvalCommand(block)

        # There are no flags, but we need it to respect --
        _, arg_r = flag_spec.ParseCmdVal('eval', cmd_val)

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
        attrs, arg_r = flag_spec.ParseCmdVal('source', cmd_val)
        arg = arg_types.source(attrs.attrs)

        path = arg_r.Peek()
        if path is None:
            e_usage('missing required argument', loc.Missing)
        arg_r.Next()

        if arg.builtin:
            try:
                path = os_path.join("stdlib", path)
                contents = self.loader.Get(path)
            except (IOError, OSError):
                self.errfmt.Print_(
                    'source --builtin %r failed: No such builtin file' % path,
                    blame_loc=cmd_val.arg_locs[2])
                return 2

            line_reader = reader.StringLineReader(contents, self.arena)
            c_parser = self.parse_ctx.MakeOshParser(line_reader)
            return self._Exec(cmd_val, arg_r, path, c_parser)

        else:
            resolved = self.search_path.Lookup(path, exec_required=False)
            if resolved is None:
                resolved = path

            try:
                # Shell can't use descriptors 3-9
                f = self.fd_state.Open(resolved)
            except (IOError, OSError) as e:
                self.errfmt.Print_('source %r failed: %s' %
                                   (path, pyutil.strerror(e)),
                                   blame_loc=cmd_val.arg_locs[1])
                return 1

            line_reader = reader.FileLineReader(f, self.arena)
            c_parser = self.parse_ctx.MakeOshParser(line_reader)

            with process.ctx_FileCloser(f):
                return self._Exec(cmd_val, arg_r, path, c_parser)

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


class Command(vm._Builtin):
    """'command ls' suppresses function lookup."""

    def __init__(
            self,
            shell_ex,  # type: vm._Executor
            funcs,  # type: Dict[str, value.Proc]
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
        attrs, arg_r = flag_spec.ParseCmdVal('command',
                                             cmd_val,
                                             accept_typed_args=True)
        arg = arg_types.command(attrs.attrs)

        argv, locs = arg_r.Rest2()

        if arg.v:
            status = 0
            for kind, argument in _ResolveNames(argv, self.funcs, self.aliases,
                                                self.search_path):
                if kind is None:
                    status = 1  # nothing printed, but we fail
                else:
                    # This is for -v, -V is more detailed.
                    print(argument)
            return status

        cmd_val2 = cmd_value.Argv(argv, locs, cmd_val.typed_args,
                                  cmd_val.pos_args, cmd_val.named_args)

        # If we respected do_fork here instead of passing True, the case
        # 'command date | wc -l' would take 2 processes instead of 3.  But no other
        # shell does that, and this rare case isn't worth the bookkeeping.
        # See test/syscall
        cmd_st = CommandStatus.CreateNull(alloc_lists=True)
        return self.shell_ex.RunSimpleCommand(cmd_val2,
                                              cmd_st,
                                              True,
                                              call_procs=False)


def _ShiftArgv(cmd_val):
    # type: (cmd_value.Argv) -> cmd_value.Argv
    return cmd_value.Argv(cmd_val.argv[1:], cmd_val.arg_locs[1:],
                          cmd_val.typed_args, cmd_val.pos_args,
                          cmd_val.named_args)


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
        # type: (vm._Executor, Dict[str, value.Proc], ui.ErrorFormatter) -> None
        self.shell_ex = shell_ex
        self.procs = procs
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_spec.ParseCmdVal('runproc',
                                         cmd_val,
                                         accept_typed_args=True)
        argv, locs = arg_r.Rest2()

        if len(argv) == 0:
            raise error.Usage('requires arguments', loc.Missing)

        name = argv[0]
        if name not in self.procs:
            self.errfmt.PrintMessage('runproc: no proc named %r' % name)
            return 1

        cmd_val2 = cmd_value.Argv(argv, locs, cmd_val.typed_args,
                                  cmd_val.pos_args, cmd_val.named_args)

        cmd_st = CommandStatus.CreateNull(alloc_lists=True)
        return self.shell_ex.RunSimpleCommand(cmd_val2, cmd_st, True)


class Try(vm._Builtin):
    """Allows explicit handling of errors.

    Takes command argv, or a block:

    try ls /bad

    try {
      var x = 1 / 0

      ls | wc -l

      diff <(sort left.txt) <(sort right.txt)
    }

    TODO:
    - Set _error_str (e.UserErrorString())
    - Set _error_location
    - These could be used by a 'raise' builtin?  Or 'reraise'

    try foo
    if (_status != 0) {
      echo 'hello'
      raise  # reads _status, _error_str, and _error_location ?
    }
    """

    def __init__(
            self,
            mutable_opts,  # type: state.MutableOpts
            mem,  # type: state.Mem
            cmd_ev,  # type: cmd_eval.CommandEvaluator
            shell_ex,  # type: vm._Executor
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.mutable_opts = mutable_opts
        self.mem = mem
        self.shell_ex = shell_ex
        self.cmd_ev = cmd_ev
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_spec.ParseCmdVal('try_',
                                         cmd_val,
                                         accept_typed_args=True)

        cmd = typed_args.OptionalCommand(cmd_val)
        if cmd:
            status = 0  # success by default
            try:
                with state.ctx_Try(self.mutable_opts):
                    unused = self.cmd_ev.EvalCommand(cmd)
            except error.Expr as e:
                status = e.ExitStatus()
            except error.ErrExit as e:
                status = e.ExitStatus()
            except error.UserError as e:
                status = e.ExitStatus()

            self.mem.SetTryStatus(status)
            return 0

        if arg_r.Peek() is None:
            e_usage('expects a block or command argv', loc.Missing)

        argv, locs = arg_r.Rest2()
        cmd_val2 = cmd_value.Argv(argv, locs, cmd_val.typed_args,
                                  cmd_val.pos_args, cmd_val.named_args)

        try:
            # Temporarily turn ON errexit, but don't pass a SPID because we're
            # ENABLING and not disabling.  Note that 'if try myproc' disables it and
            # then enables it!
            with state.ctx_Try(self.mutable_opts):
                # Pass do_fork=True.  Slight annoyance: the real value is a field of
                # command.Simple().  See _NoForkLast() in CommandEvaluator We have an
                # extra fork (miss out on an optimization) of code like ( status ls )
                # or forkwait { status ls }, but that is NOT idiomatic code.  status is
                # for functions.
                cmd_st = CommandStatus.CreateNull(
                    alloc_lists=True)  # TODO: take param
                status = self.shell_ex.RunSimpleCommand(cmd_val2, cmd_st, True)
                #log('st %d', status)
        except error.Expr as e:
            status = e.ExitStatus()
        except error.ErrExit as e:
            status = e.ExitStatus()

        # special variable
        self.mem.SetTryStatus(status)
        return 0


class Error(vm._Builtin):

    def __init__(self):
        # type: () -> None
        pass

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        rd = typed_args.ReaderForProc(cmd_val)
        message = rd.PosStr()
        status = rd.NamedInt('status', 1)
        rd.Done()

        if status == 0:
            e_die('Status must be a non-zero integer', cmd_val.arg_locs[0])

        if len(cmd_val.argv) > 1:
            raise error.TypeErrVerbose(
                'Expected 0 untyped arguments, but got %d' %
                (len(cmd_val.argv) - 1), loc.Missing)

        raise error.UserError(status, message, cmd_val.arg_locs[0])


class BoolStatus(vm._Builtin):

    def __init__(self, shell_ex, errfmt):
        # type: (vm._Executor, ui.ErrorFormatter) -> None
        self.shell_ex = shell_ex
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        _, arg_r = flag_spec.ParseCmdVal('boolstatus', cmd_val)

        if arg_r.Peek() is None:
            e_usage('expected a command to run', loc.Missing)

        argv, locs = arg_r.Rest2()
        cmd_val2 = cmd_value.Argv(argv, locs, cmd_val.typed_args,
                                  cmd_val.pos_args, cmd_val.named_args)

        cmd_st = CommandStatus.CreateNull(alloc_lists=True)
        status = self.shell_ex.RunSimpleCommand(cmd_val2, cmd_st, True)

        if status not in (0, 1):
            e_die_status(status,
                         'boolstatus expected status 0 or 1, got %d' % status,
                         locs[0])

        return status


def _ResolveNames(
        names,  # type: List[str]
        funcs,  # type: Dict[str, value.Proc]
        aliases,  # type: Dict[str, str]
        search_path,  # type: state.SearchPath
):
    # type: (...) -> List[Tuple[str, str]]
    results = []  # type: List[Tuple[str, str]]
    for name in names:
        if name in funcs:
            kind = ('function', name)
        elif name in aliases:
            kind = ('alias', name)

        # TODO: Use match instead?
        elif consts.LookupNormalBuiltin(name) != 0:
            kind = ('builtin', name)
        elif consts.LookupSpecialBuiltin(name) != 0:
            kind = ('builtin', name)
        elif consts.LookupAssignBuiltin(name) != 0:
            kind = ('builtin', name)
        elif consts.IsControlFlow(name):  # continue, etc.
            kind = ('keyword', name)

        elif consts.IsKeyword(name):
            kind = ('keyword', name)
        else:
            resolved = search_path.Lookup(name)
            if resolved is None:
                no_str = None  # type: Optional[str]
                kind = (no_str, name)
            else:
                kind = ('file', resolved)
        results.append(kind)

    return results


class Type(vm._Builtin):

    def __init__(
            self,
            funcs,  # type: Dict[str, value.Proc]
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
        attrs, arg_r = flag_spec.ParseCmdVal('type', cmd_val)
        arg = arg_types.type(attrs.attrs)

        if arg.f:
            funcs = {}  # type: Dict[str, value.Proc]
        else:
            funcs = self.funcs

        status = 0
        r = _ResolveNames(arg_r.Rest(), funcs, self.aliases, self.search_path)
        for kind, name in r:
            if kind is None:
                if not arg.t:  # 'type -t X' is silent in this case
                    self.errfmt.PrintMessage('type: %r not found' % name)
                status = 1  # nothing printed, but we fail
            else:
                if arg.t:
                    print(kind)
                elif arg.p:
                    if kind == 'file':
                        print(name)
                elif arg.P:
                    if kind == 'file':
                        print(name)
                    else:
                        resolved = self.search_path.Lookup(name)
                        if resolved is None:
                            status = 1
                        else:
                            print(resolved)

                else:
                    # Alpine's abuild relies on this text because busybox ash doesn't have
                    # -t!
                    # ash prints "is a shell function" instead of "is a function", but the
                    # regex accouts for that.
                    print('%s is a %s' % (name, kind))
                    if kind == 'function':
                        # bash prints the function body, busybox ash doesn't.
                        pass

        return status
