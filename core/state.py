#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
"""
state.py - Interpreter state
"""

import cStringIO
import os

from asdl import const
from core import args
from core import legacy
from core import util
from osh.meta import ast, runtime, Id

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
    ('v', 'verbose'),
    ('f', 'noglob'),
    ('C', 'noclobber'),
    ('h', 'hashall'),
    (None, 'pipefail'),

    (None, 'debug-completion'),

    (None, 'strict-control-flow'),
    (None, 'strict-errexit'),
    (None, 'strict-array'),
    (None, 'strict-arith'),
    (None, 'strict-word-eval'),
    (None, 'strict-var-eval'),

    (None, 'vi'),
    (None, 'emacs'),

    # TODO: Add strict-arg-parse?  For example, 'trap 1 2 3' shouldn't be
    # valid, because it has an extra argument.  Builtins are inconsistent about
    # checking this.
]

# Used by core/comp_builtins.py too.
SET_OPTION_NAMES = set(name for _, name in SET_OPTIONS)

SHOPT_OPTION_NAMES = (
    'nullglob', 'failglob', 'expand_aliases', 'extglob', 'progcomp',
    'hostcomplete', 'lastpipe')


class ExecOpts(object):

  def __init__(self, mem, readline):
    """
    Args:
      mem: state.Mem, for SHELLOPTS
    """
    self.mem = mem
    # Used for 'set -o vi/emacs'
    self.readline = readline

    # Depends on the shell invocation (sh -i, etc.)  This is not technically an
    # 'set' option, but it appears in $-.
    self.interactive = False

    # set -o / set +o
    self.errexit = _ErrExit()  # -e
    self.nounset = False  # -u
    self.pipefail = False
    self.xtrace = False  # NOTE: uses PS4
    self.verbose = False  # like xtrace, but prints unevaluated commands
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

    # No-op for bash compatibility.  We always expand aliases.
    self.expand_aliases = False
    self.extglob = False  # No-op for bash compatibility.
    self.progcomp = False  # ditto
    self.hostcomplete = False  # ditto, for words with '@'
    self.lastpipe = False  # No-op because it's always on.

    #
    # OSH-specific options that are not yet implemented.
    #

    self.strict_arith = False  # e.g. $(( x )) where x doesn't look like integer
    self.strict_word_eval = False
    # Whether we statically know variables, e.g. $PYTHONPATH vs.
    # $ENV['PYTHONPATH'], and behavior of 'or' and 'if' expressions.
    # This is off by default because we want the interactive shell to match.
    self.strict_var_eval = False
    self.strict_scope = False  # disable dynamic scope
    # TODO: strict_bool.  Some of this is covered by arithmetic, e.g. -eq.

    # Don't need flags -e and -n.  -e is $'\n', and -n is write.
    self.sane_echo = False

    self.vi = False
    self.emacs = False

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
    if opt_name not in SET_OPTION_NAMES:
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
      if opt_name == 'verbose' and b:
        log('Warning: set -o verbose not implemented')
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

  def SetShoptOption(self, opt_name, b):
    """ For shopt -s/-u. """
    if opt_name not in SHOPT_OPTION_NAMES:
      raise args.UsageError('Invalid option %r' % opt_name)
    setattr(self, opt_name, b)

  def ShowOptions(self, opt_names):
    """ For 'set -o' and 'shopt -p -o' """
    # TODO: Maybe sort them differently?
    opt_names = opt_names or SET_OPTION_NAMES
    for opt_name in opt_names:
      if opt_name == 'errexit':
        b = self.errexit.errexit
      else:
        attr = opt_name.replace('-', '_')
        b = getattr(self, attr)
      print('set %so %s' % ('-' if b else '+', opt_name))

  def ShowShoptOptions(self, opt_names):
    """ For 'shopt -p' """
    opt_names = opt_names or SHOPT_OPTION_NAMES  # show all
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

  def Dump(self):
    return {
        'argv': self.argv,
        'num_shifted': self.num_shifted,
    }

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
  def __init__(self, mutable=True):
    self.vars = {}  # string -> runtime.cell
    self.mutable = mutable

  def Dump(self):
    """Dump the stack frame as reasonably compact and readable JSON."""

    vars_json = {}
    for name, cell in self.vars.iteritems():
      cell_json = {}

      flags = ''
      if cell.exported:
        flags += 'x'
      if cell.readonly:
        flags += 'r'
      if flags:
        cell_json['flags'] = flags

      # For compactness, just put the value right in the cell.
      tag = cell.val.tag
      if tag == value_e.Undef:
        cell_json['type'] = 'Undef'
      elif tag == value_e.Str:
        cell_json['type'] = 'Str'
        cell_json['value'] = cell.val.s
      elif tag == value_e.StrArray:
        cell_json['type'] = 'StrArray'
        cell_json['value'] = cell.val.strs

      vars_json[name] = cell_json

    return {
        'vars': vars_json,
        'mutable': self.mutable,
    }

  def __repr__(self):
    f = cStringIO.StringIO()
    f.write('<_StackFrame mutable:%s' % self.mutable)
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
    self.argv0 = argv0
    self.argv_stack = [_ArgFrame(argv)]
    self.var_stack = [_StackFrame()]

    # The debug_stack isn't strictly necessary for execution.  We use it for
    # crash dumps and for 3 parallel arrays: FUNCNAME, BASH_SOURCE,
    # BASH_LINENO.  The First frame points at the global vars and argv.
    self.debug_stack = [(None, None, const.NO_INTEGER, 0, 0)]
    self.bash_source = []  # for implementing BASH_SOURCE
    self.current_spid = const.NO_INTEGER

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

  def Dump(self):
    """Copy state before unwinding the stack."""
    var_stack = [frame.Dump() for frame in self.var_stack]
    argv_stack = [frame.Dump() for frame in self.argv_stack]
    debug_stack = []
    for func_name, source_name, call_spid, argv_i, var_i in self.debug_stack:
      d = {}
      if func_name:
        d['func_called'] = func_name
      elif source_name:
        d['file_sourced'] = source_name
      else:
        pass  # It's a frame for FOO=bar?  Or the top one?

      d['call_spid'] = call_spid
      if call_spid != const.NO_INTEGER:  # first frame has this issue
        span = self.arena.GetLineSpan(call_spid)
        path, line_num = self.arena.GetDebugInfo(span.line_id)
        line = self.arena.GetLine(span.line_id)
        d['call_path'] = path
        d['call_line_num'] = line_num
        d['call_line'] = line

      d['argv_frame'] = argv_i
      d['var_frame'] = var_i
      debug_stack.append(d)

    return var_stack, argv_stack, debug_stack

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

    # bash-completion uses this.  Value copied from bash.  It doesn't integrate
    # with 'readline' yet.
    SetGlobalString(self, 'COMP_WORDBREAKS', '"\'><=;|&(:')

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

  def SetCurrentSpanId(self, span_id):
    """Set the current source location, for BASH_SOURCE, BASH_LINENO, LINENO,
    etc.
    """
    if span_id == const.NO_INTEGER:
      log('Warning: SimpleCommand or Assignment has no location information')
      return

    span = self.arena.GetLineSpan(span_id)
    source_name, line_num = self.arena.GetDebugInfo(span.line_id)

    # Mutate Str() objects for now.
    self.source_name.s = source_name
    self.line_num.s = str(line_num)

    self.current_spid = span_id

  #
  # Stack
  #

  def PushCall(self, func_name, def_spid, argv):
    """For function calls."""
    self.argv_stack.append(_ArgFrame(argv))
    self.var_stack.append(_StackFrame())

    # bash uses this order: top of stack first.
    self._PushDebugStack(func_name, None)

    span = self.arena.GetLineSpan(def_spid)
    def_source_name, _ = self.arena.GetDebugInfo(span.line_id)
    self.bash_source.append(def_source_name)

  def PopCall(self):
    self.bash_source.pop()
    self._PopDebugStack()

    self.var_stack.pop()
    self.argv_stack.pop()

  def PushSource(self, source_name, argv):
    """For 'source foo.sh 1 2 3."""
    if argv:
      self.argv_stack.append(_ArgFrame(argv))
    # Match bash's behavior for ${FUNCNAME[@]}.  But it would be nicer to add
    # the name of the script here?
    self._PushDebugStack(None, source_name)
    self.bash_source.append(source_name)

  def PopSource(self, argv):
    self.bash_source.pop()
    self._PopDebugStack()
    if argv:
      self.argv_stack.pop()

  def PushTemp(self):
    """For the temporary scope in 'FOO=bar BAR=baz echo'."""
    # We don't want the 'read' builtin to write to this frame!
    self.var_stack.append(_StackFrame(mutable=False))
    self._PushDebugStack(None, None)

  def PopTemp(self):
    self._PopDebugStack()
    self.var_stack.pop()

  def _PushDebugStack(self, func_name, source_name):
    # self.current_spid is set before every SimpleCommand and Assignment.
    # Function calls and 'source' are both SimpleCommand.

    # These integers are handles/pointers, for use in CrashDumper.
    argv_i = len(self.argv_stack) - 1
    var_i = len(self.var_stack) - 1

    # The stack is a 5-tuple, where func_name and source_name are optional.  If
    # both are unset, then it's aTemp frame'.
    self.debug_stack.append(
        (func_name, source_name, self.current_spid, argv_i, var_i)
    )

  def _PopDebugStack(self):
    self.debug_stack.pop()

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

  def _FindCellAndNamespace(self, name, lookup_mode, writing=True):
    """Helper for getting and setting variable.

    Need a mode to skip Temp scopes.  For Setting.

    Args:
      name: the variable name
      lookup_mode: scope_e
      writing: Is this lookup for a read or a write?

    Returns:
      cell: The cell corresponding to looking up 'name' with the given mode, or
        None if it's not found.
      namespace: The namespace it should be set to or deleted from.
    """
    if lookup_mode == scope_e.Dynamic:
      for i in range(len(self.var_stack) - 1, -1, -1):
        frame = self.var_stack[i]
        if not frame.mutable and writing:
          continue
        namespace = frame.vars
        if name in namespace:
          cell = namespace[name]
          return cell, namespace
      return None, self.var_stack[0].vars  # set in global namespace

    elif lookup_mode == scope_e.LocalOnly:
      frame = self.var_stack[-1]
      if not frame.mutable and writing:
        frame = self.var_stack[-2]
        # The frame below a readonly one should be mutable.
        assert frame.mutable, frame
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

  def IsAssocArray(self, name, lookup_mode):
    """Returns whether a name resolve to a cell with an associative array.
    
    We need to know this to evaluate the index expression properly -- should it
    be coerced to an integer or not?
    """
    cell, _ = self._FindCellAndNamespace(name, lookup_mode)
    if cell:
      if cell.val.tag == value_e.AssocArray:  # foo=([key]=value)
        return True
      if cell.is_assoc_array:  # declare -A
        return True
    return False

  def SetVar(self, lval, value, new_flags, lookup_mode, strict_array=False):
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
        if var_flags_e.AssocArray in new_flags:
          cell.is_assoc_array = True
      else:
        if value is None:
          # set -o nounset; local foo; echo $foo  # It's still undefined!
          value = runtime.Undef()  # export foo, readonly foo
        cell = runtime.cell(value,
                            var_flags_e.Exported in new_flags,
                            var_flags_e.ReadOnly in new_flags,
                            var_flags_e.AssocArray in new_flags)
        namespace[lval.name] = cell

      if (cell.val is not None and cell.val.tag == value_e.StrArray and
          cell.exported):
        e_die("Can't export array")  # TODO: error context

    elif lval.tag == lvalue_e.LhsIndexedName:
      # TODO: All paths should have this?  We can get here by a[x]=1 or
      # (( a[ x ] = 1 )).  Maybe we should make them different?
      if lval.spids:
        left_spid = lval.spids[0]
      else:
        left_spid = const.NO_INTEGER

      # TODO: This is a parse error!
      # a[1]=(1 2 3)
      if value.tag == value_e.StrArray:
        e_die("Can't assign array to array member", span_id=left_spid)

      cell, namespace = self._FindCellAndNamespace(lval.name, lookup_mode)
      if not cell:
        self._BindNewArrayWithEntry(namespace, lval, value, new_flags)
        return

      # bash/mksh have annoying behavior of letting you do LHS assignment to
      # Undef, which then turns into an array.  (Undef means that set -o
      # nounset fails.)
      cell_tag = cell.val.tag
      if (cell_tag == value_e.Str or 
          (cell_tag == value_e.Undef and strict_array)):
        # s=x
        # s[1]=y  # invalid
        e_die("Entries in value of type %s can't be assigned to",
              cell.val.__class__.__name__, span_id=left_spid)

      if cell.readonly:
        e_die("Can't assign to readonly value", span_id=left_spid)

      if cell_tag == value_e.Undef:
        if cell.is_assoc_array:
          self._BindNewAssocArrayWithEntry(namespace, lval, value, new_flags)
        else:
          self._BindNewArrayWithEntry(namespace, lval, value, new_flags)
        return

      if cell_tag == value_e.StrArray:
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
        return

      if cell_tag == value_e.AssocArray:
        cell.val.d[lval.index] = value.s
        return

    else:
      raise AssertionError(lval.__class__.__name__)

  def _BindNewArrayWithEntry(self, namespace, lval, value, new_flags):
    """Fill 'namespace' with a new indexed array entry."""
    items = [None] * lval.index
    items.append(value.s)
    new_value = runtime.StrArray(items)

    # arrays can't be exported; can't have AssocArray flag
    readonly = var_flags_e.ReadOnly in new_flags
    namespace[lval.name] = runtime.cell(new_value, False, readonly, False)

  def _BindNewAssocArrayWithEntry(self, namespace, lval, value, new_flags):
    """Fill 'namespace' with a new indexed array entry."""
    d = {lval.index: value.s}  # TODO: RHS has to be string?
    new_value = runtime.AssocArray(d)

    # associative arrays can't be exported; don't need AssocArray flag
    readonly = var_flags_e.ReadOnly in new_flags
    namespace[lval.name] = runtime.cell(new_value, False, readonly, False)

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
      strs = []
      for func_name, source_name, _, _, _ in reversed(self.debug_stack):
        if func_name:
          strs.append(func_name)
        if source_name:
          strs.append('source')  # bash doesn't give name
        # Temp stacks are ignored
      return runtime.StrArray(strs)  # TODO: Reuse this object too?

    # This isn't the call source, it's the source of the function DEFINITION
    # (or the sourced # file itself).
    if name == 'BASH_SOURCE':
      return runtime.StrArray(list(reversed(self.bash_source)))

    # This is how bash source SHOULD be defined, but it's not!
    if name == 'CALL_SOURCE':
      strs = []
      for func_name, source_name, call_spid, _, _ in reversed(self.debug_stack):
        if call_spid == const.NO_INTEGER:  # should only happen for the first entry
          continue
        span = self.arena.GetLineSpan(call_spid)
        path, _ = self.arena.GetDebugInfo(span.line_id)
        strs.append(path)
      return runtime.StrArray(strs)  # TODO: Reuse this object too?

    if name == 'BASH_LINENO':
      strs = []
      for func_name, source_name, call_spid, _, _ in reversed(self.debug_stack):
        if call_spid == const.NO_INTEGER:  # should only happen for the first entry
          continue
        span = self.arena.GetLineSpan(call_spid)
        _, line_num = self.arena.GetDebugInfo(span.line_id)
        strs.append(str(line_num))
      return runtime.StrArray(strs)  # TODO: Reuse this object too?

    if name == 'LINENO':
      return self.line_num

    # This is OSH-specific.  Get rid of it in favor of ${BASH_SOURCE[0]} ?
    if name == 'SOURCE_NAME':
      return self.source_name

    cell, _ = self._FindCellAndNamespace(name, lookup_mode, writing=False)

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
      for name, cell in scope.vars.iteritems():
        if cell.exported and cell.val.tag == value_e.Str:
          exported[name] = cell.val.s
    return exported

  def VarNames(self):
    """For compgen -A variable."""
    # Look up the stack, yielding all variables.  Bash seems to do this.
    for scope in self.var_stack:
      for name, _ in scope.vars.iteritems():
        yield name


def SetLocalString(mem, name, s):
  """Set a local string.

  Used for:
  1) for loop iteration variables
  2) temporary environments like FOO=bar BAR=$FOO cmd,
  3) read builtin
  """
  assert isinstance(s, str)
  mem.SetVar(ast.LhsName(name), runtime.Str(s), (), scope_e.LocalOnly)


def SetStringDynamic(mem, name, s):
  """Set a string by looking up the stack.

  Used for getopts.
  """
  assert isinstance(s, str)
  mem.SetVar(ast.LhsName(name), runtime.Str(s), (), scope_e.Dynamic)


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
