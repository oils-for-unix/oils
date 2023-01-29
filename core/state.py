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

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.runtime_asdl import (
    value, value_e, value_t, value__Str, value__MaybeStrArray, value__AssocArray,
    lvalue, lvalue_e, lvalue_t, lvalue__Named, lvalue__Indexed, lvalue__Keyed,
    scope_e, scope_t, hay_node
)
from _devbuild.gen.syntax_asdl import loc
from _devbuild.gen.types_asdl import opt_group_i
from _devbuild.gen import runtime_asdl  # for cell
from asdl import runtime
from core import error
from core.pyerror import e_usage, e_die, log
from core import pyos
from core import pyutil
from core import optview
from core import ui
from frontend import consts
from frontend import match
from mycpp import mylib
from mycpp.mylib import print_stderr, tagswitch, iteritems, NewDict
from osh import split
from pylib import os_path
from pylib import path_stat

import libc
import posix_ as posix
from posix_ import X_OK  # translated directly to C macro

from typing import Tuple, List, Dict, Optional, Any, cast, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.option_asdl import option_t
  from _devbuild.gen.runtime_asdl import cell, Proc
  from core import alloc
  from osh import sh_expr_eval


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
    val = self.mem.GetValue('PATH')
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
        found = posix.access(full_path, X_OK)
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
    mylib.dict_erase(self.cache, name)

  def ClearCache(self):
    # type: () -> None
    """For hash -r."""
    self.cache.clear()

  def CachedCommands(self):
    # type: () -> List[str]
    return self.cache.values()


class ctx_Source(object):
  """For source builtin."""

  def __init__(self, mem, source_name, argv):
    # type: (Mem, str, List[str]) -> None
    mem.PushSource(source_name, argv)
    self.mem = mem
    self.argv = argv

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.mem.PopSource(self.argv)


class ctx_Option(object):
  """shopt --unset errexit { false } """
  def __init__(self, mutable_opts, opt_nums, b):
    # type: (MutableOpts, List[int], bool) -> None
    for opt_num in opt_nums:
      mutable_opts.Push(opt_num, b)
      if opt_num == option_i.errexit:
        mutable_opts.errexit_disabled_spid.append(runtime.NO_SPID)  # it wasn't disabled

    self.mutable_opts = mutable_opts
    self.opt_nums = opt_nums

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    for opt_num in self.opt_nums:  # don't bother to do it in reverse order
      if opt_num == option_i.errexit:
        self.mutable_opts.errexit_disabled_spid.pop()
      self.mutable_opts.Pop(opt_num)


class ctx_AssignBuiltin(object):
  """local x=$(false) is disallowed."""
  def __init__(self, mutable_opts):
    # type: (MutableOpts) -> None
    self.strict = False
    if mutable_opts.Get(option_i.strict_errexit):
      mutable_opts.Push(option_i.allow_csub_psub, False)
      self.strict = True

    self.mutable_opts = mutable_opts

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    if self.strict:
      self.mutable_opts.Pop(option_i.allow_csub_psub)


class ctx_OilExpr(object):
  """ Command sub must fail in 'mystring' ++ $(false) """
  def __init__(self, mutable_opts):
    # type: (MutableOpts) -> None
    mutable_opts.Push(option_i.command_sub_errexit, True)
    self.mutable_opts = mutable_opts

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.mutable_opts.Pop(option_i.command_sub_errexit)


class ctx_ErrExit(object):
  """Manages the errexit setting.

  - The user can change it with builtin 'set' at any point in the code.
  - These constructs implicitly disable 'errexit':
    - if / while / until conditions
    - ! (part of pipeline)
    - && ||
  """
  def __init__(self, mutable_opts, b, span_id):
    # type: (MutableOpts, bool, int) -> None

    # If we're disabling it, we need a span ID.  If not, then we should NOT
    # have one.
    assert b == (span_id == runtime.NO_SPID)

    mutable_opts.Push(option_i.errexit, b)
    mutable_opts.errexit_disabled_spid.append(span_id)

    self.strict = False
    if mutable_opts.Get(option_i.strict_errexit):
      mutable_opts.Push(option_i.allow_csub_psub, False)
      self.strict = True

    self.mutable_opts = mutable_opts

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.mutable_opts.errexit_disabled_spid.pop()
    self.mutable_opts.Pop(option_i.errexit)

    if self.strict:
      self.mutable_opts.Pop(option_i.allow_csub_psub)


class ctx_HayNode(object):
  """ haynode builtin makes new names in the tree visible """
  def __init__(self, hay_state, hay_name):
    # type: (Hay, Optional[str]) -> None
    #log('pairs %s', pairs)
    self.hay_state = hay_state
    self.hay_state.Push(hay_name)

  def __enter__(self):
    # type: () -> None
    return

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.hay_state.Pop()


class ctx_HayEval(object):
  """
  - Turn on shopt oil:all and _running_hay
  - Disallow recursive 'hay eval'
  - Ensure result is isolated for 'hay eval :result'

  More leakage:

  External:
  - execute programs (ext_prog)
  - redirect
  - pipelines, subshell, & etc?
    - do you have to put _running_hay() checks everywhere?

  Internal:

  - state.Mem()
    - should we at least PushTemp()?
    - But then they can do setglobal
  - Option state

  - Disallow all builtins except echo/write/printf?
    - maybe could do that at the top level
    - source builtin, read builtin
    - cd / pushd / popd
    - trap -- hm yeah this one is bad

  - procs?  Not strictly necessary
    - you should be able to define them, but not call the user ...

  """
  def __init__(self, hay_state, mutable_opts, mem):
    # type: (Hay, MutableOpts, Mem) -> None
    self.hay_state = hay_state
    self.mutable_opts = mutable_opts
    self.mem = mem

    if mutable_opts.Get(option_i._running_hay):
      # This blames the right 'hay' location
      e_die("Recursive 'hay eval' not allowed")

    for opt_num in consts.OIL_ALL:
      mutable_opts.Push(opt_num, True)
    mutable_opts.Push(option_i._running_hay, True)

    self.hay_state.PushEval()
    self.mem.PushTemp()

  def __enter__(self):
    # type: () -> None
    return

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None

    self.mem.PopTemp()
    self.hay_state.PopEval()

    self.mutable_opts.Pop(option_i._running_hay)
    for opt_num in consts.OIL_ALL:
      self.mutable_opts.Pop(opt_num)


