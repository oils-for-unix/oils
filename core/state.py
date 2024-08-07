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
import time as time_  # avoid name conflict

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.runtime_asdl import (scope_e, scope_t, Cell)
from _devbuild.gen.syntax_asdl import (loc, loc_t, Token, debug_frame,
                                       debug_frame_e, debug_frame_t)
from _devbuild.gen.types_asdl import opt_group_i
from _devbuild.gen.value_asdl import (value, value_e, value_t, sh_lvalue,
                                      sh_lvalue_e, sh_lvalue_t, LeftName,
                                      y_lvalue_e, regex_match, regex_match_e,
                                      regex_match_t, RegexMatch)
from core import error
from core.error import e_usage, e_die
from core import num
from core import pyos
from core import pyutil
from core import optview
from display import ui
from core import util
from frontend import consts
from frontend import location
from frontend import match
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import (log, print_stderr, str_switch, tagswitch, iteritems,
                         NewDict)
from osh import split
from pylib import os_path
from pylib import path_stat

import libc
import posix_ as posix
from posix_ import X_OK  # translated directly to C macro

from typing import Tuple, List, Dict, Optional, Any, cast, TYPE_CHECKING

if TYPE_CHECKING:
    from _devbuild.gen.option_asdl import option_t
    from core import alloc
    from osh import sh_expr_eval

_ = log

# This was derived from bash --norc -c 'argv "$COMP_WORDBREAKS".
# Python overwrites this to something Python-specific in Modules/readline.c, so
# we have to set it back!
# Used in both core/competion.py and osh/state.py
_READLINE_DELIMS = ' \t\n"\'><=;|&(:'

# flags for mem.SetValue()
SetReadOnly = 1 << 0
ClearReadOnly = 1 << 1
SetExport = 1 << 2
ClearExport = 1 << 3
SetNameref = 1 << 4
ClearNameref = 1 << 5


def LookupExecutable(name, path_dirs, exec_required=True):
    # type: (str, List[str], bool) -> Optional[str]
    """
    Returns either
    - the name if it's a relative path that exists
    - the executable name resolved against path_dirs
    - None if not found
    """
    if len(name) == 0:  # special case for "$(true)"
        return None

    if '/' in name:
        return name if path_stat.exists(name) else None

    for path_dir in path_dirs:
        full_path = os_path.join(path_dir, name)
        if exec_required:
            found = posix.access(full_path, X_OK)
        else:
            found = path_stat.exists(full_path)

        if found:
            return full_path

    return None


class SearchPath(object):
    """For looking up files in $PATH."""

    def __init__(self, mem):
        # type: (Mem) -> None
        self.mem = mem
        self.cache = {}  # type: Dict[str, str]

    def _GetPath(self):
        # type: () -> List[str]

        # TODO: Could cache this to avoid split() allocating all the time.
        val = self.mem.GetValue('PATH')
        UP_val = val
        if val.tag() == value_e.Str:
            val = cast(value.Str, UP_val)
            return val.s.split(':')
        else:
            return []  # treat as empty path

    def LookupOne(self, name, exec_required=True):
        # type: (str, bool) -> Optional[str]
        """
        Returns the path itself (if relative path), the resolved path, or None.
        """
        return LookupExecutable(name,
                                self._GetPath(),
                                exec_required=exec_required)

    def LookupReflect(self, name, do_all):
        # type: (str, bool) -> List[str]
        """
        Like LookupOne(), with an option for 'type -a' to return all paths.
        """
        if len(name) == 0:  # special case for "$(true)"
            return []

        if '/' in name:
            if path_stat.exists(name):
                return [name]
            else:
                return []

        results = []  # type: List[str]
        for path_dir in self._GetPath():
            full_path = os_path.join(path_dir, name)
            if path_stat.exists(full_path):
                results.append(full_path)
                if not do_all:
                    return results

        return results

    def CachedLookup(self, name):
        # type: (str) -> Optional[str]
        #log('name %r', name)
        if name in self.cache:
            return self.cache[name]

        full_path = self.LookupOne(name)
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


class ctx_ErrTrap(object):
    """For trap ERR."""

    def __init__(self, mem):
        # type: (Mem) -> None
        mem.running_err_trap = True
        self.mem = mem

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.running_err_trap = False


