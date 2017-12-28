#!/usr/bin/env python
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

from core import args
from core import runtime
from core import util
from core.id_kind import Id

from osh import ast_ as ast

part_value_e = runtime.part_value_e
value_e = runtime.value_e
lvalue_e = runtime.lvalue_e
scope_e = runtime.scope_e
var_flags_e = runtime.var_flags_e

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


# Used by builtin
SET_OPTIONS = [
    ('e', 'errexit'),
    ('n', 'noexec'),
    ('u', 'nounset'),
    ('x', 'xtrace'),
    ('f', 'noglob'),
    ('C', 'noclobber'),
    (None, 'pipefail'),

    (None, 'debug-completion'),

    (None, 'strict-control-flow'),
]

_SET_OPTION_NAMES = set(name for _, name in SET_OPTIONS)


class ExecOpts(object):

  def __init__(self, mem):
    """
    Args:
      mem: state.Mem, for SHELLOPTS
    """
    self.mem = mem

    # set -o / set +o
    self.errexit = _ErrExit()  # -e
    self.nounset = False  # -u
    self.pipefail = False
    self.xtrace = False  # NOTE: uses PS4
    self.noglob = False  # -f
    self.noexec = False  # -n
    self.noclobber = False  # -C
    self.debug_completion = False
    self.strict_control_flow = False

    shellopts = self.mem.GetVar('SHELLOPTS')
    assert shellopts.tag == value_e.Str, shellopts
    self._InitOptionsFromEnv(shellopts.s)

    # shopt -s / -u
    self.nullglob = False 
    self.failglob = False 

    # OSH-specific
    self.strict_arith = False  # e.g. $(( x )) where x doesn't look like integer
    self.strict_array = False  # ${a} not ${a[0]}, require double quotes, etc.
    self.strict_command = False  # break at top level.
    self.strict_word = False  # word splitting, etc.
    self.strict_scope = False  # disable dynamic scope

    # TODO: strict_bool.  Some of this is covered by arithmetic, e.g. -eq.

  def _InitOptionsFromEnv(self, shellopts):
    # e.g. errexit:nounset:pipefail
    lookup = set(shellopts.split(':'))
    for _, name in SET_OPTIONS:
      if name in lookup:
        self._SetOption(name, True)

  def ErrExit(self):
    return self.errexit.errexit

  def GetDollarHyphen(self):
    chars = []
    if self.ErrExit():
      chars.append('e')
    if self.nounset:
      chars.append('u')
    # NO letter for pipefail?
    if self.xtrace:
      chars.append('x')
    if self.noexec:
      chars.append('n')

    # bash has:
    # - c for sh -c, i for sh -i (mksh also has this)
    # - h for hashing (mksh also has this)
    # - B for brace expansion
    return ''.join(chars)

  def _SetOption(self, opt_name, b):
    """Private version for synchronizing from SHELLOPTS."""
    assert '_' not in opt_name
    if opt_name not in _SET_OPTION_NAMES:
      raise args.UsageError('Invalid option %r' % opt_name)
    if opt_name == 'errexit':
      self.errexit.Set(b)
    else:
      # strict-control-flow -> strict_control_flow
      opt_name = opt_name.replace('-', '_')
      setattr(self, opt_name, b)

  def SetOption(self, opt_name, b):
    """ For set -o, set +o, or shopt -s/-u -o. """
    self._SetOption(opt_name, b)

    val = self.mem.GetVar('SHELLOPTS')
    assert val.tag == value_e.Str
    shellopts = val.s

    # Now check if SHELLOPTS needs to be updated.  It may be exported.
    #
    # NOTE: It might be better to skip rewriting SEHLLOPTS in the common case
    # where it is not used.  We could do it lazily upon GET.

    # Also, it would be slightly more efficient to update SHELLOPTS if
    # settings were batched, Examples:
    # - set -eu
    # - shopt -s foo bar
    if b:
      if opt_name not in shellopts:
        new_val = runtime.Str('%s:%s' % (shellopts, opt_name))
        self.mem.InternalSetGlobal('SHELLOPTS', new_val)
    else:
      if opt_name in shellopts:
        names = [n for n in shellopts.split(':') if n != opt_name]
        new_val = runtime.Str(':'.join(names))
        self.mem.InternalSetGlobal('SHELLOPTS', new_val)

  SHOPT_OPTIONS = ('nullglob', 'failglob')

  def SetShoptOption(self, opt_name, b):
    """ For shopt -s/-u. """
    if opt_name not in self.SHOPT_OPTIONS:
      raise args.UsageError('Invalid option %r' % opt_name)
    setattr(self, opt_name, b)

  def ShowOptions(self, opt_names):
    """ For 'set -o' and 'shopt -p -o' """
    # TODO: Maybe sort them differently?
    opt_names = opt_names or _SET_OPTION_NAMES
    for opt_name in opt_names:
      if opt_name == 'errexit':
        b = self.errexit.errexit
      else:
        attr = opt_name.replace('-', '_')
        b = getattr(self, attr)
      print('set %so %s' % ('-' if b else '+', opt_name))

  def ShowShoptOptions(self, opt_names):
    """ For 'shopt -p' """
    opt_names = opt_names or self.SHOPT_OPTIONS  # show all
    for opt_name in opt_names:
      b = getattr(self, opt_name)
      print('shopt -%s %s' % ('s' if b else 'u', opt_name))


