# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
state.py - Interpreter state
"""
from __future__ import print_function

import cStringIO

from _devbuild.gen.id_kind_asdl import Id, Id_t
from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.runtime_asdl import (
    value, value_e, value_t, value__Str, value__MaybeStrArray, value__AssocArray,
    lvalue, lvalue_e, lvalue_t, lvalue__Named, lvalue__Indexed, lvalue__Keyed,
    scope_e, scope_t,
)
from _devbuild.gen import runtime_asdl  # for cell
from asdl import runtime
from core import error
from core import pyutil
from core.pyutil import e_usage, stderr_line
from core import ui
from core.util import log, e_die
from core import optview
from frontend import consts
from frontend import match
from mycpp import mylib
from mycpp.mylib import tagswitch, iteritems
from osh import split
from pylib import os_path
from pylib import path_stat

import libc
import posix_ as posix

from typing import Tuple, List, Dict, Optional, Any, cast, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cell
  from core.alloc import Arena


# This was derived from bash --norc -c 'argv "$COMP_WORDBREAKS".
# Python overwrites this to something Python-specific in Modules/readline.c, so
# we have to set it back!
# Used in both core/competion.py and osh/state.py
_READLINE_DELIMS = ' \t\n"\'><=;|&(:'

LINE_ZERO = -2  # special value that's not runtime.NO_SPID


# flags for SetVar
SetReadOnly   = 1 << 0
ClearReadOnly = 1 << 1
SetExport     = 1 << 2
ClearExport   = 1 << 3
SetNameref    = 1 << 4
ClearNameref  = 1 << 5


class SearchPath(object):
  """For looking up files in $PATH."""

  def __init__(self, mem):
    # type: (Mem) -> None
    self.mem = mem
    self.cache = {}  # type: Dict[str, str]

  def Lookup(self, name, exec_required=True):
    # type: (str, bool) -> Optional[str]
    """
    Returns the path itself (for relative path), the resolve path, or None.
    """
    if '/' in name:
      if path_stat.exists(name):
        return name
      else:
        return None

    # TODO: Could cache this computation to avoid allocating every time for all
    # the splitting.
    val = self.mem.GetVar('PATH')
    UP_val = val
    if val.tag_() == value_e.Str:
      val = cast(value__Str, UP_val)
      path_list = val.s.split(':')
    else:
      path_list = []  # treat as empty path

    for path_dir in path_list:
      full_path = os_path.join(path_dir, name)

      # NOTE: dash and bash only check for EXISTENCE in 'command -v' (and 'type
      # -t').  OSH follows mksh and zsh.  Note that we can still get EPERM if
      # the permissions are changed between check and use.
      if exec_required:
        found = posix.access(full_path, posix.X_OK_)
      else:
        found = path_stat.exists(full_path)  # for 'source'

      if found:
        return full_path

    return None

  def CachedLookup(self, name):
    # type: (str) -> Optional[str]
    if name in self.cache:
      return self.cache[name]

    full_path = self.Lookup(name)
    if full_path is not None:
      self.cache[name] = full_path
    return full_path

  def MaybeRemoveEntry(self, name):
    # type: (str) -> None
    """When the file system changes."""
    try:
      del self.cache[name]
    except KeyError:
      pass

  def ClearCache(self):
    # type: () -> None
    """For hash -r."""
    self.cache.clear()

  def CachedCommands(self):
    # type: () -> List[str]
    return self.cache.values()


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
    # type: () -> None
    self._value = False  # the setting
    # SUBTLE INVARIANT: There's only ONE valid integer in the stack that's not
    # runtime.NO_SPID, and it's either a valid span_id or 0.  Push() and Set()
    # enforce this.
    self.stack = []  # type: List[int]

  def Push(self, span_id):
    # type: (int) -> None
    """Temporarily disable errexit."""
    assert span_id != runtime.NO_SPID
    if self._value:
      self._value = False
      self.stack.append(span_id)  # value to restore
    else:
      self.stack.append(runtime.NO_SPID)  # INVALID span ID / "False"

  def Pop(self):
    # type: () -> None
    """Restore the previous value."""
    self._value = (self.stack.pop() != runtime.NO_SPID)

  def SpidIfDisabled(self):
    # type: () -> int
    for n in self.stack:
      if n != runtime.NO_SPID:  # set -e will be restored later
        return n
    return runtime.NO_SPID

  def Set(self, b):
    # type: (bool) -> None
    """Set the errexit flag.

    Callers: set -o errexit, shopt -s oil:all, strict:all.
    """
    for i, n in enumerate(self.stack):
      if n != runtime.NO_SPID:  # set -e will be restored later
        # Ignore set -e or set +e now, but its effect becomes visible LATER.
        # This is confusing behavior that all shells implement!  strict_errexit
        # makes it a non-issue.

        # SUBTLE: 0 isn't a valid span_id, but we will never use it for the
        # strict_errexit message.
        self.stack[i] = 0 if b else runtime.NO_SPID
        return

    self._value = b  # Otherwise just set it

  def Disable(self):
    # type: () -> None
    """For bash compatibility in command sub."""
    self._value = False

  def value(self):
    # type: () -> bool
    return self._value


class _Getter(object):

  def __init__(self, opt_array, opt_name):
    # type: (List[bool], str) -> None
    self.opt_array = opt_array
    self.num = match.MatchOption(opt_name)
    assert self.num != 0, opt_name

  def __call__(self):
    # type: () -> bool
    return self.opt_array[self.num]


class OptHook(object):
  """Interface for option hooks."""

  def OnChange(self, opt_array, opt_name, b):
    # type: (List[bool], str, bool) -> bool
    """This method is called whenever an option is changed.

    Returns success or failure.
    """
    return True


def MakeOpts(mem, opt_hook):
  # type: (Mem, OptHook) -> Tuple[optview.Parse, optview.Exec, MutableOpts]

  # 38 options
  #log('opts = %d', option_def.ArraySize())

  opt_array = [False] * option_i.ARRAY_SIZE

  errexit = _ErrExit()
  parse_opts = optview.Parse(opt_array)
  exec_opts = optview.Exec(opt_array, errexit)
  mutable_opts = MutableOpts(mem, opt_array, errexit, opt_hook)

  return parse_opts, exec_opts, mutable_opts


class MutableOpts(object):

  def __init__(self, mem, opt_array, errexit, opt_hook):
    # type: (Mem, List[bool], _ErrExit, OptHook) -> None
    self.mem = mem
    self.opt_array = opt_array
    self.errexit = errexit

    # On by default
    for opt_num in consts.DEFAULT_TRUE:
      self.opt_array[opt_num] = True

    # Used for 'set -o vi/emacs'
    self.opt_hook = opt_hook

    # This comes after all the 'set' options.
    UP_shellopts = self.mem.GetVar('SHELLOPTS')
    if UP_shellopts.tag_() == value_e.Str:  # Always true in Oil, see Init above
      shellopts = cast(value__Str, UP_shellopts)
      self._InitOptionsFromEnv(shellopts.s)

  def _InitOptionsFromEnv(self, shellopts):
    # type: (str) -> None
    # e.g. errexit:nounset:pipefail
    lookup = shellopts.split(':')
    for name in consts.SET_OPTION_NAMES:
      if name in lookup:
        self._SetOption(name, True)

  def set_interactive(self):
    # type: () -> None
    self.opt_array[option_i.interactive] = True

  def set_emacs(self):
    # type: () -> None
    self.opt_array[option_i.emacs] = True

  def set_xtrace(self, b):
    # type: (bool) -> None
    self.opt_array[option_i.xtrace] = b

  def _SetArrayByName(self, opt_name, b):
    # type: (str, bool) -> None
    if (opt_name in consts.PARSE_OPTION_NAMES and
        not self.mem.InGlobalNamespace()):
      e_die('Syntax options must be set at the top level '
            '(outside any function)')

    index = match.MatchOption(opt_name)
    if index == 0:
      # Could be an assert sometimes, but check anyway
      e_usage('got invalid option %r' % opt_name)
    self.opt_array[index] = b

  def _SetOption(self, opt_name, b):
    # type: (str, bool) -> None
    """Private version for synchronizing from SHELLOPTS."""
    assert '_' not in opt_name
    assert opt_name in consts.SET_OPTION_NAMES

    if opt_name == 'errexit':
      self.errexit.Set(b)
    else:
      if opt_name == 'verbose' and b:
        stderr_line('Warning: set -o verbose not implemented')
      self._SetArrayByName(opt_name, b)

    # note: may FAIL before we get here.

    success = self.opt_hook.OnChange(self.opt_array, opt_name, b)

  def SetOption(self, opt_name, b):
    # type: (str, bool) -> None
    """ For set -o, set +o, or shopt -s/-u -o. """
    if opt_name not in consts.SET_OPTION_NAMES:
      e_usage('got invalid option %r' % opt_name)
    self._SetOption(opt_name, b)

    UP_val = self.mem.GetVar('SHELLOPTS')
    assert UP_val.tag == value_e.Str, UP_val
    val = cast(value__Str, UP_val)
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
        new_val = value.Str('%s:%s' % (shellopts, opt_name))
        self.mem.InternalSetGlobal('SHELLOPTS', new_val)
    else:
      if opt_name in shellopts:
        names = [n for n in shellopts.split(':') if n != opt_name]
        new_val = value.Str(':'.join(names))
        self.mem.InternalSetGlobal('SHELLOPTS', new_val)

  def _SetGroup(self, opt_nums, b):
    # type: (List[int], bool) -> None
    for opt_num in opt_nums:
      b2 = not b if opt_num in consts.DEFAULT_TRUE else b
      self.opt_array[opt_num] = b2

    self.errexit.Set(b)  # Special case for all option groups

  def SetShoptOption(self, opt_name, b):
    # type: (str, bool) -> None
    """ For shopt -s/-u. """

    # shopt -s all:oil turns on all Oil options, which includes all strict #
    # options
    if opt_name == 'oil:basic':
      self._SetGroup(consts.OIL_BASIC, b)
      return

    if opt_name == 'oil:all':
      self._SetGroup(consts.OIL_ALL, b)
      return

    if opt_name == 'strict:all':
      self._SetGroup(consts.STRICT_ALL, b)
      return

    if opt_name not in consts.SHOPT_OPTION_NAMES:
      e_usage('got invalid option %r' % opt_name)

    self._SetArrayByName(opt_name, b)

  def ShowOptions(self, opt_names):
    # type: (List[str]) -> None
    """ For 'set -o' and 'shopt -p -o' """
    # TODO: Maybe sort them differently?

    if len(opt_names) == 0:  # if none, supplied, show all
      opt_names = consts.SET_OPTION_NAMES

    for opt_name in opt_names:
      if opt_name not in consts.SET_OPTION_NAMES:
        e_usage('got invalid option %r' % opt_name)

      if opt_name == 'errexit':
        b = self.errexit.value()
      else:
        index = match.MatchOption(opt_name)
        assert index != 0, opt_name
        b = self.opt_array[index]
      print('set %so %s' % ('-' if b else '+', opt_name))

  def ShowShoptOptions(self, opt_names):
    # type: (List[str]) -> None
    """ For 'shopt -p' """
    if len(opt_names) == 0:
      opt_names = consts.VISIBLE_SHOPT_NAMES  # if none supplied, show all
    for opt_name in opt_names:
      index = match.MatchOption(opt_name)
      if index == 0:
        e_usage('got invalid option %r' % opt_name)
      b = self.opt_array[index]
      print('shopt -%s %s' % ('s' if b else 'u', opt_name))


class _ArgFrame(object):
  """Stack frame for arguments array."""

  def __init__(self, argv):
    # type: (List[str]) -> None
    self.argv = argv
    self.num_shifted = 0

  def __repr__(self):
    # type: () -> str
    return '<_ArgFrame %s %d at %x>' % (self.argv, self.num_shifted, id(self))

  def Dump(self):
    # type: () -> Dict[str, Any]
    return {
        'argv': self.argv,
        'num_shifted': self.num_shifted,
    }

  def GetArgNum(self, arg_num):
    # type: (int) -> value_t
    index = self.num_shifted + arg_num - 1
    if index >= len(self.argv):
      return value.Undef()

    return value.Str(self.argv[index])

  def GetArgv(self):
    # type: () -> List[str]
    return self.argv[self.num_shifted : ]

  def GetNumArgs(self):
    # type: () -> int
    return len(self.argv) - self.num_shifted

  def SetArgv(self, argv):
    # type: (List[str]) -> None
    self.argv = argv
    self.num_shifted = 0


if mylib.PYTHON:
  def _DumpVarFrame(frame):
    # type: (Dict[str, cell]) -> Any
    """Dump the stack frame as reasonably compact and readable JSON."""

    vars_json = {}
    for name, cell in frame.iteritems():
      cell_json = {}  # type: Dict[str, Any]

      buf = mylib.BufWriter()
      if cell.exported:
        buf.write('x')
      if cell.readonly:
        buf.write('r')
      flags = buf.getvalue()
      if len(flags):
        cell_json['flags'] = flags

      # For compactness, just put the value right in the cell.
      val = None  # type: value_t
      with tagswitch(cell.val) as case:
        if case(value_e.Undef):
          cell_json['type'] = 'Undef'

        elif case(value_e.Str):
          val = cast(value__Str, cell.val)
          cell_json['type'] = 'Str'
          cell_json['value'] = val.s

        elif case(value_e.MaybeStrArray):
          val = cast(value__MaybeStrArray, cell.val)
          cell_json['type'] = 'MaybeStrArray'
          cell_json['value'] = val.strs

        elif case(value_e.AssocArray):
          val = cast(value__AssocArray, cell.val)
          cell_json['type'] = 'AssocArray'
          cell_json['value'] = val.d

      vars_json[name] = cell_json

    return vars_json


class DirStack(object):
  """For pushd/popd/dirs."""
  def __init__(self):
    # type: () -> None
    self.stack = []  # type: List[str]
    self.Reset()  # Invariant: it always has at least ONE entry.

  def Reset(self):
    # type: () -> None
    del self.stack[:] 
    self.stack.append(posix.getcwd())

  def Push(self, entry):
    # type: (str) -> None
    self.stack.append(entry)

  def Pop(self):
    # type: () -> str
    if len(self.stack) <= 1:
      return None
    self.stack.pop()  # remove last
    return self.stack[-1]  # return second to last

  def Iter(self):
    # type: () -> List[str]
    """Iterate in reverse order."""
    # mycpp REWRITE:
    #return reversed(self.stack)
    ret = []  # type: List[str]
    ret.extend(self.stack)
    ret.reverse()
    return ret


# NOTE: not used!
if mylib.PYTHON:
  def _FormatStack(var_stack):
    # type: (List[Any]) -> str
    """Temporary debugging.

    TODO: Turn this into a real JSON dump or something.
    """
    f = cStringIO.StringIO()
    for i, entry in enumerate(var_stack):
      f.write('[%d] %s' % (i, entry))
      f.write('\n')
    return f.getvalue()


def _GetWorkingDir():
  # type: () -> str
  """Fallback for pwd and $PWD when there's no 'cd' and no inherited $PWD."""
  try:
    return posix.getcwd()
  except OSError as e:
    e_die("Can't determine working directory: %s", pyutil.strerror_OS(e))


