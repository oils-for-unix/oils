#!/usr/bin/python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
"""
state.py -- Interpreter state
"""

import os

from core import runtime
from core import util
from core.id_kind import Id

from osh import ast_ as ast

part_value_e = runtime.part_value_e
value_e = runtime.value_e
lvalue_e = runtime.lvalue_e

log = util.log
e_die = util.e_die


class _ErrExit:
  """Manages the errexit setting.

  - The user can change it with builtin 'set' at any point in the code.
  - These constructs implicitly disable 'errexit':
    - if / while / until conditions
    - ! (part of pipeline)
    - && ||

  An _ErrExit object prevents these two mechanisms from clobbering each other.
  """

  def __init__(self):
    self.errexit = False  # the setting
    self.stack = []

  def Push(self):
    if self.errexit:
      self.errexit = False
      self.stack.append(True)  # value to restore
    else:
      self.stack.append(False)

  def Pop(self):
    self.errexit = self.stack.pop()

  def Set(self, b):
    if True in self.stack:  # are we in a temporary state?
      # TODO: Add error context.
      e_die("Can't set 'errexit' in a context where it's disabled "
            "(if, !, && ||, while/until conditions)")
    self.errexit = b


class ExecOpts(object):

  def __init__(self):
    self.errexit = _ErrExit()

    # TODO: Set from flags
    self.nounset = False
    self.pipefail = False
    self.xtrace = False  # NOTE: uses PS4
    self.noglob = False  # -f
    self.noexec = False  # -n

    # OSH-specific
    self.strict_arith = False  # e.g. $(( x )) where x doesn't look like integer
    self.strict_array = False  # ${a} not ${a[0]}, require double quotes, etc.
    self.strict_command = False  # break at top level.
    self.strict_word = False  # word splitting, etc.
    self.strict_scope = False  # disable dynamic scope

    # TODO: strict_bool.  Some of this is covered by arithmetic, e.g. -eq.

  def ErrExit(self):
    return self.errexit.errexit


class _ArgFrame(object):
  """Stack frame for arguments array."""

  def __init__(self, argv):
    self.argv = argv
    self.num_shifted = 0

  def GetArgNum(self, arg_num):
    index = self.num_shifted + arg_num - 1
    if index >= len(self.argv):
      return runtime.Undef()

    return runtime.Str(str(self.argv[index]))

  def GetArgv(self):
    return self.argv[self.num_shifted : ]

  def GetNumArgs(self):
    return len(self.argv) - self.num_shifted

  def SetArgv(self, argv):
    self.argv = argv
    self.num_shifted = 0


