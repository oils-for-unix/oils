#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
"""
cmd_exec.py

System calls we care about:
  fork exec
  dup2 pipe
  open read write close

  Maybe later: process state stuff, like setpgrp and so forth

TODO:
  - test file descriptor state in the CHILD.  Assert that we don't have extra
    stuff.

  - extra: process sub: <() .  Does this create a temporary named pipe or
    something?
    When I strace bash, I see calls to open("/dev/fd/63")
  - extra: coprocess.  This is covered in APUE.
    - what are coprocesses used for?  Awk has this too.
    - http://wiki.bash-hackers.org/syntax/keywords/coproc
    - http://unix.stackexchange.com/questions/86270/how-do-you-use-the-command-coproc-in-bash
      -- good history.  Lots of good info about buffering.
      -- Yeah I think leave this for later.
  - extra: async -- this is interleaved with the interpreter

strace bash -c 'diff -u <(echo one) <(echo two)'

open("/dev/fd/63", O_RDONLY)            = 3
open("/dev/fd/62", O_RDONLY)            = 4
read(3, "one\n", 4096)                  = 4
read(3, "", 4092)                       = 0
read(4, "two\n", 4096)                  = 4
read(4, "", 4092)                       = 0

OK then it passes them like this.  OK you fork diff with some fds.  Do all Unix
operating systems have this?

execve("/usr/bin/diff", ["diff", "-u", "/dev/fd/63", "/dev/fd/62"], [/* 68 vars */]) = 0

NOTE: you cannot STATICALLY know if a command is a builtin, because it depends
on $PATH at runtime.  So you can't automatically insert subshell nodes at
compile time I think.  It has to be done at runtime.  For oil, you can
statically resolve things.

Problems:

$ < Makefile cat | < NOTES.txt head

This just does head?  Last one wins.
"""

import os
import resource
import stat
import sys
import time

from core import args
from core import braces
from core import expr_eval
from core import word_eval
from core import ui
from core import util

from core import builtin
from core.id_kind import Id, RedirType, REDIR_TYPE, REDIR_DEFAULT_FD
from core import process
from core import runtime
from core import state

from osh import ast_ as ast

import libc  # for fnmatch

EBuiltin = builtin.EBuiltin

command_e = ast.command_e
redir_e = ast.redir_e
lhs_expr_e = ast.lhs_expr_e

value_e = runtime.value_e
scope = runtime.scope
var_flags = runtime.var_flags

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

  def IsBreak(self):
    return self.token.id == Id.ControlFlow_Break

  def IsContinue(self):
    return self.token.id == Id.ControlFlow_Continue

  def ReturnValue(self):
    assert self.IsReturn()
    return self.arg