class Hay(object):
  """State for DSLs."""

  def __init__(self):
    # type: () -> None
    self.root_defs = hay_node()
    self.cur_defs = self.root_defs  # Same as ClearDefs()
    self.def_stack = [self.root_defs]

    node = self._MakeOutputNode()
    self.result_stack = [node]  # type: List[Dict[str, Any]]
    self.output = None  # type: Dict[str, Any]

  def _MakeOutputNode(self):
    # type: () -> Dict[str, Any]
    d = NewDict()
    d['source'] = None  
    d['children'] = []
    return d

  def PushEval(self):
    # type: () -> None

    # remove previous results
    node = self._MakeOutputNode()
    self.result_stack = [node]

    self.output = None  # remove last reuslt

  def PopEval(self):
    # type: () -> None

    # Save the result
    self.output = self.result_stack[0]

    # Clear results
    node = self._MakeOutputNode()
    self.result_stack = [node]

  if mylib.PYTHON:  # TODO: hay results should be a value_t tree

    def AppendResult(self, d):
      # type: (Dict[str, Any]) -> None
      """Called by haynode builtin."""
      self.result_stack[-1]['children'].append(d)

    def Result(self):
      # type: () -> Dict[str, Any]
      """ Called by hay eval and eval_hay() """
      return self.output

    def HayRegister(self):
      # type: () -> Dict[str, Any]
      """ Called by _hay() function """
      return self.result_stack[0]

  def Resolve(self, first_word):
    # type: (str) -> bool
    return first_word in self.cur_defs.children

  def DefinePath(self, path):
    # type: (List[str]) -> None
    """Fill a tree from the given path."""
    current = self.root_defs
    for name in path:
      if name not in current.children:
        current.children[name] = hay_node()
      current = current.children[name]

  def Reset(self):
    # type: () -> None

    # reset definitions
    self.root_defs = hay_node()
    self.cur_defs = self.root_defs

    # reset output
    self.PopEval()

  def Push(self, hay_name):
    # type: (Optional[str]) -> None
    """
    package cppunit { }   # pushes a namespace
    haynode package cppunit { }   # just assumes every TYPE 'package' is valid
    """
    if mylib.PYTHON:
      top = self.result_stack[-1]
      self.result_stack.append(top['children'][-1])

    #log('> PUSH')
    if hay_name is None:
      self.def_stack.append(self.cur_defs)  # no-op
    else:
      # Caller should ensure this
      assert hay_name in self.cur_defs.children, hay_name

      self.cur_defs = self.cur_defs.children[hay_name]
      self.def_stack.append(self.cur_defs)

  def Pop(self):
    # type: () -> None
    self.def_stack.pop()
    self.cur_defs = self.def_stack[-1]

    if mylib.PYTHON:
      self.result_stack.pop()


class OptHook(object):
  """Interface for option hooks."""

  def __init__(self):
    # type: () -> None
    """Empty constructor for mycpp."""
    pass

  def OnChange(self, opt0_array, opt_name, b):
    # type: (List[bool], str, bool) -> bool
    """This method is called whenever an option is changed.

    Returns success or failure.
    """
    return True


def InitOpts():
  # type: () -> List[bool]

  opt0_array = [False] * option_i.ARRAY_SIZE
  for opt_num in consts.DEFAULT_TRUE:
    opt0_array[opt_num] = True
  return opt0_array


def MakeOpts(mem, opt_hook):
  # type: (Mem, OptHook) -> Tuple[optview.Parse, optview.Exec, MutableOpts]

  # Unusual representation: opt0_array + opt_stacks.  For two features:
  # 
  # - POSIX errexit disable semantics
  # - Oil's shopt --set nullglob { ... }
  #
  # We could do it with a single List of stacks.  But because shopt --set
  # random_option { ... } is very uncommon, we optimize and store the ZERO
  # element of the stack in a flat array opt0_array (default False), and then
  # the rest in opt_stacks, where the value could be None.  By allowing the
  # None value, we save ~50 or so list objects in the common case.
  
  opt0_array = InitOpts()
  # Overrides, including errexit
  no_stack = None  # type: List[bool]  # for mycpp
  opt_stacks = [no_stack] * option_i.ARRAY_SIZE  # type: List[List[bool]]

  parse_opts = optview.Parse(opt0_array, opt_stacks)
  exec_opts = optview.Exec(opt0_array, opt_stacks)
  mutable_opts = MutableOpts(mem, opt0_array, opt_stacks, opt_hook)

  return parse_opts, exec_opts, mutable_opts


def _SetGroup(opt0_array, opt_nums, b):
  # type: (List[bool], List[int], bool) -> None
  for opt_num in opt_nums:
    b2 = not b if opt_num in consts.DEFAULT_TRUE else b
    opt0_array[opt_num] = b2


def MakeOilOpts():
  # type: () -> optview.Parse
  opt0_array = InitOpts()
  _SetGroup(opt0_array, consts.OIL_ALL, True)

  no_stack = None  # type: List[bool]
  opt_stacks = [no_stack] * option_i.ARRAY_SIZE  # type: List[List[bool]]

  parse_opts = optview.Parse(opt0_array, opt_stacks)
  return parse_opts


def _AnyOptionNum(opt_name):
  # type: (str) -> option_t
  opt_num = consts.OptionNum(opt_name)
  if opt_num == 0:
    e_usage('got invalid option %r' % opt_name)

  # Note: we relaxed this for Oil so we can do 'shopt --unset errexit' consistently
  #if opt_num not in consts.SHOPT_OPTION_NUMS:
  #  e_usage("doesn't own option %r (try 'set')" % opt_name)

  return opt_num


def _SetOptionNum(opt_name):
  # type: (str) -> option_t
  opt_num = consts.OptionNum(opt_name)
  if opt_num == 0:
    e_usage('got invalid option %r' % opt_name)

  if opt_num not in consts.SET_OPTION_NUMS:
    e_usage("invalid option %r (try shopt)" % opt_name)

  return opt_num


