from __future__ import print_function

from _devbuild.gen.runtime_asdl import scope_e
from _devbuild.gen.value_asdl import value, value_e
from core.error import e_die
from core import pyos
from core import pyutil
from core import optview
from core import state
from frontend import location
from mycpp.mylib import tagswitch, iteritems
from osh import split

import libc
import posix_ as posix

from typing import Dict, cast

# This was derived from bash --norc -c 'argv "$COMP_WORDBREAKS".
# Python overwrites this to something Python-specific in Modules/readline.c, so
# we have to set it back!
# Used in both core/competion.py and osh/state.py
_READLINE_DELIMS = ' \t\n"\'><=;|&(:'


def GetWorkingDir():
    # type: () -> str
    """Fallback for pwd and $PWD when there's no 'cd' and no inherited $PWD."""
    try:
        return posix.getcwd()
    except (IOError, OSError) as e:
        e_die("Can't determine working directory: %s" % pyutil.strerror(e))


def InitDefaultVars(mem):
    # type: (state.Mem) -> None

    # These 3 are special, can't be changed
    state.SetGlobalString(mem, 'UID', str(posix.getuid()))
    state.SetGlobalString(mem, 'EUID', str(posix.geteuid()))
    state.SetGlobalString(mem, 'PPID', str(posix.getppid()))

    # For getopts builtin - meant to be read, not changed
    state.SetGlobalString(mem, 'OPTIND', '1')

    # These can be changed.  Could go AFTER environment, e.g. in
    # InitVarsAfterEnv().

    # Default value; user may unset it.
    # $ echo -n "$IFS" | python -c 'import sys;print repr(sys.stdin.read())'
    # ' \t\n'
    state.SetGlobalString(mem, 'IFS', split.DEFAULT_IFS)

    state.SetGlobalString(mem, 'HOSTNAME', libc.gethostname())

    # In bash, this looks like 'linux-gnu', 'linux-musl', etc.  Scripts test
    # for 'darwin' and 'freebsd' too.  They generally don't like at 'gnu' or
    # 'musl'.  We don't have that info, so just make it 'linux'.
    state.SetGlobalString(mem, 'OSTYPE', pyos.OsType())

    # When xtrace_rich is off, this is just like '+ ', the shell default
    state.SetGlobalString(mem, 'PS4',
                          '${SHX_indent}${SHX_punct}${SHX_pid_str} ')

    # bash-completion uses this.  Value copied from bash.  It doesn't integrate
    # with 'readline' yet.
    state.SetGlobalString(mem, 'COMP_WORDBREAKS', _READLINE_DELIMS)

    # TODO on $HOME: bash sets it if it's a login shell and not in POSIX mode!
    # if (login_shell == 1 && posixly_correct == 0)
    #   set_home_var ();


def CopyVarsFromEnv(exec_opts, environ, mem):
    # type: (optview.Exec, Dict[str, str], state.Mem) -> None

    # POSIX shell behavior: env vars become exported global vars
    if not exec_opts.no_exported():
        # This is the way dash and bash work -- at startup, they turn everything in
        # 'environ' variable into shell variables.  Bash has an export_env
        # variable.  Dash has a loop through environ in init.c
        for n, v in iteritems(environ):
            mem.SetNamed(location.LName(n),
                         value.Str(v),
                         scope_e.GlobalOnly,
                         flags=state.SetExport)

    # YSH behavior: env vars go in ENV dict, not exported vars.  Note that
    # ysh:upgrade can have BOTH ENV and exported vars.  It's OK if they're on
    # at the same time.
    if exec_opts.env_obj():
        # This is for invoking bin/ysh
        # If you run bin/osh, then exec_opts.env_obj() will be FALSE at this point.
        # When you write shopt --set ysh:all or ysh:upgrade, then the shopt
        # builtin will call MaybeInitEnvDict()
        mem.MaybeInitEnvDict(environ)