class _ArgFrame(object):
  """Stack frame for arguments array."""

  def __init__(self, argv):
    self.argv = argv
    self.num_shifted = 0

  def __repr__(self):
    return '<_ArgFrame %s %d at %x>' % (self.argv, self.num_shifted, id(self))

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


class DirStack(object):
  """For pushd/popd/dirs."""

  def __init__(self):
    self.stack = []
    self.Reset()
    
  def Reset(self):
    self.stack[:] = [os.getcwd()]

  def Push(self, entry):
    self.stack.append(entry)

  def Pop(self):
    if len(self.stack) <= 1:
      return None
    return self.stack.pop()

  def Iter(self):
    """Iterate in reverse order."""
    return reversed(self.stack)


class Mem(object):
  """For storing variables.

  Mem is better than "Env" -- Env implies OS stuff.

  Callers:
    User code: assigning and evaluating variables, in command context or
      arithmetic context.
    Completion engine: for COMP_WORDS, etc.
    Builtins call it implicitly: read, cd for $PWD, $OLDPWD, etc.

  Modules: cmd_exec, word_eval, expr_eval, completion
  """

  def __init__(self, argv0, argv, environ, arena):
    top = {}  # string -> runtime.cell
    self.var_stack = [top]
    self.argv0 = argv0
    self.argv_stack = [_ArgFrame(argv)]
    # NOTE: could use deque and appendleft/popleft, but
    # 1. ASDL type checking of StrArray doesn't allow it (could be fixed)
    # 2. We don't otherwise depend on the collections module
    self.func_name_stack = []

    self.last_status = 0  # Mutable public variable
    self.last_job_id = -1  # Uninitialized value mutable public variable

    # Done ONCE on initialization
    self.root_pid = os.getpid()

    self._InitDefaults()
    self._InitVarsFromEnv(environ)
    self.arena = arena

  def __repr__(self):
    parts = []
    parts.append('<Mem')
    for i, frame in enumerate(self.var_stack):
      parts.append('  -- %d --' % i)
      for n, v in frame.iteritems():
        parts.append('  %s %s' % (n, v))
    parts.append('>')
    return '\n'.join(parts) + '\n'

  def _InitDefaults(self):
    # Default value; user may unset it.
    # $ echo -n "$IFS" | python -c 'import sys;print repr(sys.stdin.read())'
    # ' \t\n'
    SetGlobalString(self, 'IFS', ' \t\n')
    SetGlobalString(self, 'PWD', os.getcwd())

    # NOTE: Should we put these in a namespace for Oil?
    SetGlobalString(self, 'UID', str(os.getuid()))
    SetGlobalString(self, 'EUID', str(os.geteuid()))
    # For getopts builtin
    SetGlobalString(self, 'OPTIND', '1')

    # For xtrace
    SetGlobalString(self, 'PS4', '+ ')

  def _InitVarsFromEnv(self, environ):
    # This is the way dash and bash work -- at startup, they turn everything in
    # 'environ' variable into shell variables.  Bash has an export_env
    # variable.  Dash has a loop through environ in init.c
    for n, v in environ.iteritems():
      self.SetVar(ast.LhsName(n), runtime.Str(v),
                 (var_flags_e.Exported,), scope_e.GlobalOnly)

    # If it's not in the environment, initialize it.  This makes it easier to
    # update later in ExecOpts.
    v = self.GetVar('SHELLOPTS')
    if v.tag == value_e.Undef:
      SetGlobalString(self, 'SHELLOPTS', '')
    # Now make it readonly
    self.SetVar(
        ast.LhsName('SHELLOPTS'), None, (var_flags_e.ReadOnly,),
        scope_e.GlobalOnly)

  #
  # Stack
  #

  def PushCall(self, func_name, argv):
    """For function calls."""
    # bash uses this order: top of stack first.
    self.func_name_stack.append(func_name)

    self.var_stack.append({})
    self.argv_stack.append(_ArgFrame(argv))

  def PopCall(self):
    self.func_name_stack.pop()

    self.var_stack.pop()
    self.argv_stack.pop()

  def PushTemp(self):
    """For the temporary scope in 'FOO=bar BAR=baz echo'."""
    self.var_stack.append({})

  def PopTemp(self):
    self.var_stack.pop()

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
  # Special Vars
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
  # Named Vars
  #

  def _FindCellAndNamespace(self, name, lookup_mode):
    """
    Returns:
      cell: The cell corresponding to looking up 'name' with the given mode, or
        None if it's not found.
      namespace: The namespace it should be set to or deleted from.
    """
    if lookup_mode == scope_e.Dynamic:
      found = False
      for i in range(len(self.var_stack) - 1, -1, -1):
        namespace = self.var_stack[i]
        if name in namespace:
          cell = namespace[name]
          return cell, namespace
      return None, self.var_stack[0]

    elif lookup_mode == scope_e.LocalOnly:
      namespace = self.var_stack[-1]
      return namespace.get(name), namespace

    elif lookup_mode == scope_e.GlobalOnly:
      namespace = self.var_stack[0]
      return namespace.get(name), namespace

    else: 
      raise AssertionError(lookup_mode)

  def SetVar(self, lval, value, new_flags, lookup_mode):
    """
    Args:
      lval: lvalue
      val: value, or None if only changing flags
      new_flags: tuple of flags to set: ReadOnly | Exported 
        () means no flags to start with
        None means unchanged?
      scope:
        Local | Global | Dynamic - for builtins, PWD, etc.

      NOTE: in bash, PWD=/ changes the directory.  But not in dash.
    """
    # STRICTNESS / SANENESS:
    #
    # 1) Don't create arrays automatically, e.g. a[1000]=x
    # 2) Never change types?  yeah I think that's a good idea, at least for oil
    # (not sh, for compatibility).  set -o strict-types or something.  That
    # means arrays have to be initialized with let arr = [], which is fine.
    # This helps with stuff like IFS.  It starts off as a string, and assigning
    # it to a list is en error.  I guess you will have to turn this no for
    # bash?

    assert new_flags is not None

    if lval.tag == lvalue_e.LhsName:
      #if lval.name == 'ldflags':
      # TODO: Turn this into a tracing feature.  Like osh --tracevar ldflags
      # --tracevar foo.  Has to respect environment variables too.
      if 0:
        util.log('--- SETTING ldflags to %s', value)
        if lval.spids:
          span_id = lval.spids[0]
          line_span = self.arena.GetLineSpan(span_id)
          line_id = line_span.line_id
          #line = arena.GetLine(line_id)
          path, line_num = self.arena.GetDebugInfo(line_id)
          col = line_span.col
          #length = line_span.length
          util.log('--- spid %s: %s, line %d, col %d', span_id, path,
                   line_num+1, col)

          # TODO: Need the arena to look it up the line spid and line number.

      # Maybe this should return one of (cell, scope).  existing cell, or the
      # scope to put it in?
      # _FindCellOrScope

      cell, namespace = self._FindCellAndNamespace(lval.name, lookup_mode)
      if cell:
        if value is not None:
          if cell.readonly:
            # TODO: error context
            e_die("Can't assign to readonly value %r", lval.name)
          cell.val = value
        if var_flags_e.Exported in new_flags:
          cell.exported = True
        if var_flags_e.ReadOnly in new_flags:
          cell.readonly = True
      else:
        if value is None:
          value = runtime.Undef()  # export foo, readonly foo
        cell = runtime.cell(value,
                            var_flags_e.Exported in new_flags ,
                            var_flags_e.ReadOnly in new_flags )
        namespace[lval.name] = cell

      if (cell.val is not None and cell.val.tag == value_e.StrArray and
          cell.exported):
        e_die("Can't export array")  # TODO: error context

    elif lval.tag == lvalue_e.LhsIndexedName:
      # a[1]=(1 2 3)
      if value.tag == value_e.StrArray:
        e_die("Can't assign array to array member")  # TODO: error context

      cell, namespace = self._FindCellAndNamespace(lval.name, lookup_mode)
      if cell:
        if cell.val.tag != value_e.StrArray:
          # s=x
          # s[1]=y
          e_die("Can't index non-array")  # TODO: error context

        if cell.readonly:
          e_die("Can't assign to readonly value")

        strs = cell.val.strs
        try:
          strs[lval.index] = value.s
        except IndexError:
          # Fill it in with None.  It could look like this:
          # ['1', 2, 3, None, None, '4', None]
          # Then ${#a[@]} counts the entries that are not None.
          #
          # TODO: strict-array for Oil arrays won't auto-fill.
          n = len(strs) - lval.index + 1
          strs.extend([None] * n)
          strs[lval.index] = value.s
      else:
        # TODO:
        # - This is a bug, because a[2]=2 creates an array of length ONE, even
        # though the index is two.
        # - Maybe represent as hash table?  Then it's not an ASDL type?

        # representations:
        # - array_item.Str array_item.Undef
        # - parallel array: val.strs, val.undefs
        # - or change ASDL type checking
        #   - ASDL language does not allow: StrArray(string?* strs)
        # - or add dict to ASDL?  Didn't it support obj?
        #   - finding the max index is linear time?
        #     - also you have to sort the indices
        #
        # array ops:
        # a=(1 2)
        # a[1]=x
        # a+=(1 2)
        # ${a[@]}  - get all
        # ${#a[@]} - length
        # ${!a[@]} - keys
        # That seems pretty minimal.

        items = [''] * lval.index
        items.append(value.s)
        new_value = runtime.StrArray(items)
        # arrays can't be exported
        cell = runtime.cell(new_value, False,
                            var_flags_e.ReadOnly in new_flags)
        namespace[lval.name] = cell

    else:
      raise AssertionError

  def InternalSetGlobal(self, name, new_val):
    """For setting read-only globals internally.

    Args:
      name: string (not Lhs)
      new_val: value

    The variable must already exist.

    Use case: SHELLOPTS.
    """
    cell = self.var_stack[0][name]
    cell.val = new_val

  # NOTE: Have a default for convenience
  def GetVar(self, name, lookup_mode=scope_e.Dynamic):
    assert isinstance(name, str), name

    # Do lookup of system globals before looking at user variables.  Note: we
    # could optimize this at compile-time like $?.  That would break
    # ${!varref}, but it's already broken for $?.
    if name == 'FUNCNAME':
      # bash wants it in reverse order.  This is a little inefficient but we're
      # not depending on deque().
      strs = list(reversed(self.func_name_stack))
      return runtime.StrArray(strs)

    cell, _ = self._FindCellAndNamespace(name, lookup_mode)

    if cell:
      return cell.val

    return runtime.Undef()

  def Unset(self, lval, lookup_mode):
    """
    Returns:
      Success or failure.  A non-existent variable is still considered success.
    """
    if lval.tag == lvalue_e.LhsName:  # unset x
      cell, namespace = self._FindCellAndNamespace(lval.name, lookup_mode)
      if cell:
        if cell.readonly:
          e_die("Can't unset readonly variable %r", lval.name)
        del namespace[lval.name]  # it must be here
        return True  # found
      else:
        return False

    elif lval.tag == lvalue_e.LhsIndexedName:  # unset a[1]
      raise NotImplementedError

    else:
      raise AssertionError

  def ClearFlag(self, name, flag, lookup_mode):
    cell, namespace = self._FindCellAndNamespace(name, lookup_mode)
    if cell:
      if flag == var_flags_e.Exported:
        cell.exported = False
      else:
        raise AssertionError
      return True
    else:
      return False

  def GetExported(self):
    """Get all the variables that are marked exported."""
    # TODO: This is run on every SimpleCommand.  Should we have a dirty flag?
    # We have to notice these things:
    # - If an exported variable is changed.
    # - If the set of exported variables changes.  

    exported = {}
    # Search from globals up.  Names higher on the stack will overwrite names
    # lower on the stack.
    for scope in self.var_stack:
      for name, cell in scope.items():
        if cell.exported and cell.val.tag == value_e.Str:
          exported[name] = cell.val.s
    return exported


def SetLocalString(mem, name, s):
  """Set a local string.

  Used for:
  1) for loop iteration variables
  2) temporary environments like FOO=bar BAR=$FOO cmd, 
  3) read builtin
  """
  assert isinstance(s, str)
  mem.SetVar(ast.LhsName(name), runtime.Str(s), (), scope_e.LocalOnly)


def SetGlobalString(mem, name, s):
  """Helper for completion, $PWD, etc."""
  assert isinstance(s, str)
  val = runtime.Str(s)
  mem.SetVar(ast.LhsName(name), val, (), scope_e.GlobalOnly)


def SetGlobalArray(mem, name, a):
  """Helper for completion."""
  assert isinstance(a, list)
  mem.SetVar(ast.LhsName(name), runtime.StrArray(a), (), scope_e.GlobalOnly)


def GetGlobal(mem, name):
  assert isinstance(name, str), name
  return mem.GetVar(name, scope_e.GlobalOnly)
