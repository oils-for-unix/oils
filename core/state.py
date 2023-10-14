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

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.runtime_asdl import (value, value_e, value_t, lvalue,
                                        lvalue_e, lvalue_t, scope_e, scope_t,
                                        HayNode, Cell, FuncValue)
from _devbuild.gen.syntax_asdl import (loc, loc_t, Token, debug_frame,
                                       debug_frame_e, debug_frame_t)
from _devbuild.gen.types_asdl import opt_group_i
from asdl import runtime
from core import error
from core.error import e_usage, e_die
from core import pyos
from core import pyutil
from core import optview
from core import ui
from frontend import consts
from frontend import location
from frontend import match
from mycpp import mylib
from mycpp.mylib import log, print_stderr, tagswitch, iteritems, NewDict
from osh import split
from pylib import os_path
from pylib import path_stat

import libc
import posix_ as posix
from posix_ import X_OK  # translated directly to C macro

from typing import Tuple, List, Dict, Optional, Any, cast, TYPE_CHECKING

if TYPE_CHECKING:
    from _devbuild.gen.option_asdl import option_t
    from _devbuild.gen.runtime_asdl import ProcValue
    from core import alloc
    from core import code
    from osh import sh_expr_eval

# This was derived from bash --norc -c 'argv "$COMP_WORDBREAKS".
# Python overwrites this to something Python-specific in Modules/readline.c, so
# we have to set it back!
# Used in both core/competion.py and osh/state.py
_READLINE_DELIMS = ' \t\n"\'><=;|&(:'

# flags for SetVar
SetReadOnly = 1 << 0
ClearReadOnly = 1 << 1
SetExport = 1 << 2
ClearExport = 1 << 3
SetNameref = 1 << 4
ClearNameref = 1 << 5


class SearchPath(object):
    """For looking up files in $PATH."""

    def __init__(self, mem):
        # type: (Mem) -> None
        self.mem = mem
        self.cache = {}  # type: Dict[str, str]

    def Lookup(self, name, exec_required=True):
        # type: (str, bool) -> Optional[str]
        """Returns the path itself (for relative path), the resolve path, or
        None."""
        if '/' in name:
            if path_stat.exists(name):
                return name
            else:
                return None

        # TODO: Could cache this computation to avoid allocating every time for all
        # the splitting.
        val = self.mem.GetValue('PATH')
        UP_val = val
        if val.tag() == value_e.Str:
            val = cast(value.Str, UP_val)
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

        # Whenever we're sourcing, the 'is-main' builtin will return 1 (false)
        self.to_restore = self.mem.is_main
        self.mem.is_main = False

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.PopSource(self.argv)

        self.mem.is_main = self.to_restore


class ctx_DebugTrap(object):
    """For trap DEBUG."""

    def __init__(self, mem):
        # type: (Mem) -> None
        mem.running_debug_trap = True
        self.mem = mem

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.running_debug_trap = False


class ctx_Option(object):
    """Shopt --unset errexit { false }"""

    def __init__(self, mutable_opts, opt_nums, b):
        # type: (MutableOpts, List[int], bool) -> None
        for opt_num in opt_nums:
            mutable_opts.Push(opt_num, b)
            if opt_num == option_i.errexit:
                mutable_opts.errexit_disabled_tok.append(
                    None)  # it wasn't disabled

        self.mutable_opts = mutable_opts
        self.opt_nums = opt_nums

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        for opt_num in self.opt_nums:  # don't bother to do it in reverse order
            if opt_num == option_i.errexit:
                self.mutable_opts.errexit_disabled_tok.pop()
            self.mutable_opts.Pop(opt_num)


class ctx_AssignBuiltin(object):
    """Local x=$(false) is disallowed."""

    def __init__(self, mutable_opts):
        # type: (MutableOpts) -> None
        self.strict = False
        if mutable_opts.Get(option_i.strict_errexit):
            mutable_opts.Push(option_i._allow_command_sub, False)
            mutable_opts.Push(option_i._allow_process_sub, False)
            self.strict = True

        self.mutable_opts = mutable_opts

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        if self.strict:
            self.mutable_opts.Pop(option_i._allow_command_sub)
            self.mutable_opts.Pop(option_i._allow_process_sub)


class ctx_YshExpr(object):
    """Command sub must fail in 'mystring' ++ $(false)"""

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

    def __init__(self, mutable_opts, b, disabled_tok):
        # type: (MutableOpts, bool, Optional[Token]) -> None

        # If we're disabling it, we need a span ID.  If not, then we should NOT
        # have one.
        assert b == (disabled_tok is None)

        mutable_opts.Push(option_i.errexit, b)
        mutable_opts.errexit_disabled_tok.append(disabled_tok)

        self.strict = False
        if mutable_opts.Get(option_i.strict_errexit):
            mutable_opts.Push(option_i._allow_command_sub, False)
            mutable_opts.Push(option_i._allow_process_sub, False)
            self.strict = True

        self.mutable_opts = mutable_opts

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mutable_opts.errexit_disabled_tok.pop()
        self.mutable_opts.Pop(option_i.errexit)

        if self.strict:
            self.mutable_opts.Pop(option_i._allow_command_sub)
            self.mutable_opts.Pop(option_i._allow_process_sub)


class ctx_Try(object):

    def __init__(self, mutable_opts):
        # type: (MutableOpts) -> None

        mutable_opts.Push(option_i.errexit, True)
        self.mutable_opts = mutable_opts

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mutable_opts.Pop(option_i.errexit)


class ctx_HayNode(object):
    """Haynode builtin makes new names in the tree visible."""

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

        for opt_num in consts.YSH_ALL:
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
        for opt_num in consts.YSH_ALL:
            self.mutable_opts.Pop(opt_num)


