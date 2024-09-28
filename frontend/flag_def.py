#!/usr/bin/env python2
"""Flag parser defintions."""

from __future__ import print_function

from frontend import args
from frontend.flag_spec import (FlagSpec, FlagSpecAndMore, _FlagSpecAndMore)
from frontend import option_def

#
# Definitions for builtin_assign
#

EXPORT_SPEC = FlagSpec('export_')
EXPORT_SPEC.ShortFlag('-n')
EXPORT_SPEC.ShortFlag('-f')  # stubbed
EXPORT_SPEC.ShortFlag('-p')

READONLY_SPEC = FlagSpec('readonly')

# TODO: Check the consistency of -a and -A against values, here and below.
READONLY_SPEC.ShortFlag('-a')
READONLY_SPEC.ShortFlag('-A')
READONLY_SPEC.ShortFlag('-p')

NEW_VAR_SPEC = FlagSpec('new_var')

# print stuff
NEW_VAR_SPEC.ShortFlag('-f')
NEW_VAR_SPEC.ShortFlag('-F')
NEW_VAR_SPEC.ShortFlag('-p')

NEW_VAR_SPEC.ShortFlag('-g')  # Look up in global scope

# Options +r +x +n
NEW_VAR_SPEC.PlusFlag('x')  # export
NEW_VAR_SPEC.PlusFlag('r')  # readonly
NEW_VAR_SPEC.PlusFlag('n')  # named ref

# Common between readonly/declare
NEW_VAR_SPEC.ShortFlag('-a')
NEW_VAR_SPEC.ShortFlag('-A')
NEW_VAR_SPEC.ShortFlag('-i')  # no-op for integers
NEW_VAR_SPEC.ShortFlag('-u')  # no-op for case
NEW_VAR_SPEC.ShortFlag('-l')  # no-op for case

UNSET_SPEC = FlagSpec('unset')
UNSET_SPEC.ShortFlag('-v')
UNSET_SPEC.ShortFlag('-f')
#UNSET_SPEC.ShortFlag('-z', args.String)

#
# Definitions for builtin_meta
#

# Unused because there are no flags!  Just --.
EVAL_SPEC = FlagSpec('eval')
SOURCE_SPEC = FlagSpec('source')
SOURCE_SPEC.LongFlag('--builtin')

COMMAND_SPEC = FlagSpec('command')
COMMAND_SPEC.ShortFlag('-v')
COMMAND_SPEC.ShortFlag('-V')
COMMAND_SPEC.ShortFlag('-p')

TYPE_SPEC = FlagSpec('type')
TYPE_SPEC.ShortFlag('-f')
TYPE_SPEC.ShortFlag('-t')
TYPE_SPEC.ShortFlag('-p')
TYPE_SPEC.ShortFlag('-P')
TYPE_SPEC.ShortFlag('-a')

#
# Definitions for builtin_pure
#

ALIAS_SPEC = FlagSpec('alias')  # no flags yet
UNALIAS_SPEC = FlagSpec('unalias')  # no flags yet
UNALIAS_SPEC.ShortFlag('-a')

SHOPT_SPEC = FlagSpec('shopt')
SHOPT_SPEC.ShortFlag('-s', long_name='--set')
SHOPT_SPEC.ShortFlag('-u', long_name='--unset')
SHOPT_SPEC.ShortFlag('-o')  # use 'set -o' names
# TODO: --print could print in a verbose format.  (Annoying: codegen conflicts
# with Python keyword.)
SHOPT_SPEC.ShortFlag('-p')
SHOPT_SPEC.ShortFlag('-q')  # query option settings

HASH_SPEC = FlagSpec('hash')
HASH_SPEC.ShortFlag('-r')

ECHO_SPEC = FlagSpec('echo')
ECHO_SPEC.ShortFlag('-e')  # no backslash escapes
ECHO_SPEC.ShortFlag('-n')

#
# osh/builtin_printf.py
#

PRINTF_SPEC = FlagSpec('printf')
PRINTF_SPEC.ShortFlag('-v', args.String)

