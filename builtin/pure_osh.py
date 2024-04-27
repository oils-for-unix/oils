#!/usr/bin/env python2
"""
pure_osh.py - Builtins that don't do any I/O.

If the OSH interpreter were embedded in another program, these builtins can be
safely used, e.g. without worrying about modifying the file system.

NOTE: There can be spew on stdout, e.g. for shopt -p and so forth.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.syntax_asdl import loc
from _devbuild.gen.types_asdl import opt_group_i

from core import error
from core.error import e_usage
from core import state
from core import ui
from core import vm
from data_lang import j8_lite
from frontend import args
from frontend import consts
from frontend import flag_util
from frontend import match
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import print_stderr, log

from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value
    from core.state import MutableOpts, Mem, SearchPath
    from osh.cmd_eval import CommandEvaluator

_ = log


class Boolean(vm._Builtin):
    """For :, true, false."""

    def __init__(self, status):
        # type: (int) -> None
        self.status = status

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        # These ignore regular args, but shouldn't accept typed args.
        typed_args.DoesNotAccept(cmd_val.typed_args)
        return self.status


class Alias(vm._Builtin):

    def __init__(self, aliases, errfmt):
        # type: (Dict[str, str], ui.ErrorFormatter) -> None
        self.aliases = aliases
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('alias', cmd_val)
        argv = arg_r.Rest()

        if len(argv) == 0:
            for name in sorted(self.aliases):
                alias_exp = self.aliases[name]
                # This is somewhat like bash, except we use %r for ''.
                print('alias %s=%r' % (name, alias_exp))
            return 0

        status = 0
        for i, arg in enumerate(argv):
            name, alias_exp = mylib.split_once(arg, '=')
            if alias_exp is None:  # if we get a plain word without, print alias
                alias_exp = self.aliases.get(name)
                if alias_exp is None:
                    self.errfmt.Print_('No alias named %r' % name,
                                       blame_loc=cmd_val.arg_locs[i])
                    status = 1
                else:
                    print('alias %s=%r' % (name, alias_exp))
            else:
                self.aliases[name] = alias_exp

        #print(argv)
        #log('AFTER ALIAS %s', aliases)
        return status


class UnAlias(vm._Builtin):

    def __init__(self, aliases, errfmt):
        # type: (Dict[str, str], ui.ErrorFormatter) -> None
        self.aliases = aliases
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('unalias', cmd_val)
        argv = arg_r.Rest()

        if len(argv) == 0:
            e_usage('requires an argument', loc.Missing)

        status = 0
        for i, name in enumerate(argv):
            if name in self.aliases:
                mylib.dict_erase(self.aliases, name)
            else:
                self.errfmt.Print_('No alias named %r' % name,
                                   blame_loc=cmd_val.arg_locs[i])
                status = 1
        return status


def SetOptionsFromFlags(exec_opts, opt_changes, shopt_changes):
    # type: (MutableOpts, List[Tuple[str, bool]], List[Tuple[str, bool]]) -> None
    """Used by core/shell.py."""

    # We can set ANY option with -o.  -O is too annoying to type.
    for opt_name, b in opt_changes:
        exec_opts.SetAnyOption(opt_name, b)

    for opt_name, b in shopt_changes:
        exec_opts.SetAnyOption(opt_name, b)


class Set(vm._Builtin):

    def __init__(self, exec_opts, mem):
        # type: (MutableOpts, Mem) -> None
        self.exec_opts = exec_opts
        self.mem = mem

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        # TODO:
        # - How to integrate this with auto-completion?  Have to handle '+'.

        if len(cmd_val.argv) == 1:
            # 'set' without args shows visible variable names and values.  According
            # to POSIX:
            # - the names should be sorted, and
            # - the code should be suitable for re-input to the shell.  We have a
            #   spec test for this.
            # Also:
            # - autoconf also wants them to fit on ONE LINE.
            # http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#set
            mapping = self.mem.GetAllVars()
            for name in sorted(mapping):
                str_val = mapping[name]
                code_str = '%s=%s' % (name, j8_lite.MaybeShellEncode(str_val))
                print(code_str)
            return 0

        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
        arg_r.Next()  # skip 'set'
        arg = flag_util.ParseMore('set', arg_r)

        # 'set -o' shows options.  This is actually used by autoconf-generated
        # scripts!
        if arg.show_options:
            self.exec_opts.ShowOptions([])
            return 0

        # Note: set -o nullglob is not valid.  The 'shopt' builtin is preferred in
        # YSH, and we want code to be consistent.
        for opt_name, b in arg.opt_changes:
            self.exec_opts.SetOldOption(opt_name, b)

        for opt_name, b in arg.shopt_changes:
            self.exec_opts.SetAnyOption(opt_name, b)

        # Hm do we need saw_double_dash?
        if arg.saw_double_dash or not arg_r.AtEnd():
            self.mem.SetArgv(arg_r.Rest())
        return 0


class Shopt(vm._Builtin):

    def __init__(self, mutable_opts, cmd_ev):
        # type: (MutableOpts, CommandEvaluator) -> None
        self.mutable_opts = mutable_opts
        self.cmd_ev = cmd_ev

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('shopt',
                                             cmd_val,
                                             accept_typed_args=True)

        arg = arg_types.shopt(attrs.attrs)
        opt_names = arg_r.Rest()

        if arg.p:  # print values
            if arg.o:  # use set -o names
                self.mutable_opts.ShowOptions(opt_names)
            else:
                self.mutable_opts.ShowShoptOptions(opt_names)
            return 0

        if arg.q:  # query values
            for name in opt_names:
                index = consts.OptionNum(name)
                if index == 0:
                    return 2  # bash gives 1 for invalid option; 2 is better
                if not self.mutable_opts.opt0_array[index]:
                    return 1  # at least one option is not true
            return 0  # all options are true

        if arg.s:
            b = True
        elif arg.u:
            b = False
        else:
            # If no flags are passed, print the options.  bash prints uses a
            # different format for 'shopt', but we use the same format as 'shopt
            # -p'.
            self.mutable_opts.ShowShoptOptions(opt_names)
            return 0

        cmd = typed_args.OptionalBlock(cmd_val)
        if cmd:
            opt_nums = []  # type: List[int]
            for opt_name in opt_names:
                # TODO: could consolidate with checks in core/state.py and option
                # lexer?
                opt_group = consts.OptionGroupNum(opt_name)
                if opt_group == opt_group_i.YshUpgrade:
                    opt_nums.extend(consts.YSH_UPGRADE)
                    continue

                if opt_group == opt_group_i.YshAll:
                    opt_nums.extend(consts.YSH_ALL)
                    continue

                if opt_group == opt_group_i.StrictAll:
                    opt_nums.extend(consts.STRICT_ALL)
                    continue

                index = consts.OptionNum(opt_name)
                if index == 0:
                    # TODO: location info
                    e_usage('got invalid option %r' % opt_name, loc.Missing)
                opt_nums.append(index)

            with state.ctx_Option(self.mutable_opts, opt_nums, b):
                unused = self.cmd_ev.EvalCommand(cmd)
            return 0  # cd also returns 0

        # Otherwise, set options.
        for opt_name in opt_names:
            # We allow set -o options here
            self.mutable_opts.SetAnyOption(opt_name, b)

        return 0


class Hash(vm._Builtin):

    def __init__(self, search_path):
        # type: (SearchPath) -> None
        self.search_path = search_path

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('hash', cmd_val)
        arg = arg_types.hash(attrs.attrs)

        rest = arg_r.Rest()
        if arg.r:
            if len(rest):
                e_usage('got extra arguments after -r', loc.Missing)
            self.search_path.ClearCache()
            return 0

        status = 0
        if len(rest):
            for cmd in rest:  # enter in cache
                full_path = self.search_path.CachedLookup(cmd)
                if full_path is None:
                    print_stderr('hash: %r not found' % cmd)
                    status = 1
        else:  # print cache
            commands = self.search_path.CachedCommands()
            commands.sort()
            for cmd in commands:
                print(cmd)

        return status


def _ParseOptSpec(spec_str):
    # type: (str) -> Dict[str, bool]
    spec = {}  # type: Dict[str, bool]
    i = 0
    n = len(spec_str)
    while True:
        if i >= n:
            break
        ch = spec_str[i]
        spec[ch] = False
        i += 1
        if i >= n:
            break
        # If the next character is :, change the value to True.
        if spec_str[i] == ':':
            spec[ch] = True
            i += 1
    return spec


class GetOptsState(object):
    """State persisted across invocations.

    This would be simpler in GetOpts.
    """

    def __init__(self, mem, errfmt):
        # type: (Mem, ui.ErrorFormatter) -> None
        self.mem = mem
        self.errfmt = errfmt
        self._optind = -1
        self.flag_pos = 1  # position within the arg, public var

    def _OptInd(self):
        # type: () -> int
        """Returns OPTIND that's >= 1, or -1 if it's invalid."""
        # Note: OPTIND could be value.Int?
        try:
            result = state.GetInteger(self.mem, 'OPTIND')
        except error.Runtime as e:
            self.errfmt.Print_(e.UserErrorString())
            result = -1
        return result

    def GetArg(self, argv):
        # type: (List[str]) -> Optional[str]
        """Get the value of argv at OPTIND.

        Returns None if it's out of range.
        """

        #log('_optind %d flag_pos %d', self._optind, self.flag_pos)

        optind = self._OptInd()
        if optind == -1:
            return None
        self._optind = optind  # save for later

        i = optind - 1  # 1-based index
        #log('argv %s i %d', argv, i)
        if 0 <= i and i < len(argv):
            return argv[i]
        else:
            return None

    def IncIndex(self):
        # type: () -> None
        """Increment OPTIND."""
        # Note: bash-completion uses a *local* OPTIND !  Not global.
        assert self._optind != -1
        state.BuiltinSetString(self.mem, 'OPTIND', str(self._optind + 1))
        self.flag_pos = 1

    def SetArg(self, optarg):
        # type: (str) -> None
        """Set OPTARG."""
        state.BuiltinSetString(self.mem, 'OPTARG', optarg)

    def Fail(self):
        # type: () -> None
        """On failure, reset OPTARG."""
        state.BuiltinSetString(self.mem, 'OPTARG', '')


def _GetOpts(
        spec,  # type: Dict[str, bool]
        argv,  # type: List[str]
        my_state,  # type: GetOptsState
        errfmt,  # type: ui.ErrorFormatter
):
    # type: (...) -> Tuple[int, str]
    current = my_state.GetArg(argv)
    #log('current %s', current)

    if current is None:  # out of range, etc.
        my_state.Fail()
        return 1, '?'

    if not current.startswith('-') or current == '-':
        my_state.Fail()
        return 1, '?'

    flag_char = current[my_state.flag_pos]

    if my_state.flag_pos < len(current) - 1:
        my_state.flag_pos += 1  # don't move past this arg yet
        more_chars = True
    else:
        my_state.IncIndex()
        my_state.flag_pos = 1
        more_chars = False

    if flag_char not in spec:  # Invalid flag
        return 0, '?'

    if spec[flag_char]:  # does it need an argument?
        if more_chars:
            optarg = current[my_state.flag_pos:]
        else:
            optarg = my_state.GetArg(argv)
            if optarg is None:
                my_state.Fail()
                # TODO: Add location info
                errfmt.Print_('getopts: option %r requires an argument.' %
                              current)
                tmp = [j8_lite.MaybeShellEncode(a) for a in argv]
                print_stderr('(getopts argv: %s)' % ' '.join(tmp))

                # Hm doesn't cause status 1?
                return 0, '?'
        my_state.IncIndex()
        my_state.SetArg(optarg)
    else:
        my_state.SetArg('')

    return 0, flag_char


class GetOpts(vm._Builtin):
    """
  Vars used:
    OPTERR: disable printing of error messages
  Vars set:
    The variable named by the second arg
    OPTIND - initialized to 1 at startup
    OPTARG - argument
  """

    def __init__(self, mem, errfmt):
        # type: (Mem, ui.ErrorFormatter) -> None
        self.mem = mem
        self.errfmt = errfmt

        # TODO: state could just be in this object
        self.my_state = GetOptsState(mem, errfmt)
        self.spec_cache = {}  # type: Dict[str, Dict[str, bool]]

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
        arg_r.Next()

        # NOTE: If first char is a colon, error reporting is different.  Alpine
        # might not use that?
        spec_str = arg_r.ReadRequired('requires an argspec')

        var_name, var_loc = arg_r.ReadRequired2(
            'requires the name of a variable to set')

        spec = self.spec_cache.get(spec_str)
        if spec is None:
            spec = _ParseOptSpec(spec_str)
            self.spec_cache[spec_str] = spec

        user_argv = self.mem.GetArgv() if arg_r.AtEnd() else arg_r.Rest()
        #log('user_argv %s', user_argv)
        status, flag_char = _GetOpts(spec, user_argv, self.my_state,
                                     self.errfmt)

        if match.IsValidVarName(var_name):
            state.BuiltinSetString(self.mem, var_name, flag_char)
        else:
            # NOTE: The builtin has PARTIALLY set state.  This happens in all shells
            # except mksh.
            raise error.Usage('got invalid variable name %r' % var_name,
                              var_loc)
        return status