class MutableOpts(object):

  def __init__(self, mem, opt0_array, opt_stacks, opt_hook):
    # type: (Mem, List[bool], List[List[bool]], OptHook) -> None
    self.mem = mem
    self.opt0_array = opt0_array
    self.opt_stacks = opt_stacks
    self.errexit_disabled_spid = []  # type: List[int]

    # Used for 'set -o vi/emacs'
    self.opt_hook = opt_hook

  def Init(self):
    # type: () -> None

    # This comes after all the 'set' options.
    UP_shellopts = self.mem.GetValue('SHELLOPTS')
    if UP_shellopts.tag_() == value_e.Str:  # Always true in Oil, see Init above
      shellopts = cast(value__Str, UP_shellopts)
      self._InitOptionsFromEnv(shellopts.s)

  def _InitOptionsFromEnv(self, shellopts):
    # type: (str) -> None
    # e.g. errexit:nounset:pipefail
    lookup = shellopts.split(':')
    for opt_num in consts.SET_OPTION_NUMS:
      name = consts.OptionName(opt_num) 
      if name in lookup:
        self._SetOldOption(name, True)

  def Push(self, opt_num, b):
    # type: (int, bool) -> None
    overlay = self.opt_stacks[opt_num]
    if overlay is None or len(overlay) == 0:
      self.opt_stacks[opt_num] = [b]  # Allocate a new list
    else:
      overlay.append(b)

  def Pop(self, opt_num):
    # type: (int) -> bool
    overlay = self.opt_stacks[opt_num]
    assert overlay is not None
    return overlay.pop()

  def PushDynamicScope(self, b):
    # type: (bool) -> None
    """
    b: False if it's a proc, and True if it's a shell function
    """
    # If it's already disabled, keep it disabled
    if not self.Get(option_i.dynamic_scope):
      b = False
    self.Push(option_i.dynamic_scope, b)

  def PopDynamicScope(self):
    # type: () -> None
    self.Pop(option_i.dynamic_scope)

  def Get(self, opt_num):
    # type: (int) -> bool
    # Like _Getter in core/optview.py
    overlay = self.opt_stacks[opt_num]
    if overlay is None or len(overlay) == 0:
      return self.opt0_array[opt_num]
    else:
      return overlay[-1]  # the top value

  def _Set(self, opt_num, b):
    # type: (int, bool) -> None
    """Used to disable errexit.  For bash compatibility in command sub."""

    # Like _Getter in core/optview.py
    overlay = self.opt_stacks[opt_num]
    if overlay is None or len(overlay) == 0:
      self.opt0_array[opt_num] = b
    else:
      overlay[-1] = b  # The top value

  def set_interactive(self):
    # type: () -> None
    self._Set(option_i.interactive, True)

  def set_redefine_proc(self):
    # type: () -> None
    """For interactive shells."""
    self._Set(option_i.redefine_proc, True)

  def set_redefine_module(self):
    # type: () -> None
    """For interactive shells."""
    self._Set(option_i.redefine_module, True)

  def set_emacs(self):
    # type: () -> None
    self._Set(option_i.emacs, True)

  def set_xtrace(self, b):
    # type: (bool) -> None
    self._Set(option_i.xtrace, b)

  def _SetArrayByNum(self, opt_num, b):
    # type: (int, bool) -> None
    if (opt_num in consts.PARSE_OPTION_NUMS and
        not self.mem.InGlobalNamespace()):
      e_die('Syntax options must be set at the top level '
            '(outside any function)')

    self._Set(opt_num, b)

  def SetDeferredErrExit(self, b):
    # type: (bool) -> None
    """Set the errexit flag, possibly deferring it.

    Implements the unusual POSIX "defer" behavior.  Callers: set -o errexit,
    shopt -s oil:all, oil:upgrade
    """
    #log('Set %s', b)

    # Defer it until we pop by setting the BOTTOM OF THE STACK.
    self.opt0_array[option_i.errexit] = b

  def DisableErrExit(self):
    # type: () -> None
    """Called by core/process.py to implement bash quirks."""
    self._Set(option_i.errexit, False)

  def ErrExitDisabledSpanId(self):
    # type: () -> int
    """If errexit is disabled by POSIX rules, return span ID for construct.

    e.g. the spid for 'if' or '&&' etc.

    Otherwise return runtime.NO_SPID
    """
    # Bug fix: The errexit disabling inherently follows a STACK DISCIPLINE.
    # But we run trap handlers in the MAIN LOOP, which break this.  So just
    # declare that it's never disabled in a trap.
    if self.Get(option_i._running_trap):
      return runtime.NO_SPID

    if len(self.errexit_disabled_spid) == 0:
      return runtime.NO_SPID

    return self.errexit_disabled_spid[-1]

    # Old complex logic.  It turns out we don't need to detect whether it was
    # actually disabled.  These are the "strict_errexit without errexit" cases
    # in spec/errexit-oil.
    """
      overlay = self.opt_stacks[option_i.errexit]
      # log('overlay %s', overlay)
      # log('errexit_disabled_spid %s', self.errexit_disabled_spid)
      if overlay is None or len(overlay) == 0:
        return runtime.NO_SPID
      else:
        was_on = self.opt0_array[option_i.errexit] or (True in overlay)
        # top of stack == False means it's disabled
        if was_on and not overlay[-1]:
          return self.errexit_disabled_spid[-1]
        else:
          return runtime.NO_SPID
    """

  def _SetOldOption(self, opt_name, b):
    # type: (str, bool) -> None
    """Private version for synchronizing from SHELLOPTS."""
    assert '_' not in opt_name
    assert opt_name in consts.SET_OPTION_NAMES

    opt_num = consts.OptionNum(opt_name)
    assert opt_num != 0, opt_name

    if opt_num == option_i.errexit:
      self.SetDeferredErrExit(b)
    else:
      if opt_num == option_i.verbose and b:
        print_stderr('Warning: set -o verbose not implemented')
      self._SetArrayByNum(opt_num, b)

    # note: may FAIL before we get here.

    success = self.opt_hook.OnChange(self.opt0_array, opt_name, b)

  def SetOldOption(self, opt_name, b):
    # type: (str, bool) -> None
    """ For set -o, set +o, or shopt -s/-u -o. """
    _ = _SetOptionNum(opt_name)  # validate it
    self._SetOldOption(opt_name, b)

    UP_val = self.mem.GetValue('SHELLOPTS')
    assert UP_val.tag_() == value_e.Str, UP_val
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

  def SetAnyOption(self, opt_name, b):
    # type: (str, bool) -> None
    """ For shopt -s/-u and sh -O/+O. """

    # shopt -s all:oil turns on all Oil options, which includes all strict #
    # options
    opt_group = consts.OptionGroupNum(opt_name)
    if opt_group == opt_group_i.OilUpgrade:
      _SetGroup(self.opt0_array, consts.OIL_UPGRADE, b)
      self.SetDeferredErrExit(b)  # Special case
      return

    if opt_group == opt_group_i.OilAll:
      _SetGroup(self.opt0_array, consts.OIL_ALL, b)
      self.SetDeferredErrExit(b)  # Special case
      return

    if opt_group == opt_group_i.StrictAll:
      _SetGroup(self.opt0_array, consts.STRICT_ALL, b)
      return

    opt_num = _AnyOptionNum(opt_name)

    if opt_num == option_i.errexit:
      self.SetDeferredErrExit(b)
      return

    self._SetArrayByNum(opt_num, b)

  def ShowOptions(self, opt_names):
    # type: (List[str]) -> None
    """ For 'set -o' and 'shopt -p -o' """
    # TODO: Maybe sort them differently?

    if len(opt_names) == 0:  # if none, supplied, show all
      opt_names = [consts.OptionName(i) for i in consts.SET_OPTION_NUMS]

    for opt_name in opt_names:
      opt_num = _SetOptionNum(opt_name)
      b = self.Get(opt_num)
      print('set %so %s' % ('-' if b else '+', opt_name))

  def ShowShoptOptions(self, opt_names):
    # type: (List[str]) -> None
    """ For 'shopt -p' """

    # Respect option gropus.
    opt_nums = []  # type: List[int]
    for opt_name in opt_names:
      opt_group = consts.OptionGroupNum(opt_name)
      if opt_group == opt_group_i.OilUpgrade:
        opt_nums.extend(consts.OIL_UPGRADE)
      elif opt_group == opt_group_i.OilAll:
        opt_nums.extend(consts.OIL_ALL)
      elif opt_group == opt_group_i.StrictAll:
        opt_nums.extend(consts.STRICT_ALL)
      else:
        index = consts.OptionNum(opt_name)
        # Minor incompatibility with bash: we validate everything before
        # printing.
        if index == 0:
          e_usage('got invalid option %r' % opt_name)
        opt_nums.append(index)

    if len(opt_names) == 0:
      # If none supplied, show all>
      # TODO: Should this show 'set' options too?
      opt_nums.extend(consts.VISIBLE_SHOPT_NUMS)

    for opt_num in opt_nums:
      b = self.Get(opt_num)
      print('shopt -%s %s' % ('s' if b else 'u', consts.OptionName(opt_num)))


