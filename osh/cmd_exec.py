#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
cmd_exec.py -- Interpreter for the command language.

Problems:
$ < Makefile cat | < NOTES.txt head

This just does head?  Last one wins.
"""
from __future__ import print_function

import resource
import time
import sys

from _devbuild.gen.id_tables import REDIR_ARG_TYPES, REDIR_DEFAULT_FD
from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import (
    compound_word,
    command_e, command_t,
    command__AndOr,
    command__BraceGroup,
    command__Case,
    command__CommandList,
    command__ControlFlow,
    command__DBracket,
    command__DoGroup,
    command__DParen,
    command__ExpandedAlias,
    command__Expr,
    command__ForEach,
    command__ForExpr,
    command__Func,
    command__If,
    command__NoOp,
    command__OilCondition,
    command__OilForIn,
    command__Pipeline,
    command__PlaceMutation,
    command__Proc,
    command__Return,
    command__Sentence,
    command__ShAssignment,
    command__ShFunction,
    command__Simple,
    command__Subshell,
    command__TimeBlock,
    command__VarDecl,
    command__WhileUntil,
    assign_op_e, source,
    place_expr__Var,
    proc_sig_e, proc_sig__Closed,
    redir_e, redir__Redir, redir__HereDoc,
)
from _devbuild.gen.runtime_asdl import (
    lvalue, lvalue_e, lvalue__ObjIndex, lvalue__ObjAttr,
    value, value_e, value_t, value__Str, value__MaybeStrArray, value__Obj,
    redirect, scope_e, var_flags_e, builtin_e,
    cmd_value__Argv, cmd_value, cmd_value_e,
    cmd_value__Argv, cmd_value__Assign,
)
from _devbuild.gen.types_asdl import redir_arg_type_e

from asdl import runtime

from core import main_loop
from core import error
from core import process
from core import ui
from core import util
from core.util import log, e_die

from frontend import args
from frontend import reader

from oil_lang import objects
from osh import braces
from osh import builtin
from osh import builtin_pure
from osh import expr_eval
from osh import state
from osh import word_

from mycpp import mylib
from mycpp.mylib import switch, tagswitch

import posix_ as posix
try:
  import libc  # for fnmatch
except ImportError:
  from benchmarks import fake_libc as libc  # type: ignore

from typing import List, Dict, Tuple, Any, Callable, cast, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.id_kind_asdl import Id_t
  from _devbuild.gen.runtime_asdl import (
      cmd_value_t, var_flags_t, cell, lvalue_t,
      builtin_t, redirect_t,
  )
  from _devbuild.gen.syntax_asdl import (
      Token, source_t, redir_t, expr__Lambda, env_pair, proc_sig__Closed,
  )
  from core.ui import ErrorFormatter
  from frontend.parse_lib import ParseContext
  from core import dev
  from oil_lang import expr_eval as oil_expr_eval
  from osh.cmd_parse import CommandParser
  from osh import word_eval
  from osh import builtin_process
  from osh import prompt
  from osh import split


# Python type name -> Oil type name
OIL_TYPE_NAMES = {
    'bool': 'Bool',
    'int': 'Int',
    'float': 'Float',
    'str': 'Str',
    'tuple': 'Tuple',
    'list': 'List',
    'dict': 'Dict',
}


# These are nodes that execute more than one COMMAND.  DParen doesn't
# count because there are no commands.
# - AndOr has multiple commands, but uses exit code in boolean way
_DISALLOWED = [
    command_e.DoGroup,  # covers ForEach and ForExpr, but not WhileUntil/If
    command_e.BraceGroup, command_e.Subshell,
    command_e.WhileUntil, command_e.If, command_e.Case,
    command_e.TimeBlock,
    command_e.CommandList,  # Happens in $(command sub)
]

def _DisallowErrExit(node):
  # type: (command_t) -> bool
  if node.tag in _DISALLOWED:
    return True

  UP_node = node # type: command_t
  # '! foo' is a pipeline according to the POSIX shell grammar, but it's NOT
  # disallowed!  It's not more than one command.
  if UP_node.tag == command_e.Pipeline:
    node = cast(command__Pipeline, UP_node)
    return len(node.children) > 1
  return False


class _ControlFlow(RuntimeError):
  """Internal execption for control flow.

  break and continue are caught by loops, return is caught by functions.

  NOTE: I tried representing this in ASDL, but in Python the base class has to
  be BaseException.  Also, 'token' is in syntax.asdl but not runtime.asdl.

  cflow =
    -- break, continue, return, exit
    Shell(token keyword, int arg)
    -- break, continue
  | OilLoop(token keyword)
    -- return
  | OilReturn(token keyword, value val)
  """

  def __init__(self, token, arg):
    # type: (Token, int) -> None
    """
    Args:
      token: the keyword token
    """
    self.token = token
    self.arg = arg

  def IsReturn(self):
    # type: () -> bool
    return self.token.id == Id.ControlFlow_Return

  def IsBreak(self):
    # type: () -> bool
    return self.token.id == Id.ControlFlow_Break

  def IsContinue(self):
    # type: () -> bool
    return self.token.id == Id.ControlFlow_Continue

  def StatusCode(self):
    # type: () -> int
    assert self.IsReturn()
    return self.arg

  def __repr__(self):
    # type: () -> str
    return '<_ControlFlow %s>' % self.token


class Deps(object):
  def __init__(self):
    # type: () -> None
    self.splitter = None    # type: split.SplitContext

    self.word_ev = None     # type: word_eval.NormalWordEvaluator
    self.arith_ev = None    # type: expr_eval.ArithEvaluator
    self.bool_ev = None     # type: expr_eval.BoolEvaluator
    self.expr_ev = None     # type: oil_expr_eval.OilEvaluator
    self.ex = None          # type: Executor
    self.prompt_ev = None   # type: prompt.Evaluator

    self.search_path = None # type: state.SearchPath
    self.ext_prog = None    # type: process.ExternalProgram

    self.dumper = None      # type: dev.CrashDumper
    self.tracer = None      # type: dev.Tracer

    self.errfmt = None      # type: ErrorFormatter
    self.debug_f = None     # type: util.DebugFile
    self.trace_f = None     # type: util.DebugFile

    # signal/hook name -> handler
    self.traps = None       # type: Dict[str, builtin_process._TrapHandler]
    # appended to by signal handlers
    self.trap_nodes = None  # type: List[command_t]

    self.job_state = None   # type: process.JobState
    self.waiter = None      # type: process.Waiter


if mylib.PYTHON:
  def _PyObjectToVal(py_val):
    # type: (Any) -> Any
    """
    Maintain the 'value' invariant in osh/runtime.asdl.

    TODO: Move this to Mem and combine with LookupVar in oil_lang/expr_eval.py.
    They are opposites.
    """
    if isinstance(py_val, str):  # var s = "hello $name"
      val = value.Str(py_val)  # type: Any
    elif isinstance(py_val, objects.StrArray):  # var a = @(a b)
      # It's safe to convert StrArray to MaybeStrArray.
      val = value.MaybeStrArray(py_val)
    elif isinstance(py_val, dict):  # var d = {name: "bob"}
      # TODO: Is this necessary?  Shell assoc arrays aren't nested and don't have
      # arbitrary values.
      val = value.AssocArray(py_val)
    else:
      val = value.Obj(py_val)
    return val


class Executor(object):
  """Executes the program by tree-walking.

  It also does some double-dispatch by passing itself into Eval() for
  Compound/WordPart.
  """
  def __init__(self,
               mem,          # type: state.Mem
               fd_state,     # type: process.FdState
               procs,        # type: Dict[str, command__ShFunction]
               builtins,     # type: Dict[builtin_t, Callable[[cmd_value_t], int]]
               exec_opts,    # type: state.ExecOpts
               parse_ctx,    # type: ParseContext
               exec_deps,    # type: Deps
  ):
    # type: (...) -> None
    """
    Args:
      mem: Mem instance for storing variables
      fd_state: FdState() for managing descriptors
      procs: dict of SHELL functions or 'procs'
      builtins: dict of builtin callables (TODO: migrate all builtins here)
      exec_opts: ExecOpts
      parse_ctx: for instantiating parsers
      exec_deps: A bundle of stateless code
    """
    self.mem = mem
    self.fd_state = fd_state
    self.procs = procs
    self.builtins = builtins
    # This is for shopt and set -o.  They are initialized by flags.
    self.exec_opts = exec_opts

    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena
    self.aliases = parse_ctx.aliases  # alias name -> string

    self.dumper = exec_deps.dumper
    self.errfmt = exec_deps.errfmt
    self.debug_f = exec_deps.debug_f  # Used by ShellFuncAction too

    self.word_ev = exec_deps.word_ev
    self.arith_ev = exec_deps.arith_ev
    self.bool_ev = exec_deps.bool_ev
    self.expr_ev = exec_deps.expr_ev

    self.search_path = exec_deps.search_path
    self.ext_prog = exec_deps.ext_prog
    self.traps = exec_deps.traps
    self.trap_nodes = exec_deps.trap_nodes

    # sleep 5 & puts a (PID, job#) entry here.  And then "jobs" displays it.
    self.job_state = exec_deps.job_state
    self.waiter = exec_deps.waiter

    self.tracer = exec_deps.tracer

    self.loop_level = 0  # for detecting bad top-level break/continue
    self.check_command_sub_status = False  # a hack

  def _EvalHelper(self, c_parser, src):
    # type: (CommandParser, source_t) -> int
    self.arena.PushSource(src)
    try:
      return main_loop.Batch(self, c_parser, self.arena)
    finally:
      self.arena.PopSource()

  def _Eval(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    if self.exec_opts.strict_eval_builtin:
      # To be less confusing, eval accepts EXACTLY one string arg.
      n = len(cmd_val.argv)
      if n != 2:
        raise args.UsageError('requires exactly 1 argument, got %d' % (n-1))
      code_str = cmd_val.argv[1]
    else:
      code_str = ' '.join(cmd_val.argv[1:])
    eval_spid = cmd_val.arg_spids[0]

    line_reader = reader.StringLineReader(code_str, self.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader)

    src = source.EvalArg(eval_spid)
    return self._EvalHelper(c_parser, src)

  def ParseTrapCode(self, code_str):
    # type: (str) -> command_t
    """
    Returns:
      A node, or None if the code is invalid.
    """
    line_reader = reader.StringLineReader(code_str, self.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader)

    # TODO: the SPID should be passed through argv
    self.arena.PushSource(source.Trap(runtime.NO_SPID))
    try:
      try:
        node = main_loop.ParseWholeFile(c_parser)
      except error.Parse as e:
        ui.PrettyPrintError(e, self.arena)
        return None

    finally:
      self.arena.PopSource()

    return node

  def _Source(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    argv = cmd_val.argv
    call_spid = cmd_val.arg_spids[0]

    try:
      path = argv[1]
    except IndexError:
      raise args.UsageError('missing required argument')

    resolved = self.search_path.Lookup(path, exec_required=False)
    if resolved is None:
      resolved = path
    try:
      f = self.fd_state.Open(resolved)  # Shell can't use descriptors 3-9
    except OSError as e:
      self.errfmt.Print('source %r failed: %s', path, posix.strerror(e.errno),
                        span_id=cmd_val.arg_spids[1])
      return 1

    try:
      line_reader = reader.FileLineReader(f, self.arena)
      c_parser = self.parse_ctx.MakeOshParser(line_reader)

      # A sourced module CAN have a new arguments array, but it always shares
      # the same variable scope as the caller.  The caller could be at either a
      # global or a local scope.
      source_argv = argv[2:]
      self.mem.PushSource(path, source_argv)
      try:
        status = self._EvalHelper(c_parser, source.SourcedFile(path, call_spid))
      finally:
        self.mem.PopSource(source_argv)

      return status

    except _ControlFlow as e:
      if e.IsReturn():
        return e.StatusCode()
      else:
        raise
    finally:
      f.close()

  def _Exec(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    # Apply redirects in this shell.  # NOTE: Redirects were processed earlier.
    if len(cmd_val.argv) == 1:
      return 0

    environ = self.mem.GetExported()
    cmd = cmd_val.argv[1]
    argv0_path = self.search_path.CachedLookup(cmd)
    if argv0_path is None:
      self.errfmt.Print('exec: %r not found', cmd,
                        span_id=cmd_val.arg_spids[1])
      sys.exit(127)  # exec never returns

    # shift off 'exec'
    c2 = cmd_value.Argv(cmd_val.argv[1:], cmd_val.arg_spids[1:])
    self.ext_prog.Exec(argv0_path, c2, environ)  # NEVER RETURNS
    assert False, "This line should never be reached" # makes mypy happy

  def _RunBuiltinAndRaise(self, builtin_id, cmd_val, fork_external):
    # type: (builtin_t, cmd_value__Argv, bool) -> int
    """
    Raises:
      args.UsageError
    """
    # Shift one arg.  Builtins don't need to know their own name.
    argv = cmd_val.argv[1:]

    # TODO: For now, hard-code the builtins that take a block, and pass them
    # cmd_val.
    # Later, we should give builtins signatures like this and check them:
    #
    # proc cd(argv Array[Str], b Block) {
    #   do evaluate(b, locals, globals)
    # }

    # Most builtins dispatch with a dictionary
    builtin_func = self.builtins.get(builtin_id)
    if builtin_func is not None:
      status = builtin_func(cmd_val)

    # Some builtins "belong" to the executor.

    elif builtin_id == builtin_e.EXEC:
      status = self._Exec(cmd_val)  # may never return
      # But if it returns, then we want to permanently apply the redirects
      # associated with it.
      self.fd_state.MakePermanent()

    elif builtin_id == builtin_e.EVAL:
      status = self._Eval(cmd_val)

    elif builtin_id in (builtin_e.SOURCE, builtin_e.DOT):
      status = self._Source(cmd_val)

    elif builtin_id == builtin_e.COMMAND:
      # TODO: How do we handle fork_external?  It doesn't fit the common
      # signature.  We also don't handle 'command local', etc.
      b = builtin_pure.Command(self, self.procs, self.aliases,
                               self.search_path)
      status = b(cmd_val, fork_external)

    elif builtin_id == builtin_e.BUILTIN:  # NOTE: uses early return style
      if len(argv) == 0:
        return 0  # this could be an error in strict mode?

      name = cmd_val.argv[1]

      # Run regular builtin or special builtin
      to_run = builtin.Resolve(name)
      if to_run == builtin_e.NONE:
        to_run = builtin.ResolveSpecial(name)
      if to_run == builtin_e.NONE:
        span_id = cmd_val.arg_spids[1]
        if builtin.ResolveAssign(name) != builtin_e.NONE:
          # NOTE: There's a similar restriction for 'command'
          self.errfmt.Print("Can't run assignment builtin recursively",
                            span_id=span_id)
        else:
          self.errfmt.Print("%r isn't a shell builtin", name, span_id=span_id)
        return 1

      cmd_val2 = cmd_value.Argv(cmd_val.argv[1:], cmd_val.arg_spids[1:],
                                cmd_val.block)
      status = self._RunBuiltinAndRaise(to_run, cmd_val2, fork_external)

    else:
      raise AssertionError('Unhandled builtin: %s' % builtin_id)

    assert isinstance(status, int)
    return status

  def _RunBuiltin(self, builtin_id, cmd_val, fork_external):
    # type: (builtin_t, cmd_value__Argv, bool) -> int
    self.errfmt.PushLocation(cmd_val.arg_spids[0])
    try:
      status = self._RunBuiltinAndRaise(builtin_id, cmd_val, fork_external)
    except args.UsageError as e:
      arg0 = cmd_val.argv[0]
      # fill in default location.  e.g. osh/state.py raises UsageError without
      # span_id.
      if e.span_id == runtime.NO_SPID:
        e.span_id = self.errfmt.CurrentLocation()
      # e.g. 'type' doesn't accept flag '-x'
      self.errfmt.Print(e.msg, prefix='%r ' % arg0, span_id=e.span_id)
      status = 2  # consistent error code for usage error
    except KeyboardInterrupt:
      if self.exec_opts.interactive:
        print()  # newline after ^C
        status = 130  # 128 + 2 for SIGINT
      else:
        # Abort a batch script
        raise
    finally:
      # Flush stdout after running ANY builtin.  This is very important!
      # Silence errors like we did from 'echo'.
      try:
        sys.stdout.flush()
      except IOError as e:
        pass

      self.errfmt.PopLocation()

    return status

  def _RunAssignBuiltin(self, cmd_val):
    # type: (cmd_value__Assign) -> int
    """Run an assignment builtin.  Except blocks copied from _RunBuiltin above."""
    self.errfmt.PushLocation(cmd_val.arg_spids[0])  # defult
    builtin_func = self.builtins[cmd_val.builtin_id]  # must be there
    try:
      status = builtin_func(cmd_val)
    except args.UsageError as e:  # Copied from _RunBuiltin
      arg0 = cmd_val.argv[0]
      if e.span_id == runtime.NO_SPID:  # fill in default location.
        e.span_id = self.errfmt.CurrentLocation()
      self.errfmt.Print(e.msg, prefix='%r ' % arg0, span_id=e.span_id)
      status = 2  # consistent error code for usage error
    except KeyboardInterrupt:
      if self.exec_opts.interactive:
        print()  # newline after ^C
        status = 130  # 128 + 2 for SIGINT
      else:
        raise
    finally:
      try:
        sys.stdout.flush()
      except IOError as e:
        pass

      self.errfmt.PopLocation()

    return status

  def _PushErrExit(self, span_id):
    # type: (int) -> None
    self.exec_opts.errexit.Push(span_id)

  def _PopErrExit(self):
    # type: () -> None
    self.exec_opts.errexit.Pop()

  # TODO: Also change to BareAssign (set global or mutate local) and
  # KeywordAssign.  The latter may have flags too.
  def _SpanIdForShAssignment(self, node):
    # type: (command__ShAssignment) -> int
    # TODO: Share with tracing (SetCurrentSpanId) and _CheckStatus
    return node.spids[0]

  def _CheckStatus(self, status, node):
    # type: (int, command_t) -> None
    """Raises ErrExitFailure, maybe with location info attached."""
    if self.exec_opts.ErrExit() and status != 0:
      # NOTE: Sometimes location info is duplicated, like on UsageError, or a
      # bad redirect.  Also, pipelines can fail twice.

      UP_node = node

      if UP_node.tag == command_e.Simple:
        node = cast(command__Simple, UP_node)
        reason = 'command in '
        span_id = word_.LeftMostSpanForWord(node.words[0])
      elif node.tag == command_e.ShAssignment:
        node = cast(command__ShAssignment, UP_node)
        reason = 'assignment in '
        span_id = self._SpanIdForShAssignment(node)
      elif node.tag == command_e.Subshell:
        node = cast(command__Subshell, UP_node)
        reason = 'subshell invoked from '
        span_id = node.spids[0]
      elif node.tag == command_e.Pipeline:
        node = cast(command__Pipeline, UP_node)
        # The whole pipeline can fail separately
        reason = 'pipeline invoked from '
        span_id = node.spids[0]  # only one spid
      else:
        # NOTE: The fallback of CurrentSpanId() fills this in.
        reason = ''
        span_id = runtime.NO_SPID

      raise error.ErrExit(
          'Exiting with status %d (%sPID %d)', status, reason, posix.getpid(),
          span_id=span_id, status=status)

  def _EvalRedirect(self, n):
    # type: (redir_t) -> redirect_t

    UP_n = n
    if UP_n.tag == redir_e.Redir:
      n = cast(redir__Redir, UP_n)

      # note: needed for redirect like 'echo foo > x$LINENO'
      self.mem.SetCurrentSpanId(n.op.span_id)
      fd = REDIR_DEFAULT_FD[n.op.id] if n.fd == runtime.NO_SPID else n.fd

      redir_type = REDIR_ARG_TYPES[n.op.id]  # could be static in the LST?

      if redir_type == redir_arg_type_e.Path:
        # NOTES
        # - no globbing.  You can write to a file called '*.py'.
        # - set -o strict-array prevents joining by spaces
        val = self.word_ev.EvalWordToString(n.arg_word)
        filename = val.s
        if not filename:
          # Whether this is fatal depends on errexit.
          raise error.RedirectEval(
              "Redirect filename can't be empty", word=n.arg_word)

        return redirect.Path(n.op.id, fd, filename, n.op.span_id)

      elif redir_type == redir_arg_type_e.Desc:  # e.g. 1>&2
        val = self.word_ev.EvalWordToString(n.arg_word)
        t = val.s
        if not t:
          raise error.RedirectEval(
              "Redirect descriptor can't be empty", word=n.arg_word)
          return None
        try:
          target_fd = int(t)
        except ValueError:
          raise error.RedirectEval(
              "Redirect descriptor should look like an integer, got %s", val,
              word=n.arg_word)
          return None

        return redirect.FileDesc(n.op.id, fd, target_fd, n.op.span_id)

      elif redir_type == redir_arg_type_e.Here:  # here word
        val = self.word_ev.EvalWordToString(n.arg_word)
        assert val.tag == value_e.Str, val
        # NOTE: bash and mksh both add \n
        return redirect.HereDoc(fd, val.s + '\n', n.op.span_id)
      else:
        raise AssertionError('Unknown redirect op')

    elif UP_n.tag == redir_e.HereDoc:
      n = cast(redir__HereDoc, UP_n)
      fd = REDIR_DEFAULT_FD[n.op.id] if n.fd == runtime.NO_SPID else n.fd
      # HACK: Wrap it in a word to evaluate.
      w = compound_word(n.stdin_parts)
      val = self.word_ev.EvalWordToString(w)
      assert val.tag == value_e.Str, val
      return redirect.HereDoc(fd, val.s, n.op.span_id)

    else:
      raise AssertionError('Unknown redirect type')

  def _EvalRedirects(self, node):
    # type: (command_t) -> List[redirect_t]
    """Evaluate redirect nodes to concrete objects.

    We have to do this every time, because you could have something like:

    for i in a b c; do
      echo foo >$i
    done

    Does it makes sense to just have RedirectNode.Eval?  Nah I think the
    Redirect() abstraction in process.py is useful.  It has a lot of methods.

    Raises:
      RedirectEvalError
    """
    # This is kind of lame because we have two switches over command_e: one for
    # redirects, and to evaluate the node.  But it's what you would do in C++ I
    # suppose.  We could also inline them.  Or maybe use RAII.
    UP_node = node
    with tagswitch(node) as case:
      if case(command_e.Simple):
        node = cast(command__Simple, UP_node)
        redirects = node.redirects
      elif case(command_e.ExpandedAlias):
        node = cast(command__ExpandedAlias, UP_node)
        redirects = node.redirects
      elif case(command_e.ShAssignment):
        node = cast(command__ShAssignment, UP_node)
        redirects = node.redirects
      elif case(command_e.DoGroup):
        node = cast(command__DoGroup, UP_node)
        redirects = node.redirects
      elif case(command_e.BraceGroup):
        node = cast(command__BraceGroup, UP_node)
        redirects = node.redirects
      elif case(command_e.Subshell):
        node = cast(command__Subshell, UP_node)
        redirects = node.redirects
      elif case(command_e.DParen):
        node = cast(command__DParen, UP_node)
        redirects = node.redirects
      elif case(command_e.DBracket):
        node = cast(command__DBracket, UP_node)
        redirects = node.redirects
      elif case(command_e.ForEach):
        node = cast(command__ForEach, UP_node)
        redirects = node.redirects
      elif case(command_e.ForExpr):
        node = cast(command__ForExpr, UP_node)
        redirects = node.redirects
      elif case(command_e.WhileUntil):
        node = cast(command__WhileUntil, UP_node)
        redirects = node.redirects
      elif case(command_e.If):
        node = cast(command__If, UP_node)
        redirects = node.redirects
      elif case(command_e.Case):
        node = cast(command__Case, UP_node)
        redirects = node.redirects
      else:
        raise AssertionError

    result = []
    for redir in redirects:
      result.append(self._EvalRedirect(redir))
    return result

  def _MakeProcess(self, node, parent_pipeline=None, inherit_errexit=True):
    # type: (command_t, process.Pipeline, bool) -> process.Process
    """
    Assume we will run the node in another process.  Return a process.
    """

    UP_node = node
    if UP_node.tag == command_e.ControlFlow:
      node = cast(command__ControlFlow, UP_node)
      # Pipeline or subshells with control flow are invalid, e.g.:
      # - break | less
      # - continue | less
      # - ( return )
      # NOTE: This could be done at parse time too.
      e_die('Invalid control flow %r in pipeline / subshell / background',
            node.token.val, token=node.token)

    # NOTE: If ErrExit(), we could be verbose about subprogram errors?  This
    # only really matters when executing 'exit 42', because the child shell
    # inherits errexit and will be verbose.  Other notes:
    #
    # - We might want errors to fit on a single line so they don't get
    # interleaved.
    # - We could turn the `exit` builtin into a FatalRuntimeError exception and
    # get this check for "free".
    thunk = process.SubProgramThunk(self, node,
                                    inherit_errexit=inherit_errexit)
    p = process.Process(thunk, self.job_state, parent_pipeline=parent_pipeline)
    return p

  def _RunSimpleCommand(self, cmd_val, fork_external):
    # type: (cmd_value_t, bool) -> int
    """Private interface to run a simple command (including assignment)."""

    UP_cmd_val = cmd_val
    if UP_cmd_val.tag == cmd_value_e.Argv:
      cmd_val = cast(cmd_value__Argv, UP_cmd_val)
      return self.RunSimpleCommand(cmd_val, fork_external)

    elif UP_cmd_val.tag == cmd_value_e.Assign:
      cmd_val = cast(cmd_value__Assign, UP_cmd_val)
      return self._RunAssignBuiltin(cmd_val)
    else:
      raise AssertionError

  def RunSimpleCommand(self, cmd_val, fork_external, funcs=True):
    # type: (cmd_value__Argv, bool, bool) -> int
    """Public interface to run a simple command (excluding assignment)

    Args:
      fork_external: for subshell ( ls / ) or ( command ls / )
    """
    assert cmd_val.tag == cmd_value_e.Argv

    argv = cmd_val.argv
    span_id = cmd_val.arg_spids[0] if cmd_val.arg_spids else runtime.NO_SPID

    # This happens when you write "$@" but have no arguments.
    if len(argv) == 0:
      if self.exec_opts.strict_argv:
        e_die("Command evaluated to an empty argv array",
              span_id=span_id)
      else:
        return 0  # status 0, or skip it?

    arg0 = argv[0]

    builtin_id = builtin.ResolveAssign(arg0)
    if builtin_id != builtin_e.NONE:
      # command readonly is disallowed, for technical reasons.  Could relax it
      # later.
      self.errfmt.Print("Can't run assignment builtin recursively",
                        span_id=span_id)
      return 1

    builtin_id = builtin.ResolveSpecial(arg0)
    if builtin_id != builtin_e.NONE:
      status = self._RunBuiltin(builtin_id, cmd_val, fork_external)
      # TODO: Enable this and fix spec test failures.
      # Also update _SPECIAL_BUILTINS in osh/builtin.py.
      #if status != 0:
      #  e_die('special builtin failed', status=status)
      return status

    # Builtins like 'true' can be redefined as functions.
    if funcs:
      # TODO: if shopt -s namespaces, then look up in current namespace FIRST.
      #
      # Then fallback on self.procs, which should be renamed self.procs?
      #
      # honestly there is no real chance of colllision because
      # foo-bar() {} can't be accessed anyway
      # functions can have hyphens, but variables can't

      func_node = self.procs.get(arg0)
      if func_node is not None:
        eo = self.exec_opts
        if eo.strict_errexit and eo.errexit.SpidIfDisabled() != runtime.NO_SPID:
          # NOTE: This would be checked below, but this gives a better error
          # message.
          e_die("can't disable errexit running a function. "
                "Maybe wrap the function in a process with the at-splice "
                "pattern.", span_id=span_id)

        # NOTE: Functions could call 'exit 42' directly, etc.
        status = self._RunProc(func_node, argv[1:])
        return status

      # TODO:
      # look up arg0 in global namespace?  And see if the type is value.Obj
      # And it's a proc?
      # isinstance(val.obj, objects.Proc)
      UP_val = self.mem.GetVar(arg0)

      if mylib.PYTHON:  # Not reusing CPython objects
        if UP_val.tag == value_e.Obj:
          val = cast(value__Obj, UP_val)
          if isinstance(val.obj, objects.Proc):
            status = self._RunOilProc(val.obj, argv[1:])
            return status

    builtin_id = builtin.Resolve(arg0)

    if builtin_id != builtin_e.NONE:
      return self._RunBuiltin(builtin_id, cmd_val, fork_external)

    environ = self.mem.GetExported()  # Include temporary variables

    if cmd_val.block:
      e_die('Unexpected block passed to external command %r', arg0,
            span_id=cmd_val.block.spids[0])

    # Resolve argv[0] BEFORE forking.
    argv0_path = self.search_path.CachedLookup(arg0)
    if argv0_path is None:
      self.errfmt.Print('%r not found', arg0, span_id=span_id)
      return 127

    if fork_external:
      thunk = process.ExternalThunk(self.ext_prog, argv0_path, cmd_val, environ)
      p = process.Process(thunk, self.job_state)
      status = p.Run(self.waiter)
      return status

    self.ext_prog.Exec(argv0_path, cmd_val, environ)  # NEVER RETURNS
    assert False, "This line should never be reached" # makes mypy happy

  def _RunPipeline(self, node):
    # type: (command__Pipeline) -> int
    pi = process.Pipeline()

    # First n-1 processes (which is empty when n == 1)
    n = len(node.children)
    for i in xrange(n - 1):
      p = self._MakeProcess(node.children[i], parent_pipeline=pi)
      pi.Add(p)

    # Last piece of code is in THIS PROCESS.  'echo foo | read line; echo $line'
    pi.AddLast((self, node.children[n-1]))

    pipe_status = pi.Run(self.waiter, self.fd_state)
    self.mem.SetPipeStatus(pipe_status)

    if self.exec_opts.pipefail:
      # The status is that of the last command that is non-zero.
      status = 0
      for st in pipe_status:
        if st != 0:
          status = st
    else:
      status = pipe_status[-1]  # status of last one is pipeline status

    return status

  def _RunJobInBackground(self, node):
    # type: (command_t) -> int
    # Special case for pipeline.  There is some evidence here:
    # https://www.gnu.org/software/libc/manual/html_node/Launching-Jobs.html#Launching-Jobs
    #
    #  "You can either make all the processes in the process group be children
    #  of the shell process, or you can make one process in group be the
    #  ancestor of all the other processes in that group. The sample shell
    #  program presented in this chapter uses the first approach because it
    #  makes bookkeeping somewhat simpler."
    UP_node = node

    if UP_node.tag == command_e.Pipeline:
      node = cast(command__Pipeline, UP_node)
      pi = process.Pipeline()
      for child in node.children:
        pi.Add(self._MakeProcess(child, parent_pipeline=pi))

      pi.Start(self.waiter)
      last_pid = pi.LastPid()
      self.mem.last_bg_pid = last_pid   # for $!

      job_id = self.job_state.AddJob(pi)  # show in 'jobs' list
      log('[%%%d] Started Pipeline with PID %d', job_id, last_pid)

    else:
      # Problem: to get the 'set -b' behavior of immediate notifications, we
      # have to register SIGCHLD.  But then that introduces race conditions.
      # If we haven't called Register yet, then we won't know who to notify.

      #log('job state %s', self.job_state)
      p = self._MakeProcess(node)
      pid = p.Start()
      self.mem.last_bg_pid = pid  # for $!
      job_id = self.job_state.AddJob(p)  # show in 'jobs' list
      log('[%%%d] Started PID %d', job_id, pid)
    return 0

  def _EvalTempEnv(self, more_env, flags):
    # type: (List[env_pair], Tuple[var_flags_t, ...]) -> None
    """For FOO=1 cmd."""
    for e_pair in more_env:
      val = self.word_ev.EvalWordToString(e_pair.val)
      # Set each var so the next one can reference it.  Example:
      # FOO=1 BAR=$FOO ls /
      self.mem.SetVar(lvalue.Named(e_pair.name), val, flags,
                      scope_e.LocalOnly)

  def _Dispatch(self, node, fork_external):
    # type: (command_t, bool) -> Tuple[int, bool]
    # If we call RunCommandSub in a recursive call to the executor, this will
    # be set true (if strict-errexit is false).  But it only lasts for one
    # command.
    self.check_command_sub_status = False

    #argv0 = None  # for error message
    check_errexit = False  # for errexit

    UP_node = node

    if UP_node.tag == command_e.Simple:
      node = cast(command__Simple, UP_node)
      check_errexit = True

      # Find span_id for a basic implementation of $LINENO, e.g.
      # PS4='+$SOURCE_NAME:$LINENO:'
      # Note that for '> $LINENO' the span_id is set in _EvalRedirect.
      # TODO: Can we avoid setting this so many times?  See issue #567.
      if len(node.words):
        span_id = word_.LeftMostSpanForWord(node.words[0])
        self.mem.SetCurrentSpanId(span_id)

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
      cmd_val = self.word_ev.EvalWordSequence2(words, allow_assign=True)

      UP_cmd_val = cmd_val
      if UP_cmd_val.tag == cmd_value_e.Argv:
        cmd_val = cast(cmd_value__Argv, UP_cmd_val)
        argv = cmd_val.argv
        cmd_val.block = node.block  # may be None
      else:
        argv = ['TODO: trace string for assignment']
        if node.block:
          assert node.block.tag_() == command_e.BraceGroup, node
          block = cast(command__BraceGroup, node.block)
          e_die("ShAssignment builtins don't accept blocks",
                span_id=block.spids[0])

      # This comes before evaluating env, in case there are problems evaluating
      # it.  We could trace the env separately?  Also trace unevaluated code
      # with set-o verbose?
      self.tracer.OnSimpleCommand(argv)

      # NOTE: RunSimpleCommand never returns when fork_external=False!
      if len(node.more_env):  # I think this guard is necessary?
        is_other_special = False  # TODO: There are other special builtins too!
        if cmd_val.tag == cmd_value_e.Assign or is_other_special:
          # Special builtins have their temp env persisted.
          self._EvalTempEnv(node.more_env, ())
          status = self._RunSimpleCommand(cmd_val, fork_external)
        else:
          self.mem.PushTemp()
          try:
            self._EvalTempEnv(node.more_env, (var_flags_e.Exported,))
            status = self._RunSimpleCommand(cmd_val, fork_external)
          finally:
            self.mem.PopTemp()
      else:
        status = self._RunSimpleCommand(cmd_val, fork_external)

    elif UP_node.tag == command_e.ExpandedAlias:
      node = cast(command__ExpandedAlias, UP_node)
      # Expanded aliases need redirects and env bindings from the calling
      # context, as well as redirects in the expansion!

      # TODO: SetCurrentSpanId to OUTSIDE?  Don't bother with stuff inside
      # expansion, since aliases are discouarged.

      if len(node.more_env):
        self.mem.PushTemp()
        try:
          self._EvalTempEnv(node.more_env, (var_flags_e.Exported,))
          status = self._Execute(node.child)
        finally:
          self.mem.PopTemp()
      else:
        status = self._Execute(node.child)

    elif UP_node.tag == command_e.Sentence:
      node = cast(command__Sentence, UP_node)
      # Don't check_errexit since this isn't a real node!
      if node.terminator.id == Id.Op_Semi:
        status = self._Execute(node.child)
      else:
        status = self._RunJobInBackground(node.child)

    elif UP_node.tag == command_e.Pipeline:
      node = cast(command__Pipeline, UP_node)
      check_errexit = True
      if len(node.stderr_indices):
        e_die("|& isn't supported", span_id=node.spids[0])

      if node.negated:
        self._PushErrExit(node.spids[0])  # ! spid
        try:
          status2 = self._RunPipeline(node)
        finally:
          self._PopErrExit()

        # errexit is disabled for !.
        check_errexit = False
        status = 1 if status2 == 0 else 0
      else:
        status = self._RunPipeline(node)

    elif UP_node.tag == command_e.Subshell:
      node = cast(command__Subshell, UP_node)
      check_errexit = True
      # This makes sure we don't waste a process if we'd launch one anyway.
      p = self._MakeProcess(node.command_list)
      status = p.Run(self.waiter)

    elif UP_node.tag == command_e.DBracket:
      node = cast(command__DBracket, UP_node)
      span_id = node.spids[0]
      self.mem.SetCurrentSpanId(span_id)

      check_errexit = True
      result = self.bool_ev.Eval(node.expr)
      status = 0 if result else 1

    elif UP_node.tag == command_e.DParen:
      node = cast(command__DParen, UP_node)
      span_id = node.spids[0]
      self.mem.SetCurrentSpanId(span_id)

      check_errexit = True
      i = self.arith_ev.EvalToInt(node.child)
      status = 1 if i == 0 else 0

    elif UP_node.tag == command_e.OilCondition:
      node = cast(command__OilCondition, UP_node)
      # TODO: Do we need location information?  Yes, probably for execptions in
      # Oil expressions.
      #span_id = node.spids[0]
      #self.mem.SetCurrentSpanId(span_id)

      obj = self.expr_ev.EvalExpr(node.e)
      status = 0 if obj else 1

    # TODO: Change x = 1 + 2*3 into its own Decl node.
    elif UP_node.tag == command_e.VarDecl:
      # TODO: This should be constant, equivalent to const x = 'foo'

      node = cast(command__VarDecl, UP_node)
      if node.keyword is None or node.keyword.id == Id.KW_Const:
        self.mem.SetCurrentSpanId(node.lhs[0].name.span_id)  # point to var name

        # Note: there's only one LHS
        vd_lval = lvalue.Named(node.lhs[0].name.val)
        py_val = self.expr_ev.EvalExpr(node.rhs)
        val = _PyObjectToVal(py_val)

        self.mem.SetVar(vd_lval, val, (var_flags_e.ReadOnly,),
                        scope_e.LocalOnly, keyword_id=None)
        status = 0

      else:
        self.mem.SetCurrentSpanId(node.keyword.span_id)  # point to var

        py_val = self.expr_ev.EvalExpr(node.rhs)
        vd_lvals = []
        vals = []
        if len(node.lhs) == 1:  # TODO: optimize this common case (but measure)
          vd_lval = lvalue.Named(node.lhs[0].name.val)
          val = _PyObjectToVal(py_val)

          vd_lvals.append(vd_lval)
          vals.append(val)
        else:
          it = py_val.__iter__()
          for vd_lhs in node.lhs:
            vd_lval = lvalue.Named(vd_lhs.name.val)
            val = _PyObjectToVal(it.next())

            vd_lvals.append(vd_lval)
            vals.append(val)

        for vd_lval, val in zip(vd_lvals, vals):
          self.mem.SetVar(
              vd_lval, val, (), scope_e.LocalOnly, keyword_id=node.keyword.id)

        status = 0

    elif UP_node.tag == command_e.PlaceMutation:

      if mylib.PYTHON:  # DISABLED because it relies on CPytho now
        node = cast(command__PlaceMutation, UP_node)
        self.mem.SetCurrentSpanId(node.keyword.span_id)  # point to setvar/set

        with switch(node.keyword.id) as case:
          if case(Id.KW_SetVar):
            lookup_mode = scope_e.LocalOrGlobal
          elif case(Id.KW_Set):
            lookup_mode = scope_e.LocalOnly
          elif case(Id.KW_SetGlobal):
            lookup_mode = scope_e.GlobalOnly
          elif case(Id.KW_SetRef):
            # So this can modify two levels up?
            lookup_mode = scope_e.Dynamic

            # TODO: setref upvalue = 'returned'
            e_die("setref isn't implemented")
          else:
            raise AssertionError(node.keyword.id)

        if node.op.id == Id.Arith_Equal:
          py_val = self.expr_ev.EvalExpr(node.rhs)

          lvals_ = []  # type: List[lvalue_t]
          py_vals = []
          if len(node.lhs) == 1:  # TODO: Optimize this common case (but measure)
            # See ShAssignment
            # EvalLhs
            # EvalLhsAndLookup for +=
            lval_ = self.expr_ev.EvalPlaceExpr(node.lhs[0]) # type: lvalue_t

            lvals_.append(lval_)
            py_vals.append(py_val)
          else:
            it = py_val.__iter__()
            for pm_lhs in node.lhs:
              lval_ = self.expr_ev.EvalPlaceExpr(pm_lhs)
              py_val = it.next()

              lvals_.append(lval_)
              py_vals.append(py_val)

          # TODO: Resolve the asymmetry betwen Named vs ObjIndex,ObjAttr.
          for UP_lval_, py_val in zip(lvals_, py_vals):
            tag = UP_lval_.tag_()
            if tag == lvalue_e.ObjIndex:
              lval_ = cast(lvalue__ObjIndex, UP_lval_)
              lval_.obj[lval_.index] = py_val
            elif tag == lvalue_e.ObjAttr:
              lval_ = cast(lvalue__ObjAttr, UP_lval_)
              setattr(lval_.obj, lval_.attr, py_val)
            else:
              val = _PyObjectToVal(py_val)
              # top level variable
              self.mem.SetVar(UP_lval_, val, (), lookup_mode,
                              keyword_id=node.keyword.id)

        # TODO: Other augmented assignments
        elif node.op.id == Id.Arith_PlusEqual:
          # NOTE: x, y += 1 in Python is a SYNTAX error, but it's checked in the
          # transformer and not the grammar.  We should do that too.

          place_expr = cast(place_expr__Var, node.lhs[0])
          pe_lval = lvalue.Named(place_expr.name.val)
          py_val = self.expr_ev.EvalExpr(node.rhs)

          new_py_val = self.expr_ev.EvalPlusEquals(pe_lval, py_val)
          # This should only be an int or float, so we don't need the logic above
          val = value.Obj(new_py_val)

          self.mem.SetVar(pe_lval, val, (), lookup_mode,
                          keyword_id=node.keyword.id)

        else:
          raise NotImplementedError(node.op)

      status = 0  # TODO: what should status be?

    elif UP_node.tag == command_e.ShAssignment:  # Only unqualified assignment
      node = cast(command__ShAssignment, UP_node)

      lookup_mode = scope_e.Dynamic
      for pair in node.pairs:
        # Use the spid of each pair.
        self.mem.SetCurrentSpanId(pair.spids[0])

        if pair.op == assign_op_e.PlusEqual:
          assert pair.rhs, pair.rhs  # I don't think a+= is valid?
          val = self.word_ev.EvalRhsWord(pair.rhs)
          old_val, lval = expr_eval.EvalLhsAndLookup(pair.lhs, self.arith_ev,
                                                     self.mem, self.exec_opts,
                                                     lookup_mode=lookup_mode)
          UP_old_val = old_val
          UP_val = val
          sig = (old_val.tag, val.tag)
          if sig == (value_e.Undef, value_e.Str):
            pass  # val is RHS
          elif sig == (value_e.Undef, value_e.MaybeStrArray):
            pass  # val is RHS
          elif sig == (value_e.Str, value_e.Str):
            old_val = cast(value__Str, old_val)
            val = cast(value__Str, val)
            val = value.Str(old_val.s + val.s)
          elif sig == (value_e.Str, value_e.MaybeStrArray):
            e_die("Can't append array to string")
          elif sig == (value_e.MaybeStrArray, value_e.Str):
            e_die("Can't append string to array")
          elif sig == (value_e.MaybeStrArray, value_e.MaybeStrArray):
            old_val = cast(value__MaybeStrArray, old_val)
            val = cast(value__MaybeStrArray, val)
            val = value.MaybeStrArray(old_val.strs + val.strs)

        else:  # plain assignment
          spid = pair.spids[0]  # Source location for tracing
          lval = expr_eval.EvalLhs(pair.lhs, self.arith_ev, self.mem, spid,
                                   lookup_mode)

          # RHS can be a string or array.
          if pair.rhs:
            val = self.word_ev.EvalRhsWord(pair.rhs)
            assert isinstance(val, value_t), val

          else:  # e.g. 'readonly x' or 'local x'
            val = None

        # NOTE: In bash and mksh, declare -a myarray makes an empty cell with
        # Undef value, but the 'array' attribute.

        #log('setting %s to %s with flags %s', lval, val, flags)
        flags = ()
        self.mem.SetVar(lval, val, flags, lookup_mode)
        self.tracer.OnShAssignment(lval, pair.op, val, flags, lookup_mode)

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
        self._CheckStatus(last_status, node)
        status = last_status  # A global assignment shouldn't clear $?.
      else:
        status = 0

    elif UP_node.tag == command_e.Return:
      node = cast(command__Return, UP_node)
      val = self.expr_ev.EvalExpr(node.e)
      raise _ControlFlow(node.keyword, val)

    elif UP_node.tag == command_e.Expr:
      node = cast(command__Expr, UP_node)

      self.mem.SetCurrentSpanId(node.keyword.span_id)
      obj = self.expr_ev.EvalExpr(node.e)

      if node.keyword.id == Id.Lit_Equals:
        # NOTE: It would be nice to unify this with 'repr', but there isn't a
        # good way to do it with the value/PyObject split.
        class_name = obj.__class__.__name__
        oil_name = OIL_TYPE_NAMES.get(class_name, class_name)
        print('(%s)   %s' % (oil_name, repr(obj)))

      # TODO: What about exceptions?  They just throw?
      status = 0

    elif UP_node.tag == command_e.ControlFlow:
      node = cast(command__ControlFlow, UP_node)
      tok = node.token

      if node.arg_word:  # Evaluate the argument
        val = self.word_ev.EvalWordToString(node.arg_word)
        assert val.tag == value_e.Str
        try:
          arg = int(val.s)  # They all take integers
        except ValueError:
          e_die('%r expected a number, got %r',
              node.token.val, val.s, word=node.arg_word)
      else:
        if tok.id in (Id.ControlFlow_Exit, Id.ControlFlow_Return):
          arg = self.mem.LastStatus()
        else:
          arg = 0  # break 0 levels, nothing for continue

      # NOTE: A top-level 'return' is OK, unlike in bash.  If you can return
      # from a sourced script, it makes sense to return from a main script.
      ok = True
      if (tok.id in (Id.ControlFlow_Break, Id.ControlFlow_Continue) and
          self.loop_level == 0):
        ok = False

      if ok:
        if tok.id == Id.ControlFlow_Exit:
          raise util.UserExit(arg)  # handled differently than other control flow
        else:
          raise _ControlFlow(tok, arg)
      else:
        msg = 'Invalid control flow at top level'
        if self.exec_opts.strict_control_flow:
          e_die(msg, token=tok)
        else:
          # Only print warnings, never fatal.
          # Bash oddly only exits 1 for 'return', but no other shell does.
          self.errfmt.Print(msg, prefix='warning: ', span_id=tok.span_id)
          status = 0

    # The only difference between these next two is that CommandList
    # has no redirects.  We already took care of that above.  But we
    # need to split them up for mycpp.
    elif UP_node.tag == command_e.CommandList:
      node = cast(command__CommandList, UP_node)
      status = self._ExecuteList(node.children)
      check_errexit = False

    elif UP_node.tag == command_e.BraceGroup:
      node = cast(command__BraceGroup, UP_node)
      status = self._ExecuteList(node.children)
      check_errexit = False

    elif UP_node.tag == command_e.AndOr:
      node = cast(command__AndOr, UP_node)
      # NOTE: && and || have EQUAL precedence in command mode.  See case #13
      # in dbracket.test.sh.

      left = node.children[0]

      # Suppress failure for every child except the last one.
      self._PushErrExit(node.spids[0])
      try:
        status = self._Execute(left)
      finally:
        self._PopErrExit()

      i = 1
      n = len(node.children)
      while i < n:
        #log('i %d status %d', i, status)
        child = node.children[i]
        op_id = node.ops[i-1]

        #log('child %s op_id %s', child, op_id)

        if op_id == Id.Op_DPipe and status == 0:
          i += 1
          continue  # short circuit

        elif op_id == Id.Op_DAmp and status != 0:
          i += 1
          continue  # short circuit

        if i == n - 1:  # errexit handled differently for last child
          status = self._Execute(child)
          check_errexit = True
        else:
          self._PushErrExit(node.spids[i])  # blame the right && or ||
          try:
            status = self._Execute(child)
          finally:
            self._PopErrExit()

        i += 1

    elif UP_node.tag == command_e.WhileUntil:
      node = cast(command__WhileUntil, UP_node)
      status = 0

      self.loop_level += 1
      try:
        while True:
          try:
            self._PushErrExit(node.spids[0])  # while/until spid
            try:
              cond_status = self._ExecuteList(node.cond)
            finally:
              self._PopErrExit()

            if node.keyword.id == Id.KW_While:
              if cond_status != 0:
                break
            else:
              if cond_status == 0:
                break
            status = self._Execute(node.body)  # last one wins

          except _ControlFlow as e:
            # Important: 'break' can occur in the CONDITION or body
            if e.IsBreak():
              status = 0
              break
            elif e.IsContinue():
              status = 0
              continue
            else:  # return needs to pop up more
              raise
      finally:
        self.loop_level -= 1

    elif UP_node.tag == command_e.ForEach:
      node = cast(command__ForEach, UP_node)
      self.mem.SetCurrentSpanId(node.spids[0])  # for x in $LINENO

      iter_name = node.iter_name
      if node.do_arg_iter:
        iter_list = self.mem.GetArgv()
      else:
        words = braces.BraceExpandWords(node.iter_words)
        iter_list = self.word_ev.EvalWordSequence(words)
        # We need word splitting and so forth
        # NOTE: This expands globs too.  TODO: We should pass in a Globber()
        # object.

      status = 0  # in case we don't loop
      self.loop_level += 1
      try:
        for x in iter_list:
          #log('> ForEach setting %r', x)
          state.SetLocalString(self.mem, iter_name, x)
          #log('<')

          try:
            status = self._Execute(node.body)  # last one wins
          except _ControlFlow as e:
            if e.IsBreak():
              status = 0
              break
            elif e.IsContinue():
              status = 0
            else:  # return needs to pop up more
              raise
      finally:
        self.loop_level -= 1

    elif UP_node.tag == command_e.ForExpr:
      node = cast(command__ForExpr, UP_node)
      status = 0

      init = node.init
      cond = node.cond
      body = node.body
      update = node.update

      if init:
        self.arith_ev.Eval(init)

      self.loop_level += 1
      try:
        while True:
          if cond:
            # We only accept integers as conditions
            cond_int = self.arith_ev.EvalToInt(cond)
            if cond_int == 0:  # false
              break

          try:
            status = self._Execute(body)
          except _ControlFlow as e:
            if e.IsBreak():
              status = 0
              break
            elif e.IsContinue():
              status = 0
            else:  # return needs to pop up more
              raise

          if update:
            self.arith_ev.Eval(update)

      finally:
        self.loop_level -= 1

    elif UP_node.tag == command_e.OilForIn:
      node = cast(command__OilForIn, UP_node)
      # NOTE: This is a metacircular implementation using the iterable
      # protocol.
      status = 0

      obj = self.expr_ev.EvalExpr(node.iterable)
      if isinstance(obj, str):
        e_die("Strings aren't iterable")
      else:
        it = obj.__iter__()

      body = node.body
      iter_name = node.lhs[0].name.val  # TODO: proper lvalue
      while True:
        try:
          loop_val = it.next()
        except StopIteration:
          break
        self.mem.SetVar(lvalue.Named(iter_name), _PyObjectToVal(loop_val), (),
                        scope_e.LocalOnly)

        # Copied from above
        try:
          status = self._Execute(body)
        except _ControlFlow as e:
          if e.IsBreak():
            status = 0
            break
          elif e.IsContinue():
            status = 0
          else:  # return needs to pop up more
            raise

    elif UP_node.tag == command_e.DoGroup:
      node = cast(command__DoGroup, UP_node)
      status = self._ExecuteList(node.children)
      check_errexit = False  # not real statements

    elif UP_node.tag == command_e.ShFunction:
      node = cast(command__ShFunction, UP_node)
      # TODO: if shopt -s namespaces, then enter it in self.mem
      # self.mem.SetVar(value.Obj(...))

      # NOTE: Would it make sense to evaluate the redirects BEFORE entering?
      # It will save time on function calls.
      self.procs[node.name] = node
      status = 0

    elif UP_node.tag == command_e.Proc:
      node = cast(command__Proc, UP_node)
      UP_proc_sig = node.sig
      if UP_proc_sig.tag == proc_sig_e.Closed:
        proc_sig = cast(proc_sig__Closed, UP_proc_sig)
        defaults = [None] * len(proc_sig.params)
        for i, param in enumerate(proc_sig.params):
          if param.default_val:
            py_val = self.expr_ev.EvalExpr(param.default_val)
            defaults[i] = _PyObjectToVal(py_val)
      else:
        defaults = None

      obj = objects.Proc(node, defaults)

      self.mem.SetVar(
          lvalue.Named(node.name.val), value.Obj(obj), (), scope_e.GlobalOnly)
      status = 0

    elif UP_node.tag == command_e.Func:
      node = cast(command__Func, UP_node)
      # Note: funcs have the Python pitfall where mutable objects shouldn't be
      # used as default args.

      pos_defaults = [None] * len(node.pos_params)
      for i, param in enumerate(node.pos_params):
        if param.default_val:
          py_val = self.expr_ev.EvalExpr(param.default_val)
          pos_defaults[i] = _PyObjectToVal(py_val)

      named_defaults = {}
      for i, param in enumerate(node.named_params):
        if param.default_val:
          obj = self.expr_ev.EvalExpr(param.default_val)
          named_defaults[param.name.val] = value.Obj(obj)

      obj = objects.Func(node, pos_defaults, named_defaults, self)
      self.mem.SetVar(
          lvalue.Named(node.name.val), value.Obj(obj), (), scope_e.GlobalOnly)
      status = 0

    elif UP_node.tag == command_e.If:
      node = cast(command__If, UP_node)
      done = False
      for if_arm in node.arms:
        self._PushErrExit(if_arm.spids[0])  # if/elif spid
        try:
          status = self._ExecuteList(if_arm.cond)
        finally:
          self._PopErrExit()

        if status == 0:
          status = self._ExecuteList(if_arm.action)
          done = True
          break
      # TODO: The compiler should flatten this
      if not done and node.else_action is not None:
        status = self._ExecuteList(node.else_action)

    elif UP_node.tag == command_e.NoOp:
      node = cast(command__NoOp, UP_node)
      status = 0  # make it true

    elif UP_node.tag == command_e.Case:
      node = cast(command__Case, UP_node)
      val = self.word_ev.EvalWordToString(node.to_match)
      to_match = val.s

      status = 0  # If there are no arms, it should be zero?
      done = False

      for case_arm in node.arms:
        for pat_word in case_arm.pat_list:
          # NOTE: Is it OK that we're evaluating these as we go?

          # TODO: case "$@") shouldn't succeed?  That's a type error?
          # That requires strict-array?

          pat_val = self.word_ev.EvalWordToString(pat_word, do_fnmatch=True)
          #log('Matching word %r against pattern %r', to_match, pat_val.s)
          if libc.fnmatch(pat_val.s, to_match):
            status = self._ExecuteList(case_arm.action)
            done = True  # TODO: Parse ;;& and for fallthrough and such?
            break  # Only execute action ONCE
        if done:
          break

    elif UP_node.tag == command_e.TimeBlock:
      node = cast(command__TimeBlock, UP_node)
      # TODO:
      # - When do we need RUSAGE_CHILDREN?
      # - Respect TIMEFORMAT environment variable.
      # "If this variable is not set, Bash acts as if it had the value"
      # $'\nreal\t%3lR\nuser\t%3lU\nsys\t%3lS'
      # "A trailing newline is added when the format string is displayed."

      start_t = time.time()  # calls gettimeofday() under the hood
      start_u = resource.getrusage(resource.RUSAGE_SELF)
      status = self._Execute(node.pipeline)

      end_t = time.time()
      end_u = resource.getrusage(resource.RUSAGE_SELF)

      real = end_t - start_t
      user = end_u.ru_utime - start_u.ru_utime
      sys_ = end_u.ru_stime - start_u.ru_stime
      libc.print_time(real, user, sys_)

    else:
      raise NotImplementedError(node.__class__.__name__)

    return status, check_errexit

  def _Execute(self, node, fork_external=True):
    # type: (command_t, bool) -> int
    """Apply redirects, call _Dispatch(), and performs the errexit check.

    Args:
      node: syntax_asdl.command_t
      fork_external: if we get a SimpleCommand that is an external command,
        should we fork first?  This is disabled in the context of a pipeline
        process and a subshell.
    """
    # See core/builtin.py for the Python signal handler that appends to this
    # list.

    if len(self.trap_nodes):
      # Make a copy and clear it so we don't cause an infinite loop.
      to_run = list(self.trap_nodes)
      del self.trap_nodes[:]
      for trap_node in to_run:  # NOTE: Don't call this 'node'!
        self._Execute(trap_node)

    # strict_errexit check for all compound commands.
    # TODO: Speed this up with some kind of bit mask?
    eo = self.exec_opts
    if eo.strict_errexit and _DisallowErrExit(node):

      span_id = eo.errexit.SpidIfDisabled()
      if span_id != runtime.NO_SPID:
        node_str = node.__class__.__name__.split('_')[-1]  # e.g. BraceGroup
        e_die("errexit is disabled here, but strict_errexit disallows it "
              "with a compound command (%s)", node_str, span_id=span_id)

    # These nodes have no redirects.
    # TODO: Speed this up with some kind of bit mask?
    if node.tag in (
        command_e.NoOp, command_e.ControlFlow, command_e.Pipeline,
        command_e.AndOr, command_e.CommandList, command_e.Sentence,
        command_e.TimeBlock, command_e.ShFunction, command_e.VarDecl,
        command_e.PlaceMutation, command_e.OilCondition, command_e.OilForIn,
        command_e.Proc, command_e.Func, command_e.Return, command_e.Expr,
        command_e.BareDecl):
      redirects = []  # type: List[redirect_t]
    else:
      try:
        redirects = self._EvalRedirects(node)
      except error.RedirectEval as e:
        ui.PrettyPrintError(e, self.arena)
        redirects = None

    check_errexit = True

    if redirects is None:  # evaluation error
      status = 1

    elif len(redirects):
      if self.fd_state.Push(redirects, self.waiter):
        try:
          status, check_errexit = self._Dispatch(node, fork_external)
        finally:
          self.fd_state.Pop()
        #log('_dispatch returned %d', status)
      else:  # Error applying redirects, e.g. bad file descriptor.
        status = 1

    else:  # No redirects
      status, check_errexit = self._Dispatch(node, fork_external)

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
      self._CheckStatus(status, node)
    return status

  def _ExecuteList(self, children):
    # type: (List[command_t]) -> int
    status = 0  # for empty list
    for child in children:
      status = self._Execute(child)  # last status wins
    return status

  def LastStatus(self):
    # type: () -> int
    """For main_loop.py to determine the exit code of the shell itself."""
    return self.mem.LastStatus()

  def ExecuteAndCatch(self, node, fork_external=True):
    # type: (command_t, bool) -> Tuple[bool, bool]
    """Execute a subprogram, handling _ControlFlow and fatal exceptions.

    Args:
      node: LST subtree
      fork_external: whether external commands require forking

    Returns:
      TODO: use enum 'why' instead of the 2 booleans

    Used by main_loop.py.

    Also:
    - SubProgramThunk for pipelines, subshell, command sub, process sub
    - TODO: Signals besides EXIT trap

    Most other clients call _Execute():
    - _Source() for source builtin
    - _Eval() for eval builtin
    - _RunProc() for function call
    """
    is_return = False
    is_fatal = False
    try:
      status = self._Execute(node, fork_external=fork_external)
    except _ControlFlow as e:
      # Return at top level is OK, unlike in bash.
      if e.IsReturn():
        is_return = True
        status = e.StatusCode()
      else:
        # Invalid control flow
        self.errfmt.Print(
            "Loop and control flow can't be in different processes",
            span_id=e.token.span_id)
        is_fatal = True
        # All shells exit 0 here.  It could be hidden behind
        # strict-control-flow if the incompatibility causes problems.
        status = 1
    except error.Parse as e:
      self.dumper.MaybeCollect(self, e)  # Do this before unwinding stack
      raise
    except error.FatalRuntime as e:
      self.dumper.MaybeCollect(self, e)  # Do this before unwinding stack

      if not e.HasLocation():  # Last resort!
        e.span_id = self.mem.CurrentSpanId()

      ui.PrettyPrintError(e, self.arena, prefix='fatal: ')
      is_fatal = True
      status = e.exit_status if e.exit_status is not None else 1

    self.dumper.MaybeDump(status)
    self.mem.SetLastStatus(status)
    return is_return, is_fatal

  def MaybeRunExitTrap(self):
    # type: () -> bool
    """If an EXIT trap exists, run it.
    
    Returns:
      Whether we should use the status of the handler.

      This is odd behavior, but all bash/dash/mksh seem to agree on it.
      See cases 7-10 in builtin-trap.test.sh.
    """
    handler = self.traps.get('EXIT')
    if handler:
      is_return, is_fatal = self.ExecuteAndCatch(handler.node)
      return is_return  # explicit 'return' in the trap handler!
    else:
      return False  # nothing run, don't use its status

  def RunCommandSub(self, node):
    # type: (command_t) -> str
    p = self._MakeProcess(node,
                          inherit_errexit=self.exec_opts.inherit_errexit)

    r, w = posix.pipe()
    p.AddStateChange(process.StdoutToPipe(r, w))
    _ = p.Start()
    #log('Command sub started %d', pid)

    chunks = []
    posix.close(w)  # not going to write
    while True:
      byte_str = posix.read(r, 4096)
      if len(byte_str) == 0:
        break
      chunks.append(byte_str)
    posix.close(r)

    status = p.Wait(self.waiter)

    # OSH has the concept of aborting in the middle of a WORD.  We're not
    # waiting until the command is over!
    if self.exec_opts.more_errexit:
      if self.exec_opts.ErrExit() and status != 0:
        raise error.ErrExit(
            'Command sub exited with status %d (%r)', status,
            node.__class__.__name__)
    else:
      # Set a flag so we check errexit at the same time as bash.  Example:
      #
      # a=$(false)
      # echo foo  # no matter what comes here, the flag is reset
      #
      # Set ONLY until this command node has finished executing.
      self.check_command_sub_status = True
      self.mem.SetLastStatus(status)

    # Runtime errors test case: # $("echo foo > $@")
    # Why rstrip()?
    # https://unix.stackexchange.com/questions/17747/why-does-shell-command-substitution-gobble-up-a-trailing-newline-char
    return ''.join(chunks).rstrip('\n')

  def RunProcessSub(self, node, op_id):
    # type: (command_t, Id_t) -> str
    """Process sub creates a forks a process connected to a pipe.

    The pipe is typically passed to another process via a /dev/fd/$FD path.

    TODO:

    sane-proc-sub:
    - wait for all the words

    Otherwise, set $!  (mem.last_bg_pid)

    strict-proc-sub:
    - Don't allow it anywhere except SimpleCommand, any redirect, or
    ShAssignment?  And maybe not even assignment?

    Should you put return codes in @PROCESS_SUB_STATUS?  You need two of them.
    """
    p = self._MakeProcess(node)

    r, w = posix.pipe()

    if op_id == Id.Left_ProcSubIn:
      # Example: cat < <(head foo.txt)
      #
      # The head process should write its stdout to a pipe.
      redir = process.StdoutToPipe(r, w) # type: process.ChildStateChange

    elif op_id == Id.Left_ProcSubOut:
      # Example: head foo.txt > >(tac)
      #
      # The tac process should read its stdin from a pipe.
      #
      # NOTE: This appears to hang in bash?  At least when done interactively.
      # It doesn't work at all in osh interactively?
      redir = process.StdinFromPipe(r, w)

    else:
      raise AssertionError

    p.AddStateChange(redir)

    # Fork, letting the child inherit the pipe file descriptors.
    pid = p.Start()

    # After forking, close the end of the pipe we're not using.
    if op_id == Id.Left_ProcSubIn:
      posix.close(w)
    elif op_id == Id.Left_ProcSubOut:
      posix.close(r)
    else:
      raise AssertionError

    # NOTE: Like bash, we never actually wait on it!
    # TODO: At least set $! ?

    # Is /dev Linux-specific?
    if op_id == Id.Left_ProcSubIn:
      return '/dev/fd/%d' % r

    elif op_id == Id.Left_ProcSubOut:
      return '/dev/fd/%d' % w

    else:
      raise AssertionError

  def _RunProc(self, func_node, argv):
    # type: (command__ShFunction, List[str]) -> int
    """Run a shell "functions".

    For SimpleCommand and registered completion hooks.
    """
    self.mem.PushCall(func_node.name, func_node.spids[0], argv)

    # Redirects still valid for functions.
    # Here doc causes a pipe and Process(SubProgramThunk).
    try:
      status = self._Execute(func_node.body)
    except _ControlFlow as e:
      if e.IsReturn():
        status = e.StatusCode()
      else:
        # break/continue used in the wrong place.
        e_die('Unexpected %r (in function call)', e.token.val, token=e.token)
    except (error.FatalRuntime, error.Parse) as e:
      self.dumper.MaybeCollect(self, e)  # Do this before unwinding stack
      raise
    finally:
      self.mem.PopCall()

    return status

  def _RunOilProc(self, proc, argv):
    # type: (objects.Proc, List[str]) -> int
    """
    Run an oil proc foo { } or proc foo(x, y, @names) { }
    """
    node = proc.node
    sig = node.sig
    if sig.tag == proc_sig_e.Closed:
      # We're binding named params.  User should use @rest.  No 'shift'.
      proc_argv = [] # type: List[str]
    else:
      proc_argv = argv

    self.mem.PushCall(node.name.val, node.name.span_id, proc_argv)

    n_args = len(argv)
    UP_sig = sig

    if UP_sig.tag == proc_sig_e.Closed:  # proc is-closed []
      sig = cast(proc_sig__Closed, UP_sig)
      for i, p in enumerate(sig.params):
        if i < n_args:
          val = value.Str(argv[i])
        else:
          val = proc.defaults[i]
          if val is None:
            e_die("No value provided for param %r", p.name.val)
        self.mem.SetVar(lvalue.Named(p.name.val), val, (), scope_e.LocalOnly)

      n_params = len(sig.params)
      if sig.rest:
        leftover = value.MaybeStrArray(argv[n_params:])
        self.mem.SetVar(
            lvalue.Named(sig.rest.val), leftover, (), scope_e.LocalOnly)
      else:
        if n_args > n_params:
          raise TypeError(
              "proc %r expected %d arguments, but got %d" %
              (node.name.val, n_params, n_args))

    # TODO:
    # - Handle &block param?  How to do that?  It's really the
    #   syntax_asdl.command_t type?  Or objects.Block probably.

    try:
      status = self._Execute(node.body)
    except _ControlFlow as e:
      if e.IsReturn():
        status = e.StatusCode()
      else:
        # break/continue used in the wrong place.
        e_die('Unexpected %r (in function call)', e.token.val, token=e.token)
    except (error.FatalRuntime, error.Parse) as e:
      self.dumper.MaybeCollect(self, e)  # Do this before unwinding stack
      raise
    finally:
      self.mem.PopCall()

    return status

  if mylib.PYTHON:
    def RunOilFunc(self, func, args, kwargs):
      # type: (objects.Func, Tuple[Any, ...], Dict[str, Any]) -> Any
      """Run an Oil function.

      var x = abs(y)   do f(x)   @split(mystr)   @join(myarray)
      """
      # TODO:
      # - Return value register should be separate?
      #   - But how does 'return 345' work?  Is that the return builtin
      #     raising an exception?
      #     Or is it setting the register?
      #   - I think the exception can have any type, but when you catch it
      #     you determine whether it's LastStatus() or it's something else.
      #   - Something declared with 'func' CANNOT have both?
      #
      # - Type checking
      #   - If the arguments are all strings, make them @ARGV?
      #     That isn't happening right now.

      #log('RunOilFunc kwargs %s', kwargs)
      #log('RunOilFunc named_defaults %s', func.named_defaults)

      node = func.node
      self.mem.PushTemp()

      # Bind positional arguments
      n_args = len(args)
      n_params = len(node.pos_params)
      for i, param in enumerate(node.pos_params):
        if i < n_args:
          py_val = args[i]
          val = _PyObjectToVal(py_val)
        else:
          val = func.pos_defaults[i]
          if val is None:
            # Python raises TypeError.  Should we do something else?
            raise TypeError('No value provided for param %r', param.name)
        self.mem.SetVar(lvalue.Named(param.name.val), val, (), scope_e.LocalOnly)

      if node.pos_splat:
        splat_name = node.pos_splat.val

        # NOTE: This is a heterogeneous TUPLE, not list.
        leftover = value.Obj(args[n_params:])
        self.mem.SetVar(lvalue.Named(splat_name), leftover, (), scope_e.LocalOnly)
      else:
        if n_args > n_params:
          raise TypeError(
              "func %r expected %d arguments, but got %d" %
              (node.name.val, n_params, n_args))

      # Bind named arguments
      for i, param in enumerate(node.named_params):
        name = param.name
        if name.val in kwargs:
          py_val = kwargs.pop(name.val)  # REMOVE it
          val = _PyObjectToVal(py_val)
        else:
          if name.val in func.named_defaults:
            val = func.named_defaults[name.val]
          else:
            raise TypeError(
                "Named argument %r wasn't passed, and it doesn't have a default "
                "value" % name.val)

        self.mem.SetVar(lvalue.Named(name.val), val, (), scope_e.LocalOnly)

      if node.named_splat:
        splat_name = node.named_splat.val
        # Note: this dict is not an AssocArray
        leftover = value.Obj(kwargs)
        self.mem.SetVar(lvalue.Named(splat_name), leftover, (), scope_e.LocalOnly)
      else:
        if kwargs:
          raise TypeError(
              'func %r got unexpected named arguments: %s' %
              (node.name.val, ', '.join(kwargs.keys())))

      return_val = None
      try:
        self._Execute(node.body)
      except _ControlFlow as e:
        if e.IsReturn():
          # TODO: Rename this
          return_val = e.StatusCode()
      finally:
        self.mem.PopTemp()
      return return_val

    def RunLambda(self, lambda_node, args, kwargs):
      # type: (expr__Lambda, Tuple[Any, ...], Dict[str, Any]) -> Any
      """ Run a lambda like |x| x+1 """

      self.mem.PushTemp()
      # Bind params.  TODO: Reject kwargs, etc.
      for i, param in enumerate(lambda_node.params):
        val = value.Obj(args[i])
        self.mem.SetVar(lvalue.Named(param.name.val), val, (), scope_e.LocalOnly)

      return_val = None
      try:
        return_val = self.expr_ev.EvalExpr(lambda_node.body)
      finally:
        self.mem.PopTemp()
      return return_val

  def EvalBlock(self, block):
    # type: (command_t) -> Dict[str, cell]
    """
    Returns a namespace.  For config files.

    rule foo {
      a = 1
    }
    is like:
    foo = {a:1}

    """
    status = None
    self.mem.PushTemp()  # So variables don't conflict
    try:
      self._Execute(block)  # can raise FatalRuntimeError, etc.
    except _ControlFlow as e:  # A block is more like a function.
      if e.IsReturn():
        status = e.StatusCode()
      else:
        raise
    finally:
      namespace = self.mem.TopNamespace() # type: Dict[str, cell]
      self.mem.PopTemp()
    # This is the thing on self.mem?
    # Filter out everything beginning with _ ?

    # TODO: Return arbitrary values instead

    # Nothing seems to depend on this, and mypy isn't happy with it
    # because it's an int and values of the namespace dict should be
    # cells, so I've commented it out.
    #namespace['_returned'] = status
    return namespace

  def RunFuncForCompletion(self, func_node, argv):
    # type: (command__ShFunction, List[str]) -> int
    # TODO: Change this to run Oil procs and funcs too
    try:
      status = self._RunProc(func_node, argv)
    except error.FatalRuntime as e:
      ui.PrettyPrintError(e, self.arena)
      status = e.exit_status if e.exit_status is not None else 1
    except _ControlFlow as e:
      # shouldn't be able to exit the shell from a completion hook!
      # TODO: Avoid overwriting the prompt!
      self.errfmt.Print('Attempted to exit from completion hook.',
                        span_id=e.token.span_id)

      status = 1
    # NOTE: (IOError, OSError) are caught in completion.py:ReadlineCallback
    return status
