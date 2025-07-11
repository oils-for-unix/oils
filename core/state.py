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
from _devbuild.gen.runtime_asdl import (error_code_e, scope_e, scope_t, Cell)
from _devbuild.gen.syntax_asdl import (CompoundWord, loc, loc_t, Token,
                                       debug_frame, debug_frame_e,
                                       debug_frame_t)
from _devbuild.gen.types_asdl import opt_group_i
from _devbuild.gen.value_asdl import (value, value_e, value_t, Obj, sh_lvalue,
                                      sh_lvalue_e, sh_lvalue_t, LeftName,
                                      y_lvalue_e, regex_match, regex_match_e,
                                      regex_match_t, RegexMatch)
from core import bash_impl
from core import error
from core.error import e_usage, e_die
from core import num
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
from pylib import os_path

from libc import HAVE_GLOB_PERIOD
import posix_ as posix

from typing import Tuple, List, Dict, Optional, Any, cast, TYPE_CHECKING

if TYPE_CHECKING:
    from _devbuild.gen.option_asdl import option_t
    from core import alloc
    from osh import sh_expr_eval

_ = log

# flags for mem.SetValue()
SetReadOnly = 1 << 0
ClearReadOnly = 1 << 1
SetExport = 1 << 2
ClearExport = 1 << 3
SetNameref = 1 << 4
ClearNameref = 1 << 5

# For SetNamedYsh
YshDecl = 1 << 6


class ctx_Source(object):
    """For source builtin."""

    def __init__(self, mem, source_name, argv, source_loc):
        # type: (Mem, str, List[str], CompoundWord) -> None
        mem.PushSource(source_name, argv, source_loc)
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


def MakeOpts(
        mem,  # type: Mem
        environ,  # type: Dict[str, str]
        opt_hook,  # type:  OptHook
):
    # type: (...) -> Tuple[optview.Parse, optview.Exec, MutableOpts]

    # Unusual representation: opt0_array + opt_stacks.  For two features:
    #
    # - POSIX errexit disable semantics
    # - YSH shopt --set nullglob { ... }
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
    mutable_opts = MutableOpts(mem, environ, opt0_array, opt_stacks, opt_hook)

    return parse_opts, exec_opts, mutable_opts


def _SetGroup(opt0_array, opt_nums, b):
    # type: (List[bool], List[int], bool) -> None
    for opt_num in opt_nums:
        b2 = not b if opt_num in consts.DEFAULT_TRUE else b
        opt0_array[opt_num] = b2


def MakeYshParseOpts():
    # type: () -> optview.Parse
    opt0_array = InitOpts()
    _SetGroup(opt0_array, consts.YSH_ALL, True)

    no_stack = None  # type: List[bool]
    opt_stacks = [no_stack] * option_i.ARRAY_SIZE  # type: List[List[bool]]

    parse_opts = optview.Parse(opt0_array, opt_stacks)
    return parse_opts


def _AnyOptionNum(opt_name, ignore_shopt_not_impl):
    # type: (str, bool) -> option_t
    opt_num = consts.OptionNum(opt_name)
    if opt_num == 0:
        if ignore_shopt_not_impl:
            opt_num = consts.UnimplOptionNum(opt_name)
        if opt_num == 0:
            e_usage('got invalid option %r' % opt_name, loc.Missing)

    # Note: we relaxed this for YSH so we can do 'shopt --unset errexit' consistently
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


def _MaybeWarnDotglob():
    # type: () -> None
    if HAVE_GLOB_PERIOD == 0:
        # GNU libc and musl libc have GLOB_PERIOD, but Android doesn't
        print_stderr(
            "osh warning: GLOB_PERIOD wasn't found in libc, so 'shopt -s dotglob' won't work"
        )