class DebugFrame(object):

  def __init__(self, bash_source, func_name, source_name, call_spid, argv_i,
               var_i):
    # type: (Optional[str], Optional[str], Optional[str], int, int, int) -> None
    self.bash_source = bash_source

    # ONE of these is set.  func_name for 'myproc a b', and source_name for
    # 'source lib.sh'
    self.func_name = func_name
    self.source_name = source_name

    self.call_spid = call_spid 
    self.argv_i = argv_i
    self.var_i = var_i


def _InitDefaults(mem):
  # type: (Mem) -> None

  # Default value; user may unset it.
  # $ echo -n "$IFS" | python -c 'import sys;print repr(sys.stdin.read())'
  # ' \t\n'
  SetGlobalString(mem, 'IFS', split.DEFAULT_IFS)

  # NOTE: Should we put these in a name_map for Oil?
  SetGlobalString(mem, 'UID', str(posix.getuid()))
  SetGlobalString(mem, 'EUID', str(posix.geteuid()))
  SetGlobalString(mem, 'PPID', str(posix.getppid()))

  SetGlobalString(mem, 'HOSTNAME', libc.gethostname())

  # In bash, this looks like 'linux-gnu', 'linux-musl', etc.  Scripts test
  # for 'darwin' and 'freebsd' too.  They generally don't like at 'gnu' or
  # 'musl'.  We don't have that info, so just make it 'linux'.
  SetGlobalString(mem, 'OSTYPE', posix.uname()[0].lower())

  # For getopts builtin
  SetGlobalString(mem, 'OPTIND', '1')

  # For xtrace
  SetGlobalString(mem, 'PS4', '+ ')

  # bash-completion uses this.  Value copied from bash.  It doesn't integrate
  # with 'readline' yet.
  SetGlobalString(mem, 'COMP_WORDBREAKS', _READLINE_DELIMS)

  # TODO on $HOME: bash sets it if it's a login shell and not in POSIX mode!
  # if (login_shell == 1 && posixly_correct == 0)
  #   set_home_var ();


