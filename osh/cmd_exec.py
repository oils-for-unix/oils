#!/usr/bin/env python
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
import sys
import time

from asdl import const
from asdl import pretty

from core import alloc
from core import main_loop
from core import process
from core import ui
from core import util
from core.meta import (
    Id, REDIR_ARG_TYPES, REDIR_DEFAULT_FD, runtime_asdl, syntax_asdl, types_asdl)

from frontend import args
from frontend import reader

from osh import braces
from osh import builtin
from osh import expr_eval
from osh import state
from osh import builtin_bracket
from osh import word
from osh import word_compile

try:
  import libc  # for fnmatch
except ImportError:
  from benchmarks import fake_libc as libc

lex_mode_e = types_asdl.lex_mode_e
redir_arg_type_e = types_asdl.redir_arg_type_e

command_e = syntax_asdl.command_e
redir_e = syntax_asdl.redir_e
lhs_expr_e = syntax_asdl.lhs_expr_e
assign_op_e = syntax_asdl.assign_op_e

osh_word = syntax_asdl.word  # TODO: Rename the definition
word_part = syntax_asdl.word_part

lvalue = runtime_asdl.lvalue
redirect = runtime_asdl.redirect
value = runtime_asdl.value
value_e = runtime_asdl.value_e
scope_e = runtime_asdl.scope_e
var_flags_e = runtime_asdl.var_flags_e
builtin_e = runtime_asdl.builtin_e

