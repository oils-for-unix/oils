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

import posix
import resource
import time
import sys

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import (
    command_e, redir_e, lhs_expr_e, lhs_expr_t, assign_op_e, source
)
from _devbuild.gen.syntax_asdl import word as osh_word  # TODO: Rename
from _devbuild.gen.runtime_asdl import (
    lvalue, redirect, value, value_e, value_t, scope_e, var_flags_e, builtin_e,
    arg_vector
)
from _devbuild.gen.types_asdl import redir_arg_type_e

from asdl import const

from core import main_loop
from core import process
from core import ui
from core import util
from core.util import log, e_die
from core.meta import REDIR_ARG_TYPES, REDIR_DEFAULT_FD

from frontend import args
from frontend import reader

from osh import braces
from osh import builtin
from osh import expr_eval
from osh import state
from osh import word
from osh import word_compile

try:
  import libc  # for fnmatch
except ImportError:
  from benchmarks import fake_libc as libc  # type: ignore


class _ControlFlow(RuntimeError):
  """Internal execption for control flow.

  break and continue are caught by loops, return is caught by functions.
  """

  def __init__(self, token, arg):
    """
    Args:
      token: the keyword token
    """
    self.token = token
    self.arg = arg

  def IsReturn(self):
    return self.token.id == Id.ControlFlow_Return

  def IsExit(self):
    return self.token.id == Id.ControlFlow_Exit

  def IsBreak(self):
    return self.token.id == Id.ControlFlow_Break

  def IsContinue(self):
    return self.token.id == Id.ControlFlow_Continue

  def StatusCode(self):
    assert self.IsReturn() or self.IsExit()
    return self.arg

  def __repr__(self):
    return '<_ControlFlow %s>' % self.token


class Deps(object):
  def __init__(self):
    self.splitter = None

    self.word_ev = None
    self.arith_ev = None
    self.bool_ev = None
    self.ex = None
    self.prompt_ev = None

    self.ext_prog = None

    self.dumper = None
    self.tracer = None

    self.errfmt = None
    self.debug_f = None
    self.trace_f = None

    self.traps = None # signal/hook name -> callable
    self.trap_nodes = None  # list of nodes, appended to by signal handlers

    self.job_state = None
    self.waiter = None


