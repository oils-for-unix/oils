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

import cStringIO
import os

from core import args
from core import legacy
from osh.meta import runtime
from core import util
from osh.meta import Id

from osh.meta import ast

part_value_e = runtime.part_value_e
value_e = runtime.value_e
lvalue_e = runtime.lvalue_e
scope_e = runtime.scope_e
var_flags_e = runtime.var_flags_e

log = util.log
e_die = util.e_die


class _ErrExit(object):
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
    """User code calls this."""
    if True in self.stack:  # are we in a temporary state?
      # TODO: Add error context.
      e_die("Can't set 'errexit' in a context where it's disabled "
            "(if, !, && ||, while/until conditions)")
    self.errexit = b

  def Disable(self):
    """For bash compatibility in command sub."""
    self.errexit = False


# Used by builtin
SET_OPTIONS = [
    ('e', 'errexit'),
    ('n', 'noexec'),
    ('u', 'nounset'),
    ('x', 'xtrace'),
    ('f', 'noglob'),
    ('C', 'noclobber'),
    ('h', 'hashall'),
    (None, 'pipefail'),

    (None, 'debug-completion'),

    (None, 'strict-control-flow'),
    (None, 'strict-errexit'),
    (None, 'strict-array'),

    (None, 'vi'),
    (None, 'emacs'),

    # TODO: Add strict-arg-parse?  For example, 'trap 1 2 3' shouldn't be
    # valid, because it has an extra argument.  Builtins are inconsistent about
    # checking this.
]

_SET_OPTION_NAMES = set(name for _, name in SET_OPTIONS)


class ExecOpts(object):

  def __init__(self, mem):
    """
    Args:
      mem: state.Mem, for SHELLOPTS
    """
    self.mem = mem

    # Depends on the shell invocation (sh -i, etc.)  This is not technically an
    # 'set' option, but it appears in $-.
    self.interactive = False

    # set -o / set +o
    self.errexit = _ErrExit()  # -e
    self.nounset = False  # -u
    self.pipefail = False
    self.xtrace = False  # NOTE: uses PS4
    self.noglob = False  # -f
    self.noexec = False  # -n
    self.noclobber = False  # -C
    # We don't do anything with this yet.  But Aboriginal calls 'set +h'.
    self.hashall = True  # -h is true by default.

    # OSH-specific options.
    self.debug_completion = False
    self.strict_control_flow = False

    # strict_errexit makes 'local foo=$(false)' and echo $(false) fail.
    # By default, we have mimic bash's undesirable behavior of ignoring
    # these failures, since ash copied it, and Alpine's abuild relies on it.
    #
    # bash 4.4 also has shopt -s inherit_errexit, which says that command subs
    # inherit the value of errexit.  # I don't believe it is strict enough --
    # local still needs to fail.
    self.strict_errexit = False

    # Several problems:
    # - foo="$@" not allowed because it decays.  Should be foo=( "$@" ).
    # - ${a} not ${a[0]}
    # - possibly disallow $* "$*" altogether.
    # - do not allow [[ "$@" == "${a[@]}" ]]
    self.strict_array = False

    # This comes after all the 'set' options.
    shellopts = self.mem.GetVar('SHELLOPTS')
    assert shellopts.tag == value_e.Str, shellopts
    self._InitOptionsFromEnv(shellopts.s)

    # shopt -s / -u.  NOTE: bash uses $BASHOPTS rather than $SHELLOPTS for
    # these.
    self.nullglob = False
    self.failglob = False

    #
    # OSH-specific options that are not yet implemented.
    #

    self.strict_arith = False  # e.g. $(( x )) where x doesn't look like integer
    self.strict_word = False  # word splitting, etc.
    self.strict_scope = False  # disable dynamic scope
    # TODO: strict_bool.  Some of this is covered by arithmetic, e.g. -eq.

    # Don't need flags -e and -n.  -e is $'\n', and -n is write.
    self.sane_echo = False

    # Used for 'set -o vi/emacs'
    # Set by the Executor, if available
    self.readline = None

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
    if self.interactive:
      chars.append('i')

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
    elif opt_name in ('vi', 'emacs'):
      if self.readline:
        self.readline.parse_and_bind("set editing-mode " + opt_name);
      else:
        # TODO error message copied from 'cmd_exec.py'; refactor?
        util.error('Oil was not built with readline/completion.')
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


class _StackFrame(object):
  def __init__(self, readonly=False):
    self.vars = {}  # string -> runtime.cell
    self.readonly = readonly

  def __repr__(self):
    f = cStringIO.StringIO()
    f.write('<_StackFrame readonly:%s' % self.readonly)
    for name, cell in self.vars.iteritems():
      f.write('  %s = ' % name)
      f.write('  %s' % cell)
      f.write('\n')
    f.write('>')
    return f.getvalue()


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