#
# osh/builtin_misc.py
#

READ_SPEC = FlagSpec('read')
READ_SPEC.ShortFlag('-r')
READ_SPEC.ShortFlag('-s')  # silent
READ_SPEC.ShortFlag('-u', args.Int)  # file descriptor
READ_SPEC.ShortFlag('-t', args.Float)  # timeout
READ_SPEC.ShortFlag('-n', args.Int)
READ_SPEC.ShortFlag('-N', args.Int)
READ_SPEC.ShortFlag('-a', args.String)  # name of array to read into
READ_SPEC.ShortFlag('-d', args.String)
READ_SPEC.ShortFlag('-p', args.String)  # prompt

# OSH extension (not really considered YSH!)
READ_SPEC.ShortFlag('-0')  # until NUL, like IFS= read -r -d ''
# Arguably it could be named like
#   grep --null -Z
#   xargs --null -0
# But this format is NOT recommended in YSH!  It's unbuffered and slow.  We
# prefer lines with escaping.

READ_SPEC.LongFlag('--all')
READ_SPEC.LongFlag('--raw-line')
READ_SPEC.LongFlag('--num-bytes', args.Int)
# don't strip the trailing newline
READ_SPEC.LongFlag('--with-eol')

MAPFILE_SPEC = FlagSpec('mapfile')
MAPFILE_SPEC.ShortFlag('-t')

CD_SPEC = FlagSpec('cd')
CD_SPEC.ShortFlag('-L')
CD_SPEC.ShortFlag('-P')

PUSHD_SPEC = FlagSpec('pushd')

POPD_SPEC = FlagSpec('popd')

DIRS_SPEC = FlagSpec('dirs')
DIRS_SPEC.ShortFlag('-c')
DIRS_SPEC.ShortFlag('-l')
DIRS_SPEC.ShortFlag('-p')
DIRS_SPEC.ShortFlag('-v')

PWD_SPEC = FlagSpec('pwd')
PWD_SPEC.ShortFlag('-L')
PWD_SPEC.ShortFlag('-P')

HELP_SPEC = FlagSpec('help')
#HELP_SPEC.ShortFlag('-i')  # show index
# Note: bash has help -d -m -s, which change the formatting

HISTORY_SPEC = FlagSpec('history')
HISTORY_SPEC.ShortFlag('-a')
HISTORY_SPEC.ShortFlag('-r')
HISTORY_SPEC.ShortFlag('-c')
HISTORY_SPEC.ShortFlag('-d', args.Int)

#
# osh/builtin_process.py
#

EXEC_SPEC = FlagSpec('exec')

WAIT_SPEC = FlagSpec('wait')
WAIT_SPEC.ShortFlag('-n')

TRAP_SPEC = FlagSpec('trap')
TRAP_SPEC.ShortFlag('-p')
TRAP_SPEC.ShortFlag('-l')

JOB_SPEC = FlagSpec('jobs')
JOB_SPEC.ShortFlag('-l', help='long format')
JOB_SPEC.ShortFlag('-p', help='prints PID only')
JOB_SPEC.LongFlag('--debug', help='display debug info')

ULIMIT_SPEC = FlagSpec('ulimit')

ULIMIT_SPEC.ShortFlag('-a', help='Print all limits')
ULIMIT_SPEC.LongFlag('--all', help='Alias for -a')
ULIMIT_SPEC.ShortFlag('-H', help='Use hard limit')
ULIMIT_SPEC.ShortFlag('-S', help='Use soft limit')

_ULIMIT_RESOURCES = [
    '-c',
    '-d',
    '-f',
    '-n',
    '-s',
    '-t',
    '-v',
]

for u_flag in _ULIMIT_RESOURCES:
    ULIMIT_SPEC.ShortFlag(u_flag)

#
# FlagSpecAndMore
#

#
# set and shopt
#