def InitVarsAfterEnv(mem):
    # type: (state.Mem) -> None

    # If PATH SHELLOPTS PWD are not in environ, then initialize them.
    val = mem.GetValue('PATH')
    if val.tag() == value_e.Undef:
        # Setting PATH to these two dirs match what zsh and mksh do.  bash and
        # dash add {,/usr/,/usr/local}/{bin,sbin}
        state.SetGlobalString(mem, 'PATH', '/bin:/usr/bin')

    val = mem.GetValue('SHELLOPTS')
    if val.tag() == value_e.Undef:
        # Divergence: bash constructs a string here too, it doesn't just read it
        state.SetGlobalString(mem, 'SHELLOPTS', '')
    # It's readonly, even if it's not set
    mem.SetNamed(location.LName('SHELLOPTS'),
                 None,
                 scope_e.GlobalOnly,
                 flags=state.SetReadOnly)
    # NOTE: bash also has BASHOPTS

    val = mem.GetValue('PWD')
    if val.tag() == value_e.Undef:
        state.SetGlobalString(mem, 'PWD', GetWorkingDir())
    # It's EXPORTED, even if it's not set.  bash and dash both do this:
    #     env -i -- dash -c env
    mem.SetNamed(location.LName('PWD'),
                 None,
                 scope_e.GlobalOnly,
                 flags=state.SetExport)

    # Set a MUTABLE GLOBAL that's SEPARATE from $PWD.  It's used by the 'pwd'
    # builtin, and it can't be modified by users.
    val = mem.GetValue('PWD')
    assert val.tag() == value_e.Str, val
    pwd = cast(value.Str, val).s
    mem.SetPwd(pwd)


def InitBuiltins(mem, version_str):
    # type: (state.Mem, str) -> None
    """Initialize memory with shell defaults.

    Other interpreters could have different builtin variables.
    """
    # TODO: REMOVE this legacy.  ble.sh checks it!
    mem.builtins['OIL_VERSION'] = value.Str(version_str)

    mem.builtins['OILS_VERSION'] = value.Str(version_str)

    # The source builtin understands '///' to mean "relative to embedded stdlib"
    mem.builtins['LIB_OSH'] = value.Str('///osh')
    mem.builtins['LIB_YSH'] = value.Str('///ysh')

    # - C spells it NAN
    # - JavaScript spells it NaN
    # - Python 2 has float('nan'), while Python 3 has math.nan.
    #
    # - libc prints the strings 'nan' and 'inf'
    # - Python 3 prints the strings 'nan' and 'inf'
    # - JavaScript prints 'NaN' and 'Infinity', which is more stylized
    mem.builtins['NAN'] = value.Float(pyutil.nan())
    mem.builtins['INFINITY'] = value.Float(pyutil.infinity())


def InitInteractive(mem, lang):
    # type: (state.Mem, str) -> None
    """Initialization that's only done in the interactive/headless shell."""

    ps1_str = state.GetStringFromEnv(mem, 'PS1')
    if ps1_str is None:
        state.SetStringInEnv(mem, 'PS1', r'\s-\v\$ ')
    else:
        if lang == 'ysh':
            state.SetStringInEnv(mem, 'PS1', 'ysh ' + ps1_str)

    # Old logic:
    if 0:
        # PS1 is set, and it's YSH, then prepend 'ysh' to it to eliminate confusion
        ps1_val = mem.GetValue('PS1')
        with tagswitch(ps1_val) as case:
            if case(value_e.Undef):
                # Same default PS1 as bash
                state.SetGlobalString(mem, 'PS1', r'\s-\v\$ ')

            elif case(value_e.Str):
                # Hack so we don't confuse osh and ysh, but we still respect the
                # PS1.

                # The user can disable this with
                #
                # func renderPrompt() {
                #   return ("${PS1@P}")
                # }
                if lang == 'ysh':
                    user_setting = cast(value.Str, ps1_val).s
                    state.SetGlobalString(mem, 'PS1', 'ysh ' + user_setting)