def _InitVarsFromEnv(mem, environ):
  # type: (Mem, Dict[str, str]) -> None

  # This is the way dash and bash work -- at startup, they turn everything in
  # 'environ' variable into shell variables.  Bash has an export_env
  # variable.  Dash has a loop through environ in init.c
  for n, v in iteritems(environ):
    mem.SetVar(lvalue.Named(n), value.Str(v), scope_e.GlobalOnly,
               flags=SetExport)

  # If it's not in the environment, initialize it.  This makes it easier to
  # update later in MutableOpts.

  # TODO: IFS, etc. should follow this pattern.  Maybe need a SysCall
  # interface?  self.syscall.getcwd() etc.

  val = mem.GetVar('SHELLOPTS')
  if val.tag_() == value_e.Undef:
    SetGlobalString(mem, 'SHELLOPTS', '')
  # Now make it readonly
  mem.SetVar(
      lvalue.Named('SHELLOPTS'), None, scope_e.GlobalOnly, flags=SetReadOnly)

  # Usually we inherit PWD from the parent shell.  When it's not set, we may
  # compute it.
  val = mem.GetVar('PWD')
  if val.tag_() == value_e.Undef:
    SetGlobalString(mem, 'PWD', _GetWorkingDir())
  # Now mark it exported, no matter what.  This is one of few variables
  # EXPORTED.  bash and dash both do it.  (e.g. env -i -- dash -c env)
  mem.SetVar(
      lvalue.Named('PWD'), None, scope_e.GlobalOnly, flags=SetExport)


def InitMem(mem, environ, version_str):
  # type: (Mem, Dict[str, str], str) -> None
  """
  Initialize memory with shell defaults.  Other interpreters could have
  different builtin variables.
  """
  SetGlobalString(mem, 'OIL_VERSION', version_str)
  _InitDefaults(mem)
  _InitVarsFromEnv(mem, environ)
  # MUTABLE GLOBAL that's SEPARATE from $PWD.  Used by the 'pwd' builtin, but
  # it can't be modified by users.
  val = mem.GetVar('PWD')
  # should be true since it's exported
  assert val.tag_() == value_e.Str, val
  pwd = cast(value__Str, val).s
  mem.SetPwd(pwd)