def _AddShellOptions(spec):
    # type: (_FlagSpecAndMore) -> None
    """Shared between 'set' builtin and the shell's own arg parser."""
    spec.InitOptions()
    spec.InitShopt()

    for opt in option_def.All():
        if opt.builtin == 'set':
            spec.Option(opt.short_flag, opt.name)
        # Notes:
        # - shopt option don't need to be registered; we validate elsewhere
        # - 'interactive' Has a cell for internal use, but isn't allowed to be
        # modified.


MAIN_SPEC = FlagSpecAndMore('main')

MAIN_SPEC.ShortFlag('-c', args.String,
                    quit_parsing_flags=True)  # command string
MAIN_SPEC.LongFlag('--help')
MAIN_SPEC.LongFlag('--version')

# --tool ysh-ify, etc.
# default is ''
#
# More ideas for tools
#   undefined-vars - a static analysis pass
#   parse-glob - to debug parsing
#   parse-printf
MAIN_SPEC.LongFlag('--tool', [
    'tokens', 'lossless-cat', 'syntax-tree', 'fmt', 'test', 'ysh-ify', 'deps',
    'cat-em'
])

MAIN_SPEC.ShortFlag('-i')  # interactive
MAIN_SPEC.ShortFlag('-l')  # login - currently no-op
MAIN_SPEC.LongFlag('--login')  # login - currently no-op
MAIN_SPEC.LongFlag('--headless')  # accepts ECMD, etc.

# TODO: -h too
# the output format when passing -n
MAIN_SPEC.LongFlag(
    '--ast-format',
    ['text', 'abbrev-text', 'html', 'abbrev-html', 'oheap', 'none'],
    default='abbrev-text')

# Defines completion style.
MAIN_SPEC.LongFlag('--completion-display', ['minimal', 'nice'], default='nice')
# TODO: Add option for YSH prompt style?  RHS prompt?

MAIN_SPEC.LongFlag('--completion-demo')

# Debugging feature only.  $SH -n won't reparse a[x+1] and ``.  Note that $SH
# --tool automatically turns it on.
MAIN_SPEC.LongFlag('--do-lossless')

MAIN_SPEC.LongFlag('--print-status')  # TODO: Replace with a shell hook
MAIN_SPEC.LongFlag('--debug-file', args.String)
MAIN_SPEC.LongFlag('--xtrace-to-debug-file')

# This flag has is named like bash's equivalent.  We got rid of --norc because
# it can simply by --rcfile /dev/null.
MAIN_SPEC.LongFlag('--rcfile', args.String)
MAIN_SPEC.LongFlag('--rcdir', args.String)
MAIN_SPEC.LongFlag('--norc')

# e.g. to pass data on stdin but pretend that it came from a .hay file
MAIN_SPEC.LongFlag('--location-str', args.String)
MAIN_SPEC.LongFlag('--location-start-line', args.Int)

_AddShellOptions(MAIN_SPEC)

SET_SPEC = FlagSpecAndMore('set')
_AddShellOptions(SET_SPEC)

#
# Types for completion
#


def _DefineCompletionFlags(spec):
    # type: (_FlagSpecAndMore) -> None
    spec.ShortFlag('-F', args.String, help='Complete with this function')
    spec.ShortFlag('-W', args.String, help='Complete with these words')
    spec.ShortFlag('-C',
                   args.String,
                   help='Complete with stdout lines of this command')

    spec.ShortFlag(
        '-P',
        args.String,
        help=
        'Prefix is added at the beginning of each possible completion after '
        'all other options have been applied.')
    spec.ShortFlag('-S',
                   args.String,
                   help='Suffix is appended to each possible completion after '
                   'all other options have been applied.')
    spec.ShortFlag('-X',
                   args.String,
                   help='''
A glob pattern to further filter the matches.  It is applied to the list of
possible completions generated by the preceding options and arguments, and each
completion matching filterpat is removed from the list. A leading ! in
filterpat negates the pattern; in this case, any completion not matching
filterpat is removed.
''')