class Hay(object):
    """State for DSLs."""

    def __init__(self):
        # type: () -> None
        ch = NewDict()  # type: Dict[str, HayNode]
        self.root_defs = HayNode(ch)
        self.cur_defs = self.root_defs  # Same as ClearDefs()
        self.def_stack = [self.root_defs]

        node = self._MakeOutputNode()
        self.result_stack = [node]  # type: List[Dict[str, value_t]]
        self.output = None  # type: Dict[str, value_t]

    def _MakeOutputNode(self):
        # type: () -> Dict[str, value_t]
        d = NewDict()  # type: Dict[str, value_t]
        d['source'] = value.Null
        d['children'] = value.List([])
        return d

    def PushEval(self):
        # type: () -> None

        # remove previous results
        node = self._MakeOutputNode()
        self.result_stack = [node]

        self.output = None  # remove last result

    def PopEval(self):
        # type: () -> None

        # Save the result
        self.output = self.result_stack[0]

        # Clear results
        node = self._MakeOutputNode()
        self.result_stack = [node]

    def AppendResult(self, d):
        # type: (Dict[str, value_t]) -> None
        """Called by haynode builtin."""
        UP_children = self.result_stack[-1]['children']
        assert UP_children.tag() == value_e.List, UP_children
        children = cast(value.List, UP_children)
        children.items.append(value.Dict(d))

    def Result(self):
        # type: () -> Dict[str, value_t]
        """Called by hay eval and eval_hay()"""
        return self.output

    def HayRegister(self):
        # type: () -> Dict[str, value_t]
        """Called by _hay() function."""
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
                ch = NewDict()  # type: Dict[str, HayNode]
                current.children[name] = HayNode(ch)
            current = current.children[name]

    def Reset(self):
        # type: () -> None

        # reset definitions
        ch = NewDict()  # type: Dict[str, HayNode]
        self.root_defs = HayNode(ch)
        self.cur_defs = self.root_defs

        # reset output
        self.PopEval()

    def Push(self, hay_name):
        # type: (Optional[str]) -> None
        """
        Package cppunit {
        }   # pushes a namespace

        haynode package cppunit {
        }   # just assumes every TYPE 'package' is valid.
        """
        top = self.result_stack[-1]
        # TODO: Store this more efficiently?  See osh/builtin_pure.py
        children = cast(value.List, top['children'])
        last_child = cast(value.Dict, children.items[-1])
        self.result_stack.append(last_child.d)

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
    _SetGroup(opt0_array, consts.YSH_ALL, True)

    no_stack = None  # type: List[bool]
    opt_stacks = [no_stack] * option_i.ARRAY_SIZE  # type: List[List[bool]]

    parse_opts = optview.Parse(opt0_array, opt_stacks)
    return parse_opts


def _AnyOptionNum(opt_name):
    # type: (str) -> option_t
    opt_num = consts.OptionNum(opt_name)
    if opt_num == 0:
        e_usage('got invalid option %r' % opt_name, loc.Missing)

    # Note: we relaxed this for Oil so we can do 'shopt --unset errexit' consistently
    #if opt_num not in consts.SHOPT_OPTION_NUMS:
    #  e_usage("doesn't own option %r (try 'set')" % opt_name)

    return opt_num


def _SetOptionNum(opt_name):
    # type: (str) -> option_t
    opt_num = consts.OptionNum(opt_name)
    if opt_num == 0:
        e_usage('got invalid option %r' % opt_name, loc.Missing)

    if opt_num not in consts.SET_OPTION_NUMS:
        e_usage("invalid option %r (try shopt)" % opt_name, loc.Missing)

    return opt_num