class Mem(object):
  """For storing variables.

  Mem is better than "Env" -- Env implies OS stuff.

  Callers:
    User code: assigning and evaluating variables, in command context or
      arithmetic context.
    Completion engine: for COMP_WORDS, etc.
    Builtins call it implicitly: read, cd for $PWD, $OLDPWD, etc.

  Modules: cmd_eval, word_eval, expr_eval, completion
  """
  def __init__(self, dollar0, argv, arena, debug_stack):
    # type: (str, List[str], Arena, List[DebugFrame]) -> None
    """
    Args:
      arena: for computing BASH_SOURCE, etc.  Could be factored out
    """
    # circular dep initialized out of line
    self.exec_opts = None  # type: optview.Exec

    self.dollar0 = dollar0
    self.argv_stack = [_ArgFrame(argv)]
    self.var_stack = [{}]  # type: List[Dict[str, cell]]

    self.arena = arena

    # The debug_stack isn't strictly necessary for execution.  We use it for
    # crash dumps and for 4 parallel arrays: BASH_SOURCE, FUNCNAME,
    # CALL_SOURCE, and BASH_LINENO.
    self.debug_stack = debug_stack

    self.current_spid = runtime.NO_SPID

    self.line_num = value.Str('')

    self.last_status = [0]  # type: List[int]  # a stack
    self.pipe_status = [[]]  # type: List[List[int]]  # stack
    self.last_bg_pid = -1  # Uninitialized value mutable public variable

    # Done ONCE on initialization
    self.root_pid = posix.getpid()

  def __repr__(self):
    # type: () -> str
    parts = []  # type: List[str]
    parts.append('<Mem')
    for i, frame in enumerate(self.var_stack):
      parts.append('  -- %d --' % i)
      for n, v in frame.iteritems():
        parts.append('  %s %s' % (n, v))
    parts.append('>')
    return '\n'.join(parts) + '\n'

  def SetPwd(self, pwd):
    # type: (str) -> None
    """Used by builtins."""
    self.pwd = pwd

  def InGlobalNamespace(self):
    # type: () -> bool
    """For checking that syntax options are only used at the top level."""
    return len(self.argv_stack) == 1

  def Dump(self):
    # type: () -> Tuple[Any, Any, Any]
    """Copy state before unwinding the stack."""
    if mylib.PYTHON:
      var_stack = [_DumpVarFrame(frame) for frame in self.var_stack]
      argv_stack = [frame.Dump() for frame in self.argv_stack]
      debug_stack = []  # type: List[Dict[str, Any]]
      for frame in self.debug_stack:
        d = {}  # type: Dict[str, Any]
        if frame.func_name:
          d['func_called'] = frame.func_name
        elif frame.source_name:
          d['file_sourced'] = frame.source_name
        else:
          pass  # It's a frame for FOO=bar?  Or the top one?

        d['call_spid'] = frame.call_spid
        if frame.call_spid != runtime.NO_SPID:  # first frame has this issue
          span = self.arena.GetLineSpan(frame.call_spid)
          line_id = span.line_id
          d['call_source'] = self.arena.GetLineSourceString(line_id)
          d['call_line_num'] = self.arena.GetLineNumber(line_id)
          d['call_line'] = self.arena.GetLine(line_id)

        d['argv_frame'] = frame.argv_i
        d['var_frame'] = frame.var_i
        debug_stack.append(d)

      return var_stack, argv_stack, debug_stack

    raise AssertionError()

  def SetCurrentSpanId(self, span_id):
    # type: (int) -> None
    """Set the current source location, for BASH_SOURCE, BASH_LINENO, LINENO,
    etc.

    It's also set on SimpleCommand, ShAssignment, ((, [[, etc. and used as
    a fallback when e_die() didn't set any location information.
    """
    if span_id == runtime.NO_SPID:
      # NOTE: This happened in the osh-runtime benchmark for yash.
      log('Warning: span_id undefined in SetCurrentSpanId')

      #import traceback
      #traceback.print_stack()
      return
    self.current_spid = span_id

  def CurrentSpanId(self):
    # type: () -> int
    return self.current_spid

  #
  # Status Variable Stack (for isolating $PS1 and $PS4)
  #

  def PushStatusFrame(self):
    # type: () -> None
    self.last_status.append(0)
    self.pipe_status.append([])

  def PopStatusFrame(self):
    # type: () -> None
    self.last_status.pop()
    self.pipe_status.pop()

  def LastStatus(self):
    # type: () -> int
    return self.last_status[-1]

  def PipeStatus(self):
    # type: () -> List[int]
    return self.pipe_status[-1]

  def SetLastStatus(self, x):
    # type: (int) -> None
    self.last_status[-1] = x

  def SetPipeStatus(self, x):
    # type: (List[int]) -> None
    self.pipe_status[-1] = x

  #
  # Call Stack
  #

  def PushCall(self, func_name, def_spid, argv):
    # type: (str, int, List[str]) -> None
    """For function calls."""
    self.argv_stack.append(_ArgFrame(argv))
    self.var_stack.append({})

    span = self.arena.GetLineSpan(def_spid)
    source_str = self.arena.GetLineSourceString(span.line_id)

    # bash uses this order: top of stack first.
    self._PushDebugStack(source_str, func_name, None)

  def PopCall(self):
    # type: () -> None
    self._PopDebugStack()
    self.var_stack.pop()
    self.argv_stack.pop()

  def PushSource(self, source_name, argv):
    # type: (str, List[str]) -> None
    """For 'source foo.sh 1 2 3."""
    if len(argv):
      self.argv_stack.append(_ArgFrame(argv))
    # Match bash's behavior for ${FUNCNAME[@]}.  But it would be nicer to add
    # the name of the script here?
    self._PushDebugStack(source_name, None, source_name)

  def PopSource(self, argv):
    # type: (List[str]) -> None
    self._PopDebugStack()
    if len(argv):
      self.argv_stack.pop()

  def PushTemp(self):
    # type: () -> None
    """For the temporary scope in 'FOO=bar BAR=baz echo'."""
    # We don't want the 'read' builtin to write to this frame!
    self.var_stack.append({})
    self._PushDebugStack(None, None, None)

  def PopTemp(self):
    # type: () -> None
    self._PopDebugStack()
    self.var_stack.pop()

  def TopNamespace(self):
    # type: () -> Dict[str, runtime_asdl.cell]
    """For evalblock()."""
    return self.var_stack[-1]

  def _PushDebugStack(self, bash_source, func_name, source_name):
    # type: (Optional[str], Optional[str], Optional[str]) -> None
    # self.current_spid is set before every SimpleCommand, ShAssignment, [[, ((,
    # etc.  Function calls and 'source' are both SimpleCommand.

    # These integers are handles/pointers, for use in CrashDumper.
    argv_i = len(self.argv_stack) - 1
    var_i = len(self.var_stack) - 1

    # The stack is a 5-tuple, where func_name and source_name are optional.  If
    # both are unset, then it's a "temp frame".
    self.debug_stack.append(
        DebugFrame(bash_source, func_name, source_name, self.current_spid, argv_i, var_i)
    )

  def _PopDebugStack(self):
    # type: () -> None
    self.debug_stack.pop()

  #
  # Argv
  #

  def Shift(self, n):
    # type: (int) -> int
    frame = self.argv_stack[-1]
    num_args = len(frame.argv)

    if (frame.num_shifted + n) <= num_args:
      frame.num_shifted += n
      return 0  # success
    else:
      return 1  # silent error

  def GetArg0(self):
    # type: () -> value__Str
    """Like GetArgNum(0) but with a more specific type."""
    return value.Str(self.dollar0)

  def GetArgNum(self, arg_num):
    # type: (int) -> value_t
    if arg_num == 0:
      return value.Str(self.dollar0)

    return self.argv_stack[-1].GetArgNum(arg_num)

  def GetArgv(self):
    # type: () -> List[str]
    """For $* and $@."""
    return self.argv_stack[-1].GetArgv()

  def SetArgv(self, argv):
    # type: (List[str]) -> None
    """For set -- 1 2 3."""
    # from set -- 1 2 3
    self.argv_stack[-1].SetArgv(argv)

  #
  # Special Vars
  #

  def GetSpecialVar(self, op_id):
    # type: (int) -> value_t
    if op_id == Id.VSub_Bang:  # $!
      n = self.last_bg_pid
      if n == -1:
        return value.Undef()  # could be an error

    elif op_id == Id.VSub_QMark:  # $?
      # External commands need WIFEXITED test.  What about subshells?
      n = self.last_status[-1]

    elif op_id == Id.VSub_Pound:  # $#
      n = self.argv_stack[-1].GetNumArgs()

    elif op_id == Id.VSub_Dollar:  # $$
      n = self.root_pid

    else:
      raise NotImplementedError(op_id)

    return value.Str(str(n))

  #
  # Named Vars
  #

  def _ResolveNameOnly(self, name, lookup_mode):
    # type: (str, scope_t) -> Tuple[Optional[cell], Dict[str, cell]]
    """Helper for getting and setting variable.

    Args:
      name: the variable name
      lookup_mode: scope_e

    Returns:
      cell: The cell corresponding to looking up 'name' with the given mode, or
        None if it's not found.
      name_map: The name_map it should be set to or deleted from.
    """
    if lookup_mode == scope_e.Dynamic:
      for i in xrange(len(self.var_stack) - 1, -1, -1):
        name_map = self.var_stack[i]
        if name in name_map:
          cell = name_map[name]
          return cell, name_map
      no_cell = None  # type: Optional[runtime_asdl.cell]
      return no_cell, self.var_stack[0]  # set in global name_map

    elif lookup_mode == scope_e.LocalOnly:
      name_map = self.var_stack[-1]
      return name_map.get(name), name_map

    elif lookup_mode == scope_e.GlobalOnly:
      name_map = self.var_stack[0]
      return name_map.get(name), name_map

    elif lookup_mode == scope_e.LocalOrGlobal:
      # Local
      name_map = self.var_stack[-1]
      cell = name_map.get(name)
      if cell:
        return cell, name_map

      # Global
      name_map = self.var_stack[0]
      return name_map.get(name), name_map

    else:
      raise AssertionError()

  def _ResolveNameOrRef(self, name, lookup_mode):
    # type: (str, scope_t) -> Tuple[Optional[cell], Dict[str, cell], str]
    """Look up a cell and namespace, but respect the nameref flag."""
    cell, name_map = self._ResolveNameOnly(name, lookup_mode)

    if not cell or not cell.nameref:
      return cell, name_map, name  # not a nameref

    val = cell.val
    UP_val = val
    with tagswitch(val) as case:
      if case(value_e.Undef):
        # This is 'local -n undef_ref', which is kind of useless, because the
        # more common idiom is 'local -n ref=$1'.  Note that you can mutate
        # references themselves with local -n ref=new.
        if self.exec_opts.strict_nameref():
          e_die('nameref %r is undefined', name)
        else:
          return cell, name_map, name  # fallback

      elif case(value_e.Str):
        val = cast(value__Str, UP_val)
        new_name = val.s

      else:
        # SetVar() protects the invariant that nameref is Undef or Str
        raise AssertionError(val.tag_())

    if not match.IsValidVarName(new_name):
      # e.g. '#' or '1' or ''
      if self.exec_opts.strict_nameref():
        e_die('nameref %r contains invalid variable name %r', name, new_name)
      else:
        # Bash has this odd behavior of clearing the nameref bit when
        # ref=#invalid#.  strict_nameref avoids it.
        cell.nameref = False
        return cell, name_map, name  # fallback

    # Old "use" Check for circular namerefs.
    #if ref_trail is None:
    #  ref_trail = [name]
    #else:
    #  if new_name in ref_trail:
    #    e_die('Circular nameref %s', ref_trail)
    #ref_trail.append(new_name)

    # You could have a "trail" parameter here?
    cell, name_map, cell_name = self._ResolveNameOrRef(new_name, lookup_mode)
    return cell, name_map, cell_name

  def IsAssocArray(self, name, lookup_mode):
    # type: (str, scope_t) -> bool
    """Returns whether a name resolve to a cell with an associative array.
    
    We need to know this to evaluate the index expression properly -- should it
    be coerced to an integer or not?
    """
    cell, _, _ = self._ResolveNameOrRef(name, lookup_mode)
    if cell:
      if cell.val.tag_() == value_e.AssocArray:  # foo=([key]=value)
        return True
    return False

  def _CheckOilKeyword(self, keyword_id, name, cell):
    # type: (Id_t, str, Optional[cell]) -> None
    """Check that 'var' and setvar/set are used correctly.

    NOTE: These are dynamic checks, but the syntactic difference between
    definition and mutation will help translate the Oil subset of OSH to static
    languages.
    """
    if cell and keyword_id in (Id.KW_Var, Id.KW_Const):
      # TODO: Point at the ORIGINAL declaration!
      e_die("%r has already been declared", name)

    if cell is None and keyword_id in (Id.KW_Set, Id.KW_SetLocal,
                                       Id.KW_SetGlobal):
      e_die("%r hasn't been declared", name)

  def _DisallowNamerefCycle(self, name, ref_trail):
    # type: (str, List[str]) -> None
    """Recursively resolve names until the trail ends or a cycle is detected.

    Note: we're using dynamic scope because that's the most general.  This
    could produce false positives if the actual lookup mode is different
    (LocalOnly), but those should be rare and easily worked around.
    
    The other possibility is to do it during _ResolveNameOrRef, but that delays
    tne error.
    """
    cell, _ = self._ResolveNameOnly(name, scope_e.Dynamic)

    if not cell or not cell.nameref:
      return

    val = cell.val
    if val.tag_() != value_e.Str:
      return

    str_val = cast(value__Str, val)
    new_name = str_val.s

    if new_name in ref_trail:
      e_die('nameref cycle: %s', ' -> '.join(ref_trail))
    ref_trail.append(new_name)

    self._DisallowNamerefCycle(new_name, ref_trail)

  def SetVar(self, lval, val, lookup_mode, flags=0):
    # type: (lvalue_t, value_t, scope_t, int) -> None
    """
    Args:
      lval: lvalue
      val: value, or None if only changing flags
      lookup_mode:
        Local | Global | Dynamic - for builtins, PWD, etc.
      flags: bit mask of set/clear flags

      NOTE: in bash, PWD=/ changes the directory.  But not in dash.
    """
    keyword_id = flags >> 8  # opposite of _PackFlags
    # STRICTNESS / SANENESS:
    #
    # 1) Don't create arrays automatically, e.g. a[1000]=x
    # 2) Never change types?  yeah I think that's a good idea, at least for oil
    # (not sh, for compatibility).  set -o strict_types or something.  That
    # means arrays have to be initialized with let arr = [], which is fine.
    # This helps with stuff like IFS.  It starts off as a string, and assigning
    # it to a list is an error.  I guess you will have to turn this no for
    # bash?
    #
    # TODO:
    # - COMPUTED_VARS can't be set
    # - What about PWD / OLDPWD / UID / EUID ?  You can simply make them
    # readonly.
    # - $PS1 and $PS4 should be PARSED when they are set, to avoid the error on use
    # - Other validity: $HOME could be checked for existence

    UP_lval = lval
    with tagswitch(lval) as case:
      if case(lvalue_e.Named):
        lval = cast(lvalue__Named, UP_lval)

        if flags & SetNameref or flags & ClearNameref:
          # declare -n ref=x  # refers to the ref itself
          cell, name_map = self._ResolveNameOnly(lval.name, lookup_mode)
          cell_name = lval.name
        else:
          # ref=x  # mutates THROUGH the reference
          cell, name_map, cell_name = self._ResolveNameOrRef(lval.name, lookup_mode)

        self._CheckOilKeyword(keyword_id, lval.name, cell)
        if cell:
          # Clear before checking readonly bit.
          # NOTE: Could be cell.flags &= flag_clear_mask 
          if flags & ClearExport:
            cell.exported = False
          if flags & ClearReadOnly:
            cell.readonly = False
          if flags & ClearNameref:
            cell.nameref = False

          if val is not None:  # e.g. declare -rx existing
            if cell.readonly:
              # TODO: error context
              e_die("Can't assign to readonly value %r", lval.name)
            cell.val = val  # CHANGE VAL

          # NOTE: Could be cell.flags |= flag_set_mask 
          if flags & SetExport:
            cell.exported = True
          if flags & SetReadOnly:
            cell.readonly = True
          if flags & SetNameref:
            cell.nameref = True

        else:
          if val is None:  # declare -rx nonexistent
            # set -o nounset; local foo; echo $foo  # It's still undefined!
            val = value.Undef()  # export foo, readonly foo

          cell = runtime_asdl.cell(bool(flags & SetExport),
                                   bool(flags & SetReadOnly),
                                   bool(flags & SetNameref),
                                   val)
          name_map[cell_name] = cell

        # Maintain invariant that only strings and undefined cells can be
        # exported.
        assert cell.val is not None, cell

        if cell.val.tag_() not in (value_e.Undef, value_e.Str):
          if cell.exported:
            e_die("Only strings can be exported")  # TODO: error context
          if cell.nameref:
            e_die("nameref must be a string")

        # Note: we check for circular namerefs on every definition, like mksh.
        if cell.nameref:
          ref_trail = []  # type: List[str]
          self._DisallowNamerefCycle(cell_name, ref_trail)

      elif case(lvalue_e.Indexed):
        lval = cast(lvalue__Indexed, UP_lval)
        assert isinstance(lval.index, int), lval
        # There is no syntax 'declare a[x]'
        assert val is not None, val
        assert val.tag_() == value_e.Str, val
        rval = cast(value__Str, val)

        # TODO: All paths should have this?  We can get here by a[x]=1 or
        # (( a[ x ] = 1 )).  Maybe we should make them different?
        left_spid = lval.spids[0] if lval.spids else runtime.NO_SPID

        # bash/mksh have annoying behavior of letting you do LHS assignment to
        # Undef, which then turns into an INDEXED array.  (Undef means that set
        # -o nounset fails.)
        cell, name_map, _ = self._ResolveNameOrRef(lval.name, lookup_mode)
        self._CheckOilKeyword(keyword_id, lval.name, cell)
        if not cell:
          self._BindNewArrayWithEntry(name_map, lval, rval, flags)
          return

        if cell.readonly:
          e_die("Can't assign to readonly array", span_id=left_spid)

        UP_cell_val = cell.val
        # undef[0]=y is allowed
        with tagswitch(UP_cell_val) as case2:
          if case2(value_e.Undef):
            self._BindNewArrayWithEntry(name_map, lval, rval, flags)
            return

          elif case2(value_e.Str):
            # s=x
            # s[1]=y  # invalid
            e_die("Can't assign to items in a string", span_id=left_spid)

          elif case2(value_e.MaybeStrArray):
            cell_val = cast(value__MaybeStrArray, UP_cell_val)
            strs = cell_val.strs
            try:
              strs[lval.index] = rval.s
            except IndexError:
              # Fill it in with None.  It could look like this:
              # ['1', 2, 3, None, None, '4', None]
              # Then ${#a[@]} counts the entries that are not None.
              #
              # TODO: strict_array for Oil arrays won't auto-fill.
              n = lval.index - len(strs) + 1
              for i in xrange(n):
                strs.append(None)
              strs[lval.index] = rval.s
            return

        # This could be an object, eggex object, etc.  It won't be
        # AssocArray shouldn because we query IsAssocArray before evaluating
        # sh_lhs_expr.  Could conslidate with s[i] case above
        e_die("Value of type %s can't be indexed",
              ui.ValType(cell.val), span_id=left_spid)

      elif case(lvalue_e.Keyed):
        lval = cast(lvalue__Keyed, UP_lval)
        # There is no syntax 'declare A["x"]'
        assert val is not None, val
        assert val.tag_() == value_e.Str, val
        rval = cast(value__Str, val)

        left_spid = lval.spids[0] if lval.spids else runtime.NO_SPID

        cell, name_map, _ = self._ResolveNameOrRef(lval.name, lookup_mode)
        self._CheckOilKeyword(keyword_id, lval.name, cell)
        if cell.readonly:
          e_die("Can't assign to readonly associative array", span_id=left_spid)

        # We already looked it up before making the lvalue
        assert cell.val.tag == value_e.AssocArray, cell
        cell_val2 = cast(value__AssocArray, cell.val)

        cell_val2.d[lval.key] = rval.s

      else:
        raise AssertionError(lval.tag_())

  def _BindNewArrayWithEntry(self, name_map, lval, val, flags):
    # type: (Dict[str, cell], lvalue__Indexed, value__Str, int) -> None
    """Fill 'name_map' with a new indexed array entry."""
    no_str = None  # type: Optional[str]
    items = [no_str] * lval.index
    items.append(val.s)
    new_value = value.MaybeStrArray(items)

    # arrays can't be exported; can't have AssocArray flag
    readonly = bool(flags & SetReadOnly)
    name_map[lval.name] = runtime_asdl.cell(False, readonly, False, new_value)

  def InternalSetGlobal(self, name, new_val):
    # type: (str, value_t) -> None
    """For setting read-only globals internally.

    Args:
      name: string (not Lhs)
      new_val: value

    The variable must already exist.

    Use case: SHELLOPTS.
    """
    cell = self.var_stack[0][name]
    cell.val = new_val

  def GetVar(self, name, lookup_mode=scope_e.Dynamic):
    # type: (str, scope_t) -> value_t
    assert isinstance(name, str), name

    # TODO: Short-circuit down to _ResolveNameOrRef by doing a single hash
    # lookup:
    # COMPUTED_VARS = {'PIPESTATUS': 1, 'FUNCNAME': 1, ...}
    # if name not in COMPUTED_VARS: ...

    if name == 'ARGV':
      # TODO:
      # - Reuse the MaybeStrArray?
      # - @@ could be an alias for ARGV (in command mode, but not expr mode)
      return value.MaybeStrArray(self.GetArgv())

    if name == 'PIPESTATUS':
      return value.MaybeStrArray([str(i) for i in self.pipe_status[-1]])

    # Do lookup of system globals before looking at user variables.  Note: we
    # could optimize this at compile-time like $?.  That would break
    # ${!varref}, but it's already broken for $?.
    if name == 'FUNCNAME':
      # bash wants it in reverse order.  This is a little inefficient but we're
      # not depending on deque().
      strs = []  # type: List[str]
      for frame in reversed(self.debug_stack):
        if frame.func_name:
          strs.append(frame.func_name)
        if frame.source_name:
          strs.append('source')  # bash doesn't tell you the filename.
        # Temp stacks are ignored
      return value.MaybeStrArray(strs)  # TODO: Reuse this object too?

    # This isn't the call source, it's the source of the function DEFINITION
    # (or the sourced # file itself).
    if name == 'BASH_SOURCE':
      strs = []
      for frame in reversed(self.debug_stack):
        if frame.bash_source:
          strs.append(frame.bash_source)
      return value.MaybeStrArray(strs)  # TODO: Reuse this object too?

    # This is how bash source SHOULD be defined, but it's not!
    if 0:
      if name == 'CALL_SOURCE':
        strs = []
        for frame in reversed(self.debug_stack):
          # should only happen for the first entry
          if frame.call_spid == runtime.NO_SPID:
            continue
          if frame.call_spid == -2:
            strs.append('-')  # Bash does this to line up with main?
            continue
          span = self.arena.GetLineSpan(frame.call_spid)
          source_str = self.arena.GetLineSourceString(span.line_id)
          strs.append(source_str)
        return value.MaybeStrArray(strs)  # TODO: Reuse this object too?

    if name == 'BASH_LINENO':
      strs = []
      for frame in reversed(self.debug_stack):
        # should only happen for the first entry
        if frame.call_spid == runtime.NO_SPID:
          continue
        if frame.call_spid == LINE_ZERO:
          strs.append('0')  # Bash does this to line up with main?
          continue
        span = self.arena.GetLineSpan(frame.call_spid)
        line_num = self.arena.GetLineNumber(span.line_id)
        strs.append(str(line_num))
      return value.MaybeStrArray(strs)  # TODO: Reuse this object too?

    if name == 'LINENO':
      assert self.current_spid != -1, self.current_spid
      span = self.arena.GetLineSpan(self.current_spid)
      # TODO: maybe use interned GetLineNumStr?
      self.line_num.s = str(self.arena.GetLineNumber(span.line_id))
      return self.line_num

    cell, _, _ = self._ResolveNameOrRef(name, lookup_mode)

    if cell:
      return cell.val

    return value.Undef()

  def GetCell(self, name, lookup_mode=scope_e.Dynamic):
    # type: (str, scope_t) -> cell
    """For the 'repr' builtin."""
    cell, _ = self._ResolveNameOnly(name, lookup_mode)
    return cell

  def Unset(self, lval, lookup_mode, strict):
    # type: (lvalue_t, scope_t, bool) -> bool
    """
    Returns:
      Whether the cell was found.
    """
    # TODO: Refactor lvalue type to avoid this
    UP_lval = lval

    with tagswitch(lval) as case:
      if case(lvalue_e.Named):  # unset x
        lval = cast(lvalue__Named, UP_lval)
        var_name = lval.name
      elif case(lvalue_e.Indexed):  # unset 'a[1]'
        lval = cast(lvalue__Indexed, UP_lval)
        var_name = lval.name
      elif case(lvalue_e.Keyed):  # unset 'A["K"]'
        lval = cast(lvalue__Keyed, UP_lval)
        var_name = lval.name
      else:
        raise AssertionError()

    cell, name_map, cell_name = self._ResolveNameOrRef(var_name, lookup_mode)
    if not cell:
      return False  # 'unset' builtin falls back on functions
    if cell.readonly:
      raise error.Runtime("Can't unset readonly variable %r" % var_name)

    with tagswitch(lval) as case:
      if case(lvalue_e.Named):  # unset x
        name_map[cell_name].val = value.Undef()
        cell.exported = False
        # This should never happen because we do recursive lookups of namerefs.
        assert not cell.nameref, cell

      elif case(lvalue_e.Indexed):  # unset 'a[1]'
        lval = cast(lvalue__Indexed, UP_lval)

        val = cell.val
        UP_val = val
        if val.tag_() != value_e.MaybeStrArray:
          raise error.Runtime("%r isn't an array" % var_name)

        val = cast(value__MaybeStrArray, UP_val)
        # Note: Setting an entry to None and shifting entries are pretty
        # much the same in shell.
        try:
          val.strs[lval.index] = None
        except IndexError:
          # note: we could have unset --strict for this case?
          # Oil may make it strict
          pass

      elif case(lvalue_e.Keyed):  # unset 'A["K"]'
        lval = cast(lvalue__Keyed, UP_lval)

        val = cell.val
        UP_val = val

        # note: never happens because of mem.IsAssocArray test for lvalue.Keyed
        #if val.tag_() != value_e.AssocArray:
        #  raise error.Runtime("%r isn't an associative array" % lval.name)

        val = cast(value__AssocArray, UP_val)
        try:
          del val.d[lval.key]
        except KeyError:
          # note: we could have unset --strict for this case?
          pass

      else:
        raise AssertionError(lval)

    return True

  def ClearFlag(self, name, flag, lookup_mode):
    # type: (str, int, scope_t) -> bool
    """Used for export -n.

    We don't use SetVar() because even if rval is None, it will make an Undef
    value in a scope.
    """
    cell, name_map = self._ResolveNameOnly(name, lookup_mode)
    if cell:
      if flag & ClearExport:
        cell.exported = False
      if flag & ClearNameref:
        cell.nameref = False
      return True
    else:
      return False

  def GetExported(self):
    # type: () -> Dict[str, str]
    """Get all the variables that are marked exported."""
    # TODO: This is run on every SimpleCommand.  Should we have a dirty flag?
    # We have to notice these things:
    # - If an exported variable is changed.
    # - If the set of exported variables changes.

    exported = {}  # type: Dict[str, str]
    # Search from globals up.  Names higher on the stack will overwrite names
    # lower on the stack.
    for scope in self.var_stack:
      for name, cell in iteritems(scope):
        # TODO: Disallow exporting at assignment time.  If an exported Str is
        # changed to MaybeStrArray, also clear its 'exported' flag.
        if cell.exported and cell.val.tag_() == value_e.Str:
          val = cast(value__Str, cell.val)
          exported[name] = val.s
    return exported

  def VarNames(self):
    # type: () -> List[str]
    """For internal OSH completion and compgen -A variable.

    NOTE: We could also add $? $$ etc.?
    """
    ret = []  # type: List[str]
    # Look up the stack, yielding all variables.  Bash seems to do this.
    for scope in self.var_stack:
      for name in scope:
        ret.append(name)
    return ret

  def VarNamesStartingWith(self, prefix):
    # type: (str) -> List[str]
    """For ${!prefix@}"""
    # Look up the stack, yielding all variables.  Bash seems to do this.
    names = []  # type: List[str]
    for scope in self.var_stack:
      for name in scope:
        if name.startswith(prefix):
          names.append(name)
    return names

  def GetAllVars(self):
    # type: () -> Dict[str, str]
    """Get all variables and their values, for 'set' builtin. """
    result = {}  # type: Dict[str, str]
    for scope in self.var_stack:
      for name, cell in iteritems(scope):
        # TODO: Show other types?
        val = cell.val
        if val.tag_() == value_e.Str:
          str_val = cast(value__Str, val)
          result[name] = str_val.s
    return result

  def GetAllCells(self, lookup_mode=scope_e.Dynamic):
    # type: (scope_t) -> Dict[str, cell]
    """Get all variables and their values, for 'set' builtin. """
    result = {}  # type: Dict[str, cell]

    if lookup_mode == scope_e.Dynamic:
      scopes = self.var_stack
    elif lookup_mode == scope_e.LocalOnly:
      scopes = self.var_stack[-1:]
    elif lookup_mode == scope_e.GlobalOnly:
      scopes = self.var_stack[0:1]
    elif lookup_mode == scope_e.LocalOrGlobal:
      scopes = self.var_stack[0:1]
      if len(self.var_stack) > 1:
        scopes.append(self.var_stack[-1])
    else:
      raise AssertionError()

    for scope in scopes:
      for name, cell in iteritems(scope):
        result[name] = cell
    return result

  def IsGlobalScope(self):
    # type: () -> bool
    return len(self.var_stack) == 1


