#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
cmd_eval.py -- Interpreter for the command language.

Problems:
$ < Makefile cat | < NOTES.txt head

This just does head?  Last one wins.
"""
from __future__ import print_function

import sys

from _devbuild.gen.id_kind_asdl import Id, Id_str
from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.syntax_asdl import (
    IntParamBox,
    loc,
    loc_t,
    loc_e,
    Token,
    CompoundWord,
    command,
    command_e,
    command_t,
    command_str,
    condition,
    condition_e,
    condition_t,
    case_arg,
    case_arg_e,
    case_arg_t,
    BraceGroup,
    ArgList,
    assign_op_e,
    expr_t,
    place_expr,
    proc_sig,
    proc_sig_e,
    redir_param,
    redir_param_e,
    for_iter,
    for_iter_e,
    pat,
    pat_e,
)
from _devbuild.gen.runtime_asdl import (
    lvalue,
    lvalue_e,
    value,
    value_e,
    value_t,
    value_str,
    cmd_value,
    cmd_value_e,
    RedirValue,
    redirect_arg,
    flow_e,
    scope_e,
    CommandStatus,
    StatusArray,
    Proc,
)
from _devbuild.gen.types_asdl import redir_arg_type_e

from core import dev
from core import error
from core.error import e_die, e_die_status
from core import pyos  # Time().  TODO: rename
from core import state
from core import ui
from core import util
from core import vm
from frontend import consts
from frontend import lexer
from frontend import location
from osh import braces
from osh import sh_expr_eval
from osh import word_eval
from mycpp import mylib
from mycpp.mylib import log, switch, tagswitch, StrFromC
from ysh import cpython
from ysh import expr_eval
from ysh import val_ops

import posix_ as posix
import libc  # for fnmatch

from typing import List, Dict, Tuple, Optional, Any, cast, TYPE_CHECKING

if TYPE_CHECKING:
    from _devbuild.gen.id_kind_asdl import Id_t
    from _devbuild.gen.option_asdl import builtin_t
    from _devbuild.gen.runtime_asdl import cmd_value_t, Cell, lvalue_t
    from _devbuild.gen.syntax_asdl import Redir, EnvPair
    from core.alloc import Arena
    from core import optview
    from core.vm import _Executor, _AssignBuiltin
    from osh.builtin_trap import TrapState

# flags for main_loop.Batch, ExecuteAndCatch.  TODO: Should probably in
# ExecuteAndCatch, along with SetValue() flags.
IsMainProgram = 1 << 0  # the main shell program, not eval/source/subshell
RaiseControlFlow = 1 << 1  # eval/source builtins
Optimize = 1 << 2

# Python type name -> YSH type name
YSH_TYPE_NAMES = {
    'bool': 'Bool',
    'int': 'Int',
    'float': 'Float',
    'str': 'Str',
    'tuple': 'Tuple',
    'list': 'List',
    'dict': 'Dict',
}


class Deps(object):

    def __init__(self):
        # type: () -> None
        self.mutable_opts = None  # type: state.MutableOpts
        self.dumper = None  # type: dev.CrashDumper
        self.debug_f = None  # type: util._DebugFile


def _PackFlags(keyword_id, flags=0):
    # type: (Id_t, int) -> int

    # Set/Clear are lower 8 bits, and keyword is the rest
    return (keyword_id << 8) | flags


def _HasManyStatuses(node):
    # type: (command_t) -> bool
    """Code patterns that are bad for POSIX errexit.  For YSH strict_errexit.

    Note: strict_errexit also uses
      shopt --unset _allow_command_sub _allow_process_sub
    """
    # Sentence check is for   if false;   versus   if false
    if node.tag() == command_e.Sentence:
        node1 = cast(command.Sentence, node)
        return _HasManyStatuses(node1.child)

    UP_node = node
    with tagswitch(node) as case:
        if case(command_e.Simple, command_e.DBracket, command_e.DParen):
            return False

        elif case(command_e.Pipeline):
            node = cast(command.Pipeline, UP_node)
            if len(node.children) == 1:
                # '! false' is a pipeline that we want to ALLOW
                # '! ( echo subshell )' is DISALLWOED
                return _HasManyStatuses(node.children[0])
            else:
                # Multiple parts like 'ls | wc' is disallowed
                return True

        # - ShAssignment could be allowed, but its exit code will always be 0 without command subs
        # - Naively, (non-singleton) pipelines could be allowed because pipefail.
        #   BUT could be a proc executed inside a child process, which causes a
        #   problem: the strict_errexit check has to occur at runtime and there's
        #   no way to signal it ot the parent.
    return True


def PlusEquals(old_val, val):
    # type: (value_t, value_t) -> value_t
    """Implement s+=val, typeset s+=val, etc."""

    UP_old_val = old_val
    UP_val = val

    tag = val.tag()

    with tagswitch(old_val) as case:
        if case(value_e.Undef):
            pass  # val is RHS

        elif case(value_e.Str):
            if tag == value_e.Str:
                old_val = cast(value.Str, UP_old_val)
                str_to_append = cast(value.Str, UP_val)
                val = value.Str(old_val.s + str_to_append.s)

            elif tag == value_e.BashArray:
                e_die("Can't append array to string")

            else:
                raise AssertionError()  # parsing should prevent this

        elif case(value_e.BashArray):
            if tag == value_e.Str:
                e_die("Can't append string to array")

            elif tag == value_e.BashArray:
                old_val = cast(value.BashArray, UP_old_val)
                to_append = cast(value.BashArray, UP_val)

                # TODO: MUTATE the existing value for efficiency?
                strs = []  # type: List[str]
                strs.extend(old_val.strs)
                strs.extend(to_append.strs)
                val = value.BashArray(strs)

            else:
                raise AssertionError()  # parsing should prevent this

        elif case(value_e.BashAssoc):
            # TODO: Could try to match bash, it will append to ${A[0]}
            pass

        else:
            e_die("Can't append to value of type %s" %
                  value_str(old_val.tag()))

    return val


class Func(vm._Callable):

    def __init__(self, name, node, mem, cmd_ev):
        # type: (str, command.Func, state.Mem, CommandEvaluator) -> None
        self.name = name
        self.node = node
        self.cmd_ev = cmd_ev
        self.mem = mem

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        nargs = len(pos_args)
        expected = len(self.node.pos_params)
        if nargs != expected:
            raise error.InvalidType("%s() expects %d arguments but %d were given" % (self.name, expected, nargs), self.node.keyword)

        nargs = len(named_args)
        expected = len(self.node.named_params)
        if nargs != expected:
            raise error.InvalidType("%s() expects %d named arguments but %d were given" % (self.name, expected, nargs), self.node.keyword)

        with state.ctx_FuncCall(self.cmd_ev.mem, self):
            for i in xrange(0, len(pos_args)):
                pos_arg = pos_args[i]
                pos_param = self.node.pos_params[i]

                arg_name = location.LName(lexer.TokenVal(pos_param.name))
                self.mem.SetValue(arg_name, pos_arg, scope_e.LocalOnly)

            # TODO: pass named args

            try:
                self.cmd_ev._Execute(self.node.body)

                return value.Null  # implicit return
            except vm.ValueControlFlow as e:
                return e.value
            except vm.IntControlFlow as e:
                raise AssertionError('IntControlFlow in func')

        raise AssertionError('unreachable')

class ctx_LoopLevel(object):
    """For checking for invalid control flow."""

    def __init__(self, cmd_ev):
        # type: (CommandEvaluator) -> None
        cmd_ev.loop_level += 1
        self.cmd_ev = cmd_ev

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.cmd_ev.loop_level -= 1


class ctx_ErrTrap(object):
    """For trap ERR."""

    def __init__(self, cmd_ev):
        # type: (CommandEvaluator) -> None
        cmd_ev.running_err_trap = True
        self.cmd_ev = cmd_ev

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.cmd_ev.running_err_trap = False


class CommandEvaluator(object):
    """Executes the program by tree-walking.

    It also does some double-dispatch by passing itself into Eval() for
    Compound/WordPart.
    """

    def __init__(
            self,
            mem,  # type: state.Mem
            exec_opts,  # type: optview.Exec
            errfmt,  # type: ui.ErrorFormatter
            procs,  # type: Dict[str, Proc]
            funcs,  # type: Dict[str, vm._Callable]
            assign_builtins,  # type: Dict[builtin_t, _AssignBuiltin]
            arena,  # type: Arena
            cmd_deps,  # type: Deps
            trap_state,  # type: TrapState
            signal_safe,  # type: pyos.SignalSafe
    ):
        # type: (...) -> None
        """
        Args:
          mem: Mem instance for storing variables
          procs: dict of SHELL functions or 'procs'
          builtins: dict of builtin callables
                    TODO: This should only be for assignment builtins?
          cmd_deps: A bundle of stateless code
        """
        self.shell_ex = None  # type: _Executor
        self.arith_ev = None  # type: sh_expr_eval.ArithEvaluator
        self.bool_ev = None  # type: sh_expr_eval.BoolEvaluator
        self.expr_ev = None  # type: expr_eval.OilEvaluator
        self.word_ev = None  # type: word_eval.AbstractWordEvaluator
        self.tracer = None  # type: dev.Tracer

        self.mem = mem
        # This is for shopt and set -o.  They are initialized by flags.
        self.exec_opts = exec_opts
        self.errfmt = errfmt
        self.procs = procs
        self.funcs = funcs
        self.assign_builtins = assign_builtins
        self.arena = arena

        self.mutable_opts = cmd_deps.mutable_opts
        self.dumper = cmd_deps.dumper
        self.debug_f = cmd_deps.debug_f  # Used by ShellFuncAction too

        self.trap_state = trap_state
        self.signal_safe = signal_safe

        self.running_err_trap = False
        self.loop_level = 0  # for detecting bad top-level break/continue
        self.check_command_sub_status = False  # a hack.  Modified by ShellExecutor

    def CheckCircularDeps(self):
        # type: () -> None
        assert self.arith_ev is not None
        assert self.bool_ev is not None
        # Disabled for push OSH
        #assert self.expr_ev is not None
        assert self.word_ev is not None

    def _RunAssignBuiltin(self, cmd_val):
        # type: (cmd_value.Assign) -> int
        """Run an assignment builtin.

        Except blocks copied from RunBuiltin.
        """
        builtin_func = self.assign_builtins.get(cmd_val.builtin_id)
        if builtin_func is None:
            # This only happens with alternative Oils interpreters.
            e_die("Assignment builtin %r not configured" % cmd_val.argv[0],
                  cmd_val.arg_locs[0])

        with vm.ctx_FlushStdout():
            with ui.ctx_Location(self.errfmt, cmd_val.arg_locs[0]):
                try:
                    status = builtin_func.Run(cmd_val)
                except error.Usage as e:  # Copied from RunBuiltin
                    arg0 = cmd_val.argv[0]
                    if not e.HasLocation():  # fill in default location.
                        e.location = self.errfmt.CurrentLocation()
                    self.errfmt.PrefixPrint(e.msg, '%r ' % arg0, e.location)
                    status = 2  # consistent error code for usage error

        return status

    def _CheckStatus(self, status, cmd_st, node, default_loc):
        # type: (int, CommandStatus, command_t, loc_t) -> None
        """Raises error.ErrExit, maybe with location info attached."""

        assert status >= 0, status

        if status == 0:
            return  # Nothing to do

        self._MaybeRunErrTrap()

        if self.exec_opts.errexit():
            # NOTE: Sometimes we print 2 errors
            # - 'type -z' has a UsageError with location, then errexit
            # - '> /nonexistent' has an I/O error, then errexit
            # - Pipelines and subshells are compound.  Commands within them fail.
            #   - however ( exit 33 ) only prints one message.
            #
            # But we will want something like 'false' to have location info.

            UP_node = node
            with tagswitch(node) as case:
                if case(command_e.ShAssignment):
                    node = cast(command.ShAssignment, UP_node)
                    cmd_st.show_code = True  # leaf
                    # Note: we show errors from assignments a=$(false) rarely: when
                    # errexit, inherit_errexit, verbose_errexit are on, but
                    # command_sub_errexit is off!

                # Note: a subshell often doesn't fail on its own.
                elif case(command_e.Subshell):
                    node = cast(command.Subshell, UP_node)
                    cmd_st.show_code = True  # not sure about this, e.g. ( exit 42 )

                elif case(command_e.Pipeline):
                    node = cast(command.Pipeline, UP_node)
                    cmd_st.show_code = True  # not sure about this
                    # TODO: We should show which element of the pipeline failed!

            desc = StrFromC(command_str(node.tag()))

            # Override location if explicitly passed.
            # Note: this produces better results for process sub
            #   echo <(sort x)
            # and different results for some pipelines:
            #   { ls; false; } | wc -l; echo hi  # Point to | or first { ?
            if default_loc.tag() != loc_e.Missing:
                blame_loc = default_loc  # type: loc_t
            else:
                blame_loc = location.TokenForCommand(node)

            msg = '%s failed with status %d' % (desc, status)
            raise error.ErrExit(status,
                                msg,
                                blame_loc,
                                show_code=cmd_st.show_code)

    def _EvalRedirect(self, r):
        # type: (Redir) -> RedirValue

        result = RedirValue(r.op.id, r.op, r.loc, None)

        arg = r.arg
        UP_arg = arg
        with tagswitch(arg) as case:
            if case(redir_param_e.Word):
                arg_word = cast(CompoundWord, UP_arg)

                # note: needed for redirect like 'echo foo > x$LINENO'
                self.mem.SetLocationToken(r.op)

                redir_type = consts.RedirArgType(
                    r.op.id)  # could be static in the LST?

                if redir_type == redir_arg_type_e.Path:
                    # NOTES
                    # - no globbing.  You can write to a file called '*.py'.
                    # - set -o strict-array prevents joining by spaces
                    val = self.word_ev.EvalWordToString(arg_word)
                    filename = val.s
                    if len(filename) == 0:
                        # Whether this is fatal depends on errexit.
                        raise error.RedirectEval(
                            "Redirect filename can't be empty", arg_word)

                    result.arg = redirect_arg.Path(filename)
                    return result

                elif redir_type == redir_arg_type_e.Desc:  # e.g. 1>&2, 1>&-, 1>&2-
                    val = self.word_ev.EvalWordToString(arg_word)
                    t = val.s
                    if len(t) == 0:
                        raise error.RedirectEval(
                            "Redirect descriptor can't be empty", arg_word)
                        return None

                    try:
                        if t == '-':
                            result.arg = redirect_arg.CloseFd
                        elif t[-1] == '-':
                            target_fd = int(t[:-1])
                            result.arg = redirect_arg.MoveFd(target_fd)
                        else:
                            result.arg = redirect_arg.CopyFd(int(t))
                    except ValueError:
                        raise error.RedirectEval(
                            'Invalid descriptor %r.  Expected D, -, or D- where D is an '
                            'integer' % t, arg_word)
                        return None

                    return result

                elif redir_type == redir_arg_type_e.Here:  # here word
                    val = self.word_ev.EvalWordToString(arg_word)
                    assert val.tag() == value_e.Str, val
                    # NOTE: bash and mksh both add \n
                    result.arg = redirect_arg.HereDoc(val.s + '\n')
                    return result

                else:
                    raise AssertionError('Unknown redirect op')

            elif case(redir_param_e.HereDoc):
                arg = cast(redir_param.HereDoc, UP_arg)
                w = CompoundWord(
                    arg.stdin_parts)  # HACK: Wrap it in a word to eval
                val = self.word_ev.EvalWordToString(w)
                assert val.tag() == value_e.Str, val
                result.arg = redirect_arg.HereDoc(val.s)
                return result

            else:
                raise AssertionError('Unknown redirect type')

        raise AssertionError('for -Wreturn-type in C++')

    def _EvalRedirects(self, node):
        # type: (command_t) -> List[RedirValue]
        """Evaluate redirect nodes to concrete objects.

        We have to do this every time, because you could have something like:

        for i in a b c; do
          echo foo >$i
        done

        Does it makes sense to just have RedirectNode.Eval?  Nah I think the
        Redirect() abstraction in process.py is useful.  It has a lot of methods.

        Raises:
          error.RedirectEval
        """
        # This is kind of lame because we have two switches over command_e: one for
        # redirects, and to evaluate the node.  But it's what you would do in C++ I
        # suppose.  We could also inline them.  Or maybe use RAII.
        UP_node = node
        with tagswitch(node) as case:
            if case(command_e.Simple):
                node = cast(command.Simple, UP_node)
                redirects = node.redirects
            elif case(command_e.ExpandedAlias):
                node = cast(command.ExpandedAlias, UP_node)
                redirects = node.redirects
            elif case(command_e.ShAssignment):
                node = cast(command.ShAssignment, UP_node)
                redirects = node.redirects
            elif case(command_e.BraceGroup):
                node = cast(BraceGroup, UP_node)
                redirects = node.redirects
            elif case(command_e.Subshell):
                node = cast(command.Subshell, UP_node)
                redirects = node.redirects
            elif case(command_e.DParen):
                node = cast(command.DParen, UP_node)
                redirects = node.redirects
            elif case(command_e.DBracket):
                node = cast(command.DBracket, UP_node)
                redirects = node.redirects
            elif case(command_e.ForEach):
                node = cast(command.ForEach, UP_node)
                redirects = node.redirects
            elif case(command_e.ForExpr):
                node = cast(command.ForExpr, UP_node)
                redirects = node.redirects
            elif case(command_e.WhileUntil):
                node = cast(command.WhileUntil, UP_node)
                redirects = node.redirects
            elif case(command_e.If):
                node = cast(command.If, UP_node)
                redirects = node.redirects
            elif case(command_e.Case):
                node = cast(command.Case, UP_node)
                redirects = node.redirects
            else:
                # command_e.NoOp, command_e.ControlFlow, command_e.Pipeline,
                # command_e.AndOr, command_e.CommandList, command_e.DoGroup,
                # command_e.Sentence, # command_e.TimeBlock, command_e.ShFunction,
                # YSH:
                # command_e.VarDecl, command_e.PlaceMutation,
                # command_e.Proc, command_e.Func, command_e.Expr,
                # command_e.BareDecl
                redirects = []

        result = []  # type: List[RedirValue]
        for redir in redirects:
            result.append(self._EvalRedirect(redir))

        return result

    def _RunSimpleCommand(self, cmd_val, cmd_st, do_fork):
        # type: (cmd_value_t, CommandStatus, bool) -> int
        """Private interface to run a simple command (including assignment)."""
        UP_cmd_val = cmd_val
        with tagswitch(UP_cmd_val) as case:
            if case(cmd_value_e.Argv):
                cmd_val = cast(cmd_value.Argv, UP_cmd_val)
                self.tracer.OnSimpleCommand(cmd_val.argv)
                return self.shell_ex.RunSimpleCommand(cmd_val, cmd_st, do_fork)

            elif case(cmd_value_e.Assign):
                cmd_val = cast(cmd_value.Assign, UP_cmd_val)
                self.tracer.OnAssignBuiltin(cmd_val)
                return self._RunAssignBuiltin(cmd_val)

            else:
                raise AssertionError()

    def _EvalTempEnv(self, more_env, flags):
        # type: (List[EnvPair], int) -> None
        """For FOO=1 cmd."""
        for e_pair in more_env:
            val = self.word_ev.EvalRhsWord(e_pair.val)
            # Set each var so the next one can reference it.  Example:
            # FOO=1 BAR=$FOO ls /
            self.mem.SetValue(location.LName(e_pair.name),
                              val,
                              scope_e.LocalOnly,
                              flags=flags)

    def _StrictErrExit(self, node):
        # type: (command_t) -> None
        if not (self.exec_opts.errexit() and self.exec_opts.strict_errexit()):
            return

        if _HasManyStatuses(node):
            node_str = ui.CommandType(node)
            e_die(
                "strict_errexit only allows simple commands in conditionals (got %s). "
                % node_str, loc.Command(node))

    def _StrictErrExitList(self, node_list):
        # type: (List[command_t]) -> None
        """Not allowed, too confusing:

        if grep foo eggs.txt; grep bar eggs.txt; then   echo hi fi
        """
        if not (self.exec_opts.errexit() and self.exec_opts.strict_errexit()):
            return

        if len(node_list) > 1:
            e_die(
                "strict_errexit only allows a single command.  Hint: use 'try'.",
                loc.Command(node_list[0]))

        assert len(node_list) > 0
        node = node_list[0]
        if _HasManyStatuses(node):
            # TODO: consolidate error message with above
            node_str = ui.CommandType(node)
            e_die(
                "strict_errexit only allows simple commands in conditionals (got %s). "
                % node_str, loc.Command(node))

    def _EvalCondition(self, cond, blame_tok):
        # type: (condition_t, Token) -> bool
        """
        Args:
          spid: for OSH conditions, where errexit was disabled -- e.g. if
                for YSH conditions, it would be nice to blame the ( instead
        """
        b = False
        UP_cond = cond
        with tagswitch(cond) as case:
            if case(condition_e.Shell):
                cond = cast(condition.Shell, UP_cond)
                self._StrictErrExitList(cond.commands)
                with state.ctx_ErrExit(self.mutable_opts, False, blame_tok):
                    cond_status = self._ExecuteList(cond.commands)

                b = cond_status == 0

            elif case(condition_e.YshExpr):
                cond = cast(condition.YshExpr, UP_cond)
                obj = self.expr_ev.EvalExpr(cond.e, blame_tok)
                b = val_ops.ToBool(obj)

        return b

    def _EvalCaseArg(self, arg, blame):
        # type: (case_arg_t, loc_t) -> value_t
        """Evaluate a `case_arg` into a `value_t` which can be matched on in a case
        command.
        """
        UP_arg = arg
        with tagswitch(arg) as case:
            if case(case_arg_e.Word):
                arg = cast(case_arg.Word, UP_arg)
                return self.word_ev.EvalWordToString(arg.w)

            elif case(case_arg_e.YshExpr):
                arg = cast(case_arg.YshExpr, UP_arg)
                return self.expr_ev.EvalExpr(arg.e, blame)

            else:
                raise NotImplementedError()

    def _Dispatch(self, node, cmd_st):
        # type: (command_t, CommandStatus) -> int
        """Switch on the command_t variants and execute them."""

        # If we call RunCommandSub in a recursive call to the executor, this will
        # be set true (if strict_errexit is false).  But it only lasts for one
        # command.
        self.check_command_sub_status = False

        UP_node = node
        with tagswitch(node) as case:
            if case(command_e.Simple):
                node = cast(command.Simple, UP_node)

                cmd_st.check_errexit = True

                # for $LINENO, e.g.  PS4='+$SOURCE_NAME:$LINENO:'
                # Note that for '> $LINENO' the location token is set in _EvalRedirect.
                # TODO: blame_tok should always be set.
                if node.blame_tok is not None:
                    self.mem.SetLocationToken(node.blame_tok)

                self._MaybeRunDebugTrap()

                # PROBLEM: We want to log argv in 'xtrace' mode, but we may have already
                # redirected here, which screws up logging.  For example, 'echo hi
                # >/dev/null 2>&1'.  We want to evaluate argv and log it BEFORE applying
                # redirects.

                # Another problem:
                # - tracing can be called concurrently from multiple processes, leading
                # to overlap.  Maybe have a mode that creates a file per process.
                # xtrace-proc
                # - line numbers for every command would be very nice.  But then you have
                # to print the filename too.

                words = braces.BraceExpandWords(node.words)

                # Note: Individual WORDS can fail
                # - $() and <() can have failures.  This can happen in DBracket,
                #   DParen, etc. too
                # - Tracing: this can start processes for proc sub and here docs!
                cmd_val = self.word_ev.EvalWordSequence2(words,
                                                         allow_assign=True)

                UP_cmd_val = cmd_val
                if UP_cmd_val.tag() == cmd_value_e.Argv:
                    cmd_val = cast(cmd_value.Argv, UP_cmd_val)

                    if len(cmd_val.argv):  # it can be empty in rare cases
                        self.mem.SetLastArgument(cmd_val.argv[-1])
                    else:
                        self.mem.SetLastArgument('')

                    typed_args = None  # type: ArgList
                    if node.typed_args:
                        orig = node.typed_args
                        # COPY positional args because we may append an arg
                        typed_args = ArgList(orig.left, list(orig.positional),
                                             orig.named, orig.right)

                        # the block is the last argument
                        if node.block:
                            typed_args.positional.append(node.block)
                            # ArgList already has a spid in this case
                    else:
                        if node.block:
                            # Create ArgList for the block.  Since we have { } and not (),
                            # copy them from BraceGroup
                            typed_args = ArgList(node.block.brace_group.left,
                                                 [node.block], [],
                                                 node.block.brace_group.right)

                    cmd_val.typed_args = typed_args

                else:
                    if node.block:
                        e_die("ShAssignment builtins don't accept blocks",
                              node.block.brace_group.left)
                    cmd_val = cast(cmd_value.Assign, UP_cmd_val)

                    # Could reset $_ after assignment, but then we'd have to do it for
                    # all YSH constructs too.  It's easier to let it persist.  Other
                    # shells aren't consistent.
                    # self.mem.SetLastArgument('')

                # NOTE: RunSimpleCommand never returns when do_fork=False!
                if len(node.more_env):  # I think this guard is necessary?
                    is_other_special = False  # TODO: There are other special builtins too!
                    if cmd_val.tag() == cmd_value_e.Assign or is_other_special:
                        # Special builtins have their temp env persisted.
                        self._EvalTempEnv(node.more_env, 0)
                        status = self._RunSimpleCommand(
                            cmd_val, cmd_st, node.do_fork)
                    else:
                        with state.ctx_Temp(self.mem):
                            self._EvalTempEnv(node.more_env, state.SetExport)
                            status = self._RunSimpleCommand(
                                cmd_val, cmd_st, node.do_fork)
                else:
                    status = self._RunSimpleCommand(cmd_val, cmd_st,
                                                    node.do_fork)

            elif case(command_e.ExpandedAlias):
                node = cast(command.ExpandedAlias, UP_node)
                # Expanded aliases need redirects and env bindings from the calling
                # context, as well as redirects in the expansion!

                # TODO: SetLocationToken to OUTSIDE?  Don't bother with stuff inside
                # expansion, since aliases are discouraged.

                if len(node.more_env):
                    with state.ctx_Temp(self.mem):
                        self._EvalTempEnv(node.more_env, state.SetExport)
                        status = self._Execute(node.child)
                else:
                    status = self._Execute(node.child)

            elif case(command_e.Sentence):
                node = cast(command.Sentence, UP_node)
                # Don't check_errexit since this isn't a real node!
                if node.terminator.id == Id.Op_Semi:
                    status = self._Execute(node.child)
                else:
                    status = self.shell_ex.RunBackgroundJob(node.child)

            elif case(command_e.Pipeline):
                node = cast(command.Pipeline, UP_node)
                cmd_st.check_errexit = True
                for op in node.ops:
                    if op.id != Id.Op_Pipe:
                        e_die("|& isn't supported", op)

                # Remove $_ before pipeline.  This matches bash, and is important in
                # pipelines than assignments because pipelines are non-deterministic.
                self.mem.SetLastArgument('')

                # Set status to INVALID value, because we MIGHT set cmd_st.pipe_status,
                # which _Execute() boils down into a status for us.
                status = -1

                if node.negated is not None:
                    self._StrictErrExit(node)
                    with state.ctx_ErrExit(self.mutable_opts, False,
                                           node.negated):
                        # '! grep' is parsed as a pipeline, according to the grammar, but
                        # there's no pipe() call.
                        if len(node.children) == 1:
                            tmp_status = self._Execute(node.children[0])
                            status = 1 if tmp_status == 0 else 0
                        else:
                            self.shell_ex.RunPipeline(node, cmd_st)
                            cmd_st.pipe_negated = True

                    # errexit is disabled for !.
                    cmd_st.check_errexit = False
                else:
                    self.shell_ex.RunPipeline(node, cmd_st)

            elif case(command_e.Subshell):
                node = cast(command.Subshell, UP_node)
                cmd_st.check_errexit = True
                status = self.shell_ex.RunSubshell(node.child)

            elif case(command_e.DBracket):
                node = cast(command.DBracket, UP_node)
                self.mem.SetLocationToken(node.left)
                self._MaybeRunDebugTrap()

                self.tracer.PrintSourceCode(node.left, node.right, self.arena)

                cmd_st.check_errexit = True
                cmd_st.show_code = True  # this is a "leaf" for errors
                result = self.bool_ev.EvalB(node.expr)
                status = 0 if result else 1

            elif case(command_e.DParen):
                node = cast(command.DParen, UP_node)
                self.mem.SetLocationToken(node.left)
                self._MaybeRunDebugTrap()

                self.tracer.PrintSourceCode(node.left, node.right, self.arena)

                cmd_st.check_errexit = True
                cmd_st.show_code = True  # this is a "leaf" for errors
                i = self.arith_ev.EvalToInt(node.child)
                status = 1 if i == 0 else 0

            elif case(command_e.VarDecl):
                node = cast(command.VarDecl, UP_node)

                # x = 'foo' in Hay blocks
                if node.keyword is None or node.keyword.id == Id.KW_Const:
                    self.mem.SetLocationToken(
                        node.lhs[0].name)  # point to var name

                    # Note: there's only one LHS
                    vd_lval = location.LName(
                        node.lhs[0].name.tval)  # type: lvalue_t
                    val = self.expr_ev.EvalExpr(node.rhs, loc.Missing)

                    self.mem.SetValue(vd_lval,
                                      val,
                                      scope_e.LocalOnly,
                                      flags=_PackFlags(Id.KW_Const,
                                                       state.SetReadOnly))

                else:
                    self.mem.SetLocationToken(node.keyword)  # point to var

                    # TODO: optimize this common case (but measure)
                    assert len(node.lhs) == 1, node.lhs

                    vd_lval = location.LName(node.lhs[0].name.tval)
                    val = self.expr_ev.EvalExpr(node.rhs, loc.Missing)
                    self.mem.SetValue(vd_lval,
                                      val,
                                      scope_e.LocalOnly,
                                      flags=_PackFlags(node.keyword.id))

                status = 0

            elif case(command_e.PlaceMutation):

                node = cast(command.PlaceMutation, UP_node)
                self.mem.SetLocationToken(node.keyword)  # point to setvar/set

                with switch(node.keyword.id) as case2:
                    if case2(Id.KW_SetVar):
                        which_scopes = scope_e.LocalOnly
                    elif case2(Id.KW_SetGlobal):
                        which_scopes = scope_e.GlobalOnly
                    elif case2(Id.KW_SetRef):
                        # The out param is LOCAL, but the nameref lookup is dynamic
                        which_scopes = scope_e.LocalOnly
                    else:
                        raise AssertionError(node.keyword.id)

                if node.op.id == Id.Arith_Equal:
                    right_val = self.expr_ev.EvalExpr(node.rhs, loc.Missing)
                    UP_right_val = right_val

                    places = None  # type: List[lvalue_t]
                    rhs_vals = None  # type: List[value_t]

                    num_lhs = len(node.lhs)
                    if num_lhs == 1:
                        places = [self.expr_ev.EvalPlaceExpr(node.lhs[0])]
                        rhs_vals = [right_val]
                    else:
                        if right_val.tag() != value_e.List:
                            raise error.InvalidType2(right_val,
                                                     'expected a List',
                                                     loc.Missing)
                        right_val = cast(value.List, UP_right_val)

                        num_rhs = len(right_val.items)
                        if num_lhs != num_rhs:
                            raise error.Expr('%d != %d' % (num_lhs, num_rhs),
                                             loc.Missing)

                        places = []
                        rhs_vals = []
                        for i, lhs_val in enumerate(node.lhs):
                            places.append(self.expr_ev.EvalPlaceExpr(lhs_val))
                            rhs_vals.append(right_val.items[i])

                    for i, place in enumerate(places):
                        rval = rhs_vals[i]
                        UP_place = place
                        tag = place.tag()

                        if tag == lvalue_e.ObjIndex:
                            # setvar mylist[0] = 42
                            # setvar mydict['key'] = 42
                            place = cast(lvalue.ObjIndex, UP_place)

                            obj = place.obj
                            UP_obj = obj
                            with tagswitch(obj) as case:
                                if case(value_e.BashArray):
                                    obj = cast(value.BashArray, UP_obj)
                                    index = val_ops.ToInt(place.index,
                                                          loc.Missing,
                                                          prefix='List index ')
                                    r = val_ops.ToStr(rval,
                                                      loc.Missing,
                                                      prefix='List index ')
                                    obj.strs[index] = r

                                elif case(value_e.List):
                                    obj = cast(value.List, UP_obj)
                                    index = val_ops.ToInt(place.index,
                                                          loc.Missing,
                                                          prefix='List index ')
                                    obj.items[index] = rval

                                elif case(value_e.BashAssoc):
                                    obj = cast(value.BashAssoc, UP_obj)
                                    key = val_ops.ToStr(
                                        place.index,
                                        loc.Missing,
                                        prefix='BashAssoc index ')
                                    r = val_ops.ToStr(
                                        rval,
                                        loc.Missing,
                                        prefix='BashAssoc index ')
                                    obj.d[key] = r

                                elif case(value_e.Dict):
                                    obj = cast(value.Dict, UP_obj)
                                    key = val_ops.ToStr(place.index,
                                                        loc.Missing,
                                                        prefix='Dict index ')
                                    obj.d[key] = rval

                                else:
                                    raise error.InvalidType2(
                                        obj,
                                        "obj[index] expected List or Dict",
                                        loc.Missing)

                            if node.keyword.id == Id.KW_SetRef:
                                e_die('setref obj[index] not implemented')

                        else:
                            #val = cpython._PyObjToValue(py_val)
                            # top level variable
                            self.mem.SetValue(place,
                                              rval,
                                              which_scopes,
                                              flags=_PackFlags(
                                                  node.keyword.id))

                # TODO: Other augmented assignments
                elif node.op.id == Id.Arith_PlusEqual:
                    # NOTE: x, y += 1 in Python is a SYNTAX error, but it's checked in the
                    # transformer and not the grammar.  We should do that too.

                    place2 = cast(place_expr.Var, node.lhs[0])
                    pe_lval = location.LName(place2.name.tval)
                    val = self.expr_ev.EvalExpr(node.rhs, loc.Missing)

                    new_val = self.expr_ev.EvalPlusEquals(pe_lval, val)

                    self.mem.SetValue(pe_lval,
                                      new_val,
                                      which_scopes,
                                      flags=_PackFlags(node.keyword.id))

                else:
                    raise NotImplementedError(Id_str(node.op.id))

                status = 0  # TODO: what should status be?

            elif case(command_e.ShAssignment):  # Only unqualified assignment
                node = cast(command.ShAssignment, UP_node)

                # x=y is 'neutered' inside 'proc'
                which_scopes = self.mem.ScopesForWriting()

                for pair in node.pairs:
                    self.mem.SetLocationToken(pair.left)

                    if pair.op == assign_op_e.PlusEqual:
                        assert pair.rhs, pair.rhs  # I don't think a+= is valid?
                        rhs = self.word_ev.EvalRhsWord(pair.rhs)

                        lval = self.arith_ev.EvalShellLhs(
                            pair.lhs, which_scopes)
                        # do not respect set -u
                        old_val = sh_expr_eval.OldValue(lval, self.mem, None)

                        val = PlusEquals(old_val, rhs)

                    else:  # plain assignment
                        lval = self.arith_ev.EvalShellLhs(
                            pair.lhs, which_scopes)

                        # RHS can be a string or array.
                        if pair.rhs:
                            val = self.word_ev.EvalRhsWord(pair.rhs)
                            assert isinstance(val, value_t), val

                        else:  # e.g. 'readonly x' or 'local x'
                            val = None

                    # NOTE: In bash and mksh, declare -a myarray makes an empty cell with
                    # Undef value, but the 'array' attribute.

                    #log('setting %s to %s with flags %s', lval, val, flags)
                    flags = 0
                    self.mem.SetValue(lval, val, which_scopes, flags=flags)
                    self.tracer.OnShAssignment(lval, pair.op, val, flags,
                                               which_scopes)

                self._MaybeRunDebugTrap()

                # PATCH to be compatible with existing shells: If the assignment had a
                # command sub like:
                #
                # s=$(echo one; false)
                #
                # then its status will be in mem.last_status, and we can check it here.
                # If there was NOT a command sub in the assignment, then we don't want to
                # check it.

                # Only do this if there was a command sub?  How?  Look at node?
                # Set a flag in mem?   self.mem.last_status or
                if self.check_command_sub_status:
                    last_status = self.mem.LastStatus()
                    self._CheckStatus(last_status, cmd_st, node, loc.Missing)
                    status = last_status  # A global assignment shouldn't clear $?.
                else:
                    status = 0

            elif case(command_e.Expr):
                node = cast(command.Expr, UP_node)

                if mylib.PYTHON:
                    self.mem.SetLocationToken(node.keyword)
                    val = self.expr_ev.EvalExpr(node.e, loc.Missing)
                    obj = cpython._ValueToPyObj(val)

                    if node.keyword.id == Id.Lit_Equals:
                        # NOTE: It would be nice to unify this with 'repr', but there isn't a
                        # good way to do it with the value/PyObject split.
                        class_name = obj.__class__.__name__
                        oil_name = YSH_TYPE_NAMES.get(class_name, class_name)
                        print('(%s)   %s' % (oil_name, repr(obj)))

                        # BUG FIX related to forking!  Note that BUILTINS flush, but
                        # keywords don't flush.  So we have to beware of keywords that
                        # print.  TODO: Or avoid Python's print() altogether.
                        sys.stdout.flush()

                # TODO: What about exceptions?  They just throw?
                status = 0

            elif case(command_e.Retval):
                node = cast(command.Retval, UP_node)

                val = self.expr_ev.EvalExpr(node.val, node.keyword)
                raise vm.ValueControlFlow(node.keyword, val)

            elif case(command_e.ControlFlow):
                node = cast(command.ControlFlow, UP_node)
                keyword = node.keyword

                if node.arg_word:  # Evaluate the argument
                    str_val = self.word_ev.EvalWordToString(node.arg_word)

                    # Quirk: We need 'return $empty' to be valid for libtool.  This is
                    # another meaning of strict_control_flow, which also has to do with
                    # break/continue at top level.  It has the side effect of making
                    # 'return ""' valid, which shells other than zsh fail on.
                    if len(str_val.s
                           ) == 0 and not self.exec_opts.strict_control_flow():
                        arg = 0
                    else:
                        try:
                            # They all take integers.  NOTE: dash is the only shell that
                            # disallows -1!  Others wrap to 255.
                            arg = int(str_val.s)
                        except ValueError:
                            e_die(
                                '%r expected a number, got %r' %
                                (lexer.TokenVal(keyword), str_val.s),
                                loc.Word(node.arg_word))
                else:
                    if keyword.id in (Id.ControlFlow_Exit,
                                      Id.ControlFlow_Return):
                        arg = self.mem.LastStatus()
                    else:
                        arg = 1  # break or continue 1 level by default

                self.tracer.OnControlFlow(keyword.tval, arg)

                # NOTE: A top-level 'return' is OK, unlike in bash.  If you can return
                # from a sourced script, it makes sense to return from a main script.
                ok = True
                if (keyword.id
                        in (Id.ControlFlow_Break, Id.ControlFlow_Continue)
                        and self.loop_level == 0):
                    ok = False

                if ok:
                    if keyword.id == Id.ControlFlow_Exit:
                        raise util.UserExit(
                            arg)  # handled differently than other control flow
                    else:
                        raise vm.IntControlFlow(keyword, arg)
                else:
                    msg = 'Invalid control flow at top level'
                    if self.exec_opts.strict_control_flow():
                        e_die(msg, keyword)
                    else:
                        # Only print warnings, never fatal.
                        # Bash oddly only exits 1 for 'return', but no other shell does.
                        self.errfmt.PrefixPrint(msg, 'warning: ', keyword)
                        status = 0

            # Note CommandList and DoGroup have no redirects, but BraceGroup does.
            # DoGroup has 'do' and 'done' spids for translation.
            elif case(command_e.CommandList):
                node = cast(command.CommandList, UP_node)
                status = self._ExecuteList(node.children)
                cmd_st.check_errexit = False

            elif case(command_e.DoGroup):
                node = cast(command.DoGroup, UP_node)
                status = self._ExecuteList(node.children)
                cmd_st.check_errexit = False  # not real statements

            elif case(command_e.BraceGroup):
                node = cast(BraceGroup, UP_node)
                status = self._ExecuteList(node.children)
                cmd_st.check_errexit = False

            elif case(command_e.AndOr):
                node = cast(command.AndOr, UP_node)
                # NOTE: && and || have EQUAL precedence in command mode.  See case #13
                # in dbracket.test.sh.

                left = node.children[0]

                # Suppress failure for every child except the last one.
                self._StrictErrExit(left)
                with state.ctx_ErrExit(self.mutable_opts, False, node.ops[0]):
                    status = self._Execute(left)

                i = 1
                n = len(node.children)
                while i < n:
                    #log('i %d status %d', i, status)
                    child = node.children[i]
                    op = node.ops[i - 1]
                    op_id = op.id

                    #log('child %s op_id %s', child, op_id)

                    if op_id == Id.Op_DPipe and status == 0:
                        i += 1
                        continue  # short circuit

                    elif op_id == Id.Op_DAmp and status != 0:
                        i += 1
                        continue  # short circuit

                    if i == n - 1:  # errexit handled differently for last child
                        status = self._Execute(child)
                        cmd_st.check_errexit = True
                    else:
                        # blame the right && or ||
                        self._StrictErrExit(child)
                        with state.ctx_ErrExit(self.mutable_opts, False, op):
                            status = self._Execute(child)

                    i += 1

            elif case(command_e.WhileUntil):
                node = cast(command.WhileUntil, UP_node)
                status = 0

                with ctx_LoopLevel(self):
                    while True:
                        try:
                            # blame while/until spid
                            b = self._EvalCondition(node.cond, node.keyword)
                            if node.keyword.id == Id.KW_Until:
                                b = not b
                            if not b:
                                break
                            status = self._Execute(node.body)  # last one wins

                        except vm.IntControlFlow as e:
                            status = 0
                            action = e.HandleLoop()
                            if action == flow_e.Break:
                                break
                            elif action == flow_e.Raise:
                                raise

            elif case(command_e.ForEach):
                node = cast(command.ForEach, UP_node)
                self.mem.SetLocationToken(node.keyword)  # for x in $LINENO

                # for the 2 kinds of shell loop
                iter_list = None  # type: List[str]

                # for YSH loop
                iter_expr = None  # type: expr_t
                #iter_blame = None  # type: Token

                iterable = node.iterable
                UP_iterable = iterable

                with tagswitch(node.iterable) as case:
                    if case(for_iter_e.Args):
                        iter_list = self.mem.GetArgv()

                    elif case(for_iter_e.Words):
                        iterable = cast(for_iter.Words, UP_iterable)
                        words = braces.BraceExpandWords(iterable.words)
                        iter_list = self.word_ev.EvalWordSequence(words)

                    elif case(for_iter_e.YshExpr):
                        iterable = cast(for_iter.YshExpr, UP_iterable)
                        iter_expr = iterable.e
                        iter_expr_blame = iterable.blame

                n = len(node.iter_names)
                assert n > 0

                i_name = None  # type: Optional[lvalue_t]
                # required
                name1 = None  # type: lvalue_t
                name2 = None  # type: Optional[lvalue_t]

                it2 = None  # type: val_ops._ContainerIter
                if iter_list is None:  # for_expr.YshExpr
                    val = self.expr_ev.EvalExpr(iter_expr, loc.Missing)

                    UP_val = val
                    with tagswitch(val) as case:
                        if case(value_e.List):
                            val = cast(value.List, UP_val)
                            it2 = val_ops.ListIterator(val)

                            if n == 1:
                                name1 = location.LName(node.iter_names[0])
                            elif n == 2:
                                i_name = location.LName(node.iter_names[0])
                                name1 = location.LName(node.iter_names[1])
                            else:
                                # This is similar to a parse error
                                e_die_status(
                                    2,
                                    'List iteration expects at most 2 loop variables',
                                    node.keyword)

                        elif case(value_e.Dict):
                            val = cast(value.Dict, UP_val)
                            it2 = val_ops.DictIterator(val)

                            if n == 1:
                                name1 = location.LName(node.iter_names[0])
                            elif n == 2:
                                name1 = location.LName(node.iter_names[0])
                                name2 = location.LName(node.iter_names[1])
                            elif n == 3:
                                i_name = location.LName(node.iter_names[0])
                                name1 = location.LName(node.iter_names[1])
                                name2 = location.LName(node.iter_names[2])
                            else:
                                raise AssertionError()

                        else:
                            raise error.InvalidType2(
                                val, 'for loop expected List or Dict',
                                node.keyword)
                else:
                    #log('iter list %s', iter_list)
                    it2 = val_ops.ArrayIter(iter_list)

                    if n == 1:
                        name1 = location.LName(node.iter_names[0])
                    elif n == 2:
                        i_name = location.LName(node.iter_names[0])
                        name1 = location.LName(node.iter_names[1])
                    else:
                        # This is similar to a parse error
                        e_die_status(
                            2,
                            'Argv iteration expects at most 2 loop variables',
                            node.keyword)

                status = 0  # in case we loop zero times
                with ctx_LoopLevel(self):
                    while not it2.Done():
                        self.mem.SetValue(name1, it2.FirstValue(),
                                          scope_e.LocalOnly)
                        if name2:
                            self.mem.SetValue(name2, it2.SecondValue(),
                                              scope_e.LocalOnly)
                        if i_name:
                            self.mem.SetValue(i_name, value.Int(it2.Index()),
                                              scope_e.LocalOnly)

                        # increment index before handling continue, etc.
                        it2.Next()

                        try:
                            status = self._Execute(node.body)  # last one wins
                        except vm.IntControlFlow as e:
                            status = 0
                            action = e.HandleLoop()
                            if action == flow_e.Break:
                                break
                            elif action == flow_e.Raise:
                                raise

            elif case(command_e.ForExpr):
                node = cast(command.ForExpr, UP_node)

                self.mem.SetLocationToken(node.keyword)
                #self._MaybeRunDebugTrap()

                status = 0

                init = node.init
                for_cond = node.cond
                body = node.body
                update = node.update

                if init:
                    self.arith_ev.Eval(init)

                with ctx_LoopLevel(self):
                    while True:
                        if for_cond:
                            # We only accept integers as conditions
                            cond_int = self.arith_ev.EvalToInt(for_cond)
                            if cond_int == 0:  # false
                                break

                        try:
                            status = self._Execute(body)
                        except vm.IntControlFlow as e:
                            status = 0
                            action = e.HandleLoop()
                            if action == flow_e.Break:
                                break
                            elif action == flow_e.Raise:
                                raise

                        if update:
                            self.arith_ev.Eval(update)

            elif case(command_e.ShFunction):
                node = cast(command.ShFunction, UP_node)
                if node.name in self.procs and not self.exec_opts.redefine_proc_func(
                ):
                    e_die(
                        "Function %s was already defined (redefine_proc_func)" %
                        node.name, node.name_tok)
                self.procs[node.name] = Proc(node.name, node.name_tok,
                                             proc_sig.Open, node.body, [],
                                             True)

                status = 0

            elif case(command_e.Proc):
                node = cast(command.Proc, UP_node)

                proc_name = lexer.TokenVal(node.name)
                if proc_name in self.procs and not self.exec_opts.redefine_proc_func(
                ):
                    e_die(
                        "Proc %s was already defined (redefine_proc_func)" %
                        proc_name, node.name)

                defaults = None  # type: List[value_t]
                UP_sig = node.sig
                if UP_sig.tag() == proc_sig_e.Closed:
                    sig = cast(proc_sig.Closed, UP_sig)
                    no_val = None  # type: value_t
                    defaults = [no_val] * len(sig.pos_params)
                    for i, p in enumerate(sig.pos_params):
                        if p.default_val:
                            val = self.expr_ev.EvalExpr(
                                p.default_val, loc.Missing)
                            defaults[i] = val

                self.procs[proc_name] = Proc(proc_name, node.name, node.sig,
                                             node.body, defaults,
                                             False)  # no dynamic scope

                status = 0

            elif case(command_e.Func):
                node = cast(command.Func, UP_node)

                name = lexer.TokenVal(node.name)
                if name in self.funcs and not self.exec_opts.redefine_proc_func():
                    e_die(
                        "Func %s was already defined (redefine_proc_func)" %
                        name, node.name)

                self.funcs[name] = Func(name, node, self.mem, self)

                status = 0

            elif case(command_e.If):
                node = cast(command.If, UP_node)
                done = False
                for if_arm in node.arms:
                    b = self._EvalCondition(if_arm.cond, if_arm.keyword)
                    if b:
                        status = self._ExecuteList(if_arm.action)
                        done = True
                        break
                # TODO: The compiler should flatten this
                if not done and node.else_action is not None:
                    status = self._ExecuteList(node.else_action)

            elif case(command_e.NoOp):
                status = 0  # make it true

            elif case(command_e.Case):
                node = cast(command.Case, UP_node)
                to_match = self._EvalCaseArg(node.to_match, node.case_kw)

                self.mem.SetLocationToken(node.case_kw)
                self._MaybeRunDebugTrap()

                status = 0  # If there are no arms, it should be zero?
                matched = False

                for case_arm in node.arms:
                    with tagswitch(case_arm.pattern) as case:
                        if case(pat_e.Words):
                            if to_match.tag() != value_e.Str:
                                continue  # A non-string `to_match` will never match a pat.Words
                            to_match_str = cast(value.Str, to_match)

                            pat_words = cast(pat.Words, case_arm.pattern)

                            for pat_word in pat_words.words:
                                word_val = self.word_ev.EvalWordToString(
                                    pat_word, word_eval.QUOTE_FNMATCH)

                                if libc.fnmatch(word_val.s, to_match_str.s):
                                    status = self._ExecuteList(case_arm.action)
                                    matched = True  # TODO: Parse ;;& and for fallthrough and such?
                                    break

                        elif case(pat_e.YshExprs):
                            pat_exprs = cast(pat.YshExprs, case_arm.pattern)

                            for pat_expr in pat_exprs.exprs:
                                expr_val = self.expr_ev.EvalExpr(
                                    pat_expr, case_arm.left)

                                if val_ops.ExactlyEqual(expr_val, to_match):
                                    status = self._ExecuteList(case_arm.action)
                                    matched = True
                                    break

                        elif case(pat_e.Eggex):
                            pat_eggex = cast(pat.Eggex, case_arm.pattern)
                            eggex = self.expr_ev.EvalRegex(pat_eggex.eggex)
                            eggex_val = value.Eggex(eggex, None)

                            if val_ops.RegexMatch(to_match, eggex_val,
                                                  self.mem):
                                status = self._ExecuteList(case_arm.action)
                                matched = True
                                break

                        elif case(pat_e.Else):
                            status = self._ExecuteList(case_arm.action)
                            matched = True
                            break

                        else:
                            raise AssertionError()

                    if matched:  # first match wins
                        break

            elif case(command_e.TimeBlock):
                node = cast(command.TimeBlock, UP_node)
                # TODO:
                # - When do we need RUSAGE_CHILDREN?
                # - Respect TIMEFORMAT environment variable.
                # "If this variable is not set, Bash acts as if it had the value"
                # $'\nreal\t%3lR\nuser\t%3lU\nsys\t%3lS'
                # "A trailing newline is added when the format string is displayed."

                s_real, s_user, s_sys = pyos.Time()
                status = self._Execute(node.pipeline)
                e_real, e_user, e_sys = pyos.Time()
                # note: mycpp doesn't support %.3f
                libc.print_time(e_real - s_real, e_user - s_user,
                                e_sys - s_sys)

            else:
                raise NotImplementedError(node.tag())

        # Return to caller.  Note the only case that didn't set it was Pipeline,
        # which set cmd_st.pipe_status.
        return status

    def RunPendingTraps(self):
        # type: () -> None

        trap_nodes = self.trap_state.GetPendingTraps()
        if trap_nodes is not None:
            with state.ctx_Option(self.mutable_opts, [option_i._running_trap],
                                  True):
                for trap_node in trap_nodes:
                    # Isolate the exit status.
                    with state.ctx_Registers(self.mem):
                        # Trace it.  TODO: Show the trap kind too
                        with dev.ctx_Tracer(self.tracer, 'trap', None):
                            self._Execute(trap_node)

    def _Execute(self, node):
        # type: (command_t) -> int
        """Apply redirects, call _Dispatch(), and performs the errexit check.

        Also runs trap handlers.
        """
        # TODO: Do this in "leaf" nodes?  SimpleCommand, DBracket, DParen should
        # call self.DoTick()?  That will RunPendingTraps and check the Ctrl-C flag,
        # and maybe throw an exception.
        self.RunPendingTraps()

        # We only need this somewhat hacky check in osh-cpp since python's runtime
        # handles SIGINT for us in osh.
        if mylib.CPP:
            if self.signal_safe.PollSigInt():
                raise KeyboardInterrupt()

        # Manual GC point before every statement
        mylib.MaybeCollect()

        # This has to go around redirect handling because the process sub could be
        # in the redirect word:
        #     { echo one; echo two; } > >(tac)

        # Optimization: These 2 records have rarely-used lists, so we don't pass
        # alloc_lists=True.  We create them on demand.
        cmd_st = CommandStatus.CreateNull()
        process_sub_st = StatusArray.CreateNull()

        errexit_loc = loc.Missing  # type: loc_t
        check_errexit = True

        with vm.ctx_ProcessSub(self.shell_ex, process_sub_st):
            try:
                redirects = self._EvalRedirects(node)
            except error.RedirectEval as e:
                self.errfmt.PrettyPrintError(e)
                redirects = None

            if redirects is None:  # Error evaluating redirect words
                status = 1

            else:
                if self.shell_ex.PushRedirects(redirects):
                    # This pops redirects.  There is an asymmetry because applying
                    # redirects can fail.
                    with vm.ctx_Redirect(self.shell_ex):
                        try:
                            status = self._Dispatch(node, cmd_st)
                            check_errexit = cmd_st.check_errexit
                        except error.FailGlob as e:
                            if not e.HasLocation():  # Last resort!
                                e.location = self.mem.CurrentLocation()
                            self.errfmt.PrettyPrintError(e,
                                                         prefix='failglob: ')
                            status = 1
                            check_errexit = True

                    # Compute status from @PIPESTATUS
                    pipe_status = cmd_st.pipe_status

                    if pipe_status is None:
                        # bash/mksh set PIPESTATUS set even on non-pipelines
                        # This makes it annoying to check both _process_sub_status and
                        # _pipeline_status
                        #self.mem.SetSimplePipeStatus(status)
                        pass

                    else:  # Did we run a pipeline?
                        self.mem.SetPipeStatus(pipe_status)

                        if self.exec_opts.pipefail():
                            # The status is that of the last command that is non-zero.
                            status = 0
                            for i, st in enumerate(pipe_status):
                                if st != 0:
                                    status = st
                                    errexit_loc = cmd_st.pipe_locs[i]
                        else:
                            # The status is that of last command, period.
                            status = pipe_status[-1]

                        if cmd_st.pipe_negated:
                            status = 1 if status == 0 else 0

                    if 0:
                        if status == 1 and node.tag() == command_e.Simple:
                            log('node %s', node)
                        log('node %s status %d PIPE %s',
                            command_str(node.tag()), status, pipe_status)

                else:
                    # I/O error when applying redirects, e.g. bad file descriptor.
                    status = 1

        # Compute status from _process_sub_status
        if process_sub_st.codes is not None:
            codes = process_sub_st.codes
            self.mem.SetProcessSubStatus(codes)
            if status == 0 and self.exec_opts.process_sub_fail():
                # Choose the LAST non-zero status, consistent with pipefail above.
                for i, st in enumerate(codes):
                    if st != 0:
                        status = st
                        errexit_loc = process_sub_st.locs[i]

        self.mem.SetLastStatus(status)

        # NOTE: Bash says that 'set -e' checking is done after each 'pipeline'.
        # However, any bash construct can appear in a pipeline.  So it's easier
        # just to put it at the end, instead of after every node.
        #
        # Possible exceptions:
        # - function def (however this always exits 0 anyway)
        # - assignment - its result should be the result of the RHS?
        #   - e.g. arith sub, command sub?  I don't want arith sub.
        # - ControlFlow: always raises, it has no status.
        if check_errexit:
            #log('cmd_st %s', cmd_st)
            self._CheckStatus(status, cmd_st, node, errexit_loc)

        return status

    def _ExecuteList(self, children):
        # type: (List[command_t]) -> int
        status = 0  # for empty list
        for child in children:
            # last status wins
            status = self._Execute(child)
        return status

    def LastStatus(self):
        # type: () -> int
        """For main_loop.py to determine the exit code of the shell itself."""
        return self.mem.LastStatus()

    def _NoForkLast(self, node):
        # type: (command_t) -> None

        if 0:
            log('optimizing')
            node.PrettyPrint(sys.stderr)
            log('')

        UP_node = node
        with tagswitch(node) as case:
            if case(command_e.Simple):
                node = cast(command.Simple, UP_node)
                node.do_fork = False
                if 0:
                    log('Simple optimized')

            elif case(command_e.Pipeline):
                node = cast(command.Pipeline, UP_node)
                if node.negated is None:
                    #log ('pipe')
                    self._NoForkLast(node.children[-1])

            elif case(command_e.Sentence):
                node = cast(command.Sentence, UP_node)
                self._NoForkLast(node.child)

            elif case(command_e.CommandList):
                # Subshells start with CommandList, even if there's only one.
                node = cast(command.CommandList, UP_node)
                self._NoForkLast(node.children[-1])

            elif case(command_e.BraceGroup):
                # TODO: What about redirects?
                node = cast(BraceGroup, UP_node)
                self._NoForkLast(node.children[-1])

    def _RemoveSubshells(self, node):
        # type: (command_t) -> command_t
        """Eliminate redundant subshells like ( echo hi ) | wc -l etc."""
        UP_node = node
        with tagswitch(node) as case:
            if case(command_e.Subshell):
                node = cast(command.Subshell, UP_node)
                if len(node.redirects) == 0:
                    # Note: technically we could optimize this into BraceGroup with
                    # redirects.  Some shells appear to do that.
                    if 0:
                        log('removing subshell')
                    # Optimize ( ( date ) ) etc.
                    return self._RemoveSubshells(node.child)
        return node

    def ExecuteAndCatch(self, node, cmd_flags=0):
        # type: (command_t, int) -> Tuple[bool, bool]
        """Execute a subprogram, handling vm.IntControlFlow and fatal exceptions.

        Args:
          node: LST subtree
          optimize: Whether to exec the last process rather than fork/exec

        Returns:
          TODO: use enum 'why' instead of the 2 booleans

        Used by
        - main_loop.py.
        - SubProgramThunk for pipelines, subshell, command sub, process sub
        - TODO: Signals besides EXIT trap

        Note: To do what optimize does, dash has EV_EXIT flag and yash has a
        finally_exit boolean.  We use a different algorithm.
        """
        if cmd_flags & Optimize:
            node = self._RemoveSubshells(node)
            self._NoForkLast(node)  # turn the last ones into exec

        if 0:
            log('after opt:')
            node.PrettyPrint()
            log('')

        is_return = False
        is_fatal = False
        is_errexit = False

        err = None  # type: error.FatalRuntime

        try:
            status = self._Execute(node)
        except vm.IntControlFlow as e:
            if cmd_flags & RaiseControlFlow:
                raise  # 'eval break' and 'source return.sh', etc.
            else:
                # Return at top level is OK, unlike in bash.
                if e.IsReturn():
                    is_return = True
                    status = e.StatusCode()
                else:
                    # TODO: This error message is invalid.  Can also happen in eval.
                    # We need a flag.

                    # Invalid control flow
                    self.errfmt.Print_(
                        "Loop and control flow can't be in different processes",
                        blame_loc=e.token)
                    is_fatal = True
                    # All shells exit 0 here.  It could be hidden behind
                    # strict_control_flow if the incompatibility causes problems.
                    status = 1
        except error.Parse as e:
            self.dumper.MaybeRecord(self, e)  # Do this before unwinding stack
            raise
        except error.ErrExit as e:
            err = e
            is_errexit = True
        except error.FatalRuntime as e:
            err = e

        if err:
            status = err.ExitStatus()

            is_fatal = True
            # Do this before unwinding stack
            self.dumper.MaybeRecord(self, err)

            if not err.HasLocation():  # Last resort!
                err.location = self.mem.CurrentLocation()

            if is_errexit:
                if self.exec_opts.verbose_errexit():
                    self.errfmt.PrintErrExit(cast(error.ErrExit, err),
                                             posix.getpid())
            else:
                self.errfmt.PrettyPrintError(err, prefix='fatal: ')

        # Problem: We have no idea here if a SUBSHELL (or pipeline comment) already
        # created a crash dump.  So we get 2 or more of them.
        self.dumper.MaybeDump(status)

        self.mem.SetLastStatus(status)
        return is_return, is_fatal

    def MaybeRunExitTrap(self, mut_status):
        # type: (IntParamBox) -> None
        """If an EXIT trap handler exists, run it.

        Only mutates the status if 'return' or 'exit'.  This is odd behavior, but
        all bash/dash/mksh seem to agree on it.  See cases in
        builtin-trap.test.sh.

        Note: if we could easily modulo -1 % 256 == 255 here, then we could get rid
        of this awkward interface.  But that's true in Python and not C!

        Could use i & (n-1) == i & 255  because we have a power of 2.
        https://stackoverflow.com/questions/14997165/fastest-way-to-get-a-positive-modulo-in-c-c
        """
        node = self.trap_state.GetHook('EXIT')  # type: command_t
        if node:
            # NOTE: Don't set option_i._running_trap, because that's for
            # RunPendingTraps() in the MAIN LOOP
            with dev.ctx_Tracer(self.tracer, 'trap EXIT', None):
                try:
                    is_return, is_fatal = self.ExecuteAndCatch(node)
                except util.UserExit as e:  # explicit exit
                    mut_status.i = e.status
                    return
                if is_return:  # explicit 'return' in the trap handler!
                    mut_status.i = self.LastStatus()

    def _MaybeRunDebugTrap(self):
        # type: () -> None
        """If a DEBUG trap handler exists, run it."""
        if not self.mem.ShouldRunDebugTrap():
            return

        node = self.trap_state.GetHook('DEBUG')  # type: command_t
        if node:
            # NOTE: Don't set option_i._running_trap, because that's for
            # RunPendingTraps() in the MAIN LOOP

            with dev.ctx_Tracer(self.tracer, 'trap DEBUG', None):
                with state.ctx_Registers(self.mem):  # prevent setting $? etc.
                    with state.ctx_DebugTrap(
                            self.mem):  # for SetLocationToken $LINENO
                        # Don't catch util.UserExit, etc.
                        self._Execute(node)

    def _MaybeRunErrTrap(self):
        # type: () -> None
        """If a ERR trap handler exists, run it."""

        # Prevent infinite recursion
        if self.running_err_trap:
            return

        node = self.trap_state.GetHook('ERR')  # type: command_t
        if node:
            # NOTE: Don't set option_i._running_trap, because that's for
            # RunPendingTraps() in the MAIN LOOP

            with dev.ctx_Tracer(self.tracer, 'trap ERR', None):
                #with state.ctx_Registers(self.mem):  # prevent setting $? etc.
                with ctx_ErrTrap(self):
                    self._Execute(node)

    def RunProc(self, proc, argv, arg0_loc):
        # type: (Proc, List[str], loc_t) -> int
        """Run a shell "functions".

        For SimpleCommand and registered completion hooks.
        """
        sig = proc.sig
        if sig.tag() == proc_sig_e.Closed:
            # We're binding named params.  User should use @rest.  No 'shift'.
            proc_argv = []  # type: List[str]
        else:
            proc_argv = argv

        with state.ctx_ProcCall(self.mem, self.mutable_opts, proc, proc_argv):
            n_args = len(argv)
            UP_sig = sig

            if UP_sig.tag() == proc_sig_e.Closed:  # proc is-closed ()
                sig = cast(proc_sig.Closed, UP_sig)
                for i, p in enumerate(sig.pos_params):
                    is_out_param = p.type is not None and p.type.tval == 'Ref'

                    param_name = p.name.tval
                    if i < n_args:
                        arg_str = argv[i]

                        # If we have myproc(p), and call it with myproc :arg, then bind
                        # __p to 'arg'.  That is, the param has a prefix ADDED, and the arg
                        # has a prefix REMOVED.
                        #
                        # This helps eliminate "nameref cycles".
                        if is_out_param:
                            param_name = '__' + param_name

                            if not arg_str.startswith(':'):
                                # TODO: Point to the exact argument
                                e_die(
                                    'Invalid argument %r.  Expected a name starting with :'
                                    % arg_str)
                            arg_str = arg_str[1:]

                        val = value.Str(arg_str)  # type: value_t
                    else:
                        val = proc.defaults[i]
                        if val is None:
                            e_die("No value provided for param %r" %
                                  p.name.tval)

                    if is_out_param:
                        flags = state.SetNameref
                    else:
                        flags = 0

                    self.mem.SetValue(location.LName(param_name),
                                      val,
                                      scope_e.LocalOnly,
                                      flags=flags)

                n_params = len(sig.pos_params)
                if sig.rest:
                    items = [value.Str(s)
                             for s in argv[n_params:]]  # type: List[value_t]
                    leftover = value.List(items)
                    self.mem.SetValue(location.LName(sig.rest.tval), leftover,
                                      scope_e.LocalOnly)
                else:
                    if n_args > n_params:
                        self.errfmt.Print_(
                            "proc %r expected %d arguments, but got %d" %
                            (proc.name, n_params, n_args), arg0_loc)
                        # This should be status 2 because it's like a usage error.
                        return 2

            # Redirects still valid for functions.
            # Here doc causes a pipe and Process(SubProgramThunk).
            try:
                status = self._Execute(proc.body)
            except vm.IntControlFlow as e:
                if e.IsReturn():
                    status = e.StatusCode()
                else:
                    # break/continue used in the wrong place.
                    e_die(
                        'Unexpected %r (in function call)' %
                        lexer.TokenVal(e.token), e.token)
            except error.FatalRuntime as e:
                # Dump the stack before unwinding it
                self.dumper.MaybeRecord(self, e)
                raise

        return status

    def EvalBlock(self, block):
        # type: (command_t) -> Dict[str, Cell]
        """Returns a namespace.  For config files.

        rule foo {
          a = 1
        }
        is like:
        foo = {a:1}
        """
        status = 0
        namespace_ = None  # type: Dict[str, Cell]
        try:
            self._Execute(block)  # can raise FatalRuntimeError, etc.
        except vm.IntControlFlow as e:  # A block is more like a function.
            # return in a block
            if e.IsReturn():
                status = e.StatusCode()
            else:
                e_die('Unexpected control flow in block', e.token)

        namespace_ = self.mem.TopNamespace()

        # This is the thing on self.mem?
        # Filter out everything beginning with _ ?

        # TODO: Return arbitrary values instead

        # Nothing seems to depend on this, and mypy isn't happy with it
        # because it's an int and values of the namespace dict should be
        # cells, so I've commented it out.
        #namespace['_returned'] = status

        # TODO: Have to get rid of the cells
        return namespace_

    def RunFuncForCompletion(self, proc, argv):
        # type: (Proc, List[str]) -> int
        # TODO: Change this to run YSH procs and funcs too
        try:
            status = self.RunProc(proc, argv, loc.Missing)
        except error.FatalRuntime as e:
            self.errfmt.PrettyPrintError(e)
            status = e.ExitStatus()
        except vm.IntControlFlow as e:
            # shouldn't be able to exit the shell from a completion hook!
            # TODO: Avoid overwriting the prompt!
            self.errfmt.Print_('Attempted to exit from completion hook.',
                               blame_loc=e.token)

            status = 1
        # NOTE: (IOError, OSError) are caught in completion.py:ReadlineCallback
        return status


# vim: sw=4