class MutableOpts(object):

    def __init__(self, mem, opt0_array, opt_stacks, opt_hook):
        # type: (Mem, List[bool], List[List[bool]], OptHook) -> None
        self.mem = mem
        self.opt0_array = opt0_array
        self.opt_stacks = opt_stacks
        self.errexit_disabled_tok = []  # type: List[Token]

        # Used for 'set -o vi/emacs'
        self.opt_hook = opt_hook

    def Init(self):
        # type: () -> None

        # This comes after all the 'set' options.
        UP_shellopts = self.mem.GetValue('SHELLOPTS')
        if UP_shellopts.tag(
        ) == value_e.Str:  # Always true in Oil, see Init above
            shellopts = cast(value.Str, UP_shellopts)
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
        """B: False if it's a proc, and True if it's a shell function."""
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
        """Used to disable errexit.

        For bash compatibility in command sub.
        """

        # Like _Getter in core/optview.py
        overlay = self.opt_stacks[opt_num]
        if overlay is None or len(overlay) == 0:
            self.opt0_array[opt_num] = b
        else:
            overlay[-1] = b  # The top value

    def set_interactive(self):
        # type: () -> None
        self._Set(option_i.interactive, True)

    def set_redefine_proc_func(self):
        # type: () -> None
        """For interactive shells."""
        self._Set(option_i.redefine_proc_func, True)

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
                not self.mem.ParsingChangesAllowed()):
            e_die('Syntax options must be set at the top level '
                  '(outside any function)')

        self._Set(opt_num, b)

    def SetDeferredErrExit(self, b):
        # type: (bool) -> None
        """Set the errexit flag, possibly deferring it.

        Implements the unusual POSIX "defer" behavior.  Callers: set -o
        errexit, shopt -s oil:all, oil:upgrade
        """
        #log('Set %s', b)

        # Defer it until we pop by setting the BOTTOM OF THE STACK.
        self.opt0_array[option_i.errexit] = b

    def DisableErrExit(self):
        # type: () -> None
        """Called by core/process.py to implement bash quirks."""
        self._Set(option_i.errexit, False)

    def ErrExitDisabledToken(self):
        # type: () -> Optional[Token]
        """If errexit is disabled by POSIX rules, return Token for construct.

        e.g. the Token for 'if' or '&&' etc.
        """
        # Bug fix: The errexit disabling inherently follows a STACK DISCIPLINE.
        # But we run trap handlers in the MAIN LOOP, which break this.  So just
        # declare that it's never disabled in a trap.
        if self.Get(option_i._running_trap):
            return None

        if len(self.errexit_disabled_tok) == 0:
            return None

        return self.errexit_disabled_tok[-1]

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
        """For set -o, set +o, or shopt -s/-u -o."""
        unused = _SetOptionNum(opt_name)  # validate it
        self._SetOldOption(opt_name, b)

        UP_val = self.mem.GetValue('SHELLOPTS')
        assert UP_val.tag() == value_e.Str, UP_val
        val = cast(value.Str, UP_val)
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
        """For shopt -s/-u and sh -O/+O."""

        # shopt -s all:oil turns on all Oil options, which includes all strict #
        # options
        opt_group = consts.OptionGroupNum(opt_name)
        if opt_group == opt_group_i.YshUpgrade:
            _SetGroup(self.opt0_array, consts.YSH_UPGRADE, b)
            self.SetDeferredErrExit(b)  # Special case
            return

        if opt_group == opt_group_i.YshAll:
            _SetGroup(self.opt0_array, consts.YSH_ALL, b)
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
        """For 'set -o' and 'shopt -p -o'."""
        # TODO: Maybe sort them differently?

        if len(opt_names) == 0:  # if none, supplied, show all
            opt_names = [consts.OptionName(i) for i in consts.SET_OPTION_NUMS]

        for opt_name in opt_names:
            opt_num = _SetOptionNum(opt_name)
            b = self.Get(opt_num)
            print('set %so %s' % ('-' if b else '+', opt_name))

    def ShowShoptOptions(self, opt_names):
        # type: (List[str]) -> None
        """For 'shopt -p'."""

        # Respect option groups.
        opt_nums = []  # type: List[int]
        for opt_name in opt_names:
            opt_group = consts.OptionGroupNum(opt_name)
            if opt_group == opt_group_i.YshUpgrade:
                opt_nums.extend(consts.YSH_UPGRADE)
            elif opt_group == opt_group_i.YshAll:
                opt_nums.extend(consts.YSH_ALL)
            elif opt_group == opt_group_i.StrictAll:
                opt_nums.extend(consts.STRICT_ALL)
            else:
                index = consts.OptionNum(opt_name)
                # Minor incompatibility with bash: we validate everything before
                # printing.
                if index == 0:
                    e_usage('got invalid option %r' % opt_name, loc.Missing)
                opt_nums.append(index)

        if len(opt_names) == 0:
            # If none supplied, show all>
            # TODO: Should this show 'set' options too?
            opt_nums.extend(consts.VISIBLE_SHOPT_NUMS)

        for opt_num in opt_nums:
            b = self.Get(opt_num)
            print('shopt -%s %s' %
                  ('s' if b else 'u', consts.OptionName(opt_num)))


class _ArgFrame(object):
    """Stack frame for arguments array."""

    def __init__(self, argv):
        # type: (List[str]) -> None
        self.argv = argv
        self.num_shifted = 0

    def __repr__(self):
        # type: () -> str
        return '<_ArgFrame %s %d at %x>' % (self.argv, self.num_shifted,
                                            id(self))

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
            return value.Undef

        return value.Str(self.argv[index])

    def GetArgv(self):
        # type: () -> List[str]
        return self.argv[self.num_shifted:]

    def GetNumArgs(self):
        # type: () -> int
        return len(self.argv) - self.num_shifted

    def SetArgv(self, argv):
        # type: (List[str]) -> None
        self.argv = argv
        self.num_shifted = 0


if mylib.PYTHON:

    def _DumpVarFrame(frame):
        # type: (Dict[str, Cell]) -> Any
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
                    val = cast(value.Str, cell.val)
                    cell_json['type'] = 'Str'
                    cell_json['value'] = val.s

                elif case(value_e.BashArray):
                    val = cast(value.BashArray, cell.val)
                    cell_json['type'] = 'BashArray'
                    cell_json['value'] = val.strs

                elif case(value_e.BashAssoc):
                    val = cast(value.BashAssoc, cell.val)
                    cell_json['type'] = 'BashAssoc'
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
        """ For dirs -c """
        del self.stack[:]
        self.stack.append(posix.getcwd())

    def Replace(self, d):
        # type: (str) -> None
        """ For cd / """
        self.stack[-1] = d

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


def _GetWorkingDir():
    # type: () -> str
    """Fallback for pwd and $PWD when there's no 'cd' and no inherited $PWD."""
    try:
        return posix.getcwd()
    except (IOError, OSError) as e:
        e_die("Can't determine working directory: %s" % pyutil.strerror(e))


def _LineNumber(tok):
    # type: (Optional[Token]) -> str
    """ For $BASH_LINENO """
    if tok is None:
        return '-1'
    return str(tok.line.line_num)


