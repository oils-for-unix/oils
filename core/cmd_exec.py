#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
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
import stat
import sys

from core.cmd_node import ENode, ListNode, RedirectType

from core import util
from core.util import log

from core import arith_eval
from core import bool_eval
from core import word_eval

from core import completion
from core.builtin import EBuiltin
from core.process import (
    FdState, Pipeline, Process,
    HereDocRedirect, DescriptorRedirect, FilenameRedirect,
    FuncThunk, ExternalThunk, SubProgramThunk, BuiltinThunk)
from core.word_node import EAssignScope
from core.value import Value


class ExecOpts(object):

  def __init__(self):
    # TODO: Set from flags
    self.nounset = False
    self.errexit = False
    self.pipefail = False
    self.noglob = False  # -f
    self.bash_array = True


# Does there need to be a Mem() for Make?  Lazily evaluated functions?

class Mem(object):
  """Mem is better than "Env" -- Env implies OS stuff."""

  def __init__(self, argv0, argv):
    self.top = {}  # string -> (flags, Value)
    self.var_stack = [self.top]
    self.argv0 = argv
    self.argv_stack = [argv]  # TODO: Initialize to shell arg!
    self.last_status = 0  # Mutable public variable

  def Push(self, argv):
    self.top = {}
    self.var_stack.append(self.top)
    self.argv_stack.append(argv)

  def Pop(self):
    self.var_stack.pop()
    self.argv_stack.pop()

  def GetArgv(self):
    """For $* and $@."""
    return self.argv_stack[-1]  # top of stack

  def SetArgv(self, argv):
    """For set -- 1 2 3."""
    #print('ARGV', argv)
    # from set -- 1 2 3
    self.argv_stack[-1] = argv

  def SetGlobalArray(self, name, a):
    """Helper for completion."""
    assert isinstance(a, list)
    val = Value.FromArray(a)
    pairs = [(name, val)]
    self.SetGlobal(pairs, 0)

  def SetGlobalString(self, name, s):
    """Helper for completion."""
    assert isinstance(s, str)
    val = Value.FromString(s)
    pairs = [(name, val)]
    self.SetGlobal(pairs, 0)

  def GetGlobal(self, name):
    """Helper for completion."""
    g = self.var_stack[0]  # global scope
    #print('!!GetGlobal', self.var_stack)
    if name in g:
      _, value = g[name]
      return True, value
    return False, None

  def Get(self, name):
    for i in range(len(self.var_stack)-1, -1, -1):
      scope = self.var_stack[i]
      if name in scope:
        # Don't need to use flags
        _, value = scope[name]
        return True, value

    # Fall back on environment
    v = os.getenv(name)
    if v is not None:
      return True, Value.FromString(v)

    return False, None

  def SetGlobal(self, pairs, flags):
    """For completion."""
    g = self.var_stack[0]  # global scope
    for name, value in pairs:
      assert isinstance(value, Value), value
      g[name] = flags, value

  def SetLocal(self, pairs, flags):
    # TODO: respect flags
    # TRACE: hm maybe.  It's for debugging, but seems exotic.

    # types: indexed, associative, integer?  Not sure if any of these are
    # valuable.  Integer could be useful for type checking, but this is a
    # DYNAMIC flag.

    # - If the value is readonly, don't set it.
    # - If the value is marked 'export', call setenv()

    # - Never change types?  yeah I think that's a good idea, at least for oil
    # (not sh, for compatibility).  set -o strict-types or something.  That
    # means arrays have to be initialized with let arr = [], which is fine.

    # This helps with stuff like IFS.  It starts off as a string, and assigning
    # it to a list is en error.  I guess you will have to turn this no for
    # bash?
    for name, value in pairs:
      assert isinstance(value, Value), value
      self.top[name] = flags, value

  # Are special vars here?  # like $? and $0 ?
  # IFS, PWD, etc.

  def GetTraceback(self, token):
    # TODO: When you Push(), add a function pointer.  And then walk
    # self.argv_stack here.
    # We also need a token number.
    pass