def SetLocalString(mem, name, s):
  # type: (Mem, str, str) -> None
  """Set a local string.

  Used for:
  1) for loop iteration variables
  2) temporary environments like FOO=bar BAR=$FOO cmd,
  3) read builtin
  """
  assert isinstance(s, str)
  mem.SetVar(lvalue.Named(name), value.Str(s), scope_e.LocalOnly)


def SetStringDynamic(mem, name, s):
  # type: (Mem, str, str) -> None
  """Set a string by looking up the stack.

  Used for getopts.
  """
  assert isinstance(s, str)
  mem.SetVar(lvalue.Named(name), value.Str(s), scope_e.Dynamic)


def SetArrayDynamic(mem, name, a):
  # type: (Mem, str, List[str]) -> None
  """Set an array by looking up the stack.

  Used for _init_completion.
  """
  assert isinstance(a, list)
  mem.SetVar(lvalue.Named(name), value.MaybeStrArray(a), scope_e.Dynamic)


def SetGlobalString(mem, name, s):
  # type: (Mem, str, str) -> None
  """Helper for completion, etc."""
  assert isinstance(s, str)
  val = value.Str(s)
  mem.SetVar(lvalue.Named(name), val, scope_e.GlobalOnly)


def SetGlobalArray(mem, name, a):
  # type: (Mem, str, List[str]) -> None
  """Helper for completion."""
  assert isinstance(a, list)
  mem.SetVar(lvalue.Named(name), value.MaybeStrArray(a), scope_e.GlobalOnly)


def SetLocalArray(mem, name, a):
  # type: (Mem, str, List[str]) -> None
  """Helper for completion."""
  assert isinstance(a, list)
  mem.SetVar(lvalue.Named(name), value.MaybeStrArray(a), scope_e.LocalOnly)


def ExportGlobalString(mem, name, s):
  # type: (Mem, str, str) -> None
  """Helper for completion, $PWD, $OLDPWD, etc."""
  assert isinstance(s, str)
  val = value.Str(s)
  mem.SetVar(lvalue.Named(name), val, scope_e.GlobalOnly, flags=SetExport)


def GetGlobal(mem, name):
  # type: (Mem, str) -> value_t
  assert isinstance(name, str), name
  return mem.GetVar(name, scope_e.GlobalOnly)