log = util.log
e_die = util.e_die


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
    self.dumper = None
    self.tracer = None
    self.debug_f = None
    self.trace_f = None


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
    self.debug_f = exec_deps.debug_f  # Used by ShellFuncAction too

    self.splitter = exec_deps.splitter
    self.word_ev = exec_deps.word_ev
    self.arith_ev = exec_deps.arith_ev
    self.bool_ev = exec_deps.bool_ev

    self.traps = {}  # signal/hook name -> callable
    self.nodes_to_run = []  # list of nodes, appended to by signal handlers
    self.dir_stack = state.DirStack()

    self.targets = []  # make syntax enters stuff here -- Target()
                       # metaprogramming or regular target syntax
                       # Whether argv[0] is make determines if it is executed

    self.waiter = process.Waiter()
    # sleep 5 & puts a (PID, job#) entry here.  And then "jobs" displays it.
    self.job_state = process.JobState()
    self.tracer = exec_deps.tracer

    self.loop_level = 0  # for detecting bad top-level break/continue
    self.check_command_sub_status = False  # a hack

  def _EvalHelper(self, c_parser, source_name):
    self.arena.PushSource(source_name)
    try:
      return main_loop.Batch(self, c_parser, self.arena)
    finally:
      self.arena.PopSource()

  def _Eval(self, argv, eval_spid):
    # TODO:
    # - (argv, spid) should be a pattern for all builtins?  They all will need
    # to report usage errors.
    # - set -o sane-eval should change eval to take a single string.
    code_str = ' '.join(argv)
    line_reader = reader.StringLineReader(code_str, self.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader)

    span = self.arena.GetLineSpan(eval_spid)
    path, line_num = self.arena.GetDebugInfo(span.line_id)

    source_name = '<eval string from %s:%d>' % (path, line_num)
    return self._EvalHelper(c_parser, source_name)

  def ParseTrapCode(self, code_str):
    """
    Returns:
      A node, or None if the code is invalid.
    """
    line_reader = reader.StringLineReader(code_str, self.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader)

    source_name = '<trap string>'
    self.arena.PushSource(source_name)

    try:
      try:
        node = main_loop.ParseWholeFile(c_parser)
      except util.ParseError as e:
        util.error('Parse error in %r:', source_name)
        ui.PrettyPrintError(e, self.arena, sys.stderr)
        return None

    finally:
      self.arena.PopSource()

    return node

  def _Source(self, argv):
    try:
      path = argv[0]
    except IndexError:
      # TODO: Should point to the source statement that failed.
      util.error('source: missing required argument')
      return 1

    try:
      f = self.fd_state.Open(path)  # Shell can't use descriptors 3-9
    except OSError as e:
      # TODO: Should point to the source statement that failed.
      util.error('source %r failed: %s', path, posix.strerror(e.errno))
      return 1

    try:
      line_reader = reader.FileLineReader(f, self.arena)
      c_parser = self.parse_ctx.MakeOshParser(line_reader)

      # A sourced module CAN have a new arguments array, but it always shares
      # the same variable scope as the caller.  The caller could be at either a
      # global or a local scope.
      source_argv = argv[1:]
      self.mem.PushSource(path, source_argv)
      try:
        status = self._EvalHelper(c_parser, path)
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

  def _Exec(self, argv):
    # Either execute command with redirects, or apply redirects in this shell.
    # NOTE: Redirects were processed earlier.
    if argv:
      environ = self.mem.GetExported()
      process.ExecExternalProgram(argv, environ)  # never returns
    else:
      return 0

  def _RunBuiltin(self, builtin_id, argv, span_id):
    argv = argv[1:]  # Builtins don't need to know their own name.

    #
    # TODO: Convert everything to this new style
    #

    builtin_func = self.builtins.get(builtin_id)
    if builtin_func is not None:
      status = builtin_func(argv)

    elif builtin_id == builtin_e.EXEC:
      status = self._Exec(argv)  # may never return
      # But if it returns, then we want to permanently apply the redirects
      # associated with it.
      self.fd_state.MakePermanent()

    elif builtin_id == builtin_e.READ:
      status = builtin.Read(argv, self.splitter, self.mem)

    elif builtin_id == builtin_e.ECHO:
      status = builtin.Echo(argv)

    elif builtin_id == builtin_e.PRINTF:
      status = builtin.Printf(argv, self.mem)

    elif builtin_id == builtin_e.SHIFT:
      status = builtin.Shift(argv, self.mem)

    elif builtin_id == builtin_e.CD:
      status = builtin.Cd(argv, self.mem, self.dir_stack)

    elif builtin_id == builtin_e.SET:
      status = builtin.Set(argv, self.exec_opts, self.mem)

    elif builtin_id == builtin_e.SHOPT:
      status = builtin.Shopt(argv, self.exec_opts)

    elif builtin_id == builtin_e.UNSET:
      status = builtin.Unset(argv, self.mem, self.funcs)

    elif builtin_id == builtin_e.EXPORT:
      status = builtin.Export(argv, self.mem)

    elif builtin_id == builtin_e.WAIT:
      status = builtin.Wait(argv, self.waiter, self.job_state, self.mem)

    elif builtin_id == builtin_e.JOBS:
      status = builtin.Jobs(argv, self.job_state)

    elif builtin_id == builtin_e.PUSHD:
      status = builtin.Pushd(argv, self.mem.GetVar('HOME'), self.dir_stack)

    elif builtin_id == builtin_e.POPD:
      status = builtin.Popd(argv, self.mem.GetVar('HOME'), self.dir_stack)

    elif builtin_id == builtin_e.DIRS:
      status = builtin.Dirs(argv, self.mem.GetVar('HOME'), self.dir_stack)

    elif builtin_id == builtin_e.PWD:
      status = builtin.Pwd(argv, self.mem)

    elif builtin_id in (builtin_e.SOURCE, builtin_e.DOT):
      status = self._Source(argv)

    elif builtin_id == builtin_e.TRAP:
      status = builtin.Trap(argv, self.traps, self.nodes_to_run, self)

    elif builtin_id == builtin_e.UMASK:
      status = builtin.Umask(argv)

    elif builtin_id == builtin_e.EVAL:
      status = self._Eval(argv, span_id)

    elif builtin_id == builtin_e.COLON:  # special builtin like 'true'
      status = 0

    elif builtin_id == builtin_e.TRUE:
      status = 0

    elif builtin_id == builtin_e.FALSE:
      status = 1

    elif builtin_id == builtin_e.TEST:
      status = builtin_bracket.Test(argv, False)

    elif builtin_id == builtin_e.BRACKET:
      status = builtin_bracket.Test(argv, True)  # need_right_bracket

    elif builtin_id == builtin_e.GETOPTS:
      status = builtin.GetOpts(argv, self.mem)

    elif builtin_id == builtin_e.COMMAND:
      path = self.mem.GetVar('PATH')
      status = builtin.Command(argv, self.funcs, path)

    elif builtin_id == builtin_e.TYPE:
      path = self.mem.GetVar('PATH')
      status = builtin.Type(argv, self.funcs, path)

    elif builtin_id == builtin_e.HELP:
      loader = util.GetResourceLoader()
      status = builtin.Help(argv, loader)

    elif builtin_id in (builtin_e.DECLARE, builtin_e.TYPESET):
      # These are synonyms
      status = builtin.DeclareTypeset(argv, self.mem, self.funcs)

    elif builtin_id == builtin_e.ALIAS:
      status = builtin.Alias(argv, self.aliases)

    elif builtin_id == builtin_e.UNALIAS:
      status = builtin.UnAlias(argv, self.aliases)

    elif builtin_id == builtin_e.REPR:
      status = builtin.Repr(argv, self.mem)

    else:
      raise AssertionError('Unhandled builtin: %s' % builtin_id)

    assert isinstance(status, int)
    return status

  def _PushErrExit(self):
    self.exec_opts.errexit.Push()

  def _PopErrExit(self):
    self.exec_opts.errexit.Pop()

  def _CheckStatus(self, status, node, argv0=None):
    """ErrExitFailure with location info attached."""
    if self.exec_opts.ErrExit() and status != 0:
      # Add context based on node type
      if node.tag == command_e.SimpleCommand:
        argv0 = argv0 or '<unknown>'
        raise util.ErrExitFailure(
            '[%d] %r command exited with status %d', posix.getpid(), argv0,
            status, word=node.words[0], status=status)
      elif node.tag == command_e.Assignment:
        span_id = self._SpanIdForAssignment(node)
        raise util.ErrExitFailure(
            '[%d] assignment exited with status %d', posix.getpid(),
            status, span_id=span_id, status=status)

      else:
        raise util.ErrExitFailure(
            '[%d] %r exited with status %d', posix.getpid(),
            node.__class__.__name__, status, status=status)

  def _EvalLhs(self, node, spid, lookup_mode):
    """lhs_expr -> lvalue."""
    assert isinstance(node, syntax_asdl.lhs_expr), node

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
        # NOTE: no globbing.  You can write to a file called '*.py'.
        val = self.word_ev.EvalWordToString(n.arg_word)
        if val.tag != value_e.Str:  # TODO: This error never fires
          util.error("Redirect filename must be a string, got %s", val)
          return None
        filename = val.s
        if not filename:
          # Whether this is fatal depends on errexit.
          util.error("Redirect filename can't be empty")
          return None

        return redirect.PathRedirect(n.op.id, fd, filename)

      elif redir_type == redir_arg_type_e.Desc:  # e.g. 1>&2
        val = self.word_ev.EvalWordToString(n.arg_word)
        if val.tag != value_e.Str:  # TODO: This error never fires
          util.error("Redirect descriptor should be a string, got %s", val)
          return None
        t = val.s
        if not t:
          util.error("Redirect descriptor can't be empty")
          return None
        try:
          target_fd = int(t)
        except ValueError:
          util.error(
              "Redirect descriptor should look like an integer, got %s", val)
          return None

        return redirect.DescRedirect(n.op.id, fd, target_fd)

      elif redir_type == redir_arg_type_e.Here:  # here word
        val = self.word_ev.EvalWordToString(n.arg_word)
        assert val.tag == value_e.Str, val
        # NOTE: bash and mksh both add \n
        return redirect.HereRedirect(fd, val.s + '\n')
      else:
        raise AssertionError('Unknown redirect op')

    elif n.tag == redir_e.HereDoc:
      # HACK: Wrap it in a word to evaluate.
      w = osh_word.CompoundWord(n.stdin_parts)
      val = self.word_ev.EvalWordToString(w)
      assert val.tag == value_e.Str, val
      return redirect.HereRedirect(fd, val.s)

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
    """
    redirects = []
    for redir in node.redirects:
      r = self._EvalRedirect(redir)
      if r is None:
        return None  # bad redirect
      redirects.append(r)
    return redirects

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

  def _RunSimpleCommand(self, argv, fork_external, span_id, funcs=True):
    """
    Args:
      fork_external: for subshell ( ls / ) or ( command ls / )
    """
    # This happens when you write "$@" but have no arguments.
    if not argv:
      return 0  # status 0, or skip it?

    arg0 = argv[0]

    builtin_id = builtin.ResolveSpecial(arg0)
    if builtin_id != builtin_e.NONE:
      try:
        status = self._RunBuiltin(builtin_id, argv, span_id)
      except args.UsageError as e:
        ui.usage('osh %r usage error: %s', arg0, e)
        status = 2  # consistent error code for usage error
      return status

    # Builtins like 'true' can be redefined as functions.
    if funcs:
      func_node = self.funcs.get(arg0)
      if func_node is not None:
        # NOTE: Functions could call 'exit 42' directly, etc.
        status = self._RunFunc(func_node, argv[1:])
        return status

    builtin_id = builtin.Resolve(arg0)

    if builtin_id == builtin_e.COMMAND:  # 'command ls' suppresses function lookup
      n = len(argv)
      if n == 1:
        return 0  # 'command', like the 'if not argv' case above
      # The 'command' builtin syntax is simple enough that this is 100%
      # correct, not a heuristic.
      elif n >= 2 and argv[1] != '-v':
        return self._RunSimpleCommand(argv[1:], fork_external, span_id,
                                      funcs=False)

    if builtin_id != builtin_e.NONE:
      try:
        status = self._RunBuiltin(builtin_id, argv, span_id)
      except args.UsageError as e:
        ui.usage('osh %r usage error: %s', arg0, e)
        status = 2  # consistent error code for usage error
      return status

    environ = self.mem.GetExported()  # Include temporary variables

    if fork_external:
      thunk = process.ExternalThunk(argv, environ)
      p = process.Process(thunk)
      status = p.Run(self.waiter)
      return status

    # NOTE: Never returns!
    process.ExecExternalProgram(argv, environ)

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
    state.SetGlobalArray(self.mem, 'PIPESTATUS', [str(p) for p in pipe_status])

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

  # TODO: Also change to BareAssign (set global or mutate local) and
  # KeywordAssign.  The latter may have flags too.
  def _SpanIdForAssignment(self, node):
    # TODO: Share with tracing (SetCurrentSpanId) and _CheckStatus
    return node.spids[0]

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
      argv = self.word_ev.EvalWordSequence(words)

      # This comes before evaluating env, in case there are problems evaluating
      # it.  We could trace the env separately?  Also trace unevaluated code
      # with set-o verbose?
      self.tracer.OnSimpleCommand(argv)

      if node.more_env:
        self.mem.PushTemp()
      try:
        for env_pair in node.more_env:
          val = self.word_ev.EvalWordToString(env_pair.val)
          # Set each var so the next one can reference it.  Example:
          # FOO=1 BAR=$FOO ls /
          self.mem.SetVar(lvalue.LhsName(env_pair.name), val,
                          (var_flags_e.Exported,), scope_e.TempEnv)

        # NOTE: This might never return!  In the case of fork_external=False.
        status = self._RunSimpleCommand(argv, fork_external, span_id)
      finally:
        if node.more_env:
          self.mem.PopTemp()

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
      p = self._MakeProcess(node.child)
      status = p.Run(self.waiter)

    elif node.tag == command_e.DBracket:
      check_errexit = True
      result = self.bool_ev.Eval(node.expr)
      status = 0 if result else 1

    elif node.tag == command_e.DParen:
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
            assert isinstance(val, runtime_asdl.value), val

          else:  # e.g. 'readonly x' or 'local x'
            val = None

        # NOTE: In bash and mksh, declare -a myarray makes an empty cell with
        # Undef value, but the 'array' attribute.

        #log('setting %s to %s with flags %s', lval, val, flags)
        self.mem.SetVar(lval, val, flags, lookup_mode,
                        strict_array=self.exec_opts.strict_array)

        # Assignment always appears to have a spid.
        if node.spids:
          current_spid = node.spids[0]
        else:
          current_spid = const.NO_INTEGER
        self.mem.SetCurrentSpanId(current_spid)
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
          self._CheckStatus(self.mem.last_status, node)
          # A global assignment shouldn't clear $?.
          status = self.mem.last_status
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
        arg = int(val.s)  # They all take integers
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
        ui.PrintFilenameAndLine(tok.span_id, self.arena)
        util.warn(msg)
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
      node: syntax_asdl.command
      fork_external: if we get a SimpleCommand that is an external command,
        should we fork first?  This is disabled in the context of a pipeline
        process and a subshell.
    """
    # See core/builtin.py for the Python signal handler that appends to this
    # list.

    if self.nodes_to_run:
      # Make a copy and clear it so we don't cause an infinite loop.
      to_run = list(self.nodes_to_run)
      del self.nodes_to_run[:]
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
      redirects = self._EvalRedirects(node)

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

    self.mem.last_status = status

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
    return self.mem.last_status

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
        raise  # Invalid
    except util.ParseError as e:
      self.dumper.MaybeCollect(self, e)  # Do this before unwinding stack
      raise
    except util.FatalRuntimeError as e:
      self.dumper.MaybeCollect(self, e)  # Do this before unwinding stack
      ui.PrettyPrintError(e, self.arena)
      is_fatal = True
      status = e.exit_status if e.exit_status is not None else 1

    self.dumper.MaybeDump(status)

    self.mem.last_status = status
    return is_control_flow, is_fatal

  # NOTE: Is this only used by tests?
  def Execute(self, node, fork_external=True):
    """Execute a subprogram, handling _ControlFlow and fatal exceptions.

    This is just like ExecuteAndCatch(), but we return a status.

    Returns:
      status: numeric exit code
    """
    self.ExecuteAndCatch(node, fork_external=fork_external)
    return self.LastStatus()

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
      self.mem.last_status = status

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
    # the CALLER.  For example:

    # f() { echo hi; } 1>&2
    # f 2>&1

    def_redirects = self._EvalRedirects(func_node)
    if def_redirects is None:  # error
      return None
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
      ui.PrettyPrintError(e, self.arena, sys.stderr)
      status = e.exit_status if e.exit_status is not None else 1
    except _ControlFlow as e:
       # shouldn't be able to exit the shell from a completion hook!
      util.error('Attempted to exit from completion hook.')
      status = 1
    return status