if mylib.PYTHON:

    def _AddCallToken(d, token):
        # type: (Dict[str, Any], Optional[Token]) -> None
        if token is None:
            return
        d['call_source'] = ui.GetLineSourceString(token.line)
        d['call_line_num'] = token.line.line_num
        d['call_line'] = token.line.content


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
        mem.SetValue(location.LName(n),
                     value.Str(v),
                     scope_e.GlobalOnly,
                     flags=SetExport)

    # If it's not in the environment, initialize it.  This makes it easier to
    # update later in MutableOpts.

    # TODO: IFS, etc. should follow this pattern.  Maybe need a SysCall
    # interface?  self.syscall.getcwd() etc.

    val = mem.GetValue('SHELLOPTS')
    if val.tag() == value_e.Undef:
        SetGlobalString(mem, 'SHELLOPTS', '')
    # Now make it readonly
    mem.SetValue(location.LName('SHELLOPTS'),
                 None,
                 scope_e.GlobalOnly,
                 flags=SetReadOnly)

    # Usually we inherit PWD from the parent shell.  When it's not set, we may
    # compute it.
    val = mem.GetValue('PWD')
    if val.tag() == value_e.Undef:
        SetGlobalString(mem, 'PWD', _GetWorkingDir())
    # Now mark it exported, no matter what.  This is one of few variables
    # EXPORTED.  bash and dash both do it.  (e.g. env -i -- dash -c env)
    mem.SetValue(location.LName('PWD'),
                 None,
                 scope_e.GlobalOnly,
                 flags=SetExport)

    val = mem.GetValue('PATH')
    if val.tag() == value_e.Undef:
        # Setting PATH to these two dirs match what zsh and mksh do.  bash and dash
        # add {,/usr/,/usr/local}/{bin,sbin}
        SetGlobalString(mem, 'PATH', '/bin:/usr/bin')


def InitMem(mem, environ, version_str):
    # type: (Mem, Dict[str, str], str) -> None
    """Initialize memory with shell defaults.

    Other interpreters could have different builtin variables.
    """
    # TODO: REMOVE this legacy.  ble.sh checks it!
    SetGlobalString(mem, 'OIL_VERSION', version_str)

    SetGlobalString(mem, 'OILS_VERSION', version_str)
    _InitDefaults(mem)
    _InitVarsFromEnv(mem, environ)

    # MUTABLE GLOBAL that's SEPARATE from $PWD.  Used by the 'pwd' builtin, but
    # it can't be modified by users.
    val = mem.GetValue('PWD')
    # should be true since it's exported
    assert val.tag() == value_e.Str, val
    pwd = cast(value.Str, val).s
    mem.SetPwd(pwd)


def InitInteractive(mem):
    # type: (Mem) -> None
    """Initialization that's only done in the interactive/headless shell."""

    # Same default PS1 as bash
    if mem.GetValue('PS1').tag() == value_e.Undef:
        SetGlobalString(mem, 'PS1', r'\s-\v\$ ')


class ctx_FuncCall(object):
    """For func calls."""

    def __init__(self, mem, func):
        # type: (Mem, FuncValue) -> None
        mem.PushCall(func.name, func.parsed.name, None)
        self.mem = mem

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.PopCall(False)