class Executor(object):
  """Executes the program by tree-walking.

  It also does some double-dispatch by passing itself into Eval() for
  CommandWord/WordPart.
  """
  def __init__(self, mem, builtins, funcs, comp_lookup, exec_opts,
      make_parser):
    """
    Args:
      mem: Mem instance for storing variables
      builtins: builtin metadata/implementation
      funcs: registry of functions (these names are completed)
      comp_lookup: completion pattern/action
      make_parser: Callback for creating a new command parser (eval and source)
    """
    self.mem = mem
    self.builtins = builtins
    # function space is different than var space.  Not hierarchical.
    self.funcs = funcs
    # Completion hooks, set by 'complete' builtin.
    self.comp_lookup = comp_lookup
    # This is for shopt and set -o.  They are initialized by flags.
    self.exec_opts = exec_opts
    self.make_parser = make_parser

    self.ev = word_eval.NormalEvaluator(mem, exec_opts, self)

    self.mem.last_status = 0  # For $?

    self.traps = {}
    self.fd_state = FdState()

    # TODO: Pass these in from main()
    self.aliases = {}  # alias name -> string
    self.targets = []  # make syntax enters stuff here -- Target()
                       # metaprogramming or regular target syntax
                       # Whether argv[0] is make determines if it is executed

    # sleep 5 & puts a (PID, job#) entry here.  And then "jobs" displays it.
    self.jobs = {}

    # for pushd, popd, dirs (though these are all bash-specific)
    self.dir_stack = []

    self.traceback = None
    self.traceback_msg = ''
    self.error_stack = []

  def Error(self):
    return self.error_stack

  def _AddErrorContext(self, msg, *args):
    if msg:
      msg = msg % args
    self.error_stack.append(msg)

  def _SetException(self, traceback, msg):
    self.traceback = traceback
    self.traceback_msg = msg

  def _Read(self, argv):
    names = argv[1:]
    line = sys.stdin.readline()
    # TODO: split line and do that logic
    val = Value.FromString(line.strip())
    pairs = [(names[0], val)]
    self.mem.SetLocal(pairs, 0)  # read always uses local variables?
    return 0

  def _Echo(self, argv):
    argv = argv[1:]
    for a in argv[:-1]:
      sys.stdout.write(a)
      sys.stdout.write(' ')  # arg separator
    if argv:
      sys.stdout.write(argv[-1])
    sys.stdout.write('\n')
    sys.stdout.flush()
    return 0

  def _Set(self, argv):
    # TODO:
    # - mutate settings in self.exec_opts
    #   - parse -o and +o, -e and +e, etc.
    # - change self.mem perhaps (set -- 1 2 3)

    # Replace the top of the stack
    if len(argv) >= 2 and argv[1] == '--':
      self.mem.SetArgv(argv[2:])
    else:
      try:
        flag = argv[1]
        name = argv[2]
      except IndexError:
        raise NotImplementedError(argv)

      if flag != '-o':
        raise NotImplementedError()

      if name == 'errexit':
        self.exec_opts.errexit = True
      elif name == 'nounset':
        self.exec_opts.nounset = True
      elif name == 'pipefail':
        self.exec_opts.pipefail = True
      else:
        raise NotImplementedError(name)
    return 0

  def _Unset(self, argv):
    # mutate self.mem
    # NOTE: sh has DYNAMIC SCOPE, so you need tests for that here.
    raise NotImplementedError

  def _Shift(self, argv):
    # Mutates self.mem
    raise NotImplementedError

  def _Trap(self, argv):
    # TODO: register trap

    # Example:
    # trap -- 'echo "hi  there" | wc ' SIGINT
    #
    # Then hit Ctrl-C.
    #
    # Yeah you need the EvalHelper.  traps is a list of signals to parsed
    # NODES.

    log(self.traps)
    return 0

  def _Complete(self, argv):
    # TODO: Parse flags?  How?  
    # opts = self.builtins.Parse(EBuiltin.COMPLETE, argv)

    command = argv[1]  # e.g. 'grep'
    func_name = argv[2]

    # NOTE: bash doesn't actually check the name until completion time, but
    # obviously it's better to check here.
    func = self.funcs.get(func_name)
    if func is None:
      print('Function %r not found' % func_name)
      return 1

    chain = completion.ShellFuncAction(self, func)
    self.comp_lookup.RegisterName(command, chain)
    # TODO: Some feedback would be nice?
    return 0

  def _EvalHelper(self, code_str):
    c_parser = self.make_parser(code_str)
    node = c_parser.ParseFile()
    # NOTE: We could model a parse error as an exception, like Python, so we
    # get a traceback.  (This won't be applicable for a static module system.)
    if not node:
      print('Error parsing code %r' % code_str)
      return 1
    status, cflow = self.Execute(node)
    return status

  def _Eval(self, argv):
    # TODO: in oil, eval shouldn't take multiple args.  For clarity 'eval ls
    # foo' will say "extra arg".
    code_str = argv[1]
    return self._EvalHelper(code_str)

  def _Source(self, argv):
    with open(argv[1]) as f:
      code_str = f.read()
    return self._EvalHelper(code_str)

  def _Exec(self, argv):
    # Either execute command with redirects, or apply redirects in this shell.
    # NOTE: Redirects were processed earlier.
    argv = argv[1:]
    if argv:
      thunk = ExternalThunk(argv)
      thunk.RunInParent() # never returns
    else:
      return 0

  def RunBuiltin(self, builtin_id, argv):
    cflow = EBuiltin.NONE  # default value
    restore_fd_state = True

    # TODO: Just test Type() == COMMAND word, and then if it's a command word,
    # type IsBuiltin().  And then builtins are NOT tokens!  Keywords might be
    # tokens, but builtins aren't.

    # TODO: figure out a quicker dispatch mechanism.  Just make a table of
    # builtins I guess.
    if builtin_id == EBuiltin.READ:
      status = self._Read(argv)

    elif builtin_id == EBuiltin.ECHO:
      status = self._Echo(argv)

    elif builtin_id == EBuiltin.EXIT:
      try:
        code = int(argv[1])
      except IndexError:
        pass
      except ValueError as e:
        print("Invalid argument %r" % argv[1], file=sys.stderr)
        code = 1  # Runtime Error
      # TODO: Should this be turned into our own SystemExit exception?
      sys.exit(code)

    elif builtin_id == EBuiltin.BREAK:
      status = 0
      cflow = EBuiltin.BREAK

    elif builtin_id == EBuiltin.CONTINUE:
      status = 0
      cflow = EBuiltin.CONTINUE

    elif builtin_id == EBuiltin.RETURN:
      # TODO: Hook up the rest of this!  Need to know when you're in a function
      # body.
      status = 0
      cflow = EBuiltin.RETURN

    elif builtin_id in (EBuiltin.SOURCE, EBuiltin.DOT):
      status = self._Source(argv)

    elif builtin_id == EBuiltin.TRAP:
      status = self._Trap(argv)

    elif builtin_id == EBuiltin.EVAL:
      status = self._Eval(argv)

    elif builtin_id == EBuiltin.EXEC:
      status = self._Exec(argv)  # may never return
      restore_fd_state = False

    elif builtin_id == EBuiltin.SET:
      status = self._Set(argv)

    elif builtin_id == EBuiltin.COMPLETE:
      status = self._Complete(argv)

    elif builtin_id == EBuiltin.COMPGEN:
      status = self._CompGen(argv)

    elif builtin_id == EBuiltin.DEBUG_LINE:
      status = self.builtins.DebugLine(argv)

    else:
      raise AssertionError('Unhandled builtin: %d' % builtin_id)

    return status, cflow

  def RunFunc(self, func_node, argv):
    """Called by FuncThunk."""
    func_body = func_node.children[0]
    # TODO: Call func with $@, $1, etc.

    self.mem.Push(argv[1:])

    # Redirects still valid for functions.
    # Here doc causes a pipe and Process(SubProgramThunk).
    status, cflow = self.Execute(func_body)
    self.mem.Pop()
    return status, cflow

  def _GetThunkForSimpleCommand(self, argv, more_env):
    """
    Given a node, resolve the first command word, and return a thunk.  The
    thunk may be run in either the parent shell process or a child process.

    Args:
      argv: evaluated arguments
      more_env: evaluated environment

    Returns:
      is_external: If the node MUST be run in an external process.
      thunk: thunk to run

      True, ExternalThunk() instance, or 
      False, argv if the thing to run isn't representable by an external
        command.
        argv can be None too.

    For deciding whether we need a subshell.
    """
    assert argv, "Need at least one arugment"

    # TODO: respect the special builtin order too

    builtin_id = self.builtins.Resolve(argv[0])
    if builtin_id != EBuiltin.NONE:
      return BuiltinThunk(self, builtin_id, argv)
    func_node = self.funcs.get(argv[0])
    if func_node is not None:
      return FuncThunk(self, func_node, argv)

    return ExternalThunk(argv, more_env)

  def _GetProcessForNode(self, node):
    """
    Assume we will run the node in another process.  Return a process.
    """
    if node.type == ENode.SIMPLE_COMMAND:
      argv = self.ev.EvalWords(node.words)
      if argv is None:
        err = self.ev.Error()
        raise AssertionError("Error evaluating words: %s" % err)
      more_env = self.ev.EvalEnv(node.more_env)
      if more_env is None:
        # TODO:
        raise AssertionError()
      thunk = self._GetThunkForSimpleCommand(argv, more_env)
    else:
      thunk = SubProgramThunk(self, node)

    redirects = self._EvalRedirects(node.redirects)
    p = Process(thunk, fd_state=self.fd_state, redirects=redirects)
    return p

  def _EvalRedirects(self, nodes):
    """Evaluate redirect nodes to concrete objects.

    We have to do this every time, because you could have something like:

    for i in a b c; do
      echo foo >$i
    done

    Does it makes sense to just have RedirectNode.Eval?  Nah I think the
    Redirect() abstraction in the executor is useful.  It has a lot of
    methods.
    """
    redirects = []
    for n in nodes:
      if n.type == RedirectType.FILENAME:
        # NOTE: no globbing.  You can write to a file called '*.py'.
        ok, val = self.ev.EvalCommandWord(n.filename)
        if not ok:
          return False
        is_str, filename = val.AsString()
        if not is_str:
          self._AddErrorContext("filename to redirect to should be a string")
          return False
        if not filename:
          self._AddErrorContext("filename can't be empty")
          return False

        redirects.append(FilenameRedirect(n.op, n.fd, filename))

      elif n.type == RedirectType.DESCRIPTOR:  # e.g. 1>&2
        ok, val = self.ev.EvalCommandWord(n.target_fd)
        if not ok:
          return False
        is_str, t = val.AsString()
        if not is_str:
          self._AddErrorContext(
              "descriptor to redirect to should be an integer, not list")
          return False
        if not t:
          self._AddErrorContext("descriptor can't be empty")
          return False
        try:
          target_fd = int(t)
        except ValueError:
          self._AddErrorContext(
              "descriptor to redirect to should be an integer, not string")
          return False
        redirects.append(DescriptorRedirect(n.op, n.fd, target_fd))

      elif n.type == RedirectType.HERE_DOC:
        ok, val = self.ev.EvalCommandWord(n.body_word)
        if not ok:
          return False
        is_str, body = val.AsString()
        assert is_str, val  # here doc body can only be parsed as a string!
        redirects.append(HereDocRedirect(n.op, n.fd, body))

      else:
        raise AssertionError
    return redirects

  def _RunPipeline(self, node):
    # TODO: Also check for "echo" and "read".  Turn them into HereDocRedirect()
    # and p.CaptureOutput()

    # NOTE: First or last one can use the "main" shell thread.  Doesn't have to
    # run in subshell.  Although I guess it's simpler if it always does.

    pi = Pipeline()

    for child in node.children:
      p = self._GetProcessForNode(child)
      pi.Add(p)

    #print(pi)

    # TODO: Set PipeStatus() in self.mem
    pipe_status = pi.Run()

    if self.exec_opts.pipefail:
      # If any process failed, the status of the entire pipeline is 1.
      status = 0
      for st in pipe_status:
        if st != 0:
          status = 1
    else:
      status = pipe_status[-1]  # last one determines status

    return status, EBuiltin.NONE  # no control flow

  def ExecuteTop(self, node):
    """
    Execute from the top level.  

    TODO: This is wrong; we can't only check here.
    """
    status, cflow = self.Execute(node)
    if cflow != EBuiltin.NONE:
      print('break / continue can only be used inside loop')
      status = 129  # TODO: Fix this.  Use correct macros
    return status, cflow

  def Execute(self, node):
    """
    Args:
      node: of type AstNode
    """
    redirects = self._EvalRedirects(node.redirects)

    # TODO: Change this to its own enum?
    # or add EBuiltin.THROW     _throw?  For testing.
    # Is this different han exit?  exit should really be throw.  Because we
    # want to be able to unwind the stack, show stats, etc.  Exiting in the
    # middle is bad.
    # exit and _throw could be the same, except _throw takes an error message,
    # and exits 1, and shows traceback.
    cflow = EBuiltin.NONE

    # TODO: Only eval argv[0] once.  It can have side effects!

    if node.type == ENode.SIMPLE_COMMAND:
      argv = self.ev.EvalWords(node.words)
      if argv is None:
        err = self.ev.Error()
        # TODO: Throw shell exception
        raise AssertionError('Error evaluating words: %s' % err)
      more_env = self.ev.EvalEnv(node.more_env)
      if more_env is None:
        print(self.error_stack)
        # TODO: throw exception
        raise AssertionError()
      thunk = self._GetThunkForSimpleCommand(argv, more_env)

      # Don't waste a process if we'd launch one anyway.
      if thunk.IsExternal():
        p = Process(thunk, fd_state=self.fd_state, redirects=redirects)
        status = p.Run()

        if os.WIFEXITED(status):
          status = os.WEXITSTATUS(status)
          #print('exited with code', code)
        else:
          sig = os.WTERMSIG(status)
          #print('exited with signal', sig)
          # TODO: Is this right?
          status = 0

      else:  # Internal
        for r in redirects:
          r.ApplyInParent(self.fd_state)

        status, cflow = thunk.RunInParent()
        restore_fd_state = thunk.ShouldRestoreFdState()

        # Special case for exec 1>&2 (with no args): we permanently change the
        # fd state.  BUT we don't want to restore later.
        #
        # TODO: Instead of this, maybe r.ApplyPermaent(self.fd_state)?
        if restore_fd_state:
          self.fd_state.RestoreAll()
        else:
          self.fd_state.ForgetAll()

    elif node.type == ENode.PIPELINE:
      status, cflow = self._RunPipeline(node)

    elif node.type == ENode.SUBSHELL:
      # This makes sure we don't waste a process if we'd launch one anyway.
      p = self._GetProcessForNode(node.children[0])
      status = p.Run()

    elif node.type == ENode.DBRACKET:
      ok, b = bool_eval.BEval(node.bnode, self.ev)
      status = 0 if b else 1
      # TODO: if not OK, then turn it into an exception

    elif node.type == ENode.DPAREN:
      i = arith_eval.ArithEval(node.anode, self.ev)
      # Negate the value: non-zero in arithmetic is true, which is zero in
      # shell land
      status = 0 if i != 0 else 1
      # TODO: if not OK, then turn it into an exception

    elif node.type == ENode.ASSIGN:
      # TODO: Respect flags: readonly, export, sametype, etc.
      # Just pass the Value
      pairs = []
      for name, word in node.bindings:
        # NOTE: do_glob=False, because foo=*.a makes foo equal to '*.a',
        # literally.
        ok, val = self.ev.EvalCommandWord(word)
        if not ok:
          return None
        pairs.append((name, val))

      if node.scope == EAssignScope.LOCAL:
        self.mem.SetLocal(pairs, node.flags)
      elif node.scope == EAssignScope.GLOBAL:
        self.mem.SetGlobal(pairs, node.flags)
      else:
        raise AssertionError(node.scope)

      # TODO: This should be eval of RHS, unlike bash!
      status = 0

    elif node.type == ENode.LIST:
      status = 0  # for empty list
      for child in node.children:
        status, cflow = self.Execute(child)  # last status wins
        if cflow in (EBuiltin.BREAK, EBuiltin.CONTINUE):
          break

    elif node.type == ENode.AND_OR:
      #print(node.children)
      left, right = node.children
      status, cflow = self.Execute(left)

      if node.op == Id.Op_OrIf:
        if status != 0:
          status = self.Execute(right)
      elif node.op == Id.Op_AndIf:
        if status == 0:
          status = self.Execute(right)
      else:
        raise AssertionError

    elif node.type == ENode.WHILE:
      cond, action = node.children

      while True:
        status, _ = self.Execute(cond)
        if status != 0:
          break
        status, cflow = self.Execute(action)  # last one wins
        if cflow == EBuiltin.BREAK:
          cflow = EBuiltin.NONE  # reset since we respected it
          break
        if cflow == EBuiltin.CONTINUE:
          cflow = EBuiltin.NONE  # reset since we respected it

    elif node.type == ENode.FOR:
      iter_name = node.iter_name
      if node.do_arg_iter:
        iter_list = self.mem.GetArgv()
      else:
        iter_list = self.ev.EvalWords(node.iter_words)
        # We need word splitting and so forth
        # NOTE: This expands globs too.  TODO: We should pass in a Globber()
        # object.
      status = 0  # in case we don't loop
      cflow = EBuiltin.NONE
      for x in iter_list:
        flags = 0
        pairs = [(iter_name, Value.FromString(x))]
        self.mem.SetLocal(pairs, flags)

        assert len(node.children) == 1
        status, cflow = self.Execute(node.children[0])

        if cflow == EBuiltin.BREAK:
          cflow = EBuiltin.NONE  # reset since we respected it
          break
        if cflow == EBuiltin.CONTINUE:
          cflow = EBuiltin.NONE  # reset since we respected it

    elif node.type == ENode.FUNCTION_DEF:
      self.funcs[node.name] = node
      status = 0

    elif node.type == ENode.IF:
      i = 0
      while i < len(node.children):
        cond = node.children[i]
        body = node.children[i+1]
        status, _ = self.Execute(cond)
        if status == 0:
          status, _ = self.Execute(body)
          break
        i += 2

    elif node.type == ENode.ELSE_TRUE:
      status = 0  # make it true

    elif node.type == ENode.CASE:
      raise NotImplementedError

    else:
      raise AssertionError(node.type)

    if self.exec_opts.errexit:
      if status != 0:
        # TODO: token should be set to what?  Is it node.begin_word and
        # node.end_word?
        token = None
        tb = self.mem.GetTraceback(token)
        self._SetException(tb,
            "Command %s exited with code %d" % ('TODO', status))
        # cflow should be EXCEPT

    # TODO: Is this the right place to put it?  Does it need a stack for
    # function calls?
    self.mem.last_status = status
    return status, cflow