def _DefineCompletionOptions(spec):
    # type: (_FlagSpecAndMore) -> None
    """Common -o options for complete and compgen."""
    spec.InitOptions()

    # bashdefault, default, filenames, nospace are used in git
    spec.Option2('bashdefault',
                 help='If nothing matches, perform default bash completions')
    spec.Option2(
        'default',
        help="If nothing matches, use readline's default filename completion")
    spec.Option2(
        'filenames',
        help="The completion function generates filenames and should be "
        "post-processed")
    spec.Option2('dirnames',
                 help="If nothing matches, perform directory name completion")
    spec.Option2(
        'nospace',
        help="Don't append a space to words completed at the end of the line")
    spec.Option2(
        'plusdirs',
        help="After processing the compspec, attempt directory name completion "
        "and return those matches.")


def _DefineCompletionActions(spec):
    # type: (_FlagSpecAndMore) -> None
    """Common -A actions for complete and compgen."""

    # NOTE: git-completion.bash uses -f and -v.
    # My ~/.bashrc on Ubuntu uses -d, -u, -j, -v, -a, -c, -b
    spec.InitActions()
    spec.Action('a', 'alias')
    spec.Action('b', 'binding')
    spec.Action('c', 'command')
    spec.Action('d', 'directory')
    spec.Action('e', 'export')
    spec.Action('f', 'file')
    spec.Action('k', 'keyword')
    spec.Action('j', 'job')
    spec.Action('u', 'user')
    spec.Action('v', 'variable')
    spec.Action(None, 'builtin')
    spec.Action(None, 'function')
    spec.Action(None, 'helptopic')  # help
    spec.Action(None, 'setopt')  # set -o
    spec.Action(None, 'shopt')  # shopt -s
    spec.Action(None, 'signal')  # kill -s
    spec.Action(None, 'stopped')


COMPLETE_SPEC = FlagSpecAndMore('complete')

_DefineCompletionFlags(COMPLETE_SPEC)
_DefineCompletionOptions(COMPLETE_SPEC)
_DefineCompletionActions(COMPLETE_SPEC)

COMPLETE_SPEC.ShortFlag('-E', help='Define the compspec for an empty line')
COMPLETE_SPEC.ShortFlag(
    '-D', help='Define the compspec that applies when nothing else matches')

# I would like this to be less compatible
# Field name conflicts with 'print' keyword
#COMPLETE_SPEC.LongFlag(
#    '--print', help='Print spec')

COMPGEN_SPEC = FlagSpecAndMore('compgen')  # for -o and -A

# TODO: Add -l for COMP_LINE.  -p for COMP_POINT ?
_DefineCompletionFlags(COMPGEN_SPEC)
_DefineCompletionOptions(COMPGEN_SPEC)
_DefineCompletionActions(COMPGEN_SPEC)

COMPOPT_SPEC = FlagSpecAndMore('compopt')  # for -o
_DefineCompletionOptions(COMPOPT_SPEC)

COMPADJUST_SPEC = FlagSpecAndMore('compadjust')

COMPADJUST_SPEC.ShortFlag(
    '-n',
    args.String,
    help=
    'Do NOT split by these characters.  It omits them from COMP_WORDBREAKS.')
COMPADJUST_SPEC.ShortFlag('-s',
                          help='Treat --foo=bar and --foo bar the same way.')

COMPEXPORT_SPEC = FlagSpecAndMore('compexport')

COMPEXPORT_SPEC.ShortFlag('-c',
                          args.String,
                          help='Shell string to complete, like sh -c')

COMPEXPORT_SPEC.LongFlag('--begin',
                         args.Int,
                         help='Simulate readline begin index into line buffer')

COMPEXPORT_SPEC.LongFlag('--end',
                         args.Int,
                         help='Simulate readline end index into line buffer')

# jlines is an array of strings with NO header line
# TSV8 has a header line.  It can have flag descriptions and other data.
COMPEXPORT_SPEC.LongFlag('--format', ['jlines', 'tsv8'],
                         default='jlines',
                         help='Output format')

#
# Pure YSH
#

TRY_SPEC = FlagSpec('try_')
TRY_SPEC.LongFlag('--assign',
                  args.String,
                  help='Assign status to this variable, and return 0')