class MutableOpts(object):

    def __init__(self, mem, environ, opt0_array, opt_stacks, opt_hook):
        # type: (Mem, Dict[str, str], List[bool], List[List[bool]], OptHook) -> None
        self.mem = mem
        self.environ = environ
        self.opt0_array = opt0_array
        self.opt_stacks = opt_stacks
        self.errexit_disabled_tok = []  # type: List[Token]

        # Used for 'set -o vi/emacs'
        self.opt_hook = opt_hook

    def InitFromEnv(self, shellopts):
        # type: (str) -> None
        """Given an environment string, set the state of this object."""
        # e.g. errexit:nounset:pipefail
        lookup = shellopts.split(':')
        for opt_num in consts.SET_OPTION_NUMS:
            name = consts.OptionName(opt_num)
            if name in lookup:
                self._SetOldOption(name, True)

    def ShelloptsString(self):
        # type: () -> str
        """Return the state of this object, with respect to 'set'

        Inverse of InitFromEnv.  TODO: BASHOPTS string.
        """
        names = []  # type: List[str]
        for opt_num in consts.SET_OPTION_NUMS:
            if self.Get(opt_num):
                name = consts.OptionName(opt_num)
                names.append(name)
        return ':'.join(names)

    def Push(self, opt_num, b):
        # type: (int, bool) -> None
        if opt_num == option_i.dotglob:
            _MaybeWarnDotglob()

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
        Args
          b: dynamic scope?  False if it's a proc, and True if it's a shell
             function.
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
        """Used to disable errexit.

        For bash compatibility in command sub.
        """
        if opt_num == option_i.dotglob:
            _MaybeWarnDotglob()

        # Like _Getter in core/optview.py
        overlay = self.opt_stacks[opt_num]
        if overlay is None or len(overlay) == 0:
            self.opt0_array[opt_num] = b
        else:
            overlay[-1] = b  # The top value

    def set_interactive(self):
        # type: () -> None
        self._Set(option_i.interactive, True)

    def set_redefine_const(self):
        # type: () -> None
        """For interactive shells."""
        self._Set(option_i.redefine_const, True)

    def set_redefine_source(self):
        # type: () -> None
        """For interactive shells.  For source-guard"""
        self._Set(option_i.redefine_source, True)

    def set_emacs(self):
        # type: () -> None
        self._Set(option_i.emacs, True)

    def _SetArrayByNum(self, opt_num, b):
        # type: (int, bool) -> None
        """
        Disabled check: ParsingChangesAllowed() worked for shell functions, but
        was broken for proc and func.  Because they don't use the argv stack.

        It also doesn't work for 'eval' and 'source', as shown by ble.sh.
        (Although source inside a function is an odd usage.)

        if (opt_num in consts.PARSE_OPTION_NUMS and
                not self.mem.ParsingChangesAllowed()):
            e_die('Syntax options must be set at the top level '
                  '(outside any function)')
        """

        self._Set(opt_num, b)

    def SetDeferredErrExit(self, b):
        # type: (bool) -> None
        """Set the errexit flag, possibly deferring it.

        Implements the unusual POSIX "defer" behavior.  Callers: set -o
        errexit, shopt -s ysh:all, ysh:upgrade
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
                print_stderr('osh warning: set -o verbose not implemented')
            self._SetArrayByNum(opt_num, b)

        # note: may FAIL before we get here.

        success = self.opt_hook.OnChange(self.opt0_array, opt_name, b)

    def SetOldOption(self, opt_name, b):
        # type: (str, bool) -> None
        """For set -o, set +o, or shopt -s/-u -o."""
        unused = _SetOptionNum(opt_name)  # validate it
        self._SetOldOption(opt_name, b)

        if not self.Get(option_i.no_init_globals):
            UP_val = self.mem.GetValue('SHELLOPTS')
            assert UP_val.tag() == value_e.Str, UP_val
            val = cast(value.Str, UP_val)
            shellopts = val.s

            # Now check if SHELLOPTS needs to be updated.  It may be exported.
            #
            # NOTE: It might be better to skip rewriting SHELLOPTS in the common case
            # where it is not used.  We could do it lazily upon GET.

            # Also, it would be slightly more efficient to update SHELLOPTS if
            # settings were batched, Examples:
            # - set -eu
            # - shopt -s foo bar
            if b:
                if opt_name not in shellopts:
                    # Append it to the end, : separated
                    if len(shellopts) == 0:
                        new_val = opt_name
                    else:
                        new_val = '%s:%s' % (shellopts, opt_name)
                    self.mem.InternalSetGlobal('SHELLOPTS', value.Str(new_val))
            else:
                if opt_name in shellopts:
                    names = [n for n in shellopts.split(':') if n != opt_name]
                    new_val = ':'.join(names)
                    self.mem.InternalSetGlobal('SHELLOPTS', value.Str(new_val))

    def SetAnyOption(self, opt_name, b, ignore_shopt_not_impl=False):
        # type: (str, bool, bool) -> None
        """For shopt -s/-u and sh -O/+O.

        Problem: we allow shopt --set xtrace, but this doesn't update SHELLOPTS
        """

        # shopt -s ysh:all turns on all YSH options, which includes all strict
        # options
        opt_group = consts.OptionGroupNum(opt_name)
        if opt_group == opt_group_i.YshUpgrade:
            _SetGroup(self.opt0_array, consts.YSH_UPGRADE, b)
            self.SetDeferredErrExit(b)  # Special case
            if b:  # ENV dict
                self.mem.MaybeInitEnvDict(self.environ)
            return

        if opt_group == opt_group_i.YshAll:
            _SetGroup(self.opt0_array, consts.YSH_ALL, b)
            self.SetDeferredErrExit(b)  # Special case
            if b:  # ENV dict
                self.mem.MaybeInitEnvDict(self.environ)
            return

        if opt_group == opt_group_i.StrictAll:
            _SetGroup(self.opt0_array, consts.STRICT_ALL, b)
            return

        opt_num = _AnyOptionNum(opt_name, ignore_shopt_not_impl)

        if opt_num == option_i.errexit:
            self.SetDeferredErrExit(b)
            return

        self._SetArrayByNum(opt_num, b)


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

        # $0 is handled elsewhere
        assert 1 <= arg_num, arg_num

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

    vars_json = NewDict()  # type: Dict[str, value_t]
    for name, cell in iteritems(frame):
        cell_json = NewDict()  # type: Dict[str, value_t]

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
        #   - although InternalStringArray and BashAssoc may need 'type' tags
        #     - they don't round trip correctly
        #     - maybe add value.Tombstone here or something?
        #   - value.{Func,Eggex,...} may have value.Tombstone and
        #   vm.ValueIdString()?

        with tagswitch(cell.val) as case:
            if case(value_e.Undef):
                cell_json['val'] = value.Null

            elif case(value_e.Str, value_e.InternalStringArray,
                      value_e.BashAssoc, value_e.BashArray):
                cell_json['val'] = cell.val

            else:
                # TODO: should we show the object ID here?
                pass

        vars_json[name] = value.Dict(cell_json)

    return vars_json


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


class ctx_FuncCall(object):
    """For func calls."""

    def __init__(self, mem, func, blame_tok):
        # type: (Mem, value.Func, Token) -> None

        self.saved_globals = mem.var_stack[0]

        assert func.module_frame is not None
        mem.var_stack[0] = func.module_frame

        frame = NewDict()  # type: Dict[str, Cell]

        assert func.captured_frame is not None, func
        frame['__E__'] = Cell(False, False, False,
                              value.Frame(func.captured_frame))

        mem.var_stack.append(frame)

        # blame the location of (
        mem.debug_stack.append(blame_tok)

        self.mem = mem

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.debug_stack.pop()
        self.mem.var_stack.pop()

        self.mem.var_stack[0] = self.saved_globals


class ctx_ProcCall(object):
    """For proc calls, including shell functions."""

    def __init__(self, mem, mutable_opts, proc, argv, invoke_loc):
        # type: (Mem, MutableOpts, value.Proc, List[str], CompoundWord) -> None

        # TODO:
        # should we separate procs and shell functions?
        # - dynamic scope is one difference
        # - '$@" shift etc. are another difference

        self.saved_globals = mem.var_stack[0]

        assert proc.module_frame is not None
        mem.var_stack[0] = proc.module_frame

        frame = NewDict()  # type: Dict[str, Cell]

        # shell functions don't capture a frame
        if proc.captured_frame is not None:
            frame['__E__'] = Cell(False, False, False,
                                  value.Frame(proc.captured_frame))

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

        mem.debug_stack.append(
            debug_frame.ProcLike(invoke_loc, proc.name_tok, proc.name))

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
        self.mem.debug_stack.pop()
        self.mem.var_stack.pop()

        if self.sh_compat:
            self.mem.argv_stack.pop()

        self.mem.var_stack[0] = self.saved_globals


class ctx_EvalInFrame(object):

    def __init__(self, mem, frame):
        # type: (Mem, Dict[str, Cell]) -> None
        mem.var_stack.append(frame)

        self.mem = mem

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.var_stack.pop()


class ctx_Temp(object):
    """ POSIX shell FOO=bar mycommand """

    def __init__(self, mem):
        # type: (Mem) -> None
        self.mem = mem
        mem.PushTemp()

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.PopTemp()


class ctx_EnvObj(object):
    """YSH FOO=bar my-command"""

    def __init__(self, mem, bindings):
        # type: (Mem, Dict[str, value_t]) -> None
        self.mem = mem
        mem.PushEnvObj(bindings)

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.PopEnvObj()


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
        tmp = NewDict()  # type: Dict[str, value_t]
        mem.try_error.append(value.Dict(tmp))

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


class ctx_LoopFrame(object):

    def __init__(self, mem, do_new_frame):
        # type: (Mem, bool) -> None
        self.mem = mem
        self.do_new_frame = do_new_frame

        if self.do_new_frame:
            to_enclose = self.mem.var_stack[-1]
            self.new_frame = NewDict()  # type: Dict[str, Cell]
            self.new_frame['__E__'] = Cell(False, False, False,
                                           value.Frame(to_enclose))
            mem.var_stack.append(self.new_frame)

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        if self.do_new_frame:
            self.mem.var_stack.pop()


class ctx_EnclosedFrame(object):
    """
    Usages:

    - io->evalToDict(), which is a primitive used for Hay and the Dict proc
    - lexical scope aka static scope for block args to user-defined procs
      - Including the "closures in a loop" problem, which will be used for Hay

    var mutated = 'm'
    var shadowed = 's'

    Dict (&d) {
      shadowed = 42
      mutated = 'new'  # this is equivalent to var mutated

      setvar mutated = 'new'
    }
    echo $shadowed  # restored to 's'
    echo $mutated  # new

    Or maybe we disallow the setvar lookup?
    """

    def __init__(
            self,
            mem,  # type: Mem
            to_enclose,  # type: Dict[str, Cell]
            module_frame,  # type: Dict[str, Cell]
            out_dict,  # type: Optional[Dict[str, value_t]]
            inside=False,  # type: bool
    ):
        # type: (...) -> None
        self.mem = mem
        self.to_enclose = to_enclose
        self.module_frame = module_frame
        self.out_dict = out_dict

        if module_frame is not None:
            self.saved_globals = self.mem.var_stack[0]
            self.mem.var_stack[0] = module_frame

        if inside:
            self.new_frame = to_enclose
        else:
            # __E__ gets a lookup rule
            self.new_frame = NewDict()
            self.new_frame['__E__'] = Cell(False, False, False,
                                           value.Frame(to_enclose))

        mem.var_stack.append(self.new_frame)

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None

        if self.out_dict is not None:
            for name, cell in iteritems(self.new_frame):
                #log('name %r', name)
                #log('cell %r', cell)

                # User can hide variables with _ suffix
                # e.g. for i_ in foo bar { echo $i_ }
                if name.endswith('_'):
                    continue

                self.out_dict[name] = cell.val

        # Restore
        self.mem.var_stack.pop()

        if self.module_frame is not None:
            self.mem.var_stack[0] = self.saved_globals


class ctx_CompoundWordDebugFrame(object):

    def __init__(self, mem, w):
        # type: (Mem, CompoundWord) -> None
        mem.debug_stack.append(w)
        self.mem = mem

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value_, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.debug_stack.pop()


class ctx_TokenDebugFrame(object):

    def __init__(self, mem, tok):
        # type: (Mem, Token) -> None
        mem.debug_stack.append(tok)
        self.mem = mem

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value_, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.debug_stack.pop()


class ctx_ModuleEval(object):
    """Evaluate a module with a new global stack frame.

    e.g. setglobal in the new module doesn't leak

    Different from ctx_EnclosedFrame because the new code can't see variables in
    the old frame.
    """

    def __init__(self, mem, use_loc, out_dict, out_errors):
        # type: (Mem, CompoundWord, Dict[str, value_t], List[str]) -> None
        self.mem = mem
        self.out_dict = out_dict
        self.out_errors = out_errors

        self.new_frame = NewDict()  # type: Dict[str, Cell]
        self.saved_frame = mem.var_stack[0]

        # Somewhat of a hack for tracing within a module.
        # Other solutions:
        # - PS4 can be __builtin__, but that would break shell compatibility
        # - We can have a separate YSH mechanism that uses a different settings
        #   - We probably still want it to be scoped, like shvar PS4=z { ... }
        #
        # Note: there's a similar issue with HOSTNAME UID EUID etc.  But those
        # could be io.hostname() io.getuid(), or lazy constants, etc.

        ps4 = self.saved_frame.get('PS4')
        if ps4:
            self.new_frame['PS4'] = ps4
        # ENV is not in __builtins__ because it's mutable -- we want
        # 'setglobal' to work
        env = self.saved_frame.get('ENV')
        if env:
            self.new_frame['ENV'] = env

        assert len(mem.var_stack) == 1
        mem.var_stack[0] = self.new_frame

        # Whenever we're use-ing, the 'is-main' builtin will return 1 (false)
        self.to_restore = self.mem.is_main
        self.mem.is_main = False

        # Equivalent of PushSource()
        mem.debug_stack.append(use_loc)

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value_, traceback):
        # type: (Any, Any, Any) -> None

        self.mem.debug_stack.pop()

        self.mem.is_main = self.to_restore

        assert len(self.mem.var_stack) == 1
        self.mem.var_stack[0] = self.saved_frame

        # Now look in __export__ for the list of names to expose

        cell = self.new_frame.get('__provide__')
        if cell is None:
            self.out_errors.append("Module is missing __provide__ List")
            return

        provide_val = cell.val
        with tagswitch(provide_val) as case:
            if case(value_e.List):
                for val in cast(value.List, provide_val).items:
                    if val.tag() == value_e.Str:
                        name = cast(value.Str, val).s

                        cell = self.new_frame.get(name)
                        if cell is None:
                            self.out_errors.append(
                                "Name %r was provided, but not defined" % name)
                            continue

                        self.out_dict[name] = cell.val
                    else:
                        self.out_errors.append(
                            "Expected Str in __provide__ List, got %s" %
                            ui.ValType(val))

            else:
                self.out_errors.append("__provide__ should be a List, got %s" %
                                       ui.ValType(provide_val))


class ctx_Eval(object):
    """Push temporary set of variables, $0, $1, $2, etc."""

    def __init__(
            self,
            mem,  # type: Mem
            dollar0,  # type: Optional[str]
            pos_args,  # type: Optional[List[str]]
            vars,  # type: Optional[Dict[str, value_t]]
    ):
        # type: (...) -> None
        self.mem = mem
        self.dollar0 = dollar0
        self.pos_args = pos_args
        self.vars = vars

        # $0 needs to have lexical scoping. So we store it with other locals.
        # As "0" cannot be parsed as an lvalue, we can safely store dollar0 there.
        if dollar0 is not None:
            #assert mem.GetValue("0", scope_e.LocalOnly).tag() == value_e.Undef
            #self.dollar0_lval = LeftName("0", loc.Missing)
            #mem.SetLocalName(self.dollar0_lval, value.Str(dollar0))

            self.restore_dollar0 = self.mem.dollar0
            self.mem.dollar0 = dollar0

        if pos_args is not None:
            mem.argv_stack.append(_ArgFrame(pos_args))

        if vars is not None:
            self.restore = []  # type: List[Tuple[LeftName, value_t]]
            self._Push(vars)

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value_, traceback):
        # type: (Any, Any, Any) -> None
        if self.vars is not None:
            self._Pop()

        if self.pos_args is not None:
            self.mem.argv_stack.pop()

        if self.dollar0 is not None:
            #self.mem.SetLocalName(self.dollar0_lval, value.Undef)
            self.mem.dollar0 = self.restore_dollar0

    # Note: _Push and _Pop are separate methods because the C++ translation
    # doesn't like when they are inline in __init__ and __exit__.
    def _Push(self, vars):
        # type: (Dict[str, value_t]) -> None
        for name in vars:
            lval = location.LName(name)
            # LocalOnly because we are only overwriting the current scope
            old_val = self.mem.GetValue(name, scope_e.LocalOnly)
            self.restore.append((lval, old_val))
            self.mem.SetNamed(lval, vars[name], scope_e.LocalOnly)

    def _Pop(self):
        # type: () -> None
        for lval, old_val in self.restore:
            if old_val.tag() == value_e.Undef:
                self.mem.Unset(lval, scope_e.LocalOnly)
            else:
                self.mem.SetNamed(lval, old_val, scope_e.LocalOnly)


def _FrameLookup(frame, name, ysh_decl):
    # type: (Dict[str, Cell], str, bool) -> Tuple[Optional[Cell], Dict[str, Cell]]
    """
    Look for a name in the frame, then recursively into the enclosing __E__
    frame, if it exists
    """
    cell = frame.get(name)
    if cell:
        return cell, frame

    # var, const are declarations
    # TODO: what about proc, func?
    if not ysh_decl:
        rear_cell = frame.get('__E__')  # ctx_EnclosedFrame() sets this
        if rear_cell:
            rear_val = rear_cell.val
            assert rear_val, rear_val
            if rear_val.tag() == value_e.Frame:
                to_enclose = cast(value.Frame, rear_val).frame
                return _FrameLookup(to_enclose, name,
                                    ysh_decl)  # recursive call

    return None, None


class Mem(object):
    """For storing variables.

    Callers:
      User code: assigning and evaluating variables, in command context or
        arithmetic context.
      Completion engine: for COMP_WORDS, etc.
      Builtins call it implicitly: read, cd for $PWD, $OLDPWD, etc.

    Modules: cmd_eval, word_eval, expr_eval, completion
    """

    def __init__(
            self,
            dollar0,  # type: str
            argv,  # type: List[str]
            arena,  # type: alloc.Arena
            debug_stack,  # type: List[debug_frame_t]
            env_dict,  # type: Dict[str, value_t]
            defaults=None,  # type: Dict[str, value_t]
    ):
        # type: (...) -> None
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

        frame0 = NewDict()  # type: Dict[str, Cell]
        self.var_stack = [frame0]

        # The debug_stack isn't strictly necessary for execution.  We use it
        # for crash dumps and for 3 parallel arrays: BASH_SOURCE, FUNCNAME, and
        # BASH_LINENO.
        self.debug_stack = debug_stack

        self.env_dict = env_dict
        self.env_object = Obj(None, env_dict)  # initial state

        if defaults is None:  # for unit tests only
            self.defaults = NewDict()  # type: Dict[str, value_t]
        else:
            self.defaults = defaults

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
        tmp = NewDict()  # type: Dict[str, value_t]
        # a stack
        self.try_error = [value.Dict(tmp)]  # type: List[value.Dict]
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

        self.builtins = NewDict()  # type: Dict[str, value_t]

        # Note: Python 2 and 3 have __builtins__
        # This is just for inspection
        builtins_module = Obj(None, self.builtins)

        # Code in any module can see __builtins__
        self.builtins['__builtins__'] = builtins_module

        self.did_ysh_env = False  # only initialize ENV once per process

        from core import sh_init
        self.env_config = sh_init.EnvConfig(self, defaults)

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

    def AddBuiltin(self, name, val):
        # type: (str, value_t) -> None
        self.builtins[name] = val

    def SetPwd(self, pwd):
        # type: (str) -> None
        """Used by builtins."""
        self.pwd = pwd

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

        for frame in reversed(self.debug_stack):
            UP_frame = frame
            d = None  # type: Optional[Dict[str, value_t]]
            with tagswitch(frame) as case:
                if case(debug_frame_e.ProcLike):
                    frame = cast(debug_frame.ProcLike, UP_frame)
                    d = {
                        'type': t_call,
                        'func_name': value.Str(frame.proc_name)
                    }

                    invoke_token = location.LeftTokenForCompoundWord(
                        frame.invoke_loc)
                    assert invoke_token is not None, frame.invoke_loc
                    _AddCallToken(d, invoke_token)
                    # TODO: Add def_tok

                elif case(debug_frame_e.Source):
                    frame = cast(debug_frame.Source, UP_frame)
                    d = {
                        'type': t_source,
                        'source_name': value.Str(frame.source_name)
                    }
                    invoke_token = location.LeftTokenForCompoundWord(
                        frame.source_loc)
                    assert invoke_token is not None, frame.source_loc
                    _AddCallToken(d, invoke_token)

                # TODO: func_reflect.py DebugFrameToString handles these cases
                # We might also want to use CrashDumper there?  For 'set -u'
                # etc.
                elif case(debug_frame_e.CompoundWord):
                    pass

                elif case(debug_frame_e.Token):
                    pass

            # Note: Skip debug_frame.MainFile
            if d is not None:
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

        # Reset the expression fallback location on every line.  It REFINES the
        # line-based fallback location.
        self.loc_for_expr = loc.Missing

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

    def IsGlobalScope(self):
        # type: () -> bool
        """
        local -g uses this, probably because bash does the wrong thing and
        prints LOCALS, not globals.
        """
        # TODO: check for bugs where temp frames FOO=bar make the var stack
        # non-empty, at global scope (like the removed ParsingChangesAllowed())

        return len(self.var_stack) == 1

    def InsideFunction(self):
        # type: () -> bool
        """For the ERR trap, and use builtin"""
        # TODO: check for bugs where temp frames FOO=bar make the var stack
        # non-empty, at global scope (like the removed ParsingChangesAllowed())

        # Don't run it inside functions
        return len(self.var_stack) > 1

    def GlobalFrame(self):
        # type: () -> Dict[str, Cell]
        """For defining the global scope of modules.

        It's affected by ctx_ModuleEval()
        """
        return self.var_stack[0]

    def CurrentFrame(self):
        # type: () -> Dict[str, Cell]
        """For attaching a stack frame to a value.Block"""
        return self.var_stack[-1]

    def PushSource(self, source_name, argv, source_loc):
        # type: (str, List[str], CompoundWord) -> None
        """ For 'source foo.sh 1 2 3' """
        if len(argv):
            self.argv_stack.append(_ArgFrame(argv))

        self.debug_stack.append(debug_frame.Source(source_loc, source_name))

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

    def _BindEnvObj(self):
        # type: () -> None
        self.SetNamed(location.LName('ENV'), self.env_object,
                      scope_e.GlobalOnly)

    def MaybeInitEnvDict(self, environ):
        # type: (Dict[str, str]) -> None
        if self.did_ysh_env:
            return

        for name, s in iteritems(environ):
            self.env_dict[name] = value.Str(s)

        self._BindEnvObj()
        self.did_ysh_env = True

    def PushEnvObj(self, bindings):
        # type: (Dict[str, value_t]) -> None
        """Push "bindings" as the MOST visible part of the ENV Obj 

        i.e. first() / propView()
        """
        self.env_object = Obj(self.env_object, bindings)
        self._BindEnvObj()

    def PopEnvObj(self):
        # type: () -> None
        """Pop a Dict of bindings."""
        self.env_object = self.env_object.prototype
        if self.env_object is None:
            # Note: there isn't a way to hit this now, but let's be defensive.
            # See test case in spec/ysh-env.test.sh.
            e_die('PopEnvObj: env.prototype is null', loc.Missing)

        self._BindEnvObj()

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
            # Disabled
            if 0:
                # Problem: Doesn't obey enclosing frame?
                # Yeah it needs FrameLookup
                cell, _ = _FrameLookup(self.var_stack[-1], '0')
                if cell is not None:
                    val = cell.val
                    if val.tag() != value_e.Undef:
                        return val

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

    def _ResolveNameForYshMutation(self, name, which_scopes, ysh_decl):
        # type: (str, scope_t, bool) -> Tuple[Optional[Cell], Dict[str, Cell]]
        """Simpler version of _ResolveNameOnly for YSH.

        YSH has no namerefs, and it only has local and global mutation (setvar
        and setglobal).
        """
        if which_scopes == scope_e.LocalOnly:
            var_frame = self.var_stack[-1]
            cell, result_frame = _FrameLookup(var_frame, name, ysh_decl)
            if cell:
                return cell, result_frame
            return None, var_frame

        if which_scopes == scope_e.GlobalOnly:
            var_frame = self.var_stack[0]
            cell, result_frame = _FrameLookup(var_frame, name, ysh_decl)
            if cell:
                return cell, result_frame

            return None, var_frame

        raise AssertionError()

    def _ResolveNameOnly(self, name, which_scopes):
        # type: (str, scope_t) -> Tuple[Optional[Cell], Dict[str, Cell]]
        """Helper for getting and setting variable.

        Returns:
          cell: The cell corresponding to looking up 'name' with the given mode, or
            None if it's not found.
          var_frame: The frame it should be set to or deleted from.
        """
        if which_scopes == scope_e.Dynamic:
            for i in xrange(len(self.var_stack) - 1, -1, -1):
                var_frame = self.var_stack[i]
                cell, result_frame = _FrameLookup(var_frame, name, False)
                if cell:
                    return cell, result_frame
            return None, self.var_stack[0]  # set in global var_frame

        if which_scopes == scope_e.LocalOnly:
            var_frame = self.var_stack[-1]
            cell, result_frame = _FrameLookup(var_frame, name, False)
            if cell:
                return cell, result_frame
            return None, var_frame

        if which_scopes == scope_e.GlobalOnly:
            var_frame = self.var_stack[0]
            cell, result_frame = _FrameLookup(var_frame, name, False)
            if cell:
                return cell, result_frame

            return None, var_frame

        if which_scopes == scope_e.LocalOrGlobal:
            # Local
            var_frame = self.var_stack[-1]
            cell, result_frame = _FrameLookup(var_frame, name, False)
            if cell:
                return cell, result_frame

            # Global
            var_frame = self.var_stack[0]
            cell, result_frame = _FrameLookup(var_frame, name, False)
            if cell:
                return cell, result_frame

            return None, var_frame

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
        cell, var_frame = self._ResolveNameOnly(name, which_scopes)

        if cell is None or not cell.nameref:
            return cell, var_frame, name  # not a nameref

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
                    return cell, var_frame, name  # fallback

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
                return cell, var_frame, name  # fallback

        # Check for circular namerefs.
        if ref_trail is None:
            ref_trail = [name]
        else:
            if new_name in ref_trail:
                e_die('Circular nameref %s' % ' -> '.join(ref_trail))
        ref_trail.append(new_name)

        # 'declare -n' uses dynamic scope.
        cell, var_frame, cell_name = self._ResolveNameOrRef(
            new_name, scope_e.Dynamic, ref_trail=ref_trail)
        return cell, var_frame, cell_name

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

                if 0:
                    # Check that the frame is still alive
                    # Note: Disabled because it doesn't work with modules.  the
                    # Place captures a frame in def-test.ysh, which we want to
                    # mutate while Dict is executing in the module_frame for
                    # def.ysh.  See ctx_ModuleEval
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

                frame = place.frame
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
        """
        Set a name in the local scope - used for func/proc param binding, etc.
        """

        # Equivalent to
        # self._ResolveNameOnly(lval.name, scope_e.LocalOnly)
        var_frame = self.var_stack[-1]
        cell = var_frame.get(lval.name)

        if cell:
            if cell.readonly:
                e_die("Can't assign to readonly value %r" % lval.name,
                      lval.blame_loc)
            cell.val = val  # Mutate value_t
        else:
            cell = Cell(False, False, False, val)
            var_frame[lval.name] = cell

    def SetNamedYsh(self, lval, val, which_scopes, flags=0):
        # type: (LeftName, value_t, scope_t, int) -> None
        """Set the value of a named variable, for YSH.

        This has simpler logic than Mem.SetNamed().  It also handles 'const'
        and 'var' in closures, via the YshDecl flag.
        """
        # Scopes to handle: LocalOnly (setvar), GlobalOnly (setglobal)
        assert which_scopes in (scope_e.LocalOnly,
                                scope_e.GlobalOnly), which_scopes

        # Flags to handle: SetReadOnly (const), YshDecl (const, var)
        assert flags & ClearReadOnly == 0, flags

        assert flags & SetExport == 0, flags
        assert flags & ClearExport == 0, flags

        assert flags & SetNameref == 0, flags
        assert flags & ClearNameref == 0, flags

        cell, var_frame = self._ResolveNameForYshMutation(
            lval.name, which_scopes, bool(flags & YshDecl))

        if cell:
            # Note: this DYNAMIC check means we can't have 'const' in a loop.
            # But that's true for 'readonly' too, and hoisting it makes more
            # sense anyway.
            if cell.readonly:
                e_die("Can't assign to readonly value %r" % lval.name,
                      lval.blame_loc)
            cell.val = val  # CHANGE VAL

            if flags & SetReadOnly:
                cell.readonly = True

        else:
            cell = Cell(False, bool(flags & SetReadOnly), False, val)
            var_frame[lval.name] = cell

        # Maintain invariant that only strings and undefined cells can be
        # exported.
        assert cell.val is not None, cell

    def SetNamed(self, lval, val, which_scopes, flags=0):
        # type: (LeftName, Optional[value_t], scope_t, int) -> None
        """Set the value of a named variable.

        TODO: Clear up semantics when 'val is None'.

        This can be used to FLIP flags, while NOT changing the variable.  Or it
        can also be used to initialize?
        """
        if flags & SetNameref or flags & ClearNameref:
            # declare -n ref=x  # refers to the ref itself
            cell, var_frame = self._ResolveNameOnly(lval.name, which_scopes)
            cell_name = lval.name
        else:
            # ref=x  # mutates THROUGH the reference

            # Note on how to implement declare -n ref='a[42]'
            # 1. Call _ResolveNameOnly()
            # 2. If cell.nameref, call self.unsafe_arith.ParseVarRef() ->
            #    BracedVarSub
            # 3. Turn BracedVarSub into an sh_lvalue, and call
            #    self.unsafe_arith.SetValue() wrapper with ref_trail
            cell, var_frame, cell_name = self._ResolveNameOrRef(
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
            var_frame[cell_name] = cell

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
        # 2) Never change types?  yeah I think that's a good idea, at least for YSH
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

                # TODO: relax this for YSH
                assert val.tag() == value_e.Str, val
                rval = cast(value.Str, val)

                # Note: location could be a[x]=1 or (( a[ x ] = 1 ))
                left_loc = lval.blame_loc

                # bash/mksh have annoying behavior of letting you do LHS assignment to
                # Undef, which then turns into an INDEXED array.  (Undef means that set
                # -o nounset fails.)
                cell, var_frame, _ = self._ResolveNameOrRef(
                    lval.name, which_scopes)
                if not cell:
                    self._BindNewArrayWithEntry(var_frame, lval, rval, flags,
                                                left_loc)
                    return

                if cell.readonly:
                    e_die("Can't assign to readonly array", left_loc)

                UP_cell_val = cell.val
                # undef[0]=y is allowed
                with tagswitch(UP_cell_val) as case2:
                    if case2(value_e.Undef):
                        self._BindNewArrayWithEntry(var_frame, lval, rval,
                                                    flags, left_loc)
                        return

                    elif case2(value_e.Str):
                        # s=x
                        # s[1]=y  # invalid
                        e_die("Can't assign to items in a string", left_loc)

                    elif case2(value_e.InternalStringArray):
                        cell_val = cast(value.InternalStringArray, UP_cell_val)
                        error_code = bash_impl.InternalStringArray_SetElement(
                            cell_val, lval.index, rval.s)
                        if error_code == error_code_e.IndexOutOfRange:
                            n = bash_impl.InternalStringArray_Length(cell_val)
                            e_die(
                                "Index %d is out of bounds for array of length %d"
                                % (lval.index, n), left_loc)
                        return

                    elif case2(value_e.BashArray):
                        lhs_sp = cast(value.BashArray, UP_cell_val)
                        error_code = bash_impl.BashArray_SetElement(
                            lhs_sp, mops.IntWiden(lval.index), rval.s)
                        if error_code == error_code_e.IndexOutOfRange:
                            n_big = bash_impl.BashArray_Length(lhs_sp)
                            e_die(
                                "Index %d is out of bounds for array of length %s"
                                % (lval.index, mops.ToStr(n_big)), left_loc)
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

                cell, var_frame, _ = self._ResolveNameOrRef(
                    lval.name, which_scopes)
                if cell.readonly:
                    e_die("Can't assign to readonly associative array",
                          left_loc)

                # We already looked it up before making the sh_lvalue
                assert cell.val.tag() == value_e.BashAssoc, cell
                cell_val2 = cast(value.BashAssoc, cell.val)
                bash_impl.BashAssoc_SetElement(cell_val2, lval.key, rval.s)

            else:
                raise AssertionError(lval.tag())

    def _BindNewArrayWithEntry(self, var_frame, lval, val, flags, blame_loc):
        # type: (Dict[str, Cell], sh_lvalue.Indexed, value.Str, int, loc_t) -> None
        """Fill 'var_frame' with a new indexed array entry."""

        new_value = bash_impl.BashArray_New()
        error_code = bash_impl.BashArray_SetElement(new_value,
                                                    mops.IntWiden(lval.index),
                                                    val.s)
        if error_code == error_code_e.IndexOutOfRange:
            e_die(
                "Index %d is out of bounds for array of length 0" % lval.index,
                blame_loc)

        # arrays can't be exported; can't have BashAssoc flag
        readonly = bool(flags & SetReadOnly)
        var_frame[lval.name] = Cell(False, readonly, False, new_value)

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
            if case('_status'):  # deprecated in favor of _error.code
                return num.ToBig(self.TryStatus())

            elif case('_error'):
                return self.TryError()

            elif case('_this_dir'):
                if len(self.this_dir) == 0:
                    # e.g. osh -c '' doesn't have it set
                    # Should we give a custom error here?
                    # If you're at the interactive shell, 'source mymodule.ysh' will still
                    # work because 'source' sets it.
                    return value.Undef
                else:
                    return value.Str(self.this_dir[-1])  # top of stack

            elif case('PIPESTATUS'):
                strs2 = [str(i)
                         for i in self.pipe_status[-1]]  # type: List[str]
                return value.InternalStringArray(strs2)

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
                return value.InternalStringArray(groups)

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
                        if case2(debug_frame_e.ProcLike):
                            frame = cast(debug_frame.ProcLike, UP_frame)
                            strs.append(frame.proc_name)

                        elif case2(debug_frame_e.Source):
                            # bash doesn't tell you the filename sourced
                            strs.append('source')

                        elif case2(debug_frame_e.MainFile):
                            strs.append('main')  # also bash behavior

                        else:  # ignore
                            pass

                return value.InternalStringArray(
                    strs)  # TODO: Reuse this object too?

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
                        if case2(debug_frame_e.ProcLike):
                            frame = cast(debug_frame.ProcLike, UP_frame)

                            # Weird bash behavior
                            assert frame.def_tok.line is not None
                            source_str = ui.GetLineSourceString(
                                frame.def_tok.line)
                            strs.append(source_str)

                        elif case2(debug_frame_e.Source):
                            frame = cast(debug_frame.Source, UP_frame)
                            # Is this right?
                            strs.append(frame.source_name)

                        elif case2(debug_frame_e.MainFile):
                            frame = cast(debug_frame.MainFile, UP_frame)
                            strs.append(frame.main_filename)

                        else:  # ignore
                            pass

                return value.InternalStringArray(
                    strs)  # TODO: Reuse this object too?

            elif case('BASH_LINENO'):
                strs = []
                for frame in reversed(self.debug_stack):
                    UP_frame = frame
                    with tagswitch(frame) as case2:
                        if case2(debug_frame_e.ProcLike):
                            frame = cast(debug_frame.ProcLike, UP_frame)
                            invoke_token = location.LeftTokenForCompoundWord(
                                frame.invoke_loc)
                            assert invoke_token is not None, frame.invoke_loc
                            strs.append(_LineNumber(invoke_token))

                        elif case2(debug_frame_e.Source):
                            frame = cast(debug_frame.Source, UP_frame)
                            invoke_token = location.LeftTokenForCompoundWord(
                                frame.source_loc)
                            assert invoke_token is not None, frame.source_loc
                            strs.append(_LineNumber(invoke_token))

                        elif case2(debug_frame_e.MainFile):
                            # Bash does this to line up with 'main'
                            strs.append('0')

                        else:  # ignore
                            pass

                return value.InternalStringArray(
                    strs)  # TODO: Reuse this object too?

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

                builtin_val = self.builtins.get(name)
                if builtin_val:
                    return builtin_val

                # TODO: Can look in the builtins module, which is a value.Obj
                return value.Undef

    def GetCell(self, name, which_scopes=scope_e.Shopt):
        # type: (str, scope_t) -> Cell
        """Get both the value and flags.

        Usages:
          - the 'pp' builtin.
          - declare -p
          - ${x@a}
          - to test of 'TZ' is exported in printf?  Why?

        Note: consulting __builtins__ doesn't see necessary for any of these
        """
        if which_scopes == scope_e.Shopt:
            which_scopes = self.ScopesForReading()

        cell, _ = self._ResolveNameOnly(name, which_scopes)
        return cell

    def GetCellDeref(self, name, which_scopes=scope_e.Shopt):
        # type: (str, scope_t) -> Cell
        """Get both the value and flags. Unlike GetCell, this resolves
        name references.
        """
        if which_scopes == scope_e.Shopt:
            which_scopes = self.ScopesForReading()

        cell, _, _ = self._ResolveNameOrRef(name, which_scopes)
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

        cell, var_frame, cell_name = self._ResolveNameOrRef(
            var_name, which_scopes)
        if not cell:
            return False  # 'unset' builtin falls back on functions
        if cell.readonly:
            raise error.Runtime("Can't unset readonly variable %r" % var_name)

        with tagswitch(lval) as case:
            if case(sh_lvalue_e.Var):  # unset x
                # Make variables in higher scopes visible.
                # example: test/spec.sh builtin-vars -r 24 (ble.sh)
                mylib.dict_erase(var_frame, cell_name)

                # alternative that some shells use:
                #   var_frame[cell_name].val = value.Undef
                #   cell.exported = False

                # This should never happen because we do recursive lookups of namerefs.
                assert not cell.nameref, cell

            elif case(sh_lvalue_e.Indexed):  # unset 'a[1]'
                lval = cast(sh_lvalue.Indexed, UP_lval)
                # Note: Setting an entry to None and shifting entries are pretty
                # much the same in shell.

                val = cell.val
                UP_val = val
                if val.tag() == value_e.InternalStringArray:
                    val = cast(value.InternalStringArray, UP_val)
                    error_code = bash_impl.InternalStringArray_UnsetElement(
                        val, lval.index)
                    if error_code == error_code_e.IndexOutOfRange:
                        n = bash_impl.InternalStringArray_Length(val)
                        raise error.Runtime(
                            "%s[%d]: Index is out of bounds for array of length %d"
                            % (var_name, lval.index, n))
                elif val.tag() == value_e.BashArray:
                    val = cast(value.BashArray, UP_val)
                    error_code = bash_impl.BashArray_UnsetElement(
                        val, mops.IntWiden(lval.index))
                    if error_code == error_code_e.IndexOutOfRange:
                        big_length = bash_impl.BashArray_Length(val)
                        raise error.Runtime(
                            "%s[%d]: Index is out of bounds for array of length %s"
                            % (var_name, lval.index, mops.ToStr(big_length)))
                else:
                    raise error.Runtime("%r isn't an array" % var_name)

            elif case(sh_lvalue_e.Keyed):  # unset 'A["K"]'
                lval = cast(sh_lvalue.Keyed, UP_lval)

                val = cell.val
                UP_val = val

                # note: never happens because of mem.IsBashAssoc test for sh_lvalue.Keyed
                #if val.tag() != value_e.BashAssoc:
                #  raise error.Runtime("%r isn't an associative array" % lval.name)

                val = cast(value.BashAssoc, UP_val)
                bash_impl.BashAssoc_UnsetElement(val, lval.key)

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
        cell, var_frame = self._ResolveNameOnly(name, self.ScopesForReading())
        if cell:
            if flag & ClearExport:
                cell.exported = False
            if flag & ClearNameref:
                cell.nameref = False
            return True
        else:
            return False

    def _FillWithExported(self, new_env):
        # type: (Dict[str, str]) -> None

        # Search from globals up.  Names higher on the stack will overwrite
        # names lower on the stack.
        for scope in self.var_stack:
            for name, cell in iteritems(scope):
                if cell.exported and cell.val.tag() == value_e.Str:
                    val = cast(value.Str, cell.val)
                    new_env[name] = val.s

    def _FillEnvObj(self, new_env, env_object):
        # type: (Dict[str, str], Obj) -> None

        # Do the LEAST visible parts first
        if env_object.prototype is not None:
            self._FillEnvObj(new_env, env_object.prototype)

        # Overwrite with MOST visible parts
        for name, val in iteritems(env_object.d):
            if val.tag() != value_e.Str:
                continue
            new_env[name] = cast(value.Str, val).s

    def GetEnv(self):
        # type: () -> Dict[str, str]
        """
        Get the environment that should be used for launching processes.

        Note: This is run on every SimpleCommand.  Should we have a dirty
        flag?  We could notice these things:

        - If an exported variable is changed
        - If the set of exported variables changes.
        """
        new_env = NewDict()  # type: Dict[str, str]

        # Note: ysh:upgrade has both of these behaviors

        # OSH: Consult exported vars
        if not self.exec_opts.no_exported():
            self._FillWithExported(new_env)

        # YSH: Consult the ENV dict
        if self.exec_opts.env_obj():
            self._FillEnvObj(new_env, self.env_object)

        return new_env

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

    def GetAllCells(self, which_scopes):
        # type: (scope_t) -> Dict[str, Cell]
        """Get all variables and their values, for 'set' builtin."""
        result = NewDict()  # type: Dict[str, Cell]

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


def ObjIsReadOnly(obj):
    # type: (Obj) -> bool
    if not obj.prototype:
        return False

    # Any value makes the object read-only, but value.Bool(True) is conventional
    return '__readonly__' in obj.prototype.d


def ValueIsInvokableObj(val):
    # type: (value_t) -> Tuple[Optional[value_t], Optional[Obj]]
    """
    Returns:
      (__invoke__ Proc or BuiltinProc, self Obj) if the value is invokable
      (None, None) otherwise
    """
    if val.tag() != value_e.Obj:
        return None, None

    obj = cast(Obj, val)
    if not obj.prototype:
        return None, None

    invoke_val = obj.prototype.d.get('__invoke__')
    if invoke_val is None:
        return None, None

    # TODO: __invoke__ of wrong type could be fatal error?
    if invoke_val.tag() in (value_e.Proc, value_e.BuiltinProc):
        return invoke_val, obj

    return None, None


def _AddNames(unique, frame):
    # type: (Dict[str, bool], Dict[str, Cell]) -> None
    for name in frame:
        val = frame[name].val
        if val.tag() == value_e.Proc:
            unique[name] = True
        proc, _ = ValueIsInvokableObj(val)
        if proc is not None:
            unique[name] = True


class Procs(object):
    """
    Terminology:

    - invokable - these are INTERIOR
      - value.Proc - which can be shell function in __sh_function__ namespace, or
                     YSH proc
      - value.Obj with __invoke__
    - exterior - external commands, extern builtin

    Note: the YSH 'invoke' builtin can generalize YSH 'runproc' builtin, shell command/builtin,
          and also type / type -a
    """

    def __init__(self, mem):
        # type: (Mem) -> None
        self.mem = mem
        self.sh_funcs = NewDict()  # type: Dict[str, value_t]

        # Reflection
        #mem.AddBuiltin('__sh_function__', value.Dict(self.sh_funcs))

    def DefineShellFunc(self, name, proc):
        # type: (str, value.Proc) -> None
        self.sh_funcs[name] = proc

    def IsShellFunc(self, name):
        # type: (str) -> bool
        return name in self.sh_funcs

    def GetShellFunc(self, name):
        # type: (str) -> Optional[value.Proc]
        val = self.sh_funcs.get(name)
        if val is None:
            return None

        # Note: this runtime check became necessary when exposing
        # __sh_function__ as a YSH Dict.
        # It would be nicer if that dict were not MUTABLE!  This should not
        # work:
        #     setvar __sh_function__.foo = 42
        if val.tag() != value_e.Proc:
            return None

        return cast(value.Proc, val)

    def EraseShellFunc(self, to_del):
        # type: (str) -> None
        """Undefine a sh-func with name `to_del`, if it exists."""
        mylib.dict_erase(self.sh_funcs, to_del)

    def ShellFuncNames(self):
        # type: () -> List[str]
        """Returns a *sorted* list of all shell function names

        Callers:
          declare -f -F
        """
        names = self.sh_funcs.keys()
        names.sort()
        return names

    def DefineProc(self, name, proc):
        # type: (str, value.Proc) -> None
        """
        procs are defined in the local scope.
        """
        self.mem.var_stack[-1][name] = Cell(False, False, False, proc)
        # Doesn't make a difference?
        #self.mem.SetNamedYsh(location.LName(name), proc, scope_e.LocalOnly, flags=YshDecl)

    def IsProc(self, name):
        # type: (str) -> bool

        maybe_proc = self.mem.GetValue(name)
        # Could be Undef
        return maybe_proc.tag() == value_e.Proc

    def IsInvokableObj(self, name):
        # type: (str) -> bool

        val = self.mem.GetValue(name)
        proc, _ = ValueIsInvokableObj(val)
        return proc is not None

    def InvokableNames(self):
        # type: () -> List[str]
        """Returns a *sorted* list of all invokable names

        Callers:
          complete -A function
          pp proc - should deprecate this
        """
        unique = NewDict()  # type: Dict[str, bool]
        for name in self.sh_funcs:
            unique[name] = True

        top_frame = self.mem.var_stack[-1]
        _AddNames(unique, top_frame)

        global_frame = self.mem.var_stack[0]
        #log('%d %d', id(top_frame), id(global_frame))
        if global_frame is not top_frame:
            _AddNames(unique, global_frame)

        #log('%s', unique)

        names = unique.keys()
        names.sort()

        return names

    def GetProc(self, name):
        # type: (str) -> Tuple[Optional[value_t], Optional[Obj]]
        """Get YSH procs/invokables only, for invoke --proc
        """
        val = self.mem.GetValue(name)

        if val.tag() == value_e.Proc:
            return cast(value.Proc, val), None

        proc, self_val = ValueIsInvokableObj(val)
        if proc:
            return proc, self_val

        return None, None

    def GetInvokable(self, name):
        # type: (str) -> Tuple[Optional[value_t], Optional[Obj]]
        """Find a proc, invokable Obj, or sh-func, in that order

        Callers:
          executor.py: to actually run
          meta_oils.py runproc lookup - this is not 'invoke', because it is
             INTERIOR shell functions, procs, invokable Obj
        """
        proc, self_val = self.GetProc(name)
        if proc:
            return proc, self_val

        if name in self.sh_funcs:
            return self.sh_funcs[name], None

        return None, None


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
    BuiltinSetValue(mem, location.LName(name), bash_impl.BashArray_FromList(a))


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
    mem.SetNamed(location.LName(name), bash_impl.BashArray_FromList(a),
                 scope_e.GlobalOnly)


def SetGlobalValue(mem, name, val):
    # type: (Mem, str, value_t) -> None
    """Helper for completion, etc."""
    mem.SetNamed(location.LName(name), val, scope_e.GlobalOnly)


def SetLocalValue(mem, name, val):
    # type: (Mem, str, value_t) -> None
    """For 'use' builtin."""
    mem.SetNamed(location.LName(name), val, scope_e.LocalOnly)


def ExportGlobalString(mem, name, s):
    # type: (Mem, str, str) -> None
    """Helper for completion, $PWD, $OLDPWD, etc."""
    assert isinstance(s, str)
    val = value.Str(s)
    mem.SetNamed(location.LName(name),
                 val,
                 scope_e.GlobalOnly,
                 flags=SetExport)


# TODO: remove in favor of EnvConfig
def SetStringInEnv(mem, var_name, s):
    # type: (Mem, str, str) -> None
    if mem.exec_opts.env_obj():  # e.g. ENV.YSH_HISTFILE
        mem.env_dict[var_name] = value.Str(s)
    else:  # e.g. $YSH_HISTFILE
        SetGlobalString(mem, var_name, s)


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
    """Wrapper around GetValue().

    Check that HOME, PWD, OLDPWD, etc. are strings. bash doesn't have these
    errors because ${array} is ${array[0]}.

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