class _ArgFrame(object):
  """Stack frame for arguments array."""

  def __init__(self, argv):
    # type: (List[str]) -> None
    self.argv = argv
    self.num_shifted = 0

  def __repr__(self):
    # type: () -> str
    return '<_ArgFrame %s %d at %x>' % (self.argv, self.num_shifted, id(self))

  if mylib.PYTHON:  # mycpp has problem with dict literal
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
    # type: () -> Optional[str]
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
    e_die("Can't determine working directory: %s" % pyutil.strerror(e))


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
  SetGlobalString(mem, 'OSTYPE', pyos.OsType())

  # For getopts builtin
  SetGlobalString(mem, 'OPTIND', '1')

  # When xtrace_rich is off, this is just like '+ ', the shell default
  SetGlobalString(mem, 'PS4', '${SHX_indent}${SHX_punct}${SHX_pid_str} ')

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
    mem.SetValue(lvalue.Named(n), value.Str(v), scope_e.GlobalOnly,
                 flags=SetExport)

  # If it's not in the environment, initialize it.  This makes it easier to
  # update later in MutableOpts.

  # TODO: IFS, etc. should follow this pattern.  Maybe need a SysCall
  # interface?  self.syscall.getcwd() etc.

  val = mem.GetValue('SHELLOPTS')
  if val.tag_() == value_e.Undef:
    SetGlobalString(mem, 'SHELLOPTS', '')
  # Now make it readonly
  mem.SetValue(
      lvalue.Named('SHELLOPTS'), None, scope_e.GlobalOnly, flags=SetReadOnly)

  # Usually we inherit PWD from the parent shell.  When it's not set, we may
  # compute it.
  val = mem.GetValue('PWD')
  if val.tag_() == value_e.Undef:
    SetGlobalString(mem, 'PWD', _GetWorkingDir())
  # Now mark it exported, no matter what.  This is one of few variables
  # EXPORTED.  bash and dash both do it.  (e.g. env -i -- dash -c env)
  mem.SetValue(
      lvalue.Named('PWD'), None, scope_e.GlobalOnly, flags=SetExport)

  val = mem.GetValue('PATH')
  if val.tag_() == value_e.Undef:
    # Setting PATH to these two dirs match what zsh and mksh do.  bash and dash
    # add {,/usr/,/usr/local}/{bin,sbin}
    SetGlobalString(mem, 'PATH', '/bin:/usr/bin')


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
  val = mem.GetValue('PWD')
  # should be true since it's exported
  assert val.tag_() == value_e.Str, val
  pwd = cast(value__Str, val).s
  mem.SetPwd(pwd)


def InitInteractive(mem):
  # type: (Mem) -> None
  """Initialization that's only done in the interactive/headless shell."""

  # Same default PS1 as bash
  if mem.GetValue('PS1').tag_() == value_e.Undef:
    SetGlobalString(mem, 'PS1', r'\s-\v\$ ')


class ctx_Call(object):
  """For function calls."""

  def __init__(self, mem, mutable_opts, proc, argv):
    # type: (Mem, MutableOpts, Proc, List[str]) -> None
    mem.PushCall(proc.name, proc.name_spid, argv)
    mutable_opts.PushDynamicScope(proc.dynamic_scope)
    # It may have been disabled with ctx_ErrExit for 'if echo $(false)', but
    # 'if p' should be allowed.
    self.mem = mem
    self.mutable_opts = mutable_opts

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.mutable_opts.PopDynamicScope()
    self.mem.PopCall()


class ctx_Temp(object):
  """For FOO=bar myfunc, etc."""

  def __init__(self, mem):
    # type: (Mem) -> None
    mem.PushTemp()
    self.mem = mem

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.mem.PopTemp()


class ctx_Shvar(object):
  """For shvar LANG=C _ESCAPER=posix-sh-word _DIALECT=ninja """

  def __init__(self, mem, pairs):
    # type: (Mem, List[Tuple[str, str]]) -> None
    #log('pairs %s', pairs)
    self.mem = mem
    self.restore = []  # type: List[Tuple[lvalue_t, value_t]]
    self._Push(pairs)

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self._Pop()

  # Note: _Push and _Pop are separate methods because the C++ translation
  # doesn't like when they are inline in __init__ and __exit__.
  def _Push(self, pairs):
    # type: (List[Tuple[str, str]]) -> None
    for name, s in pairs:
      lval = lvalue.Named(name)  # type: lvalue_t
      # LocalOnly because we are only overwriting the current scope
      old_val = self.mem.GetValue(name, scope_e.LocalOnly)
      self.restore.append((lval, old_val))
      self.mem.SetValue(lval, value.Str(s), scope_e.LocalOnly)

  def _Pop(self):
    # type: () -> None
    for lval, old_val in self.restore:
      if old_val.tag_() == value_e.Undef:
        self.mem.Unset(lval, scope_e.LocalOnly)
      else:
        self.mem.SetValue(lval, old_val, scope_e.LocalOnly)


class ctx_Registers(object):
  """For $PS1, $PS4, $PROMPT_COMMAND, traps, and headless EVAL."""

  def __init__(self, mem):
    # type: (Mem) -> None

    # Because some prompts rely on the status leaking.  See issue #853.
    # PS1 also does.
    last = mem.last_status[-1]
    mem.last_status.append(last)
    mem.try_status.append(0)

    # TODO: We should also copy these values!  Turn the whole thing into a
    # frame.
    mem.pipe_status.append([])
    mem.process_sub_status.append([])

    mem.regex_matches.append([])
    self.mem = mem

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.mem.regex_matches.pop()
    self.mem.process_sub_status.pop()
    self.mem.pipe_status.pop()
    self.mem.try_status.pop()
    self.mem.last_status.pop()


