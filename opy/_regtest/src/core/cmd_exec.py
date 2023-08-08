#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
"""
cmd_exec.py -- Interpreter for the command language.

Problems:
$ < Makefile cat | < NOTES.txt head

This just does head?  Last one wins.
"""

import os
import resource
import sys
import time

from asdl import const

from core import alloc
from core import args
from core import braces
from core import expr_eval
from core import legacy
from core import reader
from core import test_builtin
from core import word
from core import word_eval
from core import ui
from core import util
from core import builtin
from core import process
from core import state
from core import word_compile

from osh.meta import ast, Id, REDIR_ARG_TYPES, REDIR_DEFAULT_FD, runtime, types
from osh import parse_lib

try:
  import libc  # for fnmatch
except ImportError:
  from benchmarks import fake_libc as libc

builtin_e = builtin.builtin_e

lex_mode_e = types.lex_mode_e
redir_arg_type_e = types.redir_arg_type_e

command_e = ast.command_e
redir_e = ast.redir_e
lhs_expr_e = ast.lhs_expr_e
assign_op_e = ast.assign_op_e

value_e = runtime.value_e
scope_e = runtime.scope_e
var_flags_e = runtime.var_flags_e

log = util.log
e_die = util.e_die


class _ControlFlow(RuntimeError):
  """Internal exception for control flow.

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


class Executor(object):
  """Executes the program by tree-walking.

  It also does some double-dispatch by passing itself into Eval() for
  CompoundWord/WordPart.
  """
  def __init__(self, mem, fd_state, status_lines, funcs, completion,
               comp_lookup, exec_opts, arena):
    """
    Args:
      mem: Mem instance for storing variables
      fd_state: FdState() for managing descriptors
      status_lines: shared with completion.  TODO: Move this to the end.
      funcs: registry of functions (these names are completed)
      completion: completion module, if available
      comp_lookup: completion pattern/action
      exec_opts: ExecOpts
      arena: for printing error locations
    """
    self.mem = mem
    self.fd_state = fd_state
    self.status_lines = status_lines  
    # function space is different than var space.  Not hierarchical.
    self.funcs = funcs
    self.completion = completion
    # Completion hooks, set by 'complete' builtin.
    self.comp_lookup = comp_lookup
    # This is for shopt and set -o.  They are initialized by flags.
    self.exec_opts = exec_opts
    self.arena = arena

    self.splitter = legacy.SplitContext(self.mem)
    self.word_ev = word_eval.NormalWordEvaluator(
        mem, exec_opts, self.splitter, self)
    self.arith_ev = expr_eval.ArithEvaluator(mem, exec_opts, self.word_ev)
    self.bool_ev = expr_eval.BoolEvaluator(mem, exec_opts, self.word_ev)

    self.traps = {}  # signal/hook name -> callable
    self.nodes_to_run = []  # list of nodes, appended to by signal handlers
    self.dir_stack = state.DirStack()

    # TODO: Pass these in from main()
    self.aliases = {}  # alias name -> string
    self.targets = []  # make syntax enters stuff here -- Target()
                       # metaprogramming or regular target syntax
                       # Whether argv[0] is make determines if it is executed

    self.waiter = process.Waiter()
    # sleep 5 & puts a (PID, job#) entry here.  And then "jobs" displays it.
    self.job_state = process.JobState()

    self.loop_level = 0  # for detecting bad top-level break/continue

    self.tracer = Tracer(exec_opts, mem, self.word_ev)
    self.check_command_sub_status = False  # a hack

  def _Complete(self, argv):
    """complete builtin - register a completion function.

    NOTE: It's a member of Executor because it creates a ShellFuncAction, which
    needs an Executor.
    """
    command = argv[0]  # e.g. 'grep'
    func_name = argv[1]

    # NOTE: bash doesn't actually check the name until completion time, but
    # obviously it's better to check here.
    func = self.funcs.get(func_name)
    if func is None:
      print('Function %r not found' % func_name)
      return 1

    if self.completion:
      chain = self.completion.ShellFuncAction(self, func)
      self.comp_lookup.RegisterName(command, chain)
      # TODO: Some feedback would be nice?
    else:
      util.error('Oil was not built with readline/completion.')
    return 0

  def _CompGen(self, argv):
    raise NotImplementedError

  def _EvalHelper(self, c_parser, source_name):
    self.arena.PushSource(source_name)
    try:
      node = c_parser.ParseWholeFile()
      # NOTE: We could model a parse error as an exception, like Python, so we
      # get a traceback.  (This won't be applicable for a static module
      # system.)
      if not node:
        util.error('Parse error in %r:', source_name)
        err = c_parser.Error()
        ui.PrintErrorStack(err, self.arena, sys.stderr)
        return 1

      status = self._Execute(node)
      return status

    finally:
      self.arena.PopSource()

  def _Eval(self, argv):
    # TODO: set -o sane-eval should change eval to
    code_str = ' '.join(argv)
    line_reader = reader.StringLineReader(code_str, self.arena)
    _, c_parser = parse_lib.MakeParser(line_reader, self.arena)
    return self._EvalHelper(c_parser, '<eval string>')

  def ParseTrapCode(self, code_str):
    """
    Returns:
      A node, or None if the code is invalid.
    """
    line_reader = reader.StringLineReader(code_str, self.arena)
    _, c_parser = parse_lib.MakeParser(line_reader, self.arena)

    source_name = '<trap string>'
    self.arena.PushSource(source_name)
    try:
      node = c_parser.ParseWholeFile()
      if not node:
        util.error('Parse error in %r:', source_name)
        err = c_parser.Error()
        ui.PrintErrorStack(err, self.arena, sys.stderr)
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
      util.error('source %r failed: %s', path, os.strerror(e.errno))
      return 1

    try:
      line_reader = reader.FileLineReader(f, self.arena)
      _, c_parser = parse_lib.MakeParser(line_reader, self.arena)
      return self._EvalHelper(c_parser, path)

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

  def _RunBuiltin(self, builtin_id, argv):
    # NOTE: Builtins don't need to know their own name.
    argv = argv[1:]

    # TODO: figure out a quicker dispatch mechanism.  Just make a table of
    # builtins I guess.
    if builtin_id == builtin_e.EXEC:
      status = self._Exec(argv)  # may never return
      # But if it returns, then we want to permanently apply the redirects
      # associated with it.
      self.fd_state.MakePermanent()

    elif builtin_id == builtin_e.READ:
      status = builtin.Read(argv, self.splitter, self.mem)

    elif builtin_id == builtin_e.ECHO:
      status = builtin.Echo(argv)

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

    elif builtin_id in (builtin_e.SOURCE, builtin_e.DOT):
      status = self._Source(argv)

    elif builtin_id == builtin_e.TRAP:
      status = builtin.Trap(argv, self.traps, self.nodes_to_run, self)

    elif builtin_id == builtin_e.UMASK:
      status = builtin.Umask(argv)

    elif builtin_id == builtin_e.EVAL:
      status = self._Eval(argv)

    elif builtin_id == builtin_e.COMPLETE:
      status = self._Complete(argv)

    elif builtin_id == builtin_e.COMPGEN:
      status = self._CompGen(argv)

    elif builtin_id == builtin_e.COLON:  # special builtin like 'true'
      status = 0

    elif builtin_id == builtin_e.TRUE:
      status = 0

    elif builtin_id == builtin_e.FALSE:
      status = 1

    elif builtin_id == builtin_e.TEST:
      status = test_builtin.Test(argv, False)

    elif builtin_id == builtin_e.BRACKET:
      status = test_builtin.Test(argv, True)  # need_right_bracket

    elif builtin_id == builtin_e.GETOPTS:
      status = builtin.GetOpts(argv, self.mem)

    elif builtin_id == builtin_e.COMMAND:
      path = self.mem.GetVar('PATH')
      status = builtin.Command(argv, self.funcs, path)

    elif builtin_id == builtin_e.TYPE:
      path = self.mem.GetVar('PATH')
      status = builtin.Type(argv, self.funcs, path)

    elif builtin_id in (builtin_e.DECLARE, builtin_e.TYPESET):
      # These are synonyms
      status = builtin.DeclareTypeset(argv, self.mem, self.funcs)

    elif builtin_id == builtin_e.HELP:
      loader = util.GetResourceLoader()
      status = builtin.Help(argv, loader)

    elif builtin_id == builtin_e.DEBUG_LINE:
      status = builtin.DebugLine(argv, self.status_lines)

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
            '[%d] %r command exited with status %d', os.getpid(), argv0,
            status, word=node.words[0], status=status)
      elif node.tag == command_e.Assignment:
        span_id = self._SpanIdForAssignment(node)
        raise util.ErrExitFailure(
            '[%d] assignment exited with status %d', os.getpid(), 
            status, span_id=span_id, status=status)

      else:
        raise util.ErrExitFailure(
            '[%d] %r exited with status %d', os.getpid(),
            node.__class__.__name__, status, status=status)

  def _EvalLhs(self, node, spid):
    """lhs_expr -> lvalue."""
    assert isinstance(node, ast.lhs_expr), node

    if node.tag == lhs_expr_e.LhsName:  # a=x
      node = runtime.LhsName(node.name)
      node.spids.append(spid)
      return node

    if node.tag == lhs_expr_e.LhsIndexedName:  # a[1+2]=x
      i = self.arith_ev.Eval(node.index)
      return runtime.LhsIndexedName(node.name, i)

    raise AssertionError(node.tag)

  def _EvalRedirect(self, n):
    fd = REDIR_DEFAULT_FD[n.op_id] if n.fd == const.NO_INTEGER else n.fd
    if n.tag == redir_e.Redir:
      redir_type = REDIR_ARG_TYPES[n.op_id]  # could be static in the LST?

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

        return runtime.PathRedirect(n.op_id, fd, filename)

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

        return runtime.DescRedirect(n.op_id, fd, target_fd)

      elif redir_type == redir_arg_type_e.Here:  # here word
        # TODO: decay should be controlled by an option
        val = self.word_ev.EvalWordToString(n.arg_word, decay=True)
        if val.tag != value_e.Str:   # TODO: This error never fires
          util.warn("Here word body should be a string, got %s", val)
          return None
        # NOTE: bash and mksh both add \n
        return runtime.HereRedirect(fd, val.s + '\n')
      else:
        raise AssertionError('Unknown redirect op')

    elif n.tag == redir_e.HereDoc:
      # TODO: decay should be controlled by an option
      val = self.word_ev.EvalWordToString(n.body, decay=True)
      if val.tag != value_e.Str:   # TODO: This error never fires
        util.warn("Here doc body should be a string, got %s", val)
        return None
      return runtime.HereRedirect(fd, val.s)

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
    # - We could return the `exit` builtin into a FatalRuntimeError exception
    # and get this check for "free".
    thunk = process.SubProgramThunk(self, node,
                                    disable_errexit=disable_errexit)
    p = process.Process(thunk, job_state=job_state)
    return p

  def _RunSimpleCommand(self, argv, fork_external):
    # This happens when you write "$@" but have no arguments.
    if not argv:
      return 0  # status 0, or skip it?

    arg0 = argv[0]

    builtin_id = builtin.ResolveSpecial(arg0)
    if builtin_id != builtin_e.NONE:
      try:
        status = self._RunBuiltin(builtin_id, argv)
      except args.UsageError as e:
        # TODO: Make this message more consistent?
        util.usage(str(e))
        status = 2  # consistent error code for usage error
      return status

    # Builtins like 'true' can be redefined as functions.
    func_node = self.funcs.get(arg0)
    if func_node is not None:
      # NOTE: Functions could call 'exit 42' directly, etc.
      status = self.RunFunc(func_node, argv)
      return status

    builtin_id = builtin.Resolve(arg0)
    if builtin_id != builtin_e.NONE:
      try:
        status = self._RunBuiltin(builtin_id, argv)
      except args.UsageError as e:
        # TODO: Make this message more consistent?
        util.usage(str(e))
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

  def _MakePipeline(self, node, job_state=None):
    # NOTE: First or last one could use the "main" shell thread.  Doesn't have
    # to run in subshell.  Although I guess it's simpler if it always does.
    # I think bash has an option to control this?  echo hi | read x; should
    # test it.
    pi = process.Pipeline(job_state=job_state)

    for child in node.children:
      p = self._MakeProcess(child)  # NOTE: evaluates, does errexit guard
      pi.Add(p)
    return pi

  def _RunPipeline(self, node):
    pi = self._MakePipeline(node)

    pipe_status = pi.Run(self.waiter)
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
      pi = self._MakePipeline(node, job_state=self.job_state)
      job_id = pi.Start(self.waiter)
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

  def _SetSourceLocation(self, span_id):
    # TODO: This API should be simplified
    line_span = self.arena.GetLineSpan(span_id)
    line_id = line_span.line_id
    source_name, line_num = self.arena.GetDebugInfo(line_id)
    self.mem.SetSourceLocation(source_name, line_num)

  # TODO: Also change to BareAssign (set global or mutate local) and
  # KeywordAssign.  The latter may have flags too.
  def _SpanIdForAssignment(self, node):
    # TODO: Share with tracing (SetSourceLocation) and _CheckStatus
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

      # This is a very basic implementation for PS4='+$SOURCE_NAME:$LINENO:'

      # TODO:
      # - It should be a stack eventually.  So if there is an exception we can
      # print the full stack trace.  Python has a list of frame objects, and
      # each one has a location?
      # - The API to get DebugInfo is overly long.
      # - Maybe just do a simple thing like osh-o line-trace without any PS4?

      # NOTE: osh2oil uses node.more_env, but we don't need that.
      found = False
      if node.words:
        first_word = node.words[0]
        span_id = word.LeftMostSpanForWord(first_word)
        if span_id == const.NO_INTEGER:
          log('Warning: word has no location information: %s', first_word)
        else:
          found = True

      if found:
        # NOTE: This is what we want to expose as variables for PS4.
        #ui.PrintFilenameAndLine(span_id, self.arena)
        self._SetSourceLocation(span_id)
      else:
        self.mem.SetSourceLocation('<unknown>', -1)

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
          self.mem.SetVar(ast.LhsName(env_pair.name), val,
                          (var_flags_e.Exported,), scope_e.TempEnv)

        # NOTE: This might never return!  In the case of fork_external=False.
        status = self._RunSimpleCommand(argv, fork_external)
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
      flags = word_compile.ParseAssignFlags(node.flags)

      if node.keyword == Id.Assign_Local:
        lookup_mode = scope_e.LocalOnly
      # typeset and declare are synonyms?  I see typeset -a a=() the most.
      elif node.keyword in (Id.Assign_Declare, Id.Assign_Typeset):
        # declare is like local, except it can also be used outside functions?
        lookup_mode = scope_e.LocalOnly
        # TODO: Respect flags.  -r and -x matter, but -a and -A might be
        # implicit in the RHS?
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
          old_val, lval = expr_eval.EvalLhs(pair.lhs, self.arith_ev, self.mem,
                                            self.exec_opts)
          sig = (old_val.tag, val.tag)
          if sig == (value_e.Undef, value_e.Str):
            pass  # val is RHS
          elif sig == (value_e.Undef, value_e.StrArray):
            pass  # val is RHS
          elif sig == (value_e.Str, value_e.Str):
            val = runtime.Str(old_val.s + val.s)
          elif sig == (value_e.Str, value_e.StrArray):
            e_die("Can't append array to string")
          elif sig == (value_e.StrArray, value_e.Str):
            e_die("Can't append string to array")
          elif sig == (value_e.StrArray, value_e.StrArray):
            val = runtime.StrArray(old_val.strs + val.strs)

        else:  # plain assignment
          spid = pair.spids[0]  # Source location for tracing
          lval = self._EvalLhs(pair.lhs, spid)

          # RHS can be a string or array.
          if pair.rhs:
            val = self.word_ev.EvalRhsWord(pair.rhs)
            assert isinstance(val, runtime.value), val
          else:
            # e.g. 'readonly x' or 'local x'
            val = None  # only changing flags

        # NOTE: In bash and mksh, declare -a myarray makes an empty cell with
        # Undef value, but the 'array' attribute.

        self.mem.SetVar(lval, val, flags, lookup_mode)

        # Assignment always appears to have a spid.
        if node.spids:
          self._SetSourceLocation(node.spids[0])
        else:
          # TODO: when does this happen?  Warn.
          #log('Warning: assignment has no location information: %s', node)
          self.mem.SetSourceLocation('<unknown>', -1)
        self.tracer.OnAssignment(lval, val, flags, lookup_mode)

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

    elif node.tag in (command_e.While, command_e.Until):
      # TODO: Compile this out?
      if node.tag == command_e.While:
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
      self.arith_ev.Eval(node.init)

      self.loop_level += 1
      try:
        while True:
          b = self.arith_ev.Eval(node.cond)
          if not b:
            break

          try:
            status = self._Execute(node.body)
          except _ControlFlow as e:
            if e.IsBreak():
              status = 0
              break
            elif e.IsContinue():
              status = 0
            else:  # return needs to pop up more
              raise

          self.arith_ev.Eval(node.update)

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
      print('real\t%.3f' % real, file=sys.stderr)
      print('user\t%.3f' % user, file=sys.stderr)
      print('sys\t%.3f' % sys_, file=sys.stderr)

    else:
      raise NotImplementedError(node.__class__.__name__)

    return status, check_errexit

  def _Execute(self, node, fork_external=True):
    """Apply redirects, call _Dispatch(), and performs the errexit check.

    Args:
      node: ast.command
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

  def ExecuteAndCatch(self, node, fork_external=True):
    """Used directly by the interactive loop."""
    is_control_flow = False
    try:
      status = self._Execute(node, fork_external=fork_external)
    except _ControlFlow as e:
      # Return at top level is OK, unlike in bash.
      if e.IsReturn() or e.IsExit():
        is_control_flow = True
        status = e.StatusCode()
      else:
        raise  # Invalid
    except util.FatalRuntimeError as e:
      ui.PrettyPrintError(e, self.arena)
      print('osh failed: %s' % e.UserErrorString(), file=sys.stderr)
      status = e.exit_status if e.exit_status is not None else 1
      # TODO: dump self.mem if requested.  Maybe speify with OIL_DUMP_PREFIX.

    # Other exceptions: SystemExit for sys.exit()
    return status, is_control_flow

  def Execute(self, node, fork_external=True):
    """Execute a subprogram, handling _ControlFlow and fatal exceptions.

    This is just like ExecuteAndCatch, but we don't return is_control_flow.

    Callers:
    - SubProgramThunk for pipelines, subshell, command sub, process sub
    - .oilrc
    - _TrapThunk
    - Interactive loop
    - main program

    Most other clients call _Execute():
    - _Source() for source builtin
    - _Eval() for eval builtin
    - RunFunc() for function call

    Args:
      node: LST subtree
      fork_external: whether external commands require forking

    Returns:
      status: numeric exit code
    """
    # Ignore is_control_flow
    status, _ = self.ExecuteAndCatch(node, fork_external=fork_external)
    return status

  def ExecuteAndRunExitTrap(self, node):
    """For the top level program, called by bin/oil.py."""
    status = self.Execute(node)
    # NOTE: 'exit 1' is ControlFlow and gets here, but subshell/commandsub
    # don't because they call sys.exit().

    # NOTE: --runtime-mem-dump runs in a similar place.

    #log('-- EXIT pid %d', os.getpid())
    #import traceback
    #traceback.print_stack()

    # NOTE: The trap handler itself can call exit!
    handler = self.traps.get('EXIT')
    if handler:
      self.Execute(handler.node)

    return status

  def RunCommandSub(self, node):
    p = self._MakeProcess(node,
                          disable_errexit=not self.exec_opts.strict_errexit)

    r, w = os.pipe()
    p.AddStateChange(process.StdoutToPipe(r, w))
    pid = p.Start()
    #log('Command sub started %d', pid)
    self.waiter.Register(pid, p.WhenDone)

    chunks = []
    os.close(w)  # not going to write
    while True:
      byte_str = os.read(r, 4096)
      if not byte_str:
        break
      chunks.append(byte_str)
    os.close(r)

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

    r, w = os.pipe()

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
      os.close(w)
    elif op_id == Id.Left_ProcSubOut:
      os.close(r)
    else:
      raise AssertionError

    #log('I am %d', os.getpid())
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

    # TODO: Generalize process sub?
    #
    # - Make it work first, bare minimum.
    # - Then Make something like Pipeline()?
    #   - you add all the argument processes
    #   - then you add the main processes, with those as args
    #   - then p.Wait()
    #     - get status for all of them?
    #
    # Problem is that you don't see this until word_eval?
    # You can scan a simple command for these though.

    # TODO:
    # - Do we need to somehow register a waiter?  After SimpleCommand,
    #   argv and redirect words need to wait?
    # - what about for loops?  case?  ControlFlow?  temp binding,
    #   assignments, etc. They all have words
    #   - disallow those?
    # I guess you need it at the end of every command sub loop?
    # But you want to detect statically if you need to wait?
    # Maybe just have a dirty flag?  needs_wait
      # - Make a pipe
      # - Start another process connected to the write end of the pipe.
      # - Return [/dev/fd/FD] as the read end of the pipe.

  def RunFunc(self, func_node, argv):
    """Used by completion engine."""
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

    self.mem.PushCall(func_node.name, argv[1:])

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
    finally:
      self.mem.PopCall()
      if def_redirects:
        self.fd_state.Pop()

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
  def __init__(self, exec_opts, mem, word_ev):
    """
    Args:
      exec_opts: For xtrace setting
      mem: for retrieving PS4
      word_ev: for evaluating PS4
    """
    self.exec_opts = exec_opts
    self.mem = mem
    self.word_ev = word_ev

    self.arena = alloc.PluginArena('<$PS4>')
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

    try:
      ps4_word = self.parse_cache[ps4]
    except KeyError:
      # We have to parse this at runtime.  PS4 should usually remain constant.
      w_parser = parse_lib.MakeWordParserForPlugin(ps4, self.arena)

      # NOTE: Reading PS4 is just like reading a here doc line.  "\n" is
      # allowed too.  The OUTER mode would stop at spaces, and ReadWord
      # doesn't allow lex_mode_e.DQ.
      ps4_word = w_parser.ReadHereDocBody()

      if not ps4_word:
        error_str = '<ERROR: cannot parse PS4>'
        t = ast.token(Id.Lit_Chars, error_str, const.NO_INTEGER)
        ps4_word = ast.CompoundWord([ast.LiteralPart(t)])
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
    cmd = ' '.join(_PrettyString(a) for a in argv)
    print('%s%s%s' % (first_char, prefix, cmd), file=sys.stderr)

  def OnAssignment(self, lval, val, flags, lookup_mode):
    # NOTE: I think tracing should be on by default?  For post-mortem viewing.
    if not self.exec_opts.xtrace:
      return

    # Now we have to get the prefix
    first_char, prefix = self._EvalPS4()
    print('%s%s%s = %s' % (first_char, prefix, lval, val), file=sys.stderr)

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


# Copied from asdl/format.py.  We're not using it directly because that is
# debug output, and this is real input.
# TODO: Is this slow?

# NOTE: bash prints \' for single quote, repr() prints "'".  Gah.  This is also
# used for printf %q and ${var@q} (bash 4.4).

import re
_PLAIN_RE = re.compile(r'^[a-zA-Z0-9\-_./]+$')

def _PrettyString(s):
  if '\n' in s:
    #return json.dumps(s)  # account for the fact that $ matches the newline
    return repr(s)
  if _PLAIN_RE.match(s):
    return s
  else:
    #return json.dumps(s)
    return repr(s)