class Tracer(object):
  """A tracer for this process.

  TODO: Connect it somehow to tracers for other processes.  So you can make an
  HTML report offline.

  https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html#Bash-Variables

  Bare minimum to debug problems:
    - argv and span ID of the SimpleCommand that corresponds to that
    - then print line number using arena
    - set -x doesn't print line numbers!  OH but you can do that with
      PS4=$LINENO
  """
  def __init__(self, parse_ctx, exec_opts, mem, word_ev, f):
    """
    Args:
      parse_ctx: For parsing PS4.
      exec_opts: For xtrace setting
      mem: for retrieving PS4
      word_ev: for evaluating PS4
    """
    self.parse_ctx = parse_ctx
    self.exec_opts = exec_opts
    self.mem = mem
    self.word_ev = word_ev
    self.f = f  # can be the --debug-file as well

    self.arena = alloc.SideArena('<$PS4>')
    self.parse_cache = {}  # PS4 value -> CompoundWord.  PS4 is scoped.

  def _EvalPS4(self):
    """For set -x."""

    val = self.mem.GetVar('PS4')
    assert val.tag == value_e.Str

    s = val.s
    if s:
      first_char, ps4 = s[0], s[1:]
    else:
      first_char, ps4 = '+', ' '  # default

    # NOTE: This cache is slightly broken because aliases are mutable!  I think
    # thati s more or less harmless though.
    try:
      ps4_word = self.parse_cache[ps4]
    except KeyError:
      # We have to parse this at runtime.  PS4 should usually remain constant.
      w_parser = self.parse_ctx.MakeWordParserForPlugin(ps4, self.arena)

      try:
        ps4_word = w_parser.ReadForPlugin()
      except util.ParseError as e:
        error_str = '<ERROR: cannot parse PS4>'
        t = syntax_asdl.token(Id.Lit_Chars, error_str, const.NO_INTEGER)
        ps4_word = osh_word.CompoundWord([word_part.LiteralPart(t)])
      self.parse_cache[ps4] = ps4_word

    #print(ps4_word)

    # TODO: Repeat first character according process stack depth.  Where is
    # that stored?  In the executor itself?  It should be stored along with
    # the PID.  Need some kind of ShellProcessState or something.
    #
    # We should come up with a better mechanism.  Something like $PROC_INDENT
    # and $OIL_XTRACE_PREFIX.

    # TODO: Handle runtime errors!  For example, you could PS4='$(( 1 / 0 ))'
    # <ERROR: cannot evaluate PS4>
    prefix = self.word_ev.EvalWordToString(ps4_word)

    return first_char, prefix.s

  def OnSimpleCommand(self, argv):
    # NOTE: I think tracing should be on by default?  For post-mortem viewing.
    if not self.exec_opts.xtrace:
      return

    first_char, prefix = self._EvalPS4()
    cmd = ' '.join(pretty.Str(a) for a in argv)
    self.f.log('%s%s%s', first_char, prefix, cmd)

  def OnAssignment(self, lval, op, val, flags, lookup_mode):
    # NOTE: I think tracing should be on by default?  For post-mortem viewing.
    if not self.exec_opts.xtrace:
      return

    # Now we have to get the prefix
    first_char, prefix = self._EvalPS4()
    op_str = {assign_op_e.Equal: '=', assign_op_e.PlusEqual: '+='}[op]
    self.f.log('%s%s%s %s %s', first_char, prefix, lval, op_str, val)

  def Event(self):
    """
    Other events:

    - Function call events.  As opposed to external commands.
    - Process Forks.  Subshell, command sub, pipeline,
    - Command Completion -- you get the status code.
    - Assignments
      - We should desugar to SetVar like mksh
    """
    pass