class ctx_ThisDir(object):
  """For $_this_dir"""

  def __init__(self, mem, filename):
    # type: (Mem, Optional[str]) -> None
    self.do_pop = False
    if filename is not None:  # script_name in main() may be -c, etc.
      d = os_path.dirname(os_path.abspath(filename))
      mem.this_dir.append(d)
      self.do_pop = True

    self.mem = mem

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    if self.do_pop:
      self.mem.this_dir.pop()


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
    # type: (str, List[str], alloc.Arena, List[DebugFrame]) -> None
    """
    Args:
      arena: for computing BASH_SOURCE, etc.  Could be factored out
    """
    # circular dep initialized out of line
    self.exec_opts = None  # type: optview.Exec
    self.unsafe_arith = None  # type: sh_expr_eval.UnsafeArith

    self.dollar0 = dollar0
    self.argv_stack = [_ArgFrame(argv)]
    frame = NewDict()  # type: Dict[str, cell]
    self.var_stack = [frame]

    self.arena = arena

    # The debug_stack isn't strictly necessary for execution.  We use it for
    # crash dumps and for 4 parallel arrays: BASH_SOURCE, FUNCNAME,
    # CALL_SOURCE, and BASH_LINENO.
    self.debug_stack = debug_stack

    self.pwd = None  # type: Optional[str]

    self.current_spid = runtime.NO_SPID

    self.line_num = value.Str('')

    # Done ONCE on initialization
    self.root_pid = posix.getpid()

    # TODO:
    # - These are REGISTERS mutated by user code.
    # - Call it self.reg_stack?  with ctx_Registers
    # - push-registers builtin
    self.last_status = [0]  # type: List[int]  # a stack
    self.try_status = [0]  # type: List[int]  # a stack
    self.pipe_status = [[]]  # type: List[List[int]]  # stack
    self.process_sub_status = [[]]  # type: List[List[int]]  # stack

    # A stack but NOT a register?
    self.this_dir = []  # type: List[str]

    # 0 is the whole match, 1..n are submatches
    self.regex_matches = [[]]  # type: List[List[str]]

    self.last_bg_pid = -1  # Uninitialized value mutable public variable

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
          span = self.arena.GetToken(frame.call_spid)
          line_id = span.line_id
          d['call_source'] = ui.GetLineSourceString(self.arena, line_id)
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

  def LastStatus(self):
    # type: () -> int
    return self.last_status[-1]

  def TryStatus(self):
    # type: () -> int
    return self.try_status[-1]

  def PipeStatus(self):
    # type: () -> List[int]
    return self.pipe_status[-1]

  def SetLastStatus(self, x):
    # type: (int) -> None
    self.last_status[-1] = x

  def SetTryStatus(self, x):
    # type: (int) -> None
    self.try_status[-1] = x

  def SetPipeStatus(self, x):
    # type: (List[int]) -> None
    self.pipe_status[-1] = x

  def SetProcessSubStatus(self, x):
    # type: (List[int]) -> None
    self.process_sub_status[-1] = x

  #
  # Call Stack
  #

  def PushCall(self, func_name, def_spid, argv):
    # type: (str, int, List[str]) -> None
    """For function calls."""
    self.argv_stack.append(_ArgFrame(argv))
    frame = NewDict()  # type: Dict[str, cell]
    self.var_stack.append(frame)

    span = self.arena.GetToken(def_spid)
    source_str = ui.GetLineSourceString(self.arena, span.line_id)

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
    """For the temporary scope in 'FOO=bar BAR=baz echo'.

    Also for PS4 evaluation with more variables.
    """
    # We don't want the 'read' builtin to write to this frame!
    frame = NewDict()  # type: Dict[str, cell]
    self.var_stack.append(frame)
    self._PushDebugStack(None, None, None)

  def PopTemp(self):
    # type: () -> None
    self._PopDebugStack()
    self.var_stack.pop()

  def TopNamespace(self):
    # type: () -> Dict[str, runtime_asdl.cell]
    """For eval_to_dict()."""
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

  def _ResolveNameOnly(self, name, which_scopes):
    # type: (str, scope_t) -> Tuple[Optional[cell], Dict[str, cell]]
    """Helper for getting and setting variable.

    Returns:
      cell: The cell corresponding to looking up 'name' with the given mode, or
        None if it's not found.
      name_map: The name_map it should be set to or deleted from.
    """
    if which_scopes == scope_e.Dynamic:
      for i in xrange(len(self.var_stack) - 1, -1, -1):
        name_map = self.var_stack[i]
        if name in name_map:
          cell = name_map[name]
          return cell, name_map
      no_cell = None  # type: Optional[runtime_asdl.cell]
      return no_cell, self.var_stack[0]  # set in global name_map

    if which_scopes == scope_e.LocalOnly:
      name_map = self.var_stack[-1]
      return name_map.get(name), name_map

    if which_scopes == scope_e.GlobalOnly:
      name_map = self.var_stack[0]
      return name_map.get(name), name_map

    if which_scopes == scope_e.LocalOrGlobal:
      # Local
      name_map = self.var_stack[-1]
      cell = name_map.get(name)
      if cell:
        return cell, name_map

      # Global
      name_map = self.var_stack[0]
      return name_map.get(name), name_map

    if which_scopes == scope_e.Parent:
      assert len(self.var_stack) >= 2
      name_map = self.var_stack[-2]
      return name_map.get(name), name_map

    raise AssertionError()

  def _ResolveNameOrRef(self, name, which_scopes, is_setref, ref_trail=None):
    # type: (str, scope_t, bool, Optional[List[str]]) -> Tuple[Optional[cell], Dict[str, cell], str]
    """Look up a cell and namespace, but respect the nameref flag.

    Resolving namerefs does RECURSIVE calls.
    """
    cell, name_map = self._ResolveNameOnly(name, which_scopes)

    if cell is None or not cell.nameref:
      if is_setref:
        e_die("setref requires a nameref (:out param)")
      return cell, name_map, name  # not a nameref

    val = cell.val
    UP_val = val
    with tagswitch(val) as case:
      if case(value_e.Undef):
        # This is 'local -n undef_ref', which is kind of useless, because the
        # more common idiom is 'local -n ref=$1'.  Note that you can mutate
        # references themselves with local -n ref=new.
        if self.exec_opts.strict_nameref():
          e_die('nameref %r is undefined' % name)
        else:
          return cell, name_map, name  # fallback

      elif case(value_e.Str):
        val = cast(value__Str, UP_val)
        new_name = val.s

      else:
        # SetValue() protects the invariant that nameref is Undef or Str
        raise AssertionError(val.tag_())

    # TODO: Respect eval_unsafe_arith here (issue 881).  See how it's done in
    # 'printf -v' with MakeArithParser
    if not match.IsValidVarName(new_name):
      # e.g. '#' or '1' or ''
      if self.exec_opts.strict_nameref():
        e_die('nameref %r contains invalid variable name %r' % (name, new_name))
      else:
        # Bash has this odd behavior of clearing the nameref bit when
        # ref=#invalid#.  strict_nameref avoids it.
        cell.nameref = False
        return cell, name_map, name  # fallback

    # Check for circular namerefs.
    if ref_trail is None:
      ref_trail = [name]
    else:
      if new_name in ref_trail:
        e_die('Circular nameref %s' % ' -> '.join(ref_trail))
    ref_trail.append(new_name)

    # 'declare -n' uses dynamic scope.  'setref' uses parent scope to avoid the
    # problem of 2 procs containing the same variable name.
    which_scopes = scope_e.Parent if is_setref else scope_e.Dynamic
    cell, name_map, cell_name = self._ResolveNameOrRef(new_name, which_scopes,
                                                       False, ref_trail=ref_trail)
    return cell, name_map, cell_name

  def IsAssocArray(self, name):
    # type: (str) -> bool
    """Returns whether a name resolve to a cell with an associative array.
    
    We need to know this to evaluate the index expression properly -- should it
    be coerced to an integer or not?
    """
    cell, _, _ = self._ResolveNameOrRef(name, self.ScopesForReading(), False)
    if cell:
      if cell.val.tag_() == value_e.AssocArray:  # foo=([key]=value)
        return True
    return False

  def SetValue(self, lval, val, which_scopes, flags=0):
    # type: (lvalue_t, value_t, scope_t, int) -> None
    """
    Args:
      lval: lvalue
      val: value, or None if only changing flags
      which_scopes:
        Local | Global | Dynamic - for builtins, PWD, etc.
      flags: packed pair (keyword_id, bit mask of set/clear flags)

    Note: in bash, PWD=/ changes the directory.  But not in dash.
    """
    keyword_id = flags >> 8  # opposite of _PackFlags
    is_setref = keyword_id == Id.KW_SetRef
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
    # - COMPUTED vars can't be set
    # - What about PWD / OLDPWD / UID / EUID ?  You can simply make them
    #   readonly.
    # - Maybe PARSE $PS1 and $PS4 when they're set, to avoid the error on use?
    # - Other validity: $HOME could be checked for existence

    UP_lval = lval
    with tagswitch(lval) as case:
      if case(lvalue_e.Named):
        lval = cast(lvalue__Named, UP_lval)
        assert lval.name is not None

        if keyword_id == Id.KW_SetRef:
          # Hidden interpreter var with __ prefix.  Matches proc call in
          # osh/cmd_eval.py
          lval.name = '__' + lval.name  # Mutating arg lval!  Happens to be OK

        if flags & SetNameref or flags & ClearNameref:
          # declare -n ref=x  # refers to the ref itself
          cell, name_map = self._ResolveNameOnly(lval.name, which_scopes)
          cell_name = lval.name
        else:
          # ref=x  # mutates THROUGH the reference

          # Note on how to implement declare -n ref='a[42]'
          # 1. Call _ResolveNameOnly()
          # 2. If cell.nameref, call self.unsafe_arith.ParseVarRef() ->
          #    braced_var_sub
          # 3. Turn braced_var_sub into an lvalue, and call
          #    self.unsafe_arith.SetValue() wrapper with ref_trail
          cell, name_map, cell_name = self._ResolveNameOrRef(lval.name,
                                                             which_scopes,
                                                             is_setref)

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
            # Note: this DYNAMIC check means we can't have 'const' in a loop.
            # But that's true for 'readonly' too, and hoisting it makes more
            # sense anyway.
            if cell.readonly:
              # TODO: error context
              e_die("Can't assign to readonly value %r" % lval.name)
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

      elif case(lvalue_e.Indexed):
        lval = cast(lvalue__Indexed, UP_lval)
        assert isinstance(lval.index, int), lval

        # There is no syntax 'declare a[x]'
        assert val is not None, val

        # TODO: relax this for Oil
        assert val.tag_() == value_e.Str, val
        rval = cast(value__Str, val)

        # 'setref' array[index] not implemented here yet
        #if keyword_id == Id.KW_SetRef:
        #  lval.name = '__' + lval.name

        # TODO: All paths should have this?  We can get here by a[x]=1 or
        # (( a[ x ] = 1 )).  Maybe we should make them different?
        left_spid = lval.spids[0] if len(lval.spids) else runtime.NO_SPID

        # bash/mksh have annoying behavior of letting you do LHS assignment to
        # Undef, which then turns into an INDEXED array.  (Undef means that set
        # -o nounset fails.)
        cell, name_map, _ = self._ResolveNameOrRef(lval.name, which_scopes,
                                                   is_setref)
        if not cell:
          self._BindNewArrayWithEntry(name_map, lval, rval, flags)
          return

        if cell.readonly:
          e_die("Can't assign to readonly array", loc.Span(left_spid))

        UP_cell_val = cell.val
        # undef[0]=y is allowed
        with tagswitch(UP_cell_val) as case2:
          if case2(value_e.Undef):
            self._BindNewArrayWithEntry(name_map, lval, rval, flags)
            return

          elif case2(value_e.Str):
            # s=x
            # s[1]=y  # invalid
            e_die("Can't assign to items in a string", loc.Span(left_spid))

          elif case2(value_e.MaybeStrArray):
            cell_val = cast(value__MaybeStrArray, UP_cell_val)
            strs = cell_val.strs

            n = len(strs)
            index = lval.index
            if index < 0:  # a[-1]++ computes this twice; could we avoid it?
              index += n

            if 0 <= index and index < n:
              strs[index] = rval.s
            else:
              # Fill it in with None.  It could look like this:
              # ['1', 2, 3, None, None, '4', None]
              # Then ${#a[@]} counts the entries that are not None.
              #
              # TODO: strict_array for Oil arrays won't auto-fill.
              n = index - len(strs) + 1
              for i in xrange(n):
                strs.append(None)
              strs[lval.index] = rval.s
            return

        # This could be an object, eggex object, etc.  It won't be
        # AssocArray shouldn because we query IsAssocArray before evaluating
        # sh_lhs_expr.  Could conslidate with s[i] case above
        e_die("Value of type %s can't be indexed" % ui.ValType(cell.val),
              loc.Span(left_spid))


      elif case(lvalue_e.Keyed):
        lval = cast(lvalue__Keyed, UP_lval)
        # There is no syntax 'declare A["x"]'
        assert val is not None, val
        assert val.tag_() == value_e.Str, val
        rval = cast(value__Str, val)

        left_spid = lval.spids[0] if len(lval.spids) else runtime.NO_SPID

        cell, name_map, _ = self._ResolveNameOrRef(lval.name, which_scopes,
                                                   is_setref)
        if cell.readonly:
          e_die("Can't assign to readonly associative array", loc.Span(left_spid))

        # We already looked it up before making the lvalue
        assert cell.val.tag_() == value_e.AssocArray, cell
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

  def GetValue(self, name, which_scopes=scope_e.Shopt):
    # type: (str, scope_t) -> value_t
    """Used by the WordEvaluator, ArithEvalutor, oil_lang/expr_eval.py, etc.

    TODO:
    - Many of these should be value.Int, not value.Str
    - And even later _pipeline_status etc. should be lists of integers, not
      strings
    """
    assert isinstance(name, str), name

    if which_scopes == scope_e.Shopt:
      which_scopes = self.ScopesForReading()
    #log('which_scopes %s', which_scopes)

    # TODO: Optimize this by doing a single hash lookup:
    # COMPUTED_VARS = {'PIPESTATUS': 1, 'FUNCNAME': 1, ...}
    # if name not in COMPUTED_VARS: ...

    if name == 'ARGV':
      # TODO:
      # - Reuse the MaybeStrArray?
      # - @@ could be an alias for ARGV (in command mode, but not expr mode)
      return value.MaybeStrArray(self.GetArgv())

    # "Registers"
    if name == '_status':
      if mylib.PYTHON:
        # TODO: value.Int()
        return value.Obj(self.TryStatus())
      else:
        return value.Undef()  # STUB

    if name == '_this_dir':
      if len(self.this_dir) == 0:
        # e.g. osh -c '' doesn't have it set
        # Should we give a custom error here?
        # If you're at the interactive shell, 'source mymodule.oil' will still
        # work because 'source' sets it.
        return value.Undef()
      else:
        return value.Str(self.this_dir[-1])  # top of stack

    if name in ('PIPESTATUS', '_pipeline_status'):
      pipe_strs = [str(i) for i in self.pipe_status[-1]] # type: List[str]
      return value.MaybeStrArray(pipe_strs)

    if name == '_process_sub_status':  # Oil naming convention
      # TODO: Shouldn't these be real integers?
      sub_strs = [str(i) for i in self.process_sub_status[-1]] # type: List[str]
      return value.MaybeStrArray(sub_strs)

    if name == 'BASH_REMATCH':
      return value.MaybeStrArray(self.regex_matches[-1])  # top of stack

    # Do lookup of system globals before looking at user variables.  Note: we
    # could optimize this at compile-time like $?.  That would break
    # ${!varref}, but it's already broken for $?.
    if name == 'FUNCNAME':
      # bash wants it in reverse order.  This is a little inefficient but we're
      # not depending on deque().
      strs = []  # type: List[str]
      for frame in reversed(self.debug_stack):
        if frame.func_name is not None:
          strs.append(frame.func_name)
        if frame.source_name is not None:
          strs.append('source')  # bash doesn't tell you the filename.
        # Temp stacks are ignored
      return value.MaybeStrArray(strs)  # TODO: Reuse this object too?

    # This isn't the call source, it's the source of the function DEFINITION
    # (or the sourced # file itself).
    if name == 'BASH_SOURCE':
      strs = []
      for frame in reversed(self.debug_stack):
        if frame.bash_source is not None:
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
          span = self.arena.GetToken(frame.call_spid)
          source_str = ui.GetLineSourceString(self.arena, span.line_id)
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
        span = self.arena.GetToken(frame.call_spid)
        line_num = self.arena.GetLineNumber(span.line_id)
        strs.append(str(line_num))
      return value.MaybeStrArray(strs)  # TODO: Reuse this object too?

    if name == 'LINENO':
      assert self.current_spid != -1, self.current_spid
      span = self.arena.GetToken(self.current_spid)
      # TODO: maybe use interned GetLineNumStr?
      self.line_num.s = str(self.arena.GetLineNumber(span.line_id))
      return self.line_num

    if name == 'BASHPID':  # TODO: Oil name for it
      return value.Str(str(posix.getpid()))

    # In the case 'declare -n ref='a[42]', the result won't be a cell.  Idea to
    # fix this:
    # 1. Call self.unsafe_arith.ParseVarRef() -> braced_var_sub
    # 2. Call self.unsafe_arith.GetNameref(bvs_part), and get a value_t
    #    We still need a ref_trail to detect cycles.
    cell, _, _ = self._ResolveNameOrRef(name, which_scopes, False)
    if cell:
      return cell.val

    return value.Undef()

  def GetCell(self, name, which_scopes=scope_e.Shopt):
    # type: (str, scope_t) -> cell
    """Get both the value and flags.

    Usages:
      - the 'pp' builtin.
      - declare -p
      - ${x@a}
      - to test of 'TZ' is exported in printf?  Why?
    """
    if which_scopes == scope_e.Shopt:
      which_scopes = self.ScopesForReading()

    cell, _ = self._ResolveNameOnly(name, which_scopes)
    return cell

  def Unset(self, lval, which_scopes):
    # type: (lvalue_t, scope_t) -> bool
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

    if which_scopes == scope_e.Shopt:
      which_scopes = self.ScopesForWriting()

    cell, name_map, cell_name = self._ResolveNameOrRef(var_name, which_scopes, False)
    if not cell:
      return False  # 'unset' builtin falls back on functions
    if cell.readonly:
      raise error.Runtime("Can't unset readonly variable %r" % var_name)

    with tagswitch(lval) as case:
      if case(lvalue_e.Named):  # unset x
        # Make variables in higher scopes visible.
        # example: test/spec.sh builtin-vars -r 24 (ble.sh)
        mylib.dict_erase(name_map, cell_name)

        # alternative that some shells use:
        #   name_map[cell_name].val = value.Undef()
        #   cell.exported = False

        # This should never happen because we do recursive lookups of namerefs.
        assert not cell.nameref, cell

      elif case(lvalue_e.Indexed):  # unset 'a[1]'
        lval = cast(lvalue__Indexed, UP_lval)
        # Note: Setting an entry to None and shifting entries are pretty
        # much the same in shell.

        val = cell.val
        UP_val = val
        if val.tag_() != value_e.MaybeStrArray:
          raise error.Runtime("%r isn't an array" % var_name)

        val = cast(value__MaybeStrArray, UP_val)
        strs = val.strs

        n = len(strs)
        last_index = n - 1
        index = lval.index
        if index < 0:
          index += n

        if index == last_index:
          # Special case: The array SHORTENS if you unset from the end.  You
          # can tell with a+=(3 4)
          strs.pop()
        elif 0 <= index and index < last_index:
          strs[index] = None
        else:
          # If it's not found, it's not an error.  In other words, 'unset'
          # ensures that a value doesn't exist, regardless of whether it
          # existed.  It's idempotent.
          # (Ousterhout specifically argues that the strict behavior was a
          # mistake for Tcl!)
          pass

      elif case(lvalue_e.Keyed):  # unset 'A["K"]'
        lval = cast(lvalue__Keyed, UP_lval)

        val = cell.val
        UP_val = val

        # note: never happens because of mem.IsAssocArray test for lvalue.Keyed
        #if val.tag_() != value_e.AssocArray:
        #  raise error.Runtime("%r isn't an associative array" % lval.name)

        val = cast(value__AssocArray, UP_val)
        mylib.dict_erase(val.d, lval.key)

      else:
        raise AssertionError(lval)

    return True

  def ScopesForReading(self):
    # type: () -> scope_t
    """Read scope."""
    return (
        scope_e.Dynamic if self.exec_opts.dynamic_scope() else
        scope_e.LocalOrGlobal
    )

  def ScopesForWriting(self):
    # type: () -> scope_t
    """Write scope."""
    return (
        scope_e.Dynamic if self.exec_opts.dynamic_scope() else
        scope_e.LocalOnly
    )

  def ClearFlag(self, name, flag):
    # type: (str, int) -> bool
    """Used for export -n.

    We don't use SetValue() because even if rval is None, it will make an Undef
    value in a scope.
    """
    cell, name_map = self._ResolveNameOnly(name, self.ScopesForReading())
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

  def GetAllCells(self, which_scopes):
    # type: (scope_t) -> Dict[str, cell]
    """Get all variables and their values, for 'set' builtin. """
    result = {}  # type: Dict[str, cell]

    if which_scopes == scope_e.Dynamic:
      scopes = self.var_stack
    elif which_scopes == scope_e.LocalOnly:
      scopes = self.var_stack[-1:]
    elif which_scopes == scope_e.GlobalOnly:
      scopes = self.var_stack[0:1]
    elif which_scopes == scope_e.LocalOrGlobal:
      scopes = [self.var_stack[0]]
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

  def ClearMatches(self):
    # type: () -> None
    top = self.regex_matches[-1]
    del top[:]  # no clear() in Python 2

  def SetMatches(self, matches):
    # type: (List[str]) -> None
    self.regex_matches[-1] = matches

  def GetMatch(self, i):
    # type: (int) -> Optional[str]
    top = self.regex_matches[-1]
    if i < len(top):
      return top[i]
    else:
      return None