class Executor(object):
  """Executes the program by tree-walking.

  It also does some double-dispatch by passing itself into Eval() for
  CompoundWord/WordPart.
  """
  def __init__(self, mem, status_lines, funcs, completion, comp_lookup,
               exec_opts, make_parser, arena):
    """
    Args:
      mem: Mem instance for storing variables
      status_lines: shared with completion.  TODO: Move this to the end.
      funcs: registry of functions (these names are completed)
      completion: completion module, if available
      comp_lookup: completion pattern/action
      make_parser: Callback for creating a new command parser (eval and source)
      arena: for printing error locations
    """
    self.mem = mem
    self.status_lines = status_lines  
    # function space is different than var space.  Not hierarchical.
    self.funcs = funcs
    self.completion = completion
    # Completion hooks, set by 'complete' builtin.
    self.comp_lookup = comp_lookup
    # This is for shopt and set -o.  They are initialized by flags.
    self.exec_opts = exec_opts
    self.make_parser = make_parser
    self.arena = arena

    self.ev = word_eval.NormalWordEvaluator(mem, exec_opts, self)
    self.arith_ev = expr_eval.ArithEvaluator(mem, exec_opts, self.ev)
    self.bool_ev = expr_eval.BoolEvaluator(mem, exec_opts, self.ev)

    self.traps = {}
    self.fd_state = process.FdState()
    self.dir_stack = []

    # TODO: Pass these in from main()
    self.aliases = {}  # alias name -> string
    self.targets = []  # make syntax enters stuff here -- Target()
                       # metaprogramming or regular target syntax
                       # Whether argv[0] is make determines if it is executed

    self.waiter = process.Waiter()
    # sleep 5 & puts a (PID, job#) entry here.  And then "jobs" displays it.
    self.job_state = process.JobState()

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

  def _EvalHelper(self, code_str):
    c_parser = self.make_parser(code_str)
    node = c_parser.ParseWholeFile()
    # NOTE: We could model a parse error as an exception, like Python, so we
    # get a traceback.  (This won't be applicable for a static module system.)
    if not node:
      print('Error parsing code %r' % code_str)
      return 1
    status = self._Execute(node)
    return status

  def _Eval(self, argv):
    # TODO: in oil, eval shouldn't take multiple args.  For clarity 'eval ls
    # foo' will say "extra arg".
    code_str = ' '.join(argv)
    return self._EvalHelper(code_str)

  def _Source(self, argv):
    # TODO: Use LineReader
    with open(argv[0]) as f:
      code_str = f.read()
    return self._EvalHelper(code_str)

  def _Exec(self, argv):
    # Either execute command with redirects, or apply redirects in this shell.
    # NOTE: Redirects were processed earlier.
    if argv:
      environ = self.mem.GetExported()
      process.ExecExternalProgram(argv, environ)  # never returns
    else:
      # TODO: self.fd_state.MakePermanent()
      return 0

  def _RunBuiltin(self, builtin_id, argv):
    restore_fd_state = True

    # NOTE: Builtins don't need to know their own name.
    argv = argv[1:]

    # TODO: figure out a quicker dispatch mechanism.  Just make a table of
    # builtins I guess.
    if builtin_id == EBuiltin.EXEC:
      status = self._Exec(argv)  # may never return
      # But if it returns, then we want to permanently apply the redirects
      # associated with it.
      self.fd_state.MakePermanent()

    elif builtin_id == EBuiltin.READ:
      status = builtin.Read(argv, self.mem)

    elif builtin_id == EBuiltin.ECHO:
      status = builtin.Echo(argv)

    elif builtin_id == EBuiltin.SHIFT:
      status = builtin.Shift(argv, self.mem)

    elif builtin_id == EBuiltin.CD:
      status = builtin._Cd(argv, self.mem)

    elif builtin_id == EBuiltin.SET:
      status = builtin.Set(argv, self.exec_opts, self.mem)

    elif builtin_id == EBuiltin.UNSET:
      status = builtin.Unset(argv, self.mem, self.funcs)

    elif builtin_id == EBuiltin.EXPORT:
      status = builtin.Export(argv, self.mem)

    elif builtin_id == EBuiltin.EXIT:
      status = builtin.Exit(argv)

    elif builtin_id == EBuiltin.WAIT:
      status = builtin.Wait(argv, self.waiter, self.job_state, self.mem)

    elif builtin_id == EBuiltin.JOBS:
      status = builtin.Jobs(argv, self.job_state)

    elif builtin_id == EBuiltin.PUSHD:
      status = builtin.Pushd(argv, self.dir_stack)

    elif builtin_id == EBuiltin.POPD:
      status = builtin.Popd(argv, self.dir_stack)

    elif builtin_id == EBuiltin.DIRS:
      status = builtin.Dirs(argv, self.dir_stack)

    elif builtin_id in (EBuiltin.SOURCE, EBuiltin.DOT):
      status = self._Source(argv)

    elif builtin_id == EBuiltin.TRAP:
      status = builtin.Trap(argv, self.traps)

    elif builtin_id == EBuiltin.UMASK:
      status = builtin.Umask(argv)

    elif builtin_id == EBuiltin.EVAL:
      status = self._Eval(argv)

    elif builtin_id == EBuiltin.COMPLETE:
      status = self._Complete(argv)

    elif builtin_id == EBuiltin.COMPGEN:
      status = self._CompGen(argv)

    elif builtin_id == EBuiltin.COLON:  # special builtin like 'true'
      status = 0

    elif builtin_id == EBuiltin.TRUE:
      status = 0

    elif builtin_id == EBuiltin.FALSE:
      status = 1

    elif builtin_id == EBuiltin.HELP:
      loader = util.GetResourceLoader()
      status = builtin.Help(argv, loader)

    elif builtin_id == EBuiltin.DEBUG_LINE:
      status = builtin.DebugLine(argv, self.status_lines)

    else:
      raise AssertionError('Unhandled builtin: %d' % builtin_id)

    assert isinstance(status, int)
    return status

  def _PushErrExit(self):
    self.exec_opts.errexit.Push()

  def _PopErrExit(self):
    self.exec_opts.errexit.Pop()

  def _CheckStatus(self, status, node, argv=None):
    if self.exec_opts.ErrExit() and status != 0:
      # TODO: Add context based on node type
      #if node.tag == command_e.SimpleCommand:
      #  e_die('%r command exited with status %d (%s)', argv[0], status,
      #        node.words[0])

      raise util.FatalRuntimeError(
          '%r command exited with status %d', node.__class__.__name__, status,
          status=status)

  def _EvalLhs(self, node):
    assert isinstance(node, ast.lhs_expr), node

    # NOTE: shares some logic with _EvalLhs in ArithEvaluator.  
    # TODO: Need to get the old value like _EvalLhs, for +=.  Maybe have a flag
    # that says whether you need it?

    if node.tag == lhs_expr_e.LhsName:  # a=x
      return runtime.LhsName(node.name)

    if node.tag == lhs_expr_e.LhsIndexedName:  # a[1+2]=x
      i = self.arith_ev.Eval(node.index)
      return runtime.LhsIndexedName(node.name, i)

    raise AssertionError(node.tag)

  def _EvalRedirect(self, n):
    fd = REDIR_DEFAULT_FD[n.op_id] if n.fd == -1 else n.fd
    if n.tag == redir_e.Redir:
      redir_type = REDIR_TYPE[n.op_id]

      if redir_type == RedirType.Path:
        # NOTE: no globbing.  You can write to a file called '*.py'.
        val = self.ev.EvalWordToString(n.arg_word)
        if val.tag != value_e.Str:
          util.warn("Redirect filename must be a string, got %s", val)
          return None
        filename = val.s
        if not filename:
          # Whether this is fatal depends on errexit.
          util.warn("Redirect filename can't be empty")
          return None

        return runtime.PathRedirect(n.op_id, fd, filename)

      elif redir_type == RedirType.Desc:  # e.g. 1>&2
        val = self.ev.EvalWordToString(n.arg_word)
        if val.tag != value_e.Str:
          util.warn("Redirect descriptor should be a string, got %s", val)
          return None
        t = val.s
        if not t:
          util.warn("Redirect descriptor can't be empty")
          return None
        try:
          target_fd = int(t)
        except ValueError:
          util.warn(
              "Redirect descriptor should look like an integer, got %s", val)
          return None

        return runtime.DescRedirect(n.op_id, fd, target_fd)

      elif redir_type == RedirType.Here:  # here word
        # TODO: decay should be controlled by an option
        val = self.ev.EvalWordToString(n.arg_word, decay=True)
        if val.tag != value_e.Str:
          util.warn("Here word body should be a string, got %s", val)
          return None
        return runtime.HereRedirect(fd, val.s)
      else:
        raise AssertionError('Unknown redirect op')

    elif n.tag == redir_e.HereDoc:
      # TODO: decay shoudl be controlled by an option
      val = self.ev.EvalWordToString(n.body, decay=True)
      if val.tag != value_e.Str:
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
        # Ignore it for now.  TODO: We might want to skip JUST the command.
        # Give it status 1, and then errexit will take care of it.
        continue
      redirects.append(r)
    return redirects

  def _EvalEnv(self, node_env, out_env):
    """Evaluate environment variable bindings.

    Args:
      node_env: list of ast.env_pair
      out_env: mutated.
    """
    # NOTE: Env evaluation is done in new scope so it doesn't persist.  It also
    # pushes argv.  Don't need that?
    self.mem.PushTemp()
    for env_pair in node_env:
      name = env_pair.name
      rhs = env_pair.val

      # Could pass extra bindings like out_env here?  But PushTemp should work?
      val = self.ev.EvalWordToString(rhs)

      # Set each var so the next one can reference it.  Example:
      # FOO=1 BAR=$FOO ls /
      self.mem.SetVar(ast.LhsName(name), val, (), scope.LocalOnly)

      out_env[name] = val.s
    self.mem.PopTemp()

  def _MakeProcess(self, node, job_state=None):
    """
    Assume we will run the node in another process.  Return a process.
    """
    if node.tag == command_e.ControlFlow:
      # Pipeline or subshells with control flow are invalid, e.g.:
      # - break | less
      # - continue | less
      # - ( return )
      # NOTE: This could be done at parse time too.
      e_die('Invalid control flow %r in pipeline / subshell / background', node.token.val,
            token=node.token)

    thunk = process.SubProgramThunk(self, node)
    p = process.Process(thunk, job_state=job_state)
    return p

  def _RunSimpleCommand(self, argv, environ, fork_external):
    # This happens when you write "$@" but have no arguments.
    if not argv:
      return 0  # status 0, or skip it?

    # TODO: respect the special builtin order too
    arg0 = argv[0]

    builtin_id = builtin.ResolveSpecial(arg0)
    if builtin_id != EBuiltin.NONE:
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
      status = self.RunFunc(func_node, argv)
      return status

    builtin_id = builtin.Resolve(arg0)
    if builtin_id != EBuiltin.NONE:
      try:
        status = self._RunBuiltin(builtin_id, argv)
      except args.UsageError as e:
        # TODO: Make this message more consistent?
        util.usage(str(e))
        status = 2  # consistent error code for usage error
      return status

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

  # TODO: This causes "bad descriptor errors"
  #XFILE = open('/tmp/xtrace.log', 'w')
  # typically fd 4, not sure why it interferes?
  #log('*** XFILE %d', XFILE.fileno())

  def _Dispatch(self, node, fork_external):
    if node.tag == command_e.SimpleCommand:
      # PROBLEM: We want to log argv in 'xtrace' mode, but we may have already
      # redirected here, which screws up loggnig.  For example, 'echo hi
      # >/dev/null 2>&1'.  We want to evaluate argv and log it BEFORE applying
      # redirects.

      # Another problem:
      # - tracing can be called concurrently from multiple processes, leading
      # to overlap.  Maybe have a mode that creates a file per process.
      # xtrace-proc
      # - line numbers for every command would be very nice.  But then you have
      # to print the filename too.

      words = braces.BraceExpandWords(node.words)
      argv = self.ev.EvalWordSequence(words)

      environ = self.mem.GetExported()
      self._EvalEnv(node.more_env, environ)

      if self.exec_opts.xtrace:
        log('+ %s', argv)
        #print('+ %s' % argv, file=sys.stderr)
        #print('+ %s' % argv, file=self.XFILE)
        #os.write(2, '+ %s\n' % argv)

      status = self._RunSimpleCommand(argv, environ, fork_external)

      if self.exec_opts.xtrace:
        #log('+ %s -> %d', argv, status)
        pass

    elif node.tag == command_e.Sentence:
      if node.terminator.id == Id.Op_Semi:
        status = self._Execute(node.child)
      else:
        status = self._RunJobInBackground(node.child)

    elif node.tag == command_e.Pipeline:
      if node.stderr_indices:
        raise NotImplementedError('|&')

      if node.negated:
        self._PushErrExit()
        try:
          status = self._RunPipeline(node)
        finally:
          self._PopErrExit()

        # EARLY EXIT: skip _CheckStatus so we don't fail in either case.
        if status == 0:
          return 1
        else:
          return 0

      else:
        status = self._RunPipeline(node)

    elif node.tag == command_e.Subshell:
      # This makes sure we don't waste a process if we'd launch one anyway.
      p = self._MakeProcess(node.child)
      status = p.Run(self.waiter)

    elif node.tag == command_e.DBracket:
      result = self.bool_ev.Eval(node.expr)
      status = 0 if result else 1

    elif node.tag == command_e.DParen:
      i = self.arith_ev.Eval(node.child)
      status = 0 if i != 0 else 1

    elif node.tag == command_e.Assignment:
      pairs = []
      if node.keyword == Id.Assign_Local:
        lookup_mode = scope.LocalOnly
        flags = ()
      elif node.keyword == Id.Assign_Readonly:
        lookup_mode = scope.Dynamic
        flags = (var_flags.ReadOnly,)
      elif node.keyword == Id.Assign_None:
        lookup_mode = scope.Dynamic
        flags = ()
      else:
        # TODO: typeset, declare, etc.  Those are dynamic though.
        raise NotImplementedError(node.keyword)

      for pair in node.pairs:
        if pair.rhs:
          # RHS can be a string or array.
          val = self.ev.EvalWordToAny(pair.rhs)
          assert isinstance(val, runtime.value), val
        else:
          # 'local x' is equivalent to local x=""
          val = runtime.Str('')

        lval = self._EvalLhs(pair.lhs)
        # TODO: Respect readonly
        #log('ASSIGNING %s -> %s', lval, val)
        self.mem.SetVar(lval, val, flags, lookup_mode)

      # TODO: This should be eval of RHS, unlike bash!
      status = 0

    elif node.tag == command_e.ControlFlow:
      if node.arg_word:  # Evaluate the argument
        val = self.ev.EvalWordToString(node.arg_word)
        assert val.tag == value_e.Str
        arg = int(val.s)  # They all take integers
      else:
        arg = 0  # return 0, break 0 levels, etc.

      # NOTE: always raises so we don't set status.
      raise _ControlFlow(node.token, arg)

    # The only difference between these two is that CommandList has no
    # redirects.  We already took care of that above.
    elif node.tag in (command_e.CommandList, command_e.BraceGroup):
      status = self._ExecuteList(node.children)

    elif node.tag == command_e.AndOr:
      #print(node.children)
      left, right = node.children

      # This is everything except the last one.
      self._PushErrExit()
      try:
        status = self._Execute(left)
      finally:
        self._PopErrExit()

      if node.op_id == Id.Op_DPipe:
        if status != 0:
          status = self._Execute(right)
      elif node.op_id == Id.Op_DAmp:
        if status == 0:
          status = self._Execute(right)
      else:
        raise AssertionError

    elif node.tag in (command_e.While, command_e.Until):
      # TODO: Compile this out?
      if node.tag == command_e.While:
        _DonePredicate = lambda status: status != 0
      else:
        _DonePredicate = lambda status: status == 0

      status = 0
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

    elif node.tag == command_e.ForEach:
      iter_name = node.iter_name
      if node.do_arg_iter:
        iter_list = self.mem.GetArgv()
      else:
        words = braces.BraceExpandWords(node.iter_words)
        iter_list = self.ev.EvalWordSequence(words)
        # We need word splitting and so forth
        # NOTE: This expands globs too.  TODO: We should pass in a Globber()
        # object.
      status = 0  # in case we don't loop
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
            continue
          else:  # return needs to pop up more
            raise

    elif node.tag == command_e.ForExpr:
      raise NotImplementedError(node.tag)

    elif node.tag == command_e.DoGroup:
      status = self._ExecuteList(node.children)

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
      val = self.ev.EvalWordToString(node.to_match)
      to_match = val.s

      status = 0  # If there are no arms, it should be zero?
      done = False

      for arm in node.arms:
        for pat_word in arm.pat_list:
          # NOTE: Is it OK that we're evaluating these as we go?
          pat_val = self.ev.EvalWordToString(pat_word, do_fnmatch=True)
          #log('Matching word %r against pattern %r', to_match, pat_val.s)
          if libc.fnmatch(pat_val.s, to_match):
            status = self._ExecuteList(arm.action)
            done = True  # TODO: Parse ;;& and for fallthrough and such?
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
      raise AssertionError(node.tag)

    # NOTE: Bash says that 'set -e' checking is done after each 'pipeline'.
    # However, any bash construct can appear in a pipeline.  So it's easier
    # just to put it at the end, instead of execute.
    #
    # Possible exceptions:
    # - function def (however this always exits 0 anyway)
    # - assignment - its result should be the result of the RHS?
    #   - e.g. arith sub, command sub?  I don't want arith sub.
    # - ControlFlow: always raises, it has no status.

    self._CheckStatus(status, node)

    # TODO: Is this the right place to put it?  Does it need a stack for
    # function calls?
    self.mem.last_status = status

    return status

  def _Execute(self, node, fork_external=True):
    """
    Args:
      node: of type AstNode
      fork_external: if we get a SimpleCommand that is an external command,
        should we fork first?  This is disabled in the context of a pipeline
        process and a subshell.
    """
    # No redirects to evaluate.
    # NOTE: Function definitions have redirects, but we do NOT want to evaluate
    # redirects them yet!  They are evaluated on every invocation instead!
    if node.tag in (
        command_e.NoOp, command_e.Assignment, command_e.ControlFlow,
        command_e.Pipeline, command_e.AndOr, command_e.CommandList,
        command_e.Sentence, command_e.TimeBlock,
        command_e.FuncDef
        ):
      redirects = []
    else:
      redirects = self._EvalRedirects(node)

    if redirects is None:
      status = 1  # Redirect error causes bad status
      self._CheckStatus(status, node)
      self.mem.last_status = status  # TODO: This is somewhat duplicated
      return status
    assert isinstance(redirects, list), redirects

    if not self.fd_state.Push(redirects, self.waiter):
      # The whole command fails with status 1, e.g. bad file descriptor.
      return 1

    try:
      status = self._Dispatch(node, fork_external)
    finally:
      self.fd_state.Pop()

    return status

  def _ExecuteList(self, children):
    status = 0  # for empty list
    for child in children:
      status = self._Execute(child)  # last status wins
    return status

  def Execute(self, node, fork_external=True):
    """Execute a top level LST node."""
    # Use exceptions internally, but exit codes externally.
    try:
      status = self._Execute(node, fork_external=fork_external)
    except _ControlFlow as e:
      # TODO: pretty print error with e.token
      log('osh failed: Unexpected %r at top level' % e.token.val)
      status = 1
    except util.FatalRuntimeError as e:
      # TODO:
      ui.PrettyPrintError(e, self.arena, sys.stderr)
      print('osh failed: %s' % e.UserErrorString(), file=sys.stderr)
      status = e.exit_status if e.exit_status is not None else 1

    # TODO: Hook this up
    #print('break / continue can only be used inside loop')
    #status = 129  # TODO: Fix this.  Use correct macros
    return status

  def RunCommandSub(self, node):
    p = self._MakeProcess(node)

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

    # TODO: Add context
    if self.exec_opts.ErrExit() and status != 0:
      e_die('Command sub exited with status %d (%r)', status,
            node.__class__.__name__)

    return ''.join(chunks).rstrip('\n')

  def RunFunc(self, func_node, argv):
    """Used by completion engine."""
    # These are redirects at DEFINITION SITE.  You can also have redirects at
    # the CALLER.  For example:

    # f() { echo hi; } 1>&2
    # f 2>&1

    def_redirects = self._EvalRedirects(func_node)
    if not self.fd_state.Push(def_redirects, self.waiter):
      return 1  # error

    self.mem.Push(argv[1:])

    # Redirects still valid for functions.
    # Here doc causes a pipe and Process(SubProgramThunk).
    try:
      status = self._Execute(func_node.body)
    except _ControlFlow as e:
      if e.IsReturn():
        status = e.ReturnValue()
      else:
        # break/continue used in the wrong place
        e_die('Unexpected %r (in function call)', e.token.val, token=e.token)
    finally:
      self.mem.Pop()
      self.fd_state.Pop()

    return status