def _FormatStack(var_stack):
  """Temporary debugging.

  TODO: Turn this into a real JSON dump or something.
  """
  f = cStringIO.StringIO()
  for i, entry in enumerate(var_stack):
    f.write('[%d] %s' % (i, entry))
    f.write('\n')
  return f.getvalue()


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
    top = _StackFrame()
    self.var_stack = [top]
    self.argv0 = argv0
    self.argv_stack = [_ArgFrame(argv)]
    # NOTE: could use deque and appendleft/popleft, but:
    # 1. ASDL type checking of StrArray doesn't allow it (could be fixed)
    # 2. We don't otherwise depend on the collections module
    self.func_name_stack = []

    # Note: we're reusing these objects because they change on every single
    # line!  Don't want to allocate more than necsesary.
    self.source_name = runtime.Str('')
    self.line_num = runtime.Str('')

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
      for n, v in frame.vars.iteritems():
        parts.append('  %s %s' % (n, v))
    parts.append('>')
    return '\n'.join(parts) + '\n'

  def _InitDefaults(self):
    # Default value; user may unset it.
    # $ echo -n "$IFS" | python -c 'import sys;print repr(sys.stdin.read())'
    # ' \t\n'
    SetGlobalString(self, 'IFS', legacy.DEFAULT_IFS)
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

    # TODO: IFS, PWD, etc. should follow this pattern.  Maybe need a SysCall
    # interface?  self.syscall.getcwd() etc.

    v = self.GetVar('SHELLOPTS')
    if v.tag == value_e.Undef:
      SetGlobalString(self, 'SHELLOPTS', '')
    # Now make it readonly
    self.SetVar(
        ast.LhsName('SHELLOPTS'), None, (var_flags_e.ReadOnly,),
        scope_e.GlobalOnly)

    v = self.GetVar('HOME')
    if v.tag == value_e.Undef:
      home_dir = util.GetHomeDir() or '~'  # No expansion if not found?
      SetGlobalString(self, 'HOME', home_dir)

  def SetSourceLocation(self, source_name, line_num):
    # Mutate Str() objects.
    self.source_name.s = source_name
    self.line_num.s = str(line_num)

  #
  # Stack
  #

  def PushCall(self, func_name, argv):
    """For function calls."""
    # bash uses this order: top of stack first.
    self.func_name_stack.append(func_name)

    self.var_stack.append(_StackFrame())
    self.argv_stack.append(_ArgFrame(argv))

  def PopCall(self):
    self.func_name_stack.pop()

    self.var_stack.pop()
    self.argv_stack.pop()

  def PushSourceArgv(self, argv):
    """For 'source foo.sh 1 2 3."""
    # Match bash's behavior for ${FUNCNAME[@]}.  But it would be nicer to add
    # the name of the script here?
    self.func_name_stack.append('source')
    if argv:
      self.argv_stack.append(_ArgFrame(argv))

  def PopSourceArgv(self, argv):
    self.func_name_stack.pop()
    if argv:
      self.argv_stack.pop()

  def PushTemp(self):
    """For the temporary scope in 'FOO=bar BAR=baz echo'."""
    # We don't want the 'read' builtin to write to this frame!
    self.var_stack.append(_StackFrame(readonly=True))

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

  def _FindCellAndNamespace(self, name, lookup_mode, is_read=False):
    """Helper for getting and setting variable.

    Need a mode to skip Temp scopes.  For Setting.

    Args:
      name: the variable name
      lookup_mode: scope_e

    Returns:
      cell: The cell corresponding to looking up 'name' with the given mode, or
        None if it's not found.
      namespace: The namespace it should be set to or deleted from.
    """
    if lookup_mode == scope_e.Dynamic:
      for i in range(len(self.var_stack) - 1, -1, -1):
        frame = self.var_stack[i]
        if frame.readonly and not is_read:
          continue
        namespace = frame.vars
        if name in namespace:
          cell = namespace[name]
          return cell, namespace
      return None, self.var_stack[0].vars  # set in global namespace

    elif lookup_mode == scope_e.LocalOnly:
      frame = self.var_stack[-1]
      if frame.readonly and not is_read:
        frame = self.var_stack[-2]
        # The frame below a readonly one shouldn't be readonly.
        assert not frame.readonly, frame
        #assert not frame.readonly, self._Format(self.var_stack)
      namespace = frame.vars
      return namespace.get(name), namespace

    elif lookup_mode == scope_e.TempEnv:
      frame = self.var_stack[-1]
      namespace = frame.vars
      return namespace.get(name), namespace

    elif lookup_mode == scope_e.GlobalOnly:
      namespace = self.var_stack[0].vars
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
          n = lval.index - len(strs) + 1
          strs.extend([None] * n)
          strs[lval.index] = value.s
      else:
        # When the array doesn't exist yet, it is created filled with None.
        # Access to the array needs to explicitly filter those sentinel values.
        # It also wastes memory. But indexed access is fast.

        # What should be optimized for? Bash uses a linked list. Random access
        # takes linear time, but iteration skips unset entries automatically.

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

        items = [None] * lval.index
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
    cell = self.var_stack[0].vars[name]
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
      # TODO: Reuse this object too?
      return runtime.StrArray(strs)

    if name == 'LINENO':
      return self.line_num

    # Instead of BASH_SOURCE.  Using Oil _ convnetion.
    if name == 'SOURCE_NAME':
      return self.source_name

    cell, _ = self._FindCellAndNamespace(name, lookup_mode, is_read=True)

    if cell:
      return cell.val

    return runtime.Undef()

  def Unset(self, lval, lookup_mode):
    """
    Returns:
      ok bool, found bool.

      ok is false if the cell is read-only.
      found is false if the name is not there.
    """
    if lval.tag == lvalue_e.LhsName:  # unset x
      cell, namespace = self._FindCellAndNamespace(lval.name, lookup_mode)
      if cell:
        found = True
        if cell.readonly:
          return False, found
        del namespace[lval.name]  # it must be here
        return True, found # found
      else:
        return True, False

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
      for name, cell in scope.vars.items():
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