#
# Wrappers to Set Variables
#

def OshLanguageSetValue(mem, lval, val, flags=0):
  # type: (Mem, lvalue_t, value_t, int) -> None
  """ Like 'setvar' (scope_e.LocalOnly), unless dynamic scope is on.
  
  That is, it respects shopt --unset dynamic_scope.

  Used for assignment builtins, (( a = b )), {fd}>out, ${x=}, etc.
  """
  which_scopes = mem.ScopesForWriting()
  mem.SetValue(lval, val, which_scopes, flags=flags)


def BuiltinSetValue(mem, lval, val):
  # type: (Mem, lvalue_t, value_t) -> None
  """Equivalent of x=$y or setref x = y 
  
  Called by BuiltinSetString and BuiltinSetArray
  Used directly by printf -v because it can mutate an array
  """
  mem.SetValue(lval, val, mem.ScopesForWriting())


def BuiltinSetString(mem, name, s):
  # type: (Mem, str, str) -> None
  """Set a string by looking up the stack.

  # Equivalent of:
  proc p(:myref) {
    setref myref = 's'
  }

  Used for 'read', 'getopts', completion builtins, etc.
  """
  assert isinstance(s, str)
  BuiltinSetValue(mem, lvalue.Named(name), value.Str(s))


def BuiltinSetArray(mem, name, a):
  # type: (Mem, str, List[str]) -> None
  """Set an array by looking up the stack.

  # Equivalent of:
  proc p(:myref) {
    setref myref = %(a b c)
  }

  Used by compadjust, read -a, etc.
  """
  assert isinstance(a, list)
  BuiltinSetValue(mem, lvalue.Named(name), value.MaybeStrArray(a))