class Mem(object):
  """For storing variables.

  Mem is better than "Env" -- Env implies OS stuff.

  Callers:
    User code: assigning and evaluating variables, in command context or
      arithmetic context.
      SetLocal -- for local
      SetReadonlyFlag
      SetExportFlag
    Completion engine: for COMP_WORDS, etc.
    Builtins call it implicitly: read, cd for $PWD, $OLDPWD, etc.

  Modules: cmd_exec, word_eval, expr_eval, completion
  """

  def __init__(self, argv0, argv, environ):
    top = {}  # string -> runtime.cell
    self.var_stack = [top]
    self.argv0 = argv0
    self.argv_stack = [_ArgFrame(argv)]

    self.last_status = 0  # Mutable public variable
    self.last_job_id = -1  # Uninitialized value mutable public variable

    # Done ONCE on initialization
    self.root_pid = os.getpid()

    self._InitDefaults()
    self._InitEnviron(environ)

  def _InitDefaults(self):
    # Default value; user may unset it.
    # $ echo -n "$IFS" | python -c 'import sys;print repr(sys.stdin.read())'
    # ' \t\n'
    self.SetGlobalString('IFS', ' \t\n')
    self.SetGlobalString('PWD', os.getcwd())

  def _InitEnviron(self, environ):
    # This is the way dash and bash work -- at startup, they turn everything in
    # 'environ' variable into shell variables.  Bash has an export_env
    # variable.  Dash has a loop through environ in init.c
    for n, v in environ.iteritems():
      self.SetGlobalString(n, v)
      self.SetExportFlag(n, True)

  #
  # Stack
  #

  def Push(self, argv):
    self.var_stack.append({})
    self.argv_stack.append(_ArgFrame(argv))

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

  def Shift(self, n):
    frame = self.argv_stack[-1]
    num_args = len(frame.argv)

    if (frame.num_shifted + n) <= num_args:
      frame.num_shifted += n
      return 0  # success
    else:
      return 1  # silent error

  def GetArgNum(self, arg_num):
    if arg_num == 0:
      return runtime.Str(self.argv0)

    return self.argv_stack[-1].GetArgNum(arg_num)

  def GetArgv(self):
    """For $* and $@."""
    return self.argv_stack[-1].GetArgv()

  def SetArgv(self, argv):
    """For set -- 1 2 3."""
    # from set -- 1 2 3
    self.argv_stack[-1].SetArgv(argv)

  #
  # Public
  #

  def GetSpecialVar(self, op_id):
    if op_id == Id.VSub_Bang:  # $!
      n = self.last_job_id
      if n == -1:
        return runtime.Undef()  # could be an error

    elif op_id == Id.VSub_QMark:  # $?
      # TODO: Have to parse status somewhere.
      # External commands need WIFEXITED test.  What about subshells?
      n = self.last_status

    elif op_id == Id.VSub_Pound:  # $#
      n = self.argv_stack[-1].GetNumArgs()

    elif op_id == Id.VSub_Dollar:  # $$
      n = self.root_pid

    else:
      raise NotImplementedError(op_id)

    return runtime.Str(str(n))

  #
  # Helper functions
  #

  def _FindInScope(self, name):
    # TODO: Return the right scope.  Respect
    # compat dynamic-scope flag?
    # or is it shopt or set ?
    # oilopt?
    pass

  def _SetInScope(self, scope, pairs):
    """Helper to set locals or globals."""
    for lval, val in pairs:
      #log('SETTING %s -> %s', lval, val)
      assert val.tag in (value_e.Str, value_e.StrArray)

      name = lval.name
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
    pairs = [(ast.LhsName(name), val)]
    self.SetGlobals(pairs)

  def SetGlobalString(self, name, s):
    """Helper for completion, $PWD, etc."""
    assert isinstance(s, str)
    val = runtime.Str(s)
    pairs = [(ast.LhsName(name), val)]
    self.SetGlobals(pairs)

  #
  # Locals
  #

  def Get(self, name):
    # TODO: Respect strict_arith to disable dynamic scope
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
    """Set a single local.

    Used for:
    1) for loop iteration variables
    2) temporary environments like FOO=bar BAR=$FOO cmd, 
    3) read builtin
    """
    pairs = [(ast.LhsName(name), val)]
    self.SetLocals(pairs)

  def _SetLocalOrGlobal(self, name, val):
    # TODO:
    # - Use _FindInScope helper?  So we preserve flags.
    # - Optionally disable dynamic scope
    # - Implement readonly, etc.  Test the readonly flag!
    cell = runtime.cell(val, False, False)

    for i in range(len(self.var_stack) - 1, -1, -1):  # dynamic scope
      scope = self.var_stack[i]
      if name in scope:
        scope[name] = cell
        break
    else:
      global_scope = self.var_stack[0]
      global_scope[name] = cell

  def SetLocalsOrGlobals(self, pairs):
    """For x=1 inside a function.
    """
    for lval, val in pairs:
      if lval.tag == lvalue_e.LhsName:
        self._SetLocalOrGlobal(lval.name, val)
      elif lval.tag == lvalue_e.LhsIndexedName:
        raise NotImplementedError('a[x]=')

  def Unset(self, name):
    found = False
    for i in range(len(self.var_stack) - 1, -1, -1):  # dynamic scope
      scope = self.var_stack[i]
      if name in scope:
        found = True
        del scope[name]
        break

    return found

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
