#!/usr/bin/python
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

from core import braces
from core import expr_eval
from core import word_eval
from core import util

from core.builtin import EBuiltin
from core.id_kind import Id, RedirType, REDIR_TYPE
from core import process
from core import runtime

from osh import ast_ as ast

import libc  # for fnmatch

command_e = ast.command_e
part_value_e = runtime.part_value_e
value_e = runtime.value_e
log = util.log


class ExecOpts(object):

  def __init__(self):
    # TODO: Set from flags
    self.nounset = False
    self.errexit = False
    self.pipefail = False
    self.noglob = False  # -f
    self.bash_array = True


class Mem(object):
  """For storing variables.

  Mem is better than "Env" -- Env implies OS stuff.
  """

  def __init__(self, argv0, argv):
    self.top = {}  # string -> runtime.cell
    self.var_stack = [self.top]
    self.argv0 = argv0
    self.argv_stack = [argv]
    self.last_status = 0  # Mutable public variable

    self._InitDefaults()

  def _InitDefaults(self):
    # Default value; user may unset it.
    # $ echo -n "$IFS" | python -c 'import sys;print repr(sys.stdin.read())'
    # ' \t\n'
    self.SetGlobalString('IFS', ' \t\n')
    self.SetGlobalString('PWD', os.getcwd())

  #
  # Stack
  #

  def Push(self, argv):
    self.var_stack.append({})
    self.argv_stack.append(argv)

  def Pop(self):
    self.var_stack.pop()
    self.argv_stack.pop()

  def PushTemp(self):
    """For FOO=bar BAR=baz command."""
    self.var_stack.append({})

  def PopTemp(self):
    """For FOO=bar BAR=baz command."""
    self.var_stack.pop()

  def GetTraceback(self, token):
    """For runtime and parse time errors."""
    # TODO: When you Push(), add a function pointer.  And then walk
    # self.argv_stack here.
    # We also need a token number.
    pass

  #
  # Argv
  #

  def GetArgv0(self):
    """For $0."""
    return self.argv0

  def GetArgv(self):
    """For $* and $@."""
    return self.argv_stack[-1]  # top of stack

  def SetArgv(self, argv):
    """For set -- 1 2 3."""
    #print('ARGV', argv)
    # from set -- 1 2 3
    self.argv_stack[-1] = argv

  #
  # Helper
  #

  def _FindInScope(self, name):
    # TODO: Return the right scope.  Respect
    # compat dynamic-scope flag?
    # or is it shopt or set ?
    # oilopt?
    pass

  def _SetInScope(self, scope, pairs):
    for lhs, val in pairs:
      #log('SETTING %s -> %s', lhs, value)
      assert val.tag in (value_e.Str, value_e.StrArray)

      name = lhs.name
      if name in scope:
        # Preserve cell flags.  For example, could be Undef and exported!
        scope[name].val = val
      else:
        scope[name] = runtime.cell(val, False, False)

  #
  # Globals
  #

  def GetGlobal(self, name):
    """Helper for completion."""
    g = self.var_stack[0]  # global scope
    if name in g:
      return g[name].val

    return runtime.Undef()

  def SetGlobals(self, pairs):
    """For completion."""
    self._SetInScope(self.var_stack[0], pairs)

  def SetGlobalArray(self, name, a):
    """Helper for completion."""
    assert isinstance(a, list)
    val = runtime.StrArray(a)
    pairs = [(ast.LeftVar(name), val)]
    self.SetGlobals(pairs)

  def SetGlobalString(self, name, s):
    """Helper for completion."""
    assert isinstance(s, str)
    val = runtime.Str(s)
    pairs = [(ast.LeftVar(name), val)]
    self.SetGlobals(pairs)

  #
  # Locals
  #

  def Get(self, name):
    # TODO: Don't implement dynamic scope
    for i in range(len(self.var_stack) - 1, -1, -1):
      scope = self.var_stack[i]
      if name in scope:
        #log('Get %s -> %s in scope %d', name, scope[name].val, i)
        # Don't need to use flags
        return scope[name].val

    # Fall back on environment
    v = os.getenv(name)
    if v is not None:
      return runtime.Str(v)

    return runtime.Undef()

  def SetLocals(self, pairs):
    # - Never change types?  yeah I think that's a good idea, at least for oil
    # (not sh, for compatibility).  set -o strict-types or something.  That
    # means arrays have to be initialized with let arr = [], which is fine.
    # This helps with stuff like IFS.  It starts off as a string, and assigning
    # it to a list is en error.  I guess you will have to turn this no for
    # bash?

    # TODO: Shells have dynamic scope for setting variables.  This is really
    # bad.
    self._SetInScope(self.var_stack[-1], pairs)

  def SetLocal(self, name, val):
    """Set a single local."""
    pairs = [(ast.LeftVar(name), val)]
    self.SetLocals(pairs)

  def Unset(self, name):
    # For unset -v (variable)
    # unset -f is different.
    raise NotImplementedError

  #
  # Export
  #

  def SetExportFlag(self, name, b):
    """
    First look for local, then global
    """
    found = False
    for i in range(len(self.var_stack) - 1, -1, -1):
      scope = self.var_stack[i]
      if name in scope:
        cell = scope[name]
        cell.exported = b
        found = True
        break

    if not found:
      # You can export an undefined variable!
      scope[name] = runtime.cell(runtime.Undef(), True, False)

  def GetExported(self):
    exported = {}
    # Search from globals up.  Names higher on the stack will overwrite names
    # lower on the stack.
    for scope in self.var_stack:
      for name, cell in scope.items():
        if cell.exported and cell.val.tag == value_e.Str:
          exported[name] = cell.val.s
    return exported

  #
  # Readonly
  #

  def SetReadonlyFlag(self, name, b):
    # Or should this get a flag name?
    # readonly needs to be respected with 'set'.
    pass