def SetGlobalString(mem, name, s):
  # type: (Mem, str, str) -> None
  """Helper for completion, etc."""
  assert isinstance(s, str)
  val = value.Str(s)
  mem.SetValue(lvalue.Named(name), val, scope_e.GlobalOnly)


def SetGlobalArray(mem, name, a):
  # type: (Mem, str, List[str]) -> None
  """Used by completion, shell initialization, etc."""
  assert isinstance(a, list)
  mem.SetValue(lvalue.Named(name), value.MaybeStrArray(a), scope_e.GlobalOnly)


def ExportGlobalString(mem, name, s):
  # type: (Mem, str, str) -> None
  """Helper for completion, $PWD, $OLDPWD, etc."""
  assert isinstance(s, str)
  val = value.Str(s)
  mem.SetValue(lvalue.Named(name), val, scope_e.GlobalOnly, flags=SetExport)

#
# Wrappers to Get Variables
#

def GetString(mem, name):
  # type: (Mem, str) -> str
  """
  Wrapper around GetValue().  Check that HOME, PWD, OLDPWD, etc. are strings.
  bash doesn't have these errors because ${array} is ${array[0]}.

  TODO: We could also check this when you're storing variables?
  """
  val = mem.GetValue(name)
  UP_val = val
  with tagswitch(val) as case:
    if case(value_e.Undef):
      raise error.Runtime("$%s isn't defined" % name)
    elif case(value_e.Str):
      return cast(value__Str, UP_val).s
    else:
      # User would have to 'unset HOME' to get rid of exported flag
      raise error.Runtime("$%s should be a string" % name)


def MaybeString(mem, name):
  # type: (Mem, str) -> Optional[str]
  """
  Like GetString(), but doesn't throw an exception.
  """
  try:
    return GetString(mem, name)
  except error.Runtime:
    return None


def GetInteger(mem, name):
  # type: (Mem, str) -> int
  """
  For OPTIND variable used in getopts builtin.  TODO: it could be value.Int() ?
  """
  val = mem.GetValue(name)
  if val.tag_() != value_e.Str:
    raise error.Runtime(
        '$%s should be a string, got %s' % (name, ui.ValType(val)))
  s = cast(value__Str, val).s
  try:
    i = int(s)
  except ValueError:
    raise error.Runtime("$%s doesn't look like an integer, got %r" % (name, s))
  return i