class Executor(object):
  """Executes the program by tree-walking.

  It also does some double-dispatch by passing itself into Eval() for
  CompoundWord/WordPart.
  """
  def __init__(self, mem, fd_state, funcs, builtins, exec_opts, parse_ctx,
               exec_deps):
    """
    Args:
      mem: Mem instance for storing variables
      fd_state: FdState() for managing descriptors
      funcs: dict of functions
      builtins: dict of builtin callables (TODO: migrate all builtins here)
      exec_opts: ExecOpts
      parse_ctx: for instantiating parsers
      exec_deps: A bundle of stateless code
    """
    self.mem = mem
    self.fd_state = fd_state
    self.funcs = funcs
    self.builtins = builtins
    # This is for shopt and set -o.  They are initialized by flags.
    self.exec_opts = exec_opts

    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena
    self.aliases = parse_ctx.aliases  # alias name -> string

    self.dumper = exec_deps.dumper
    self.errfmt = exec_deps.errfmt
    self.debug_f = exec_deps.debug_f  # Used by ShellFuncAction too

    self.splitter = exec_deps.splitter
    self.word_ev = exec_deps.word_ev
    self.arith_ev = exec_deps.arith_ev
    self.bool_ev = exec_deps.bool_ev

    self.ext_prog = exec_deps.ext_prog
    self.traps = exec_deps.traps
    self.trap_nodes = exec_deps.trap_nodes

    self.targets = []  # make syntax enters stuff here -- Target()
                       # metaprogramming or regular target syntax
                       # Whether argv[0] is make determines if it is executed

    # sleep 5 & puts a (PID, job#) entry here.  And then "jobs" displays it.
    self.job_state = exec_deps.job_state
    self.waiter = exec_deps.waiter

    self.tracer = exec_deps.tracer

    self.loop_level = 0  # for detecting bad top-level break/continue
    self.check_command_sub_status = False  # a hack

  def _EvalHelper(self, c_parser, src):
    self.arena.PushSource(src)
    try:
      return main_loop.Batch(self, c_parser, self.arena)
    finally:
      self.arena.PopSource()

  def _Eval(self, arg_vec):
    # TODO:
    # - set -o sane-eval should change eval to take a single string.
    code_str = ' '.join(arg_vec.strs[1:])
    eval_spid = arg_vec.spids[0]

    line_reader = reader.StringLineReader(code_str, self.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader)

    src = source.EvalArg(eval_spid)
    return self._EvalHelper(c_parser, src)

  def ParseTrapCode(self, code_str):
    """
    Returns:
      A node, or None if the code is invalid.
    """
    line_reader = reader.StringLineReader(code_str, self.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader)

    # TODO: the SPID should be passed through argv
    self.arena.PushSource(source.Trap(const.NO_INTEGER))
    try:
      try:
        node = main_loop.ParseWholeFile(c_parser)
      except util.ParseError as e:
        ui.PrettyPrintError(e, self.arena)
        return None

    finally:
      self.arena.PopSource()

    return node

  def _Source(self, arg_vec):
    argv = arg_vec.strs
    call_spid = arg_vec.spids[0]

    try:
      path = argv[1]
    except IndexError:
      raise args.UsageError('missing required argument')

    try:
      f = self.fd_state.Open(path)  # Shell can't use descriptors 3-9
    except OSError as e:
      self.errfmt.Print('source %r failed: %s', path, posix.strerror(e.errno),
                        span_id=arg_vec.spids[1])
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

  def _Exec(self, arg_vec):
    # Apply redirects in this shell.  # NOTE: Redirects were processed earlier.
    if len(arg_vec.strs) == 1:
      return 0

    environ = self.mem.GetExported()
    # shift off 'exec'
    arg_vec2 = arg_vector(arg_vec.strs[1:], arg_vec.spids[1:])
    self.ext_prog.Exec(arg_vec2, environ)  # NEVER RETURNS

  def _RunBuiltinAndRaise(self, builtin_id, arg_vec, fork_external):
    """
    Raises:
      args.UsageError
    """
    # Shift one arg.  Builtins don't need to know their own name.
    argv = arg_vec.strs[1:]

    # Most builtins dispatch with a dictionary
    builtin_func = self.builtins.get(builtin_id)
    if builtin_func is not None:
      status = builtin_func(arg_vec)

    # Some builtins "belong" to the executor.

    elif builtin_id == builtin_e.EXEC:
      status = self._Exec(arg_vec)  # may never return
      # But if it returns, then we want to permanently apply the redirects
      # associated with it.
      self.fd_state.MakePermanent()

    elif builtin_id == builtin_e.EVAL:
      status = self._Eval(arg_vec)

    elif builtin_id in (builtin_e.SOURCE, builtin_e.DOT):
      status = self._Source(arg_vec)

    elif builtin_id == builtin_e.COMMAND:
      # TODO: How do we hadnle fork_external?  It doesn't fit the common
      # signature.
      b = builtin.Command(self, self.funcs, self.aliases, self.mem)
      status = b(arg_vec, fork_external)

    elif builtin_id == builtin_e.BUILTIN:  # NOTE: uses early return style
      if not argv:
        return 0  # this could be an error in strict mode?

      name = arg_vec.strs[1]
      # Run regular builtin or special builtin
      to_run = builtin.Resolve(name)
      if to_run == builtin_e.NONE:
        to_run = builtin.ResolveSpecial(name)
      if to_run == builtin_e.NONE:
        self.errfmt.Print("%r isn't a shell builtin", name,
                          span_id=arg_vec.spids[1])
        return 1

      arg_vec2 = arg_vector(arg_vec.strs[1:], arg_vec.spids[1:])
      status = self._RunBuiltinAndRaise(to_run, arg_vec2, fork_external)

    else:
      raise AssertionError('Unhandled builtin: %s' % builtin_id)

    assert isinstance(status, int)
    return status

  def _RunBuiltin(self, builtin_id, arg_vec, fork_external):
    self.errfmt.PushLocation(arg_vec.spids[0])
    try:
      status = self._RunBuiltinAndRaise(builtin_id, arg_vec, fork_external)
    except args.UsageError as e:
      arg0 = arg_vec.strs[0]
      # fill in default location.  e.g. osh/state.py raises UsageError without
      # span_id.
      if e.span_id == const.NO_INTEGER:
        e.span_id = self.errfmt.CurrentLocation()
      # e.g. 'type' doesn't accept flag '-x'
      self.errfmt.Print(e.msg, prefix='%r ' % arg0, span_id=e.span_id)
      status = 2  # consistent error code for usage error
    finally:
      # Flush stdout after running ANY builtin.  This is very important!
      # Silence errors like we did from 'echo'.
      try:
        sys.stdout.flush()
      except IOError as e:
        pass

      self.errfmt.PopLocation()
    return status

  def _PushErrExit(self):
    self.exec_opts.errexit.Push()

  def _PopErrExit(self):
    self.exec_opts.errexit.Pop()

  # TODO: Also change to BareAssign (set global or mutate local) and
  # KeywordAssign.  The latter may have flags too.
  def _SpanIdForAssignment(self, node):
    # TODO: Share with tracing (SetCurrentSpanId) and _CheckStatus
    return node.spids[0]

  def _CheckStatus(self, status, node):
    """Raises ErrExitFailure, maybe with location info attached."""
    if self.exec_opts.ErrExit() and status != 0:
      # NOTE: Sometimes location info is duplicated, like on UsageError, or a
      # bad redirect.  Also, pipelines can fail twice.

      if node.tag == command_e.SimpleCommand:
        reason = 'command in '
        span_id = word.LeftMostSpanForWord(node.words[0])
      elif node.tag == command_e.Assignment:
        reason = 'assignment in '
        span_id = self._SpanIdForAssignment(node)
      elif node.tag == command_e.Subshell:
        reason = 'subshell invoked from '
        span_id = node.spids[0]
      elif node.tag == command_e.Pipeline:
        # The whole pipeline can fail separately
        reason = 'pipeline invoked from '
        span_id = node.spids[0]  # only one spid
      else:
        # NOTE: The fallback of CurrentSpanId() fills this in.
        reason = ''
        span_id = const.NO_INTEGER

      raise util.ErrExitFailure(
          'Exiting with status %d (%sPID %d)', status, reason, posix.getpid(),
          span_id=span_id, status=status)

  def _EvalLhs(self, node, spid, lookup_mode):
    """lhs_expr -> lvalue."""
    assert isinstance(node, lhs_expr_t), node

    if node.tag == lhs_expr_e.LhsName:  # a=x
      lval = lvalue.LhsName(node.name)
      lval.spids.append(spid)
      return lval

    if node.tag == lhs_expr_e.LhsIndexedName:  # a[1+2]=x
      # The index of StrArray needs to be coerced to int, but not the index of
      # an AssocArray.
      int_coerce = not self.mem.IsAssocArray(node.name, lookup_mode)
      index = self.arith_ev.Eval(node.index, int_coerce=int_coerce)

      lval = lvalue.LhsIndexedName(node.name, index)
      lval.spids.append(node.spids[0])  # copy left-most token over
      return lval

    raise AssertionError(node.tag)

  def _EvalRedirect(self, n):
    fd = REDIR_DEFAULT_FD[n.op.id] if n.fd == const.NO_INTEGER else n.fd
    if n.tag == redir_e.Redir:
      redir_type = REDIR_ARG_TYPES[n.op.id]  # could be static in the LST?

      if redir_type == redir_arg_type_e.Path:
        # NOTES
        # - no globbing.  You can write to a file called '*.py'.
        # - set -o strict-array prevents joining by spaces
        val = self.word_ev.EvalWordToString(n.arg_word)
        filename = val.s
        if not filename:
          # Whether this is fatal depends on errexit.
          raise util.RedirectEvalError(
              "Redirect filename can't be empty", word=n.arg_word)

        return redirect.PathRedirect(n.op.id, fd, filename, n.op.span_id)

      elif redir_type == redir_arg_type_e.Desc:  # e.g. 1>&2
        val = self.word_ev.EvalWordToString(n.arg_word)
        t = val.s
        if not t:
          raise util.RedirectEvalError(
              "Redirect descriptor can't be empty", word=n.arg_word)
          return None
        try:
          target_fd = int(t)
        except ValueError:
          raise util.RedirectEvalError(
              "Redirect descriptor should look like an integer, got %s", val,
              word=n.arg_word)
          return None

        return redirect.DescRedirect(n.op.id, fd, target_fd, n.op.span_id)

      elif redir_type == redir_arg_type_e.Here:  # here word
        val = self.word_ev.EvalWordToString(n.arg_word)
        assert val.tag == value_e.Str, val
        # NOTE: bash and mksh both add \n
        return redirect.HereRedirect(fd, val.s + '\n', n.op.span_id)
      else:
        raise AssertionError('Unknown redirect op')

    elif n.tag == redir_e.HereDoc:
      # HACK: Wrap it in a word to evaluate.
      w = osh_word.CompoundWord(n.stdin_parts)
      val = self.word_ev.EvalWordToString(w)
      assert val.tag == value_e.Str, val
      return redirect.HereRedirect(fd, val.s, n.op.span_id)

    else:
      raise AssertionError('Unknown redirect type')

  def _EvalRedirects(self, node):
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
    return [self._EvalRedirect(redir) for redir in node.redirects]

  def _MakeProcess(self, node, job_state=None, disable_errexit=False):
    """
    Assume we will run the node in another process.  Return a process.
    """
    if node.tag == command_e.ControlFlow:
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
                                    disable_errexit=disable_errexit)
    p = process.Process(thunk, job_state=job_state)
    return p

  def RunSimpleCommand(self, arg_vec, fork_external, funcs=True):
    """
    Args:
      fork_external: for subshell ( ls / ) or ( command ls / )
    """
    argv = arg_vec.strs
    if arg_vec.spids:
      span_id = arg_vec.spids[0]
    else:
      span_id = const.NO_INTEGER

    # This happens when you write "$@" but have no arguments.
    if not argv:
      if self.exec_opts.strict_argv:
        e_die("Command evaluated to an empty argv array",
              span_id=span_id)
      else:
        return 0  # status 0, or skip it?

    arg0 = argv[0]

    builtin_id = builtin.ResolveSpecial(arg0)
    if builtin_id != builtin_e.NONE:
      return self._RunBuiltin(builtin_id, arg_vec, fork_external)

    # Builtins like 'true' can be redefined as functions.
    if funcs:
      func_node = self.funcs.get(arg0)
      if func_node is not None:
        # NOTE: Functions could call 'exit 42' directly, etc.
        status = self._RunFunc(func_node, argv[1:])
        return status

    builtin_id = builtin.Resolve(arg0)

    if builtin_id != builtin_e.NONE:
      return self._RunBuiltin(builtin_id, arg_vec, fork_external)

    environ = self.mem.GetExported()  # Include temporary variables

    if fork_external:
      thunk = process.ExternalThunk(self.ext_prog, arg_vec, environ)
      p = process.Process(thunk)
      status = p.Run(self.waiter)
      return status

    self.ext_prog.Exec(arg_vec, environ)  # NEVER RETURNS

  def _RunPipeline(self, node):
    pi = process.Pipeline()

    # First n-1 processes (which is empty when n == 1)
    n = len(node.children)
    for i in xrange(n - 1):
      p = self._MakeProcess(node.children[i])
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
    # Special case for pipeline.  There is some evidence here:
    # https://www.gnu.org/software/libc/manual/html_node/Launching-Jobs.html#Launching-Jobs
    #
    #  "You can either make all the processes in the process group be children
    #  of the shell process, or you can make one process in group be the
    #  ancestor of all the other processes in that group. The sample shell
    #  program presented in this chapter uses the first approach because it
    #  makes bookkeeping somewhat simpler."
    if node.tag == command_e.Pipeline:
      pi = process.Pipeline()
      for child in node.children:
        pi.Add(self._MakeProcess(child, job_state=self.job_state))

      job_id = pi.StartInBackground(self.waiter, self.job_state)

      self.mem.last_job_id = job_id  # for $!
      self.job_state.Register(job_id, pi)
      log('Started background pipeline with job ID %d', job_id)

    else:
      # Problem: to get the 'set -b' behavior of immediate notifications, we
      # have to register SIGCHLD.  But then that introduces race conditions.
      # If we haven't called Register yet, then we won't know who to notify.

      #log('job state %s', self.job_state)
      p = self._MakeProcess(node, job_state=self.job_state)
      pid = p.Start()
      self.mem.last_job_id = pid  # for $!
      self.job_state.Register(pid, p)
      self.waiter.Register(pid, p.WhenDone)
      log('Started background job with pid %d', pid)
    return 0

  def _EvalTempEnv(self, more_env):
    """For FOO=1 cmd."""
    for env_pair in more_env:
      val = self.word_ev.EvalWordToString(env_pair.val)
      # Set each var so the next one can reference it.  Example:
      # FOO=1 BAR=$FOO ls /
      self.mem.SetVar(lvalue.LhsName(env_pair.name), val,
                      (var_flags_e.Exported,), scope_e.TempEnv)

  def _Dispatch(self, node, fork_external):
    # If we call RunCommandSub in a recursive call to the executor, this will
    # be set true (if strict-errexit is false).  But it only lasts for one
    # command.
    self.check_command_sub_status = False

    #argv0 = None  # for error message
    check_errexit = False  # for errexit

    if node.tag == command_e.SimpleCommand:
      check_errexit = True

      # Find span_id for a basic implementation of $LINENO, e.g.
      # PS4='+$SOURCE_NAME:$LINENO:'
      # NOTE: osh2oil uses node.more_env, but we don't need that.
      span_id = const.NO_INTEGER
      if node.words:
        first_word = node.words[0]
        span_id = word.LeftMostSpanForWord(first_word)

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
      arg_vec = self.word_ev.EvalWordSequence2(words)
      argv = arg_vec.strs

      # This comes before evaluating env, in case there are problems evaluating
      # it.  We could trace the env separately?  Also trace unevaluated code
      # with set-o verbose?
      self.tracer.OnSimpleCommand(argv)

      # NOTE: RunSimpleCommand never returns when fork_external=False!
      if node.more_env:  # I think this guard is necessary?
        self.mem.PushTemp()
        try:
          self._EvalTempEnv(node.more_env)
          status = self.RunSimpleCommand(arg_vec, fork_external)
        finally:
          self.mem.PopTemp()
      else:
        status = self.RunSimpleCommand(arg_vec, fork_external)

    elif node.tag == command_e.ExpandedAlias:
      # Expanded aliases need redirects and env bindings from the calling
      # context, as well as redirects in the expansion!

      # TODO: SetCurrentSpanId to OUTSIDE?  Don't bother with stuff inside
      # expansion, since aliases are discouarged.

      if node.more_env:
        self.mem.PushTemp()
        try:
          self._EvalTempEnv(node.more_env)
          status = self._Execute(node.child)
        finally:
          self.mem.PopTemp()
      else:
        status = self._Execute(node.child)

    elif node.tag == command_e.Sentence:
      # Don't check_errexit since this isn't a real node!
      if node.terminator.id == Id.Op_Semi:
        status = self._Execute(node.child)
      else:
        status = self._RunJobInBackground(node.child)

    elif node.tag == command_e.Pipeline:
      check_errexit = True
      if node.stderr_indices:
        raise NotImplementedError('|&')

      if node.negated:
        self._PushErrExit()
        try:
          status2 = self._RunPipeline(node)
        finally:
          self._PopErrExit()

        # errexit is disabled for !.
        check_errexit = False
        status = 1 if status2 == 0 else 0
      else:
        status = self._RunPipeline(node)

    elif node.tag == command_e.Subshell:
      check_errexit = True
      # This makes sure we don't waste a process if we'd launch one anyway.
      p = self._MakeProcess(node.command_list)
      status = p.Run(self.waiter)

    elif node.tag == command_e.DBracket:
      span_id = node.spids[0]
      self.mem.SetCurrentSpanId(span_id)

      check_errexit = True
      result = self.bool_ev.Eval(node.expr)
      status = 0 if result else 1

    elif node.tag == command_e.DParen:
      span_id = node.spids[0]
      self.mem.SetCurrentSpanId(span_id)

      check_errexit = True
      i = self.arith_ev.Eval(node.child)
      status = 0 if i != 0 else 1

    elif node.tag == command_e.Assignment:
      # TODO: Also do dynamic assignment here
      flags = word_compile.ParseAssignFlags(node.flags)

      if node.keyword == Id.Assign_Local:
        lookup_mode = scope_e.LocalOnly
      # typeset and declare are synonyms?  I see typeset -a a=() the most.
      elif node.keyword in (Id.Assign_Declare, Id.Assign_Typeset):
        # declare is like local, except it can also be used outside functions?
        if var_flags_e.Global in flags:
          lookup_mode = scope_e.GlobalOnly
        else:
          lookup_mode = scope_e.LocalOnly
      elif node.keyword == Id.Assign_Readonly:
        lookup_mode = scope_e.Dynamic
        flags.append(var_flags_e.ReadOnly)
      elif node.keyword == Id.Assign_None:  # mutate existing local or global
        lookup_mode = scope_e.Dynamic
      else:
        raise AssertionError(node.keyword)

      for pair in node.pairs:
        # Use the spid of each pair.
        self.mem.SetCurrentSpanId(pair.spids[0])

        if pair.op == assign_op_e.PlusEqual:
          assert pair.rhs, pair.rhs  # I don't think a+= is valid?
          val = self.word_ev.EvalRhsWord(pair.rhs)
          old_val, lval = expr_eval.EvalLhsAndLookup(pair.lhs, self.arith_ev,
                                                     self.mem, self.exec_opts)
          sig = (old_val.tag, val.tag)
          if sig == (value_e.Undef, value_e.Str):
            pass  # val is RHS
          elif sig == (value_e.Undef, value_e.StrArray):
            pass  # val is RHS
          elif sig == (value_e.Str, value_e.Str):
            val = value.Str(old_val.s + val.s)
          elif sig == (value_e.Str, value_e.StrArray):
            e_die("Can't append array to string")
          elif sig == (value_e.StrArray, value_e.Str):
            e_die("Can't append string to array")
          elif sig == (value_e.StrArray, value_e.StrArray):
            val = value.StrArray(old_val.strs + val.strs)

        else:  # plain assignment
          spid = pair.spids[0]  # Source location for tracing
          lval = self._EvalLhs(pair.lhs, spid, lookup_mode)

          # RHS can be a string or array.
          if pair.rhs:
            val = self.word_ev.EvalRhsWord(pair.rhs)
            assert isinstance(val, value_t), val

          else:  # e.g. 'readonly x' or 'local x'
            val = None

        # NOTE: In bash and mksh, declare -a myarray makes an empty cell with
        # Undef value, but the 'array' attribute.

        #log('setting %s to %s with flags %s', lval, val, flags)
        self.mem.SetVar(lval, val, flags, lookup_mode)
        self.tracer.OnAssignment(lval, pair.op, val, flags, lookup_mode)

      # PATCH to be compatible with existing shells: If the assignment had a
      # command sub like:
      #
      # s=$(echo one; false)
      #
      # then its status will be in mem.last_status, and we can check it here.
      # If there was NOT a command sub in the assignment, then we don't want to
      # check it.
      if node.keyword == Id.Assign_None:  # mutate existing local or global
        # Only do this if there was a command sub?  How?  Look at node?
        # Set a flag in mem?   self.mem.last_status or
        if self.check_command_sub_status:
          last_status = self.mem.LastStatus()
          self._CheckStatus(last_status, node)
          status = last_status  # A global assignment shouldn't clear $?.
        else:
          status = 0
      else:
        # To be compatible with existing shells, local assignments DO clear
        # $?.  Even in strict mode, we don't need to bother setting
        # check_errexit = True, because we would have already checked the
        # command sub in RunCommandSub.
        status = 0
        # TODO: maybe we should have a "sane-status" that respects this:
        # false; echo $?; local f=x; echo $?

    elif node.tag == command_e.ControlFlow:
      if node.arg_word:  # Evaluate the argument
        val = self.word_ev.EvalWordToString(node.arg_word)
        assert val.tag == value_e.Str
        try:
          arg = int(val.s)  # They all take integers
        except ValueError:
          e_die('%r expected a number, got %r',
              node.token.val, val.s, word=node.arg_word)
      else:
        arg = 0  # return 0, exit 0, break 0 levels, etc.

      # NOTE: We don't do anything about a top-level 'return' here.  Unlike in
      # bash, that is OK.  If you can return from a sourced script, it makes
      # sense to return from a main script.
      ok = True
      tok = node.token
      if (tok.id in (Id.ControlFlow_Break, Id.ControlFlow_Continue) and
          self.loop_level == 0):
        ok = False
        msg = 'Invalid control flow at top level'

      if ok:
        raise _ControlFlow(tok, arg)

      if self.exec_opts.strict_control_flow:
        e_die(msg, token=tok)
      else:
        # Only print warnings, never fatal.
        # Bash oddly only exits 1 for 'return', but no other shell does.
        self.errfmt.Print(msg, prefix='warning: ', span_id=tok.span_id)
        status = 0

    # The only difference between these two is that CommandList has no
    # redirects.  We already took care of that above.
    elif node.tag in (command_e.CommandList, command_e.BraceGroup):
      status = self._ExecuteList(node.children)
      check_errexit = False

    elif node.tag == command_e.AndOr:
      # NOTE: && and || have EQUAL precedence in command mode.  See case #13
      # in dbracket.test.sh.

      left = node.children[0]

      # Suppress failure for every child except the last one.
      self._PushErrExit()
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
          self._PushErrExit()
          try:
            status = self._Execute(child)
          finally:
            self._PopErrExit()

        i += 1

    elif node.tag == command_e.WhileUntil:
      if node.keyword.id == Id.KW_While:
        _DonePredicate = lambda status: status != 0
      else:
        _DonePredicate = lambda status: status == 0

      status = 0

      self.loop_level += 1
      try:
        while True:
          self._PushErrExit()
          try:
            cond_status = self._ExecuteList(node.cond)
          finally:
            self._PopErrExit()

          done = cond_status != 0
          if _DonePredicate(cond_status):
            break
          try:
            status = self._Execute(node.body)  # last one wins
          except _ControlFlow as e:
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

    elif node.tag == command_e.ForEach:
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

    elif node.tag == command_e.ForExpr:
      status = 0
      init, cond, body, update = node.init, node.cond, node.body, node.update
      if init:
        self.arith_ev.Eval(init)

      self.loop_level += 1
      try:
        while True:
          if cond:
            b = self.arith_ev.Eval(cond)
            if not b:
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

    elif node.tag == command_e.DoGroup:
      status = self._ExecuteList(node.children)
      check_errexit = False  # not real statements

    elif node.tag == command_e.FuncDef:
      # NOTE: Would it make sense to evaluate the redirects BEFORE entering?
      # It will save time on function calls.
      self.funcs[node.name] = node
      status = 0

    elif node.tag == command_e.If:
      done = False
      for arm in node.arms:
        self._PushErrExit()
        try:
          status = self._ExecuteList(arm.cond)
        finally:
          self._PopErrExit()

        if status == 0:
          status = self._ExecuteList(arm.action)
          done = True
          break
      # TODO: The compiler should flatten this
      if not done and node.else_action is not None:
        status = self._ExecuteList(node.else_action)

    elif node.tag == command_e.NoOp:
      status = 0  # make it true

    elif node.tag == command_e.Case:
      val = self.word_ev.EvalWordToString(node.to_match)
      to_match = val.s

      status = 0  # If there are no arms, it should be zero?
      done = False

      for arm in node.arms:
        for pat_word in arm.pat_list:
          # NOTE: Is it OK that we're evaluating these as we go?

          # TODO: case "$@") shouldn't succeed?  That's a type error?
          # That requires strict-array?

          pat_val = self.word_ev.EvalWordToString(pat_word, do_fnmatch=True)
          #log('Matching word %r against pattern %r', to_match, pat_val.s)
          if libc.fnmatch(pat_val.s, to_match):
            status = self._ExecuteList(arm.action)
            done = True  # TODO: Parse ;;& and for fallthrough and such?
            break  # Only execute action ONCE
        if done:
          break

    elif node.tag == command_e.TimeBlock:
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
    """Apply redirects, call _Dispatch(), and performs the errexit check.

    Args:
      node: syntax_asdl.command_t
      fork_external: if we get a SimpleCommand that is an external command,
        should we fork first?  This is disabled in the context of a pipeline
        process and a subshell.
    """
    # See core/builtin.py for the Python signal handler that appends to this
    # list.

    if self.trap_nodes:
      # Make a copy and clear it so we don't cause an infinite loop.
      to_run = list(self.trap_nodes)
      del self.trap_nodes[:]
      for node in to_run:
        self._Execute(node)

    # These nodes have no redirects.  NOTE: Function definitions have
    # redirects, but we do NOT want to evaluate them yet!  They're evaluated
    # on every invocation.
    if node.tag in (
        command_e.NoOp, command_e.Assignment, command_e.ControlFlow,
        command_e.Pipeline, command_e.AndOr, command_e.CommandList,
        command_e.Sentence, command_e.TimeBlock,
        command_e.FuncDef
        ):
      redirects = []
    else:
      try:
        redirects = self._EvalRedirects(node)
      except util.RedirectEvalError as e:
        ui.PrettyPrintError(e, self.arena)
        redirects = None

    check_errexit = True

    if redirects is None:  # evaluation error
      status = 1

    elif redirects:
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
    status = 0  # for empty list
    for child in children:
      status = self._Execute(child)  # last status wins
    return status

  def LastStatus(self):
    """For main_loop.py to determine the exit code of the shell itself."""
    return self.mem.LastStatus()

  def ExecuteAndCatch(self, node, fork_external=True):
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
    - _RunFunc() for function call
    """
    is_control_flow = False
    is_fatal = False
    try:
      status = self._Execute(node, fork_external=fork_external)
    except _ControlFlow as e:
      # Return at top level is OK, unlike in bash.
      if e.IsReturn() or e.IsExit():
        is_control_flow = True
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
    except util.ParseError as e:
      self.dumper.MaybeCollect(self, e)  # Do this before unwinding stack
      raise
    except util.FatalRuntimeError as e:
      self.dumper.MaybeCollect(self, e)  # Do this before unwinding stack

      if not e.HasLocation():  # Last resort!
        e.span_id = self.mem.CurrentSpanId()

      ui.PrettyPrintError(e, self.arena, prefix='fatal: ')
      is_fatal = True
      status = e.exit_status if e.exit_status is not None else 1
    except (IOError, OSError) as e:
      # test this with prlimit --nproc=1 --pid=$$
      ui.Stderr('osh I/O error: %s', posix.strerror(e.errno))
      status = 2  # dash gives status 2

    self.dumper.MaybeDump(status)

    self.mem.SetLastStatus(status)
    return is_control_flow, is_fatal

  def MaybeRunExitTrap(self):
    """If an EXIT trap exists, run it.
    
    Returns:
      Whether we should use the status of the handler.

      This is odd behavior, but all bash/dash/mksh seem to agree on it.
      See cases 11 and 12 in builtin-trap.test.sh.
    """
    handler = self.traps.get('EXIT')
    if handler:
      is_control_flow, is_fatal = self.ExecuteAndCatch(handler.node)
      return is_control_flow  # explicit exit/return in the trap handler!
    else:
      return False  # nothing run, don't use its status

  def RunCommandSub(self, node):
    p = self._MakeProcess(node,
                          disable_errexit=not self.exec_opts.strict_errexit)

    r, w = posix.pipe()
    p.AddStateChange(process.StdoutToPipe(r, w))
    pid = p.Start()
    #log('Command sub started %d', pid)
    self.waiter.Register(pid, p.WhenDone)

    chunks = []
    posix.close(w)  # not going to write
    while True:
      byte_str = posix.read(r, 4096)
      if not byte_str:
        break
      chunks.append(byte_str)
    posix.close(r)

    status = p.WaitUntilDone(self.waiter)

    # OSH has the concept of aborting in the middle of a WORD.  We're not
    # waiting until the command is over!
    if self.exec_opts.strict_errexit:
      if self.exec_opts.ErrExit() and status != 0:
        raise util.ErrExitFailure(
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
    """Process sub creates a forks a process connected to a pipe.

    The pipe is typically passed to another process via a /dev/fd/$FD path.

    TODO:

    sane-proc-sub:
    - wait for all the words

    Otherwise, set $!  (mem.last_job_id)

    strict-proc-sub:
    - Don't allow it anywhere except SimpleCommand, any redirect, or
    Assignment?  And maybe not even assignment?

    Should you put return codes in @PROCESS_SUB_STATUS?  You need two of them.
    """
    p = self._MakeProcess(node)

    r, w = posix.pipe()

    if op_id == Id.Left_ProcSubIn:
      # Example: cat < <(head foo.txt)
      #
      # The head process should write its stdout to a pipe.
      redir = process.StdoutToPipe(r, w)

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

    #log('I am %d', posix.getpid())
    #log('Process sub started %d', pid)
    self.waiter.Register(pid, p.WhenDone)

    # NOTE: Like bash, we never actually wait on it!
    # TODO: At least set $! ?

    # Is /dev Linux-specific?
    if op_id == Id.Left_ProcSubIn:
      return '/dev/fd/%d' % r

    elif op_id == Id.Left_ProcSubOut:
      return '/dev/fd/%d' % w

    else:
      raise AssertionError

  def _RunFunc(self, func_node, argv):
    """Used to run SimpleCommand and to run registered completion hooks."""
    # These are redirects at DEFINITION SITE.  You can also have redirects at
    # the CALL SITE.  For example:
    #
    # f() { echo hi; } 1>&2
    # f 2>&1

    try:
      def_redirects = self._EvalRedirects(func_node)
    except util.RedirectEvalError as e:
      ui.PrettyPrintError(e, self.arena)
      return 1

    if def_redirects:
      if not self.fd_state.Push(def_redirects, self.waiter):
        return 1  # error

    self.mem.PushCall(func_node.name, func_node.spids[0], argv)

    # Redirects still valid for functions.
    # Here doc causes a pipe and Process(SubProgramThunk).
    try:
      status = self._Execute(func_node.body)
    except _ControlFlow as e:
      if e.IsReturn():
        status = e.StatusCode()
      elif e.IsExit():
        raise
      else:
        # break/continue used in the wrong place.
        e_die('Unexpected %r (in function call)', e.token.val, token=e.token)
    except (util.FatalRuntimeError, util.ParseError) as e:
      self.dumper.MaybeCollect(self, e)  # Do this before unwinding stack
      raise
    finally:
      self.mem.PopCall()
      if def_redirects:
        self.fd_state.Pop()

    return status

  def RunFuncForCompletion(self, func_node, argv):
    try:
      status = self._RunFunc(func_node, argv)
    except util.FatalRuntimeError as e:
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