class ctx_ProcCall(object):
    """For proc calls."""

    def __init__(self, mem, mutable_opts, proc, argv):
        # type: (Mem, MutableOpts, ProcValue, List[str]) -> None
        mem.PushCall(proc.name, proc.name_tok, argv)
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
        self.mem.PopCall(True)


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
    """For shvar LANG=C _ESCAPER=posix-sh-word _DIALECT=ninja."""

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
            lval = location.LName(name)  # type: lvalue_t
            # LocalOnly because we are only overwriting the current scope
            old_val = self.mem.GetValue(name, scope_e.LocalOnly)
            self.restore.append((lval, old_val))
            self.mem.SetValue(lval, value.Str(s), scope_e.LocalOnly)

    def _Pop(self):
        # type: () -> None
        for lval, old_val in self.restore:
            if old_val.tag() == value_e.Undef:
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
    """For $_this_dir."""

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
        # type: (str, List[str], alloc.Arena, List[debug_frame_t]) -> None
        """
        Args:
          arena: currently unused
        """
        # circular dep initialized out of line
        self.exec_opts = None  # type: optview.Exec
        self.unsafe_arith = None  # type: sh_expr_eval.UnsafeArith

        self.dollar0 = dollar0
        self.argv_stack = [_ArgFrame(argv)]
        frame = NewDict()  # type: Dict[str, Cell]
        self.var_stack = [frame]

        # The debug_stack isn't strictly necessary for execution.  We use it
        # for crash dumps and for 3 parallel arrays: BASH_SOURCE, FUNCNAME, and
        # BASH_LINENO.
        self.debug_stack = debug_stack

        self.pwd = None  # type: Optional[str]

        self.token_for_line = None  # type: Optional[Token]
        self.loc_for_expr = loc.Missing  # type: loc_t

        self.last_arg = ''  # $_ is initially empty, NOT unset
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

        self.running_debug_trap = False  # set by ctx_DebugTrap()
        self.is_main = True  # we start out in main

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

    def ParsingChangesAllowed(self):
        # type: () -> bool
        """For checking that syntax options are only used at the top level."""

        # DISALLOW proc calls     : they push argv_stack, var_stack, debug_stack
        # ALLOW source foo.sh arg1: pushes argv_stack, debug_stack
        # ALLOW FOO=bar           : pushes var_stack
        return len(self.var_stack) == 1 or len(self.argv_stack) == 1

    def Dump(self):
        # type: () -> Tuple[Any, Any, Any]
        """Copy state before unwinding the stack."""
        if mylib.PYTHON:
            var_stack = [_DumpVarFrame(frame) for frame in self.var_stack]
            argv_stack = [frame.Dump() for frame in self.argv_stack]

            debug_stack = []  # type: List[Dict[str, Any]]
            for frame in reversed(self.debug_stack):
                UP_frame = frame
                with tagswitch(frame) as case:
                    if case(debug_frame_e.Call):
                        frame = cast(debug_frame.Call, UP_frame)
                        d = {'type': 'Call', 'func_name': frame.func_name}
                        _AddCallToken(d, frame.call_tok)
                        # TODO: Add def_tok

                    elif case(debug_frame_e.Source):
                        frame = cast(debug_frame.Source, UP_frame)
                        d = {
                            'type': 'Source',
                            'source_name': frame.source_name
                        }
                        _AddCallToken(d, frame.call_tok)

                    elif case(debug_frame_e.Main):
                        frame = cast(debug_frame.Main, UP_frame)
                        d = {'type': 'Main', 'dollar0': frame.dollar0}

                debug_stack.append(d)
            return var_stack, argv_stack, debug_stack

        raise AssertionError()

    def SetLastArgument(self, s):
        # type: (str) -> None
        """For $_"""
        self.last_arg = s

    def SetTokenForLine(self, tok):
        # type: (Token) -> None
        """Set a token to compute $LINENO

        This means it should be set on SimpleCommand, ShAssignment, ((, [[,
        case, etc. -- anything that evaluates a word.  Example: there was a bug
        with 'case $LINENO'

        This token also used as a "least-specific" / fallback location for
        errors in ExecuteAndCatch().

        Although most of that should be taken over by 'with ui.ctx_Location()`,
        for the errfmt.
        """
        if self.running_debug_trap:
            return

        if tok.span_id == runtime.NO_SPID:
            # NOTE: This happened in the osh-runtime benchmark for yash.
            log('Warning: span_id undefined in SetTokenForLine')

            #import traceback
            #traceback.print_stack()
            return

        self.token_for_line = tok

    def SetLocationForExpr(self, blame_loc):
        # type: (loc_t) -> None
        """
        A more specific fallback location, like the $[ in 

            echo $[len(42)]
        """
        self.loc_for_expr = blame_loc

    def GetFallbackLocation(self):
        # type: () -> loc_t

        if self.loc_for_expr != loc.Missing:  # more specific
            return self.loc_for_expr

        if self.token_for_line:  # less specific
            return self.token_for_line

        return loc.Missing

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

    def SetSimplePipeStatus(self, status):
        # type: (int) -> None

        # Optimization to avoid allocations
        top = self.pipe_status[-1]
        if len(top) == 1:
            top[0] = status
        else:
            self.pipe_status[-1] = [status]

    def SetProcessSubStatus(self, x):
        # type: (List[int]) -> None
        self.process_sub_status[-1] = x

    #
    # Call Stack
    #

    def PushCall(self, func_name, def_tok, argv):
        # type: (str, Token, Optional[List[str]]) -> None
        """Push argv, var, and debug stack frames.

        Currently used for proc and func calls.  TODO: New func evaluator may
        not use it.

        Args:
          def_tok: Token where proc or func was defined, used to compute
                   BASH_SOURCE.
        """
        if argv is not None:
            self.argv_stack.append(_ArgFrame(argv))
        frame = NewDict()  # type: Dict[str, Cell]
        self.var_stack.append(frame)

        # Filename, or [ stdin ], etc.
        source_str = ui.GetLineSourceString(def_tok.line)

        # self.token_for_line can be None?
        self.debug_stack.append(
            debug_frame.Call(self.token_for_line, def_tok, func_name))

    def PopCall(self, should_pop_argv_stack):
        # type: (bool) -> None
        """
        Args:
          should_pop_argv_stack: Pass False if PushCall was given None for argv
        """
        self.debug_stack.pop()

        self.var_stack.pop()

        if should_pop_argv_stack:
            self.argv_stack.pop()

    def ShouldRunDebugTrap(self):
        # type: () -> bool

        # Don't recursively run DEBUG trap
        if self.running_debug_trap:
            return False

        # Don't run it inside functions
        if len(self.var_stack) > 1:
            return False

        return True

    def PushSource(self, source_name, argv):
        # type: (str, List[str]) -> None
        """ For 'source foo.sh 1 2 3' """
        if len(argv):
            self.argv_stack.append(_ArgFrame(argv))

        # self.token_for_line can be None?
        self.debug_stack.append(
            debug_frame.Source(self.token_for_line, source_name))

    def PopSource(self, argv):
        # type: (List[str]) -> None
        self.debug_stack.pop()

        if len(argv):
            self.argv_stack.pop()

    def PushTemp(self):
        # type: () -> None
        """For the temporary scope in 'FOO=bar BAR=baz echo'.

        Also for PS4 evaluation with more variables.
        """
        # We don't want the 'read' builtin to write to this frame!
        frame = NewDict()  # type: Dict[str, Cell]
        self.var_stack.append(frame)

    def PopTemp(self):
        # type: () -> None
        self.var_stack.pop()

    def TopNamespace(self):
        # type: () -> Dict[str, Cell]
        """For eval_to_dict()."""
        return self.var_stack[-1]

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
        # type: () -> value.Str
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
                return value.Undef  # could be an error

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
        # type: (str, scope_t) -> Tuple[Optional[Cell], Dict[str, Cell]]
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
            no_cell = None  # type: Optional[Cell]
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
        # type: (str, scope_t, bool, Optional[List[str]]) -> Tuple[Optional[Cell], Dict[str, Cell], str]
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
                val = cast(value.Str, UP_val)
                new_name = val.s

            else:
                # SetValue() protects the invariant that nameref is Undef or Str
                raise AssertionError(val.tag())

        # TODO: Respect eval_unsafe_arith here (issue 881).  See how it's done in
        # 'printf -v' with MakeArithParser
        if not match.IsValidVarName(new_name):
            # e.g. '#' or '1' or ''
            if self.exec_opts.strict_nameref():
                e_die('nameref %r contains invalid variable name %r' %
                      (name, new_name))
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
        cell, name_map, cell_name = self._ResolveNameOrRef(new_name,
                                                           which_scopes,
                                                           False,
                                                           ref_trail=ref_trail)
        return cell, name_map, cell_name

    def IsBashAssoc(self, name):
        # type: (str) -> bool
        """Returns whether a name resolve to a cell with an associative array.

        We need to know this to evaluate the index expression properly
        -- should it be coerced to an integer or not?
        """
        cell, _, _ = self._ResolveNameOrRef(name, self.ScopesForReading(),
                                            False)
        if cell:
            if cell.val.tag() == value_e.BashAssoc:  # foo=([key]=value)
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
                lval = cast(lvalue.Named, UP_lval)
                assert lval.name is not None

                if keyword_id == Id.KW_SetRef:
                    # Hidden interpreter var with __ prefix.  Matches proc call in
                    # osh/cmd_eval.py
                    lval.name = '__' + lval.name  # Mutating arg lval!  Happens to be OK

                if flags & SetNameref or flags & ClearNameref:
                    # declare -n ref=x  # refers to the ref itself
                    cell, name_map = self._ResolveNameOnly(
                        lval.name, which_scopes)
                    cell_name = lval.name
                else:
                    # ref=x  # mutates THROUGH the reference

                    # Note on how to implement declare -n ref='a[42]'
                    # 1. Call _ResolveNameOnly()
                    # 2. If cell.nameref, call self.unsafe_arith.ParseVarRef() ->
                    #    BracedVarSub
                    # 3. Turn BracedVarSub into an lvalue, and call
                    #    self.unsafe_arith.SetValue() wrapper with ref_trail
                    cell, name_map, cell_name = self._ResolveNameOrRef(
                        lval.name, which_scopes, is_setref)

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
                            e_die("Can't assign to readonly value %r" %
                                  lval.name)
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
                        val = value.Undef  # export foo, readonly foo

                    cell = Cell(bool(flags & SetExport),
                                bool(flags & SetReadOnly),
                                bool(flags & SetNameref), val)
                    name_map[cell_name] = cell

                # Maintain invariant that only strings and undefined cells can be
                # exported.
                assert cell.val is not None, cell

                if cell.val.tag() not in (value_e.Undef, value_e.Str):
                    if cell.exported:
                        e_die("Only strings can be exported"
                              )  # TODO: error context
                    if cell.nameref:
                        e_die("nameref must be a string")

            elif case(lvalue_e.Indexed):
                lval = cast(lvalue.Indexed, UP_lval)
                assert isinstance(lval.index, int), lval

                # There is no syntax 'declare a[x]'
                assert val is not None, val

                # TODO: relax this for Oil
                assert val.tag() == value_e.Str, val
                rval = cast(value.Str, val)

                # 'setref' array[index] not implemented here yet
                #if keyword_id == Id.KW_SetRef:
                #  lval.name = '__' + lval.name

                # Note: location could be a[x]=1 or (( a[ x ] = 1 ))
                left_loc = lval.blame_loc

                # bash/mksh have annoying behavior of letting you do LHS assignment to
                # Undef, which then turns into an INDEXED array.  (Undef means that set
                # -o nounset fails.)
                cell, name_map, _ = self._ResolveNameOrRef(
                    lval.name, which_scopes, is_setref)
                if not cell:
                    self._BindNewArrayWithEntry(name_map, lval, rval, flags)
                    return

                if cell.readonly:
                    e_die("Can't assign to readonly array", left_loc)

                UP_cell_val = cell.val
                # undef[0]=y is allowed
                with tagswitch(UP_cell_val) as case2:
                    if case2(value_e.Undef):
                        self._BindNewArrayWithEntry(name_map, lval, rval,
                                                    flags)
                        return

                    elif case2(value_e.Str):
                        # s=x
                        # s[1]=y  # invalid
                        e_die("Can't assign to items in a string", left_loc)

                    elif case2(value_e.BashArray):
                        cell_val = cast(value.BashArray, UP_cell_val)
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
                # BashAssoc shouldn because we query IsBashAssoc before evaluating
                # sh_lhs_expr.  Could conslidate with s[i] case above
                e_die(
                    "Value of type %s can't be indexed" % ui.ValType(cell.val),
                    left_loc)

            elif case(lvalue_e.Keyed):
                lval = cast(lvalue.Keyed, UP_lval)
                # There is no syntax 'declare A["x"]'
                assert val is not None, val
                assert val.tag() == value_e.Str, val
                rval = cast(value.Str, val)

                left_loc = lval.blame_loc

                cell, name_map, _ = self._ResolveNameOrRef(
                    lval.name, which_scopes, is_setref)
                if cell.readonly:
                    e_die("Can't assign to readonly associative array",
                          left_loc)

                # We already looked it up before making the lvalue
                assert cell.val.tag() == value_e.BashAssoc, cell
                cell_val2 = cast(value.BashAssoc, cell.val)

                cell_val2.d[lval.key] = rval.s

            else:
                raise AssertionError(lval.tag())

    def _BindNewArrayWithEntry(self, name_map, lval, val, flags):
        # type: (Dict[str, Cell], lvalue.Indexed, value.Str, int) -> None
        """Fill 'name_map' with a new indexed array entry."""
        no_str = None  # type: Optional[str]
        items = [no_str] * lval.index
        items.append(val.s)
        new_value = value.BashArray(items)

        # arrays can't be exported; can't have BashAssoc flag
        readonly = bool(flags & SetReadOnly)
        name_map[lval.name] = Cell(False, readonly, False, new_value)

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
        """Used by the WordEvaluator, ArithEvaluator, ysh/expr_eval.py, etc.

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
            items = [value.Str(s)
                     for s in self.GetArgv()]  # type: List[value_t]
            return value.List(items)

        # "Registers"
        if name == '_status':
            return value.Int(self.TryStatus())

        if name == '_this_dir':
            if len(self.this_dir) == 0:
                # e.g. osh -c '' doesn't have it set
                # Should we give a custom error here?
                # If you're at the interactive shell, 'source mymodule.oil' will still
                # work because 'source' sets it.
                return value.Undef
            else:
                return value.Str(self.this_dir[-1])  # top of stack

        if name == 'PIPESTATUS':
            strs2 = [str(i) for i in self.pipe_status[-1]]  # type: List[str]
            return value.BashArray(strs2)

        if name == '_pipeline_status':
            items = [value.Int(i) for i in self.pipe_status[-1]]
            return value.List(items)

        if name == '_process_sub_status':  # Oil naming convention
            items = [value.Int(i) for i in self.process_sub_status[-1]]
            return value.List(items)

        if name == 'BASH_REMATCH':
            return value.BashArray(self.regex_matches[-1])  # top of stack

        # Do lookup of system globals before looking at user variables.  Note: we
        # could optimize this at compile-time like $?.  That would break
        # ${!varref}, but it's already broken for $?.

        if name == 'FUNCNAME':
            # bash wants it in reverse order.  This is a little inefficient but we're
            # not depending on deque().
            strs = []  # type: List[str]
            for frame in reversed(self.debug_stack):
                UP_frame = frame
                with tagswitch(frame) as case:
                    if case(debug_frame_e.Call):
                        frame = cast(debug_frame.Call, UP_frame)
                        strs.append(frame.func_name)

                    elif case(debug_frame_e.Source):
                        # bash doesn't tell you the filename sourced
                        strs.append('source')

                    elif case(debug_frame_e.Main):
                        strs.append('main')  # also bash behavior

            return value.BashArray(strs)  # TODO: Reuse this object too?

        # $BASH_SOURCE and $BASH_LINENO have OFF BY ONE design bugs:
        #
        # ${BASH_LINENO[$i]} is the line number in the source file
        # (${BASH_SOURCE[$i+1]}) where ${FUNCNAME[$i]} was called (or
        # ${BASH_LINENO[$i-1]} if referenced within another shell function).
        #
        # https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html

        if name == 'BASH_SOURCE':
            strs = []
            for frame in reversed(self.debug_stack):
                UP_frame = frame
                with tagswitch(frame) as case:
                    if case(debug_frame_e.Call):
                        frame = cast(debug_frame.Call, UP_frame)

                        # Weird bash behavior
                        assert frame.def_tok.line is not None
                        source_str = ui.GetLineSourceString(frame.def_tok.line)
                        strs.append(source_str)

                    elif case(debug_frame_e.Source):
                        frame = cast(debug_frame.Source, UP_frame)
                        # Is this right?
                        strs.append(frame.source_name)

                    elif case(debug_frame_e.Main):
                        frame = cast(debug_frame.Main, UP_frame)
                        strs.append(frame.dollar0)

            return value.BashArray(strs)  # TODO: Reuse this object too?

        if name == 'BASH_LINENO':
            strs = []
            for frame in reversed(self.debug_stack):
                UP_frame = frame
                with tagswitch(frame) as case:
                    if case(debug_frame_e.Call):
                        frame = cast(debug_frame.Call, UP_frame)
                        strs.append(_LineNumber(frame.call_tok))

                    elif case(debug_frame_e.Source):
                        frame = cast(debug_frame.Source, UP_frame)
                        strs.append(_LineNumber(frame.call_tok))

                    elif case(debug_frame_e.Main):
                        # Bash does this to line up with 'main'
                        strs.append('0')

            return value.BashArray(strs)  # TODO: Reuse this object too?

        if name == 'LINENO':
            assert self.token_for_line is not None
            # Reuse object with mutation
            # TODO: maybe use interned GetLineNumStr?
            self.line_num.s = str(self.token_for_line.line.line_num)
            return self.line_num

        if name == 'BASHPID':  # TODO: Oil name for it
            return value.Str(str(posix.getpid()))

        if name == '_':
            return value.Str(self.last_arg)

        # In the case 'declare -n ref='a[42]', the result won't be a cell.  Idea to
        # fix this:
        # 1. Call self.unsafe_arith.ParseVarRef() -> BracedVarSub
        # 2. Call self.unsafe_arith.GetNameref(bvs_part), and get a value_t
        #    We still need a ref_trail to detect cycles.
        cell, _, _ = self._ResolveNameOrRef(name, which_scopes, False)
        if cell:
            return cell.val

        return value.Undef

    def GetCell(self, name, which_scopes=scope_e.Shopt):
        # type: (str, scope_t) -> Cell
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
                lval = cast(lvalue.Named, UP_lval)
                var_name = lval.name
            elif case(lvalue_e.Indexed):  # unset 'a[1]'
                lval = cast(lvalue.Indexed, UP_lval)
                var_name = lval.name
            elif case(lvalue_e.Keyed):  # unset 'A["K"]'
                lval = cast(lvalue.Keyed, UP_lval)
                var_name = lval.name
            else:
                raise AssertionError()

        if which_scopes == scope_e.Shopt:
            which_scopes = self.ScopesForWriting()

        cell, name_map, cell_name = self._ResolveNameOrRef(
            var_name, which_scopes, False)
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
                #   name_map[cell_name].val = value.Undef
                #   cell.exported = False

                # This should never happen because we do recursive lookups of namerefs.
                assert not cell.nameref, cell

            elif case(lvalue_e.Indexed):  # unset 'a[1]'
                lval = cast(lvalue.Indexed, UP_lval)
                # Note: Setting an entry to None and shifting entries are pretty
                # much the same in shell.

                val = cell.val
                UP_val = val
                if val.tag() != value_e.BashArray:
                    raise error.Runtime("%r isn't an array" % var_name)

                val = cast(value.BashArray, UP_val)
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
                lval = cast(lvalue.Keyed, UP_lval)

                val = cell.val
                UP_val = val

                # note: never happens because of mem.IsBashAssoc test for lvalue.Keyed
                #if val.tag() != value_e.BashAssoc:
                #  raise error.Runtime("%r isn't an associative array" % lval.name)

                val = cast(value.BashAssoc, UP_val)
                mylib.dict_erase(val.d, lval.key)

            else:
                raise AssertionError(lval)

        return True

    def ScopesForReading(self):
        # type: () -> scope_t
        """Read scope."""
        return (scope_e.Dynamic
                if self.exec_opts.dynamic_scope() else scope_e.LocalOrGlobal)

    def ScopesForWriting(self):
        # type: () -> scope_t
        """Write scope."""
        return (scope_e.Dynamic
                if self.exec_opts.dynamic_scope() else scope_e.LocalOnly)

    def ClearFlag(self, name, flag):
        # type: (str, int) -> bool
        """Used for export -n.

        We don't use SetValue() because even if rval is None, it will
        make an Undef value in a scope.
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
                # changed to BashArray, also clear its 'exported' flag.
                if cell.exported and cell.val.tag() == value_e.Str:
                    val = cast(value.Str, cell.val)
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
        """Get all variables and their values, for 'set' builtin."""
        result = {}  # type: Dict[str, str]
        for scope in self.var_stack:
            for name, cell in iteritems(scope):
                # TODO: Show other types?
                val = cell.val
                if val.tag() == value_e.Str:
                    str_val = cast(value.Str, val)
                    result[name] = str_val.s
        return result

    def GetAllCells(self, which_scopes):
        # type: (scope_t) -> Dict[str, Cell]
        """Get all variables and their values, for 'set' builtin."""
        result = {}  # type: Dict[str, Cell]

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
    """Like 'setvar' (scope_e.LocalOnly), unless dynamic scope is on.

    That is, it respects shopt --unset dynamic_scope.

    Used for assignment builtins, (( a = b )), {fd}>out, ${x=}, etc.
    """
    which_scopes = mem.ScopesForWriting()
    mem.SetValue(lval, val, which_scopes, flags=flags)