class ctx_Option(object):
    """Shopt --unset errexit { false }"""

    def __init__(self, mutable_opts, opt_nums, b):
        # type: (MutableOpts, List[int], bool) -> None
        for opt_num in opt_nums:
            mutable_opts.Push(opt_num, b)
            if opt_num == option_i.errexit:
                # it wasn't disabled
                mutable_opts.errexit_disabled_tok.append(None)

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

        # Similar to $LIB_OSH/bash-strict.sh

        # TODO: consider errexit:all group, or even ysh:all
        # It would be nice if this were more efficient
        mutable_opts.Push(option_i.command_sub_errexit, True)
        mutable_opts.Push(option_i.errexit, True)
        mutable_opts.Push(option_i.pipefail, True)
        mutable_opts.Push(option_i.inherit_errexit, True)
        mutable_opts.Push(option_i.strict_errexit, True)

        # What about nounset?  This has a similar pitfall -- it's not running
        # like YSH.
        # e.g. var x = $(echo $zz)

        self.mutable_opts = mutable_opts

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mutable_opts.Pop(option_i.command_sub_errexit)
        self.mutable_opts.Pop(option_i.errexit)
        self.mutable_opts.Pop(option_i.pipefail)
        self.mutable_opts.Pop(option_i.inherit_errexit)
        self.mutable_opts.Pop(option_i.strict_errexit)


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
        # Always true in Oil, see Init above
        if UP_shellopts.tag() == value_e.Str:
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

    def ErrExitIsDisabled(self):
        # type: () -> bool
        """
        Similar to ErrExitDisabledToken, for ERR trap
        """
        if len(self.errexit_disabled_tok) == 0:
            return False

        return self.errexit_disabled_tok[-1] is not None

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

    def Dump(self):
        # type: () -> Dict[str, value_t]
        items = [value.Str(s) for s in self.argv]  # type: List[value_t]
        argv = value.List(items)
        return {
            'argv': argv,
            'num_shifted': num.ToBig(self.num_shifted),
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


def _DumpVarFrame(frame):
    # type: (Dict[str, Cell]) -> Dict[str, value_t]
    """Dump the stack frame as reasonably compact and readable JSON."""

    vars_json = {}  # type: Dict[str, value_t]
    for name, cell in iteritems(frame):
        cell_json = {}  # type: Dict[str, value_t]

        buf = mylib.BufWriter()
        if cell.exported:
            buf.write('x')
        if cell.readonly:
            buf.write('r')
        flags = buf.getvalue()
        if len(flags):
            cell_json['flags'] = value.Str(flags)

        # TODO:
        # - Use packle for crash dumps!  Then we can represent object cycles
        #   - Right now the JSON serializer will probably crash
        #   - although BashArray and BashAssoc may need 'type' tags
        #     - they don't round trip correctly
        #     - maybe add value.Tombstone here or something?
        #   - value.{Func,Eggex,...} may have value.Tombstone and
        #   vm.ValueIdString()?

        with tagswitch(cell.val) as case:
            if case(value_e.Undef):
                cell_json['val'] = value.Null

            elif case(value_e.Str, value_e.BashArray, value_e.BashAssoc):
                cell_json['val'] = cell.val

            else:
                # TODO: should we show the object ID here?
                pass

        vars_json[name] = value.Dict(cell_json)

    return vars_json


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


def _AddCallToken(d, token):
    # type: (Dict[str, value_t], Optional[Token]) -> None
    if token is None:
        return
    d['call_source'] = value.Str(ui.GetLineSourceString(token.line))
    d['call_line_num'] = num.ToBig(token.line.line_num)
    d['call_line'] = value.Str(token.line.content)


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
        mem.SetNamed(location.LName(n),
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
    mem.SetNamed(location.LName('SHELLOPTS'),
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
    mem.SetNamed(location.LName('PWD'),
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

    # The source builtin understands '///' to mean "relative to embedded stdlib"
    SetGlobalString(mem, 'LIB_OSH', '///osh')
    SetGlobalString(mem, 'LIB_YSH', '///ysh')

    # - C spells it NAN
    # - JavaScript spells it NaN
    # - Python 2 has float('nan'), while Python 3 has math.nan.
    #
    # - libc prints the strings 'nan' and 'inf'
    # - Python 3 prints the strings 'nan' and 'inf'
    # - JavaScript prints 'NaN' and 'Infinity', which is more stylized
    _SetGlobalValue(mem, 'NAN', value.Float(pyutil.nan()))
    _SetGlobalValue(mem, 'INFINITY', value.Float(pyutil.infinity()))

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
        # type: (Mem, value.Func) -> None

        frame = NewDict()  # type: Dict[str, Cell]
        mem.var_stack.append(frame)

        mem.PushCall(func.name, func.parsed.name)
        self.mem = mem

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.PopCall()
        self.mem.var_stack.pop()


class ctx_ProcCall(object):
    """For proc calls, including shell functions."""

    def __init__(self, mem, mutable_opts, proc, argv):
        # type: (Mem, MutableOpts, value.Proc, List[str]) -> None

        # TODO:
        # - argv stack shouldn't be used for procs
        #   - we can bind a real variable @A if we want
        # - procs should be in the var namespace
        #
        # should we separate procs and shell functions?
        # - dynamic scope is one difference
        # - '$@" shift etc. are another difference

        frame = NewDict()  # type: Dict[str, Cell]

        assert argv is not None
        if proc.sh_compat:
            # shell function
            mem.argv_stack.append(_ArgFrame(argv))
        else:
            # procs
            # - open: is equivalent to ...ARGV
            # - closed: ARGV is empty list
            frame['ARGV'] = _MakeArgvCell(argv)

        mem.var_stack.append(frame)

        mem.PushCall(proc.name, proc.name_tok)

        # Dynamic scope is only for shell functions
        mutable_opts.PushDynamicScope(proc.sh_compat)

        # It may have been disabled with ctx_ErrExit for 'if echo $(false)', but
        # 'if p' should be allowed.
        self.mem = mem
        self.mutable_opts = mutable_opts
        self.sh_compat = proc.sh_compat

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mutable_opts.PopDynamicScope()
        self.mem.PopCall()
        self.mem.var_stack.pop()

        if self.sh_compat:
            self.mem.argv_stack.pop()


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


class ctx_Registers(object):
    """For $PS1, $PS4, $PROMPT_COMMAND, traps, and headless EVAL.

    This is tightly coupled to state.Mem, so it's not in builtin/pure_ysh.
    """

    def __init__(self, mem):
        # type: (Mem) -> None

        # Because some prompts rely on the status leaking.  See issue #853.
        # PS1 also does.
        last = mem.last_status[-1]
        mem.last_status.append(last)
        mem.try_status.append(0)
        mem.try_error.append(value.Dict({}))

        # TODO: We should also copy these values!  Turn the whole thing into a
        # frame.
        mem.pipe_status.append([])
        mem.process_sub_status.append([])

        mem.regex_match.append(regex_match.No)

        self.mem = mem

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.regex_match.pop()

        self.mem.process_sub_status.pop()
        self.mem.pipe_status.pop()

        self.mem.try_error.pop()
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


def _MakeArgvCell(argv):
    # type: (List[str]) -> Cell
    items = [value.Str(a) for a in argv]  # type: List[value_t]
    return Cell(False, False, False, value.List(items))


class ctx_Eval(object):
    """Push temporary variable frame and override $0, $1, $2, etc."""

    def __init__(self, mem, dollar0, pos_args, vars):
        # type: (Mem, Optional[str], Optional[List[str]], Optional[Dict[str, value_t]]) -> None
        if pos_args is None:
            self.pushed_pos_args = False
        else:
            self.pushed_pos_args = True
            mem.argv_stack.append(_ArgFrame(pos_args))

        # $0 needs to have lexical scoping. So we store it with other locals.
        # As "0" cannot be parsed as an lvalue, we can safely store arg0 there.
        if dollar0 is None:
            self.pushed_dollar0 = False
        else:
            self.pushed_dollar0 = True
            assert mem.GetValue("0", scope_e.LocalOnly).tag() == value_e.Undef
            self.lval = LeftName("0", loc.Missing)
            mem.SetLocalName(self.lval, value.Str(dollar0))

        if vars is None:
            self.pushed_vars = False
        else:
            self.pushed_vars = True

            frame = {}  # type: Dict[str, Cell]
            for name in vars:
                frame[name] = Cell(False, False, False, vars[name])

            mem.var_stack.append(frame)

        self.mem = mem

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value_, traceback):
        # type: (Any, Any, Any) -> None
        if self.pushed_vars:
            self.mem.var_stack.pop()

        if self.pushed_pos_args:
            self.mem.argv_stack.pop()

        if self.pushed_dollar0:
            self.mem.SetLocalName(self.lval, value.Undef)


class Mem(object):
    """For storing variables.

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
        # If you only use YSH procs and funcs, this will remain at length 1.
        self.argv_stack = [_ArgFrame(argv)]

        frame = NewDict()  # type: Dict[str, Cell]

        frame['ARGV'] = _MakeArgvCell(argv)

        self.var_stack = [frame]

        # The debug_stack isn't strictly necessary for execution.  We use it
        # for crash dumps and for 3 parallel arrays: BASH_SOURCE, FUNCNAME, and
        # BASH_LINENO.
        self.debug_stack = debug_stack

        self.pwd = None  # type: Optional[str]
        self.seconds_start = time_.time()

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
        self.try_error = [value.Dict({})]  # type: List[value.Dict]  # a stack
        self.pipe_status = [[]]  # type: List[List[int]]  # stack
        self.process_sub_status = [[]]  # type: List[List[int]]  # stack

        # A stack but NOT a register?
        self.this_dir = []  # type: List[str]
        self.regex_match = [regex_match.No]  # type: List[regex_match_t]

        self.last_bg_pid = -1  # Uninitialized value mutable public variable

        self.running_debug_trap = False  # set by ctx_DebugTrap()
        self.running_err_trap = False  # set by ctx_ErrTrap
        self.is_main = True  # we start out in main

        # For the ctx builtin
        self.ctx_stack = []  # type: List[Dict[str, value_t]]

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
        # type: () -> Tuple[List[value_t], List[value_t], List[value_t]]
        """Copy state before unwinding the stack."""
        var_stack = [
            value.Dict(_DumpVarFrame(frame)) for frame in self.var_stack
        ]  # type: List[value_t]
        argv_stack = [value.Dict(frame.Dump())
                      for frame in self.argv_stack]  # type: List[value_t]

        debug_stack = []  # type: List[value_t]

        # Reuse these immutable objects
        t_call = value.Str('Call')
        t_source = value.Str('Source')
        t_main = value.Str('Main')

        for frame in reversed(self.debug_stack):
            UP_frame = frame
            with tagswitch(frame) as case:
                if case(debug_frame_e.Call):
                    frame = cast(debug_frame.Call, UP_frame)
                    d = {
                        'type': t_call,
                        'func_name': value.Str(frame.func_name)
                    }  # type: Dict[str, value_t]

                    _AddCallToken(d, frame.call_tok)
                    # TODO: Add def_tok

                elif case(debug_frame_e.Source):
                    frame = cast(debug_frame.Source, UP_frame)
                    d = {
                        'type': t_source,
                        'source_name': value.Str(frame.source_name)
                    }
                    _AddCallToken(d, frame.call_tok)

                elif case(debug_frame_e.Main):
                    frame = cast(debug_frame.Main, UP_frame)
                    d = {'type': t_main, 'dollar0': value.Str(frame.dollar0)}

            debug_stack.append(value.Dict(d))
        return var_stack, argv_stack, debug_stack

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
        if self.running_debug_trap or self.running_err_trap:
            return

        #if tok.span_id == runtime.NO_SPID:
        # NOTE: This happened in the osh-runtime benchmark for yash.
        #log('Warning: span_id undefined in SetTokenForLine')

        #import traceback
        #traceback.print_stack()
        #return

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

    def TryError(self):
        # type: () -> value.Dict
        return self.try_error[-1]

    def PipeStatus(self):
        # type: () -> List[int]
        return self.pipe_status[-1]

    def SetLastStatus(self, x):
        # type: (int) -> None
        self.last_status[-1] = x

    def SetTryStatus(self, x):
        # type: (int) -> None
        self.try_status[-1] = x

    def SetTryError(self, x):
        # type: (value.Dict) -> None
        self.try_error[-1] = x

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

    def PushCall(self, func_name, def_tok):
        # type: (str, Token) -> None
        """Push argv, var, and debug stack frames.

        Currently used for proc and func calls.  TODO: New func evaluator may
        not use it.

        Args:
          def_tok: Token where proc or func was defined, used to compute
                   BASH_SOURCE.
        """
        # self.token_for_line can be None?
        self.debug_stack.append(
            debug_frame.Call(self.token_for_line, def_tok, func_name))

    def PopCall(self):
        # type: () -> None
        """
        Args:
          should_pop_argv_stack: Pass False if PushCall was given None for argv
          True for proc, False for func
        """
        self.debug_stack.pop()

    def ShouldRunDebugTrap(self):
        # type: () -> bool

        # TODO: RunLastPart of pipeline can disable this

        # Don't recursively run DEBUG trap
        if self.running_debug_trap:
            return False

        # Don't run it inside functions
        if len(self.var_stack) > 1:
            return False

        return True

    def InsideFunction(self):
        # type: () -> bool
        """For the ERR trap"""

        # Don't run it inside functions
        return len(self.var_stack) > 1

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
            # $0 may be overriden, eg. by Str => replace()
            vars = self.var_stack[-1]
            if "0" in vars and vars["0"].val.tag() != value_e.Undef:
                return vars["0"].val
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

        raise AssertionError()

    def _ResolveNameOrRef(
            self,
            name,  # type: str
            which_scopes,  # type: scope_t
            ref_trail=None,  # type: Optional[List[str]]
    ):
        # type: (...) -> Tuple[Optional[Cell], Dict[str, Cell], str]
        """Look up a cell and namespace, but respect the nameref flag.

        Resolving namerefs does RECURSIVE calls.
        """
        cell, name_map = self._ResolveNameOnly(name, which_scopes)

        if cell is None or not cell.nameref:
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

        # 'declare -n' uses dynamic scope.
        cell, name_map, cell_name = self._ResolveNameOrRef(new_name,
                                                           scope_e.Dynamic,
                                                           ref_trail=ref_trail)
        return cell, name_map, cell_name

    def IsBashAssoc(self, name):
        # type: (str) -> bool
        """Returns whether a name resolve to a cell with an associative array.

        We need to know this to evaluate the index expression properly
        -- should it be coerced to an integer or not?
        """
        cell, _, _ = self._ResolveNameOrRef(name, self.ScopesForReading())
        # foo=([key]=value)
        return cell is not None and cell.val.tag() == value_e.BashAssoc

    def SetPlace(self, place, val, blame_loc):
        # type: (value.Place, value_t, loc_t) -> None

        yval = place.lval
        UP_yval = yval
        with tagswitch(yval) as case:
            if case(y_lvalue_e.Local):
                yval = cast(LeftName, UP_yval)

                # Check that the frame is still alive
                found = False
                for i in xrange(len(self.var_stack) - 1, -1, -1):
                    frame = self.var_stack[i]
                    if frame is place.frame:
                        found = True
                        #log('FOUND %s', found)
                        break
                if not found:
                    e_die(
                        "Can't assign to place that's no longer on the call stack.",
                        blame_loc)

                cell = frame.get(yval.name)
                if cell is None:
                    cell = Cell(False, False, False, val)
                    frame[yval.name] = cell
                else:
                    cell.val = val

            elif case(y_lvalue_e.Container):
                e_die('Container place not implemented', blame_loc)

            else:
                raise AssertionError()

    def SetLocalName(self, lval, val):
        # type: (LeftName, value_t) -> None

        # Equivalent to
        # self._ResolveNameOnly(lval.name, scope_e.LocalOnly)
        name_map = self.var_stack[-1]
        cell = name_map.get(lval.name)

        if cell:
            if cell.readonly:
                e_die("Can't assign to readonly value %r" % lval.name,
                      lval.blame_loc)
            cell.val = val  # Mutate value_t
        else:
            cell = Cell(False, False, False, val)
            name_map[lval.name] = cell

    def SetNamed(self, lval, val, which_scopes, flags=0):
        # type: (LeftName, value_t, scope_t, int) -> None

        if flags & SetNameref or flags & ClearNameref:
            # declare -n ref=x  # refers to the ref itself
            cell, name_map = self._ResolveNameOnly(lval.name, which_scopes)
            cell_name = lval.name
        else:
            # ref=x  # mutates THROUGH the reference

            # Note on how to implement declare -n ref='a[42]'
            # 1. Call _ResolveNameOnly()
            # 2. If cell.nameref, call self.unsafe_arith.ParseVarRef() ->
            #    BracedVarSub
            # 3. Turn BracedVarSub into an sh_lvalue, and call
            #    self.unsafe_arith.SetValue() wrapper with ref_trail
            cell, name_map, cell_name = self._ResolveNameOrRef(
                lval.name, which_scopes)

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
                    e_die("Can't assign to readonly value %r" % lval.name,
                          lval.blame_loc)
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

            cell = Cell(bool(flags & SetExport), bool(flags & SetReadOnly),
                        bool(flags & SetNameref), val)
            name_map[cell_name] = cell

        # Maintain invariant that only strings and undefined cells can be
        # exported.
        assert cell.val is not None, cell

        if cell.val.tag() not in (value_e.Undef, value_e.Str):
            if cell.exported:
                if self.exec_opts.strict_array():
                    e_die("Only strings can be exported (strict_array)",
                          lval.blame_loc)
            if cell.nameref:
                e_die("nameref must be a string", lval.blame_loc)

    def SetValue(self, lval, val, which_scopes, flags=0):
        # type: (sh_lvalue_t, value_t, scope_t, int) -> None
        """
        Args:
          lval: sh_lvalue
          val: value, or None if only changing flags
          which_scopes:
            Local | Global | Dynamic - for builtins, PWD, etc.
          flags: packed pair (keyword_id, bit mask of set/clear flags)

        Note: in bash, PWD=/ changes the directory.  But not in dash.
        """
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
            if case(sh_lvalue_e.Var):
                lval = cast(LeftName, UP_lval)

                self.SetNamed(lval, val, which_scopes, flags=flags)

            elif case(sh_lvalue_e.Indexed):
                lval = cast(sh_lvalue.Indexed, UP_lval)

                # There is no syntax 'declare a[x]'
                assert val is not None, val

                # TODO: relax this for Oil
                assert val.tag() == value_e.Str, val
                rval = cast(value.Str, val)

                # Note: location could be a[x]=1 or (( a[ x ] = 1 ))
                left_loc = lval.blame_loc

                # bash/mksh have annoying behavior of letting you do LHS assignment to
                # Undef, which then turns into an INDEXED array.  (Undef means that set
                # -o nounset fails.)
                cell, name_map, _ = self._ResolveNameOrRef(
                    lval.name, which_scopes)
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
                # sh_lhs.  Could conslidate with s[i] case above
                e_die(
                    "Value of type %s can't be indexed" % ui.ValType(cell.val),
                    left_loc)

            elif case(sh_lvalue_e.Keyed):
                lval = cast(sh_lvalue.Keyed, UP_lval)

                # There is no syntax 'declare A["x"]'
                assert val is not None, val
                assert val.tag() == value_e.Str, val
                rval = cast(value.Str, val)

                left_loc = lval.blame_loc

                cell, name_map, _ = self._ResolveNameOrRef(
                    lval.name, which_scopes)
                if cell.readonly:
                    e_die("Can't assign to readonly associative array",
                          left_loc)

                # We already looked it up before making the sh_lvalue
                assert cell.val.tag() == value_e.BashAssoc, cell
                cell_val2 = cast(value.BashAssoc, cell.val)

                cell_val2.d[lval.key] = rval.s

            else:
                raise AssertionError(lval.tag())

    def _BindNewArrayWithEntry(self, name_map, lval, val, flags):
        # type: (Dict[str, Cell], sh_lvalue.Indexed, value.Str, int) -> None
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
        """Used by the WordEvaluator, ArithEvaluator, ExprEvaluator, etc."""
        assert isinstance(name, str), name

        if which_scopes == scope_e.Shopt:
            which_scopes = self.ScopesForReading()

        with str_switch(name) as case:
            # "Registers"
            if case('_status'):
                return num.ToBig(self.TryStatus())

            elif case('_error'):
                return self.TryError()

            elif case('_this_dir'):
                if len(self.this_dir) == 0:
                    # e.g. osh -c '' doesn't have it set
                    # Should we give a custom error here?
                    # If you're at the interactive shell, 'source mymodule.oil' will still
                    # work because 'source' sets it.
                    return value.Undef
                else:
                    return value.Str(self.this_dir[-1])  # top of stack

            elif case('PIPESTATUS'):
                strs2 = [str(i)
                         for i in self.pipe_status[-1]]  # type: List[str]
                return value.BashArray(strs2)

            elif case('_pipeline_status'):
                items = [num.ToBig(i)
                         for i in self.pipe_status[-1]]  # type: List[value_t]
                return value.List(items)

            elif case('_process_sub_status'):  # YSH naming convention
                items = [num.ToBig(i) for i in self.process_sub_status[-1]]
                return value.List(items)

            elif case('BASH_REMATCH'):
                top_match = self.regex_match[-1]
                with tagswitch(top_match) as case2:
                    if case2(regex_match_e.No):
                        groups = []  # type: List[str]
                    elif case2(regex_match_e.Yes):
                        m = cast(RegexMatch, top_match)
                        groups = util.RegexGroupStrings(m.s, m.indices)
                return value.BashArray(groups)

            # Do lookup of system globals before looking at user variables.  Note: we
            # could optimize this at compile-time like $?.  That would break
            # ${!varref}, but it's already broken for $?.

            elif case('FUNCNAME'):
                # bash wants it in reverse order.  This is a little inefficient but we're
                # not depending on deque().
                strs = []  # type: List[str]
                for frame in reversed(self.debug_stack):
                    UP_frame = frame
                    with tagswitch(frame) as case2:
                        if case2(debug_frame_e.Call):
                            frame = cast(debug_frame.Call, UP_frame)
                            strs.append(frame.func_name)

                        elif case2(debug_frame_e.Source):
                            # bash doesn't tell you the filename sourced
                            strs.append('source')

                        elif case2(debug_frame_e.Main):
                            strs.append('main')  # also bash behavior

                return value.BashArray(strs)  # TODO: Reuse this object too?

            # $BASH_SOURCE and $BASH_LINENO have OFF BY ONE design bugs:
            #
            # ${BASH_LINENO[$i]} is the line number in the source file
            # (${BASH_SOURCE[$i+1]}) where ${FUNCNAME[$i]} was called (or
            # ${BASH_LINENO[$i-1]} if referenced within another shell function).
            #
            # https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html

            elif case('BASH_SOURCE'):
                strs = []
                for frame in reversed(self.debug_stack):
                    UP_frame = frame
                    with tagswitch(frame) as case2:
                        if case2(debug_frame_e.Call):
                            frame = cast(debug_frame.Call, UP_frame)

                            # Weird bash behavior
                            assert frame.def_tok.line is not None
                            source_str = ui.GetLineSourceString(
                                frame.def_tok.line)
                            strs.append(source_str)

                        elif case2(debug_frame_e.Source):
                            frame = cast(debug_frame.Source, UP_frame)
                            # Is this right?
                            strs.append(frame.source_name)

                        elif case2(debug_frame_e.Main):
                            frame = cast(debug_frame.Main, UP_frame)
                            strs.append(frame.dollar0)

                return value.BashArray(strs)  # TODO: Reuse this object too?

            elif case('BASH_LINENO'):
                strs = []
                for frame in reversed(self.debug_stack):
                    UP_frame = frame
                    with tagswitch(frame) as case2:
                        if case2(debug_frame_e.Call):
                            frame = cast(debug_frame.Call, UP_frame)
                            strs.append(_LineNumber(frame.call_tok))

                        elif case2(debug_frame_e.Source):
                            frame = cast(debug_frame.Source, UP_frame)
                            strs.append(_LineNumber(frame.call_tok))

                        elif case2(debug_frame_e.Main):
                            # Bash does this to line up with 'main'
                            strs.append('0')

                return value.BashArray(strs)  # TODO: Reuse this object too?

            elif case('LINENO'):
                assert self.token_for_line is not None
                # Reuse object with mutation
                # TODO: maybe use interned GetLineNumStr?
                self.line_num.s = str(self.token_for_line.line.line_num)
                return self.line_num

            elif case('BASHPID'):  # TODO: YSH io->getpid()
                return value.Str(str(posix.getpid()))

            elif case('_'):
                return value.Str(self.last_arg)

            elif case('SECONDS'):
                f = time_.time() - self.seconds_start
                ok, big_int = mops.FromFloat(f)
                assert ok, f  # should never be NAN or INFINITY
                return value.Int(big_int)

            else:
                # In the case 'declare -n ref='a[42]', the result won't be a cell.  Idea to
                # fix this:
                # 1. Call self.unsafe_arith.ParseVarRef() -> BracedVarSub
                # 2. Call self.unsafe_arith.GetNameref(bvs_part), and get a value_t
                #    We still need a ref_trail to detect cycles.
                cell, _, _ = self._ResolveNameOrRef(name, which_scopes)
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
        # type: (sh_lvalue_t, scope_t) -> bool
        """
        Returns:
          Whether the cell was found.
        """
        # TODO: Refactor sh_lvalue type to avoid this
        UP_lval = lval

        with tagswitch(lval) as case:
            if case(sh_lvalue_e.Var):  # unset x
                lval = cast(LeftName, UP_lval)
                var_name = lval.name
            elif case(sh_lvalue_e.Indexed):  # unset 'a[1]'
                lval = cast(sh_lvalue.Indexed, UP_lval)
                var_name = lval.name
            elif case(sh_lvalue_e.Keyed):  # unset 'A["K"]'
                lval = cast(sh_lvalue.Keyed, UP_lval)
                var_name = lval.name
            else:
                raise AssertionError()

        if which_scopes == scope_e.Shopt:
            which_scopes = self.ScopesForWriting()

        cell, name_map, cell_name = self._ResolveNameOrRef(
            var_name, which_scopes)
        if not cell:
            return False  # 'unset' builtin falls back on functions
        if cell.readonly:
            raise error.Runtime("Can't unset readonly variable %r" % var_name)

        with tagswitch(lval) as case:
            if case(sh_lvalue_e.Var):  # unset x
                # Make variables in higher scopes visible.
                # example: test/spec.sh builtin-vars -r 24 (ble.sh)
                mylib.dict_erase(name_map, cell_name)

                # alternative that some shells use:
                #   name_map[cell_name].val = value.Undef
                #   cell.exported = False

                # This should never happen because we do recursive lookups of namerefs.
                assert not cell.nameref, cell

            elif case(sh_lvalue_e.Indexed):  # unset 'a[1]'
                lval = cast(sh_lvalue.Indexed, UP_lval)
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

            elif case(sh_lvalue_e.Keyed):  # unset 'A["K"]'
                lval = cast(sh_lvalue.Keyed, UP_lval)

                val = cell.val
                UP_val = val

                # note: never happens because of mem.IsBashAssoc test for sh_lvalue.Keyed
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

        We don't use SetValue() because even if rval is None, it will make an
        Undef value in a scope.
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

    def SetRegexMatch(self, match):
        # type: (regex_match_t) -> None
        self.regex_match[-1] = match

    def GetRegexMatch(self):
        # type: () -> regex_match_t
        return self.regex_match[-1]

    def PushContextStack(self, context):
        # type: (Dict[str, value_t]) -> None
        self.ctx_stack.append(context)

    def GetContext(self):
        # type: () -> Optional[Dict[str, value_t]]
        if len(self.ctx_stack):
            return self.ctx_stack[-1]
        return None

    def PopContextStack(self):
        # type: () -> Dict[str, value_t]
        assert self.ctx_stack, "Empty context stack"
        return self.ctx_stack.pop()


class Procs:

    def __init__(self, mem):
        # type: (Mem) -> None
        self.mem = mem
        self.sh_funcs = {}  # type: Dict[str, value.Proc]

    def SetProc(self, name, proc):
        # type: (str, value.Proc) -> None
        self.mem.var_stack[0][name] = Cell(False, False, False, proc)

    def SetShFunc(self, name, proc):
        # type: (str, value.Proc) -> None
        self.sh_funcs[name] = proc

    def Get(self, name):
        # type: (str) -> value.Proc
        """Try to find a proc/sh-func by `name`, or return None if not found.

        First, we search for a proc, and then a sh-func. This means that procs
        can shadow the definition of sh-funcs.
        """
        vars = self.mem.var_stack[0]
        if name in vars:
            maybe_proc = vars[name]
            if maybe_proc.val.tag() == value_e.Proc:
                return cast(value.Proc, maybe_proc.val)

        if name in self.sh_funcs:
            return self.sh_funcs[name]

        return None

    def Del(self, to_del):
        # type: (str) -> None
        """Undefine a sh-func with name `to_del`, if it exists."""
        mylib.dict_erase(self.sh_funcs, to_del)

    def GetNames(self):
        # type: () -> List[str]
        """Returns a *sorted* list of all proc names"""
        names = list(self.sh_funcs.keys())

        vars = self.mem.var_stack[0]
        for name in vars:
            cell = vars[name]
            if cell.val.tag() == value_e.Proc:
                names.append(name)

        return sorted(names)


#
# Wrappers to Set Variables
#


def OshLanguageSetValue(mem, lval, val, flags=0):
    # type: (Mem, sh_lvalue_t, value_t, int) -> None
    """Like 'setvar' (scope_e.LocalOnly), unless dynamic scope is on.

    That is, it respects shopt --unset dynamic_scope.

    Used for assignment builtins, (( a = b )), {fd}>out, ${x=}, etc.
    """
    which_scopes = mem.ScopesForWriting()
    mem.SetValue(lval, val, which_scopes, flags=flags)


def BuiltinSetValue(mem, lval, val):
    # type: (Mem, sh_lvalue_t, value_t) -> None
    """Equivalent of x=$y

    Called by BuiltinSetString and BuiltinSetArray Used directly by
    printf -v because it can mutate an array
    """
    mem.SetValue(lval, val, mem.ScopesForWriting())


def BuiltinSetString(mem, name, s):
    # type: (Mem, str, str) -> None
    """Set a string by looking up the stack.

    Used for 'read', 'getopts', completion builtins, etc.
    """
    assert isinstance(s, str)
    BuiltinSetValue(mem, location.LName(name), value.Str(s))


def BuiltinSetArray(mem, name, a):
    # type: (Mem, str, List[str]) -> None
    """Set an array by looking up the stack.

    Used by compadjust, read -a, etc.
    """
    assert isinstance(a, list)
    BuiltinSetValue(mem, location.LName(name), value.BashArray(a))


def SetGlobalString(mem, name, s):
    # type: (Mem, str, str) -> None
    """Helper for completion, etc."""
    assert isinstance(s, str)
    val = value.Str(s)
    mem.SetNamed(location.LName(name), val, scope_e.GlobalOnly)


def SetGlobalArray(mem, name, a):
    # type: (Mem, str, List[str]) -> None
    """Used by completion, shell initialization, etc."""
    assert isinstance(a, list)
    mem.SetNamed(location.LName(name), value.BashArray(a), scope_e.GlobalOnly)


def _SetGlobalValue(mem, name, val):
    # type: (Mem, str, value_t) -> None
    """Helper for completion, etc."""
    mem.SetNamed(location.LName(name), val, scope_e.GlobalOnly)


def ExportGlobalString(mem, name, s):
    # type: (Mem, str, str) -> None
    """Helper for completion, $PWD, $OLDPWD, etc."""
    assert isinstance(s, str)
    val = value.Str(s)
    mem.SetNamed(location.LName(name),
                 val,
                 scope_e.GlobalOnly,
                 flags=SetExport)


#
# Wrappers to Get Variables
#


def DynamicGetVar(mem, name, which_scopes):
    # type: (Mem, str, scope_t) -> value_t
    """
    For getVar() and shvarGet()
    """
    val = mem.GetValue(name, which_scopes=which_scopes)

    # Undef is not a user-visible value!
    # There's no way to distinguish null from undefined.
    if val.tag() == value_e.Undef:
        return value.Null

    return val


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


# vim: sw=4