ERROR_SPEC = FlagSpec('error')
FAILED_SPEC = FlagSpec('failed')

BOOLSTATUS_SPEC = FlagSpec('boolstatus')
ASSERT_SPEC = FlagSpec('assert')

# Future directions:
# run --builtin, run --command, run --proc:
#   to "replace" 'builtin' and # 'command'

APPEND_SPEC = FlagSpec('append')

SHVAR_SPEC = FlagSpec('shvar')
#SHVAR_SPEC.Flag('-temp', args.String,
#    help='Push a NAME=val binding')
#SHVAR_SPEC.Flag('-env', args.String,
#    help='Push a NAME=val binding and set the -x flag')

CTX_SPEC = FlagSpec('ctx')

PP_SPEC = FlagSpec('pp')

SHVM_SPEC = FlagSpec('shvm')

# --verbose?
FORK_SPEC = FlagSpec('fork')
FORKWAIT_SPEC = FlagSpec('forkwait')

# Might want --list at some point
MODULE_SPEC = FlagSpec('source-guard')

RUNPROC_SPEC = FlagSpec('runproc')
RUNPROC_SPEC.ShortFlag('-h', args.Bool, help='Show all procs')

INVOKE_SPEC = FlagSpec('invoke')

# 3 coarse-grained categories.
INVOKE_SPEC.LongFlag('--builtin')    # like 'builtin', which includs special builtins
INVOKE_SPEC.LongFlag('--proc-like')  # like 'runproc' - proc, sh func, or invokable obj
INVOKE_SPEC.LongFlag('--extern')     # like 'extern' builtin

EXTERN_SPEC = FlagSpec('extern')

WRITE_SPEC = FlagSpec('write')
WRITE_SPEC.LongFlag('--sep',
                    args.String,
                    default='\n',
                    help='Characters to separate each argument')
WRITE_SPEC.LongFlag('--end',
                    args.String,
                    default='\n',
                    help='Characters to terminate the whole invocation')
WRITE_SPEC.ShortFlag('-n',
                     args.Bool,
                     help="Omit newline (synonym for -end '')")
# Do we need these two?
WRITE_SPEC.LongFlag('--json',
                    args.Bool,
                    default=False,
                    help='Write elements as JSON strings(lossy)')
WRITE_SPEC.LongFlag('--j8',
                    args.Bool,
                    default=False,
                    help='Write elements as J8 strings')
# TODO: --jlines for conditional j"" prefix?  Like maybe_shell_encode()

# Legacy that's not really needed with J8 notation.  The = operator might use a
# separate pretty printer that shows \u{3bc}
#
#   x means I want \x00
#   u means I want \u{1234}
#   raw is utf-8
if 0:
    WRITE_SPEC.LongFlag(
        '--unicode', ['raw', 'u', 'x'],
        default='raw',
        help='Encode QSN with these options.  '
        'x assumes an opaque byte string, while raw and u try to '
        'decode UTF-8.')

PUSH_REGISTERS_SPEC = FlagSpec('push-registers')

FOPEN_SPEC = FlagSpec('redir')

#
# JSON
#

JSON_WRITE_SPEC = FlagSpec('json_write')

# TODO: --compact is probably better
# --pretty=F is like JSON.stringify(d, null, 0)
JSON_WRITE_SPEC.LongFlag('--pretty',
                         args.Bool,
                         default=True,
                         help='Whitespace in output (default true)')

# Unused:
# JSON has the questionable decision of allowing (unpaired) surrogate like
# \udc00.
# When encoding, we try to catch the error on OUR side, rather than letting it
# travel over the wire.  But you can disable this.
JSON_WRITE_SPEC.LongFlag(
    '--surrogate-ok',
    args.Bool,
    default=False,
    help='Invalid UTF-8 can be encoded as surrogate like \\udc00')

JSON_WRITE_SPEC.LongFlag('--indent',
                         args.Int,
                         default=2,
                         help='Indent JSON by this amount')

JSON_READ_SPEC = FlagSpec('json_read')