def BuiltinSetValue(mem, lval, val):
    # type: (Mem, lvalue_t, value_t) -> None
    """Equivalent of x=$y or setref x = y.

    Called by BuiltinSetString and BuiltinSetArray Used directly by
    printf -v because it can mutate an array
    """
    mem.SetValue(lval, val, mem.ScopesForWriting())


def BuiltinSetString(mem, name, s):
    # type: (Mem, str, str) -> None
    """Set a string by looking up the stack.

    # Equivalent of: proc p(:myref) {   setref myref = 's' }

    Used for 'read', 'getopts', completion builtins, etc.
    """
    assert isinstance(s, str)
    BuiltinSetValue(mem, location.LName(name), value.Str(s))


def BuiltinSetArray(mem, name, a):
    # type: (Mem, str, List[str]) -> None
    """Set an array by looking up the stack.

    # Equivalent of: proc p(:myref) {   setref myref = %(a b c) }

    Used by compadjust, read -a, etc.
    """
    assert isinstance(a, list)
    BuiltinSetValue(mem, location.LName(name), value.BashArray(a))


def SetGlobalString(mem, name, s):
    # type: (Mem, str, str) -> None
    """Helper for completion, etc."""
    assert isinstance(s, str)
    val = value.Str(s)
    mem.SetValue(location.LName(name), val, scope_e.GlobalOnly)