class DirStack:
  """State for pushd/popd."""

  def __init__(self):
    self.dir_stack = []

  def Pushd(self, argv):
    self.dir_stack.append(os.getcwd())
    dest_dir = argv[1]
    os.chdir(dest_dir)  # TODO: error checking
    return 0

  def Popd(self, argv):
    try:
      dest_dir = self.dir_stack.pop()
    except IndexError:
      log('popd: directory stack is empty')
      return 1
    os.chdir(dest_dir)  # TODO: error checking
    return 0


class _FatalError(RuntimeError):
  """Internal exception for fatal errors."""
  pass


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
  def __init__(self, mem, builtins, funcs, completion, comp_lookup, exec_opts,
               make_parser):
    """
    Args:
      mem: Mem instance for storing variables
      builtins: builtin metadata/implementation
      funcs: registry of functions (these names are completed)
      completion: completion module, if available
      comp_lookup: completion pattern/action
      make_parser: Callback for creating a new command parser (eval and source)
    """
    self.mem = mem
    self.builtins = builtins
    # function space is different than var space.  Not hierarchical.
    self.funcs = funcs
    self.completion = completion
    # Completion hooks, set by 'complete' builtin.
    self.comp_lookup = comp_lookup
    # This is for shopt and set -o.  They are initialized by flags.
    self.exec_opts = exec_opts
    self.make_parser = make_parser

    self.ev = word_eval.NormalWordEvaluator(mem, exec_opts, self)

    self.mem.last_status = 0  # For $?

    self.traps = {}
    self.fd_state = process.FdState()

    # TODO: Pass these in from main()
    self.aliases = {}  # alias name -> string
    self.targets = []  # make syntax enters stuff here -- Target()
                       # metaprogramming or regular target syntax
                       # Whether argv[0] is make determines if it is executed

    # sleep 5 & puts a (PID, job#) entry here.  And then "jobs" displays it.
    self.jobs = {}

    self.dir_stack = DirStack()

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
    if not line:  # EOF
      return 1
    # TODO: split line and do that logic
    val = runtime.Str(line.strip())
    self.mem.SetLocal(names[0], val)
    return 0

  def _Echo(self, argv):
    argv = argv[1:]
    #log('echo argv %s', argv)
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

    if self.completion:
      chain = self.completion.ShellFuncAction(self, func)
      self.comp_lookup.RegisterName(command, chain)
      # TODO: Some feedback would be nice?
    else:
      print('ERROR: Oil was not built with readline/completion.', file=sys.stderr)
    return 0

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
      thunk = process.ExternalThunk(argv)
      thunk.RunInParent()  # never returns
    else:
      return 0

  def _Cd(self, argv):
    # TODO: Parse flags, error checking, etc.
    dest_dir = argv[1]
    if dest_dir == '-':
      old = self.mem.Get('OLDPWD')
      if old.tag == value_e.Undef:
        log('OLDPWD not set')
        return 1
      elif old.tag == value_e.Str:
        dest_dir = old.s
        print(dest_dir)  # Shells print the directory
      elif old.tag == value_e.StrArray:
        # Prevent the user from setting to array?
        raise AssertionError

    # Save OLDPWD.
    self.mem.SetGlobalString('OLDPWD', os.getcwd())
    os.chdir(dest_dir)
    self.mem.SetGlobalString('PWD', dest_dir)
    return 0

  def _Export(self, argv):
    for arg in argv:
      parts = arg.split('=', 1)
      if len(parts) == 1:
        name = parts[0]
      else:
        name, val = parts
        # TODO: Set the global flag
        self.mem.SetGlobalString(name, val)

      # May create an undefined variable
      self.mem.SetExportFlag(name, True)

    return 0

  def RunBuiltin(self, builtin_id, argv):
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

    elif builtin_id == EBuiltin.CD:
      status = self._Cd(argv)

    elif builtin_id == EBuiltin.PUSHD:
      status = self.dir_stack.Pushd(argv)

    elif builtin_id == EBuiltin.POPD:
      status = self.dir_stack.Popd(argv)

    elif builtin_id == EBuiltin.EXIT:
      try:
        code = int(argv[1])
      except IndexError:
        code = 0
      except ValueError as e:
        print("Invalid argument %r" % argv[1], file=sys.stderr)
        code = 1  # Runtime Error
      # TODO: Should this be turned into our own SystemExit exception?
      sys.exit(code)

    elif builtin_id == EBuiltin.EXPORT:
      status = self._Export(argv)

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

    assert isinstance(status, int)
    return status

  def RunFunc(self, func_node, argv):
    """Called by FuncThunk."""
    func_body = func_node.body
    # TODO: Call func with $@, $1, etc.

    self.mem.Push(argv[1:])

    # Redirects still valid for functions.
    # Here doc causes a pipe and Process(SubProgramThunk).
    try:
      status = self._Execute(func_body)
    except _ControlFlow as e:
      if e.IsReturn():
        status = e.ReturnValue()
      else:
        # break/continue used in the wrong place
        raise AssertionError('Invalid control flow')
    self.mem.Pop()
    return status

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
    if not argv:
      return process.NoOpThunk()

    # TODO: respect the special builtin order too
    builtin_id = self.builtins.Resolve(argv[0])
    if builtin_id != EBuiltin.NONE:
      return process.BuiltinThunk(self, builtin_id, argv)

    func_node = self.funcs.get(argv[0])
    if func_node is not None:
      return process.FuncThunk(self, func_node, argv)

    return process.ExternalThunk(argv, more_env)

  def _GetProcessForNode(self, node):
    """
    Assume we will run the node in another process.  Return a process.
    """
    if node.tag == command_e.SimpleCommand:
      words = braces.BraceExpandWords(node.words)
      argv = self.ev.EvalWordSequence(words)
      if argv is None:
        err = self.ev.Error()
        raise AssertionError("Error evaluating words: %s" % err)
      more_env = self.mem.GetExported()
      self._EvalEnv(node.more_env, more_env)
      thunk = self._GetThunkForSimpleCommand(argv, more_env)

    elif node.tag == command_e.ControlFlow:
      # TODO: Raise _FatalError
      # Pipeline or subshells with control flow are invalid, e.g.:
      # - break | less
      # - continue | less
      # - ( return )
      # NOTE: This could be done at parse time too.
      raise AssertionError('Invalid control flow %s' % node)

    else:
      thunk = process.SubProgramThunk(self, node)

    redirects = self._EvalRedirects(node)
    p = process.Process(thunk, fd_state=self.fd_state, redirects=redirects)
    return p

  def _EvalRedirects(self, node):
    """Evaluate redirect nodes to concrete objects.

    We have to do this every time, because you could have something like:

    for i in a b c; do
      echo foo >$i
    done

    Does it makes sense to just have RedirectNode.Eval?  Nah I think the
    Redirect() abstraction in process.py is useful.  It has a lot of methods.
    """
    # No redirects
    if node.tag in (
        command_e.NoOp, command_e.Assignment, command_e.ControlFlow,
        command_e.Pipeline, command_e.AndOr, command_e.CommandList,
        command_e.Sentence, command_e.TimeBlock):
      return []

    redirects = []
    for n in node.redirects:
      redir_type = REDIR_TYPE[n.op_id]
      if redir_type == RedirType.Path:
        # NOTE: no globbing.  You can write to a file called '*.py'.
        ok, val = self.ev.EvalWordToString(n.arg_word)
        if not ok:
          return False
        if val.tag != value_e.Str:
          self._AddErrorContext("filename to redirect to should be a string")
          return False
        filename = val.s
        if not filename:
          self._AddErrorContext("filename can't be empty")
          return False

        redirects.append(process.FilenameRedirect(n.op_id, n.fd, filename))

      elif redir_type == RedirType.Desc:  # e.g. 1>&2
        ok, val = self.ev.EvalWordToString(n.arg_word)
        if not ok:
          return False
        if val.tag != value_e.Str:
          self._AddErrorContext(
              "descriptor to redirect to should be an integer, not list")
          return False
        t = val.s
        if not t:
          self._AddErrorContext("descriptor can't be empty")
          return False
        try:
          target_fd = int(t)
        except ValueError:
          self._AddErrorContext(
              "descriptor to redirect to should be an integer, not string")
          return False
        redirects.append(process.DescriptorRedirect(n.op_id, n.fd, target_fd))

      elif redir_type == RedirType.Str:
        ok, val = self.ev.EvalWordToString(n.arg_word)
        if not ok:
          return False
        assert val.tag == value_e.Str, \
            "descriptor to redirect to should be an integer, not list"

        redirects.append(process.HereDocRedirect(n.op_id, n.fd, val.s))

      else:
        raise AssertionError
    return redirects

  def _EvalEnv(self, node_env, out_env):
    """Evaluate environment variable bindings.

    Args:
      more_env: list of ast.env_pair
      out_env: mutated.
    """
    # NOTE: Env evaluation is done in new scope so it doesn't persist.  It also
    # pushes argv.  Don't need that?
    self.mem.PushTemp()
    for env_pair in node_env:
      name = env_pair.name
      rhs = env_pair.val

      # Could pass extra bindings like out_env here?  But PushTemp should work?
      ok, val = self.ev.EvalWordToString(rhs)
      if not ok:
        raise AssertionError

      # Set each var so the next one can reference it.  Example:
      # FOO=1 BAR=$FOO ls /
      self.mem.SetLocal(name, val)
      # TODO: Need to pop bindings for simple commands.  Need a stack.

      out_env[name] = val.s
    self.mem.PopTemp()

  def _RunPipeline(self, node):
    # TODO: Also check for "echo" and "read".  Turn them into HereDocRedirect()
    # and p.CaptureOutput()

    # NOTE: First or last one can use the "main" shell thread.  Doesn't have to
    # run in subshell.  Although I guess it's simpler if it always does.
    pi = process.Pipeline()

    for child in node.children:
      p = self._GetProcessForNode(child)
      pi.Add(p)

    #print(pi)

    # TODO: Set PipeStatus() in self.mem
    pipe_status = pi.Run()
    #log('pipe_status %s', pipe_status)

    if self.exec_opts.pipefail:
      # If any process failed, the status of the entire pipeline is 1.
      status = 0
      for st in pipe_status:
        if st != 0:
          status = 1
    else:
      status = pipe_status[-1]  # last one determines status

    if node.negated:
      if status == 0:
        return 1
      else:
        return 0

    return status

  def _Execute(self, node):
    """
    Args:
      node: of type AstNode
    """
    redirects = self._EvalRedirects(node)

    # TODO: Only eval argv[0] once.  It can have side effects!
    if node.tag == command_e.SimpleCommand:
      words = braces.BraceExpandWords(node.words)
      argv = self.ev.EvalWordSequence(words)

      if argv is None:
        self.error_stack.extend(self.ev.Error())
        raise _FatalError()
      more_env = self.mem.GetExported()
      self._EvalEnv(node.more_env, more_env)
      thunk = self._GetThunkForSimpleCommand(argv, more_env)

      # Don't waste a process if we'd launch one anyway.
      if thunk.IsExternal():
        p = process.Process(thunk, fd_state=self.fd_state, redirects=redirects)
        status = p.Run()

      else:  # Internal
        #log('ARGV %s', argv)

        # NOTE: _EvalRedirects turns LST nodes into core/process.py nodes.  And
        # then we use polymorphism here.  Does it make sense to use functional
        # style based on the RedirType?  Might be easier to read.

        self.fd_state.PushFrame()
        for r in redirects:
          r.ApplyInParent(self.fd_state)

        status = thunk.RunInParent()
        restore_fd_state = thunk.ShouldRestoreFdState()

        # Special case for exec 1>&2 (with no args): we permanently change the
        # fd state.  BUT we don't want to restore later.
        # TODO: Instead of this, maybe r.ApplyPermaent(self.fd_state)?
        if restore_fd_state:
          self.fd_state.PopAndRestore()
        else:
          self.fd_state.PopAndForget()

    elif node.tag == command_e.Sentence:
      # TODO: Compile this away.
      status = self._Execute(node.command)

    elif node.tag == command_e.Pipeline:
      status = self._RunPipeline(node)

    elif node.tag == command_e.Subshell:
      # This makes sure we don't waste a process if we'd launch one anyway.
      p = self._GetProcessForNode(node.children[0])
      status = p.Run()

    elif node.tag == command_e.DBracket:
      bool_ev = expr_eval.BoolEvaluator(self.mem, self.ev)
      ok = bool_ev.Eval(node.expr)
      if ok:
        status = 0 if bool_ev.Result() else 1
      else:
        raise AssertionError('Error evaluating boolean: %s' % bool_ev.Error())

    elif node.tag == command_e.DParen:
      arith_ev = expr_eval.ArithEvaluator(self.mem, self.ev)
      ok = arith_ev.Eval(node.child)
      if ok:
        i = arith_ev.Result()
        # Negate the value: non-zero in arithmetic is true, which is zero in
        # shell land
        status = 0 if i != 0 else 1
      else:
        raise AssertionError('Error evaluating (( )): %s' % arith_ev.Error())

    elif node.tag == command_e.Assignment:
      pairs = []
      for pair in node.pairs:
        # RHS can be a string or array.
        ok, val = self.ev.EvalWordToAny(pair.rhs)
        assert isinstance(val, runtime.value), val
        #log('RHS %s -> %s', pair.rhs, val)
        if not ok:
          self.error_stack.extend(self.ev.Error())
          raise _FatalError()
        pairs.append((pair.lhs, val))

      if node.keyword == Id.Assign_Local:
        self.mem.SetLocals(pairs)
      else:  # could be readonly/export/etc.
        self.mem.SetGlobals(pairs)

      # TODO: This should be eval of RHS, unlike bash!
      status = 0

    elif node.tag == command_e.ControlFlow:
      if node.arg_word:  # Evaluate the argument
        ok, val = self.ev.EvalWordToString(node.arg_word)
        if not ok:
          self.error_stack.extend(self.ev.Error())
          raise _FatalError()
        assert val.tag == value_e.Str
        arg = int(val.s)  # They all take integers
      else:
        arg = 0  # return 0, break 0 levels, etc.

      raise _ControlFlow(node.token, arg)

    # The only difference between these two is that CommandList has no
    # redirects.  We already took care of that above.
    elif node.tag in (command_e.CommandList, command_e.BraceGroup):
      status = 0  # for empty list
      for child in node.children:
        status = self._Execute(child)  # last status wins

    elif node.tag == command_e.AndOr:
      #print(node.children)
      left, right = node.children
      status = self._Execute(left)

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

      while True:
        status = self._Execute(node.cond)
        done = status != 0
        if _DonePredicate(status):
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
        self.mem.SetLocal(iter_name, runtime.Str(x))
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
      # Delegate to command list
      # TODO: This should be compiled out!
      status = self._Execute(node.child)

    elif node.tag == command_e.FuncDef:
      self.funcs[node.name] = node
      status = 0

    elif node.tag == command_e.If:
      done = False
      for arm in node.arms:
        status = self._Execute(arm.cond)
        if status == 0:
          status = self._Execute(arm.action)
          done = True
          break
      # TODO: The compiler should flatten this
      if not done and node.else_action is not None:
        status = self._Execute(node.else_action)

    elif node.tag == command_e.NoOp:
      status = 0  # make it true

    elif node.tag == command_e.Case:
      ok, val = self.ev.EvalWordToString(node.to_match)
      assert ok
      to_match = val.s

      status = 0  # If there are no arms, it should be zero?
      done = False

      for arm in node.arms:
        for pat_word in arm.pat_list:
          # NOTE: Is it OK that we're evaluating these as we go?
          ok, pat_val = self.ev.EvalWordToString(pat_word, do_fnmatch=True)
          assert ok
          #log('Matching word %r against pattern %r', to_match, pat_val.s)
          if libc.fnmatch(pat_val.s, to_match):
            status = self._Execute(arm.action)
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

    if self.exec_opts.errexit:
      if status != 0:
        # TODO: token should be set to what?  Is it node.begin_word and
        # node.end_word?
        token = None
        tb = self.mem.GetTraceback(token)
        self._SetException(tb,
            "Command %s exited with code %d" % ('TODO', status))
        # TODO: raise _ControlFlow?  Except?
        # Dummy?

    # TODO: Is this the right place to put it?  Does it need a stack for
    # function calls?
    self.mem.last_status = status
    return status

  def Execute(self, node):
    """Execute a top level LST node."""
    # Use exceptions internally, but exit codes externally.
    try:
      status = self._Execute(node)
    except _ControlFlow as e:
      # TODO: Make this error message better.
      print('Break/continue/return bubbled up to top level', file=sys.stderr)
      status = 1
    except _FatalError:
      # TODO: Nicer runtime error message.
      print(self.error_stack, file=sys.stderr)
      status = 1

    # TODO: Hook this up
    #print('break / continue can only be used inside loop')
    #status = 129  # TODO: Fix this.  Use correct macros
    return status