def SetGlobalArray(mem, name, a):
    # type: (Mem, str, List[str]) -> None
    """Used by completion, shell initialization, etc."""
    assert isinstance(a, list)
    mem.SetValue(location.LName(name), value.BashArray(a), scope_e.GlobalOnly)


def ExportGlobalString(mem, name, s):
    # type: (Mem, str, str) -> None
    """Helper for completion, $PWD, $OLDPWD, etc."""
    assert isinstance(s, str)
    val = value.Str(s)
    mem.SetValue(location.LName(name),
                 val,
                 scope_e.GlobalOnly,
                 flags=SetExport)


#
# Wrappers to Get Variables
#


def GetString(mem, name):
    # type: (Mem, str) -> str
    """Wrapper around GetValue().  Check that HOME, PWD, OLDPWD, etc. are
    strings. bash doesn't have these errors because ${array} is ${array[0]}.

    TODO: We could also check this when you're storing variables?
    """
    val = mem.GetValue(name)
    UP_val = val
    with tagswitch(val) as case:
        if case(value_e.Undef):
            raise error.Runtime("$%s isn't defined" % name)
        elif case(value_e.Str):
            return cast(value.Str, UP_val).s
        else:
            # User would have to 'unset HOME' to get rid of exported flag
            raise error.Runtime("$%s should be a string" % name)


def MaybeString(mem, name):
    # type: (Mem, str) -> Optional[str]
    """Like GetString(), but doesn't throw an exception."""
    try:
        return GetString(mem, name)
    except error.Runtime:
        return None


def GetInteger(mem, name):
    # type: (Mem, str) -> int
    """For OPTIND variable used in getopts builtin.

    TODO: it could be value.Int() ?
    """
    val = mem.GetValue(name)
    if val.tag() != value_e.Str:
        raise error.Runtime('$%s should be a string, got %s' %
                            (name, ui.ValType(val)))
    s = cast(value.Str, val).s
    try:
        i = int(s)
    except ValueError:
        raise error.Runtime("$%s doesn't look like an integer, got %r" %
                            (name, s))
    return i
