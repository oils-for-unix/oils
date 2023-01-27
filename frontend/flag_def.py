#!/usr/bin/env python2
"""
flag_def.py
"""
from __future__ import print_function

from frontend import args
from frontend.flag_spec import (
    FlagSpec, FlagSpecAndMore, _FlagSpecAndMore
)
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


UNSET_SPEC = FlagSpec('unset')
UNSET_SPEC.ShortFlag('-v')
UNSET_SPEC.ShortFlag('-f')
#UNSET_SPEC.ShortFlag('-z', args.String)

#
# Definitions for builtin_meta
#

# Unused because there are no flags!  Just --.
EVAL_SPEC = FlagSpec('eval')
EVAL_SPEC = FlagSpec('source')

COMMAND_SPEC = FlagSpec('command')
COMMAND_SPEC.ShortFlag('-v')
# COMMAND_SPEC.ShortFlag('-V')  # Another verbose mode.

TYPE_SPEC = FlagSpec('type')
TYPE_SPEC.ShortFlag('-f')
TYPE_SPEC.ShortFlag('-t')
TYPE_SPEC.ShortFlag('-p')
TYPE_SPEC.ShortFlag('-P')


#
# Definitions for builtin_pure
#

ALIAS_SPEC = FlagSpec('alias')  # no flags yet
UNALIAS_SPEC = FlagSpec('unalias')  # no flags yet

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
READ_SPEC.ShortFlag('-a', args.String)  # name of array to read into
READ_SPEC.ShortFlag('-d', args.String)
READ_SPEC.ShortFlag('-p', args.String)  # prompt

# Oil extensions
READ_SPEC.ShortFlag('-0')  # until NUL, like -r -d ''
READ_SPEC.LongFlag('--all')
READ_SPEC.LongFlag('--line')
# don't strip the trailing newline
READ_SPEC.LongFlag('--with-eol')
# Decode QSN after reading a line.  Note: A QSN string can't have literal
# newlines or tabs; they must be escaped.
READ_SPEC.ShortFlag('-q', long_name='--qsn')


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
# Use Oil flags?  -index?
#HELP_SPEC.ShortFlag('-i')  # show index
# Note: bash has help -d -m -s, which change the formatting


HISTORY_SPEC = FlagSpec('history')
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


OSH_SPEC = FlagSpecAndMore('main', typed=True)

OSH_SPEC.ShortFlag('-c', args.String, quit_parsing_flags=True)  # command string
OSH_SPEC.LongFlag('--help')
OSH_SPEC.LongFlag('--version')

OSH_SPEC.ShortFlag('-i')  # interactive
OSH_SPEC.ShortFlag('-l')  # login - currently no-op
OSH_SPEC.LongFlag('--login')  # login - currently no-op
OSH_SPEC.LongFlag('--headless')  # accepts ECMD, etc.

# TODO: -h too
# the output format when passing -n
OSH_SPEC.LongFlag('--ast-format',
    ['text', 'abbrev-text', 'html', 'abbrev-html', 'oheap', 'none'],
    default='abbrev-text')

# Defines completion style.
OSH_SPEC.LongFlag('--completion-display', ['minimal', 'nice'], default='nice')
# TODO: Add option for Oil prompt style?  RHS prompt?

# Don't reparse a[x+1] and ``.  Only valid in -n mode.
OSH_SPEC.LongFlag('--one-pass-parse')

OSH_SPEC.LongFlag('--print-status')  # TODO: Replace with a shell hook
OSH_SPEC.LongFlag('--debug-file', args.String)
OSH_SPEC.LongFlag('--xtrace-to-debug-file')

# This flag has is named like bash's equivalent.  We got rid of --norc because
# it can simply by --rcfile /dev/null.
OSH_SPEC.LongFlag('--rcfile', args.String)

# e.g. to pass data on stdin but pretend that it came from a .hay file
OSH_SPEC.LongFlag('--location-str', args.String)
OSH_SPEC.LongFlag('--location-start-line', args.Int)

_AddShellOptions(OSH_SPEC)


SET_SPEC = FlagSpecAndMore('set', typed=True)
_AddShellOptions(SET_SPEC)


#
# Types for completion
#

def _DefineCompletionFlags(spec):
  # type: (_FlagSpecAndMore) -> None
  spec.ShortFlag('-F', args.String, help='Complete with this function')
  spec.ShortFlag('-W', args.String, help='Complete with these words')
  spec.ShortFlag('-P', args.String,
      help='Prefix is added at the beginning of each possible completion after '
           'all other options have been applied.')
  spec.ShortFlag('-S', args.String,
      help='Suffix is appended to each possible completion after '
           'all other options have been applied.')
  spec.ShortFlag('-X', args.String,
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
  spec.Option2('default',
      help="If nothing matches, use readline's default filename completion")
  spec.Option2('filenames',
      help="The completion function generates filenames and should be "
           "post-processed")
  spec.Option2('dirnames',
      help="If nothing matches, perform directory name completion")
  spec.Option2('nospace',
      help="Don't append a space to words completed at the end of the line")
  spec.Option2('plusdirs',
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
  spec.Action('f', 'file')
  spec.Action('j', 'job')
  spec.Action('u', 'user')
  spec.Action('v', 'variable')
  spec.Action(None, 'function')
  spec.Action(None, 'helptopic')  # help
  spec.Action(None, 'setopt')  # set -o
  spec.Action(None, 'shopt')  # shopt -s
  spec.Action(None, 'signal')  # kill -s
  spec.Action(None, 'stopped')


COMPLETE_SPEC = FlagSpecAndMore('complete', typed=True)

_DefineCompletionFlags(COMPLETE_SPEC)
_DefineCompletionOptions(COMPLETE_SPEC)
_DefineCompletionActions(COMPLETE_SPEC)

COMPLETE_SPEC.ShortFlag('-E',
    help='Define the compspec for an empty line')
COMPLETE_SPEC.ShortFlag('-D',
    help='Define the compspec that applies when nothing else matches')

COMPGEN_SPEC = FlagSpecAndMore('compgen', typed=True)  # for -o and -A

# TODO: Add -l for COMP_LINE.  -p for COMP_POINT ?
_DefineCompletionFlags(COMPGEN_SPEC)
_DefineCompletionOptions(COMPGEN_SPEC)
_DefineCompletionActions(COMPGEN_SPEC)


COMPOPT_SPEC = FlagSpecAndMore('compopt', typed=True)  # for -o
_DefineCompletionOptions(COMPOPT_SPEC)


COMPADJUST_SPEC = FlagSpecAndMore('compadjust', typed=True)

COMPADJUST_SPEC.ShortFlag('-n', args.String,
    help='Do NOT split by these characters.  It omits them from COMP_WORDBREAKS.')
COMPADJUST_SPEC.ShortFlag('-s',
    help='Treat --foo=bar and --foo bar the same way.')


#
# Pure Oil
#


TRY_SPEC = FlagSpec('try_')
TRY_SPEC.LongFlag('--assign', args.String,
    help='Assign status to this variable, and return 0')

BOOLSTATUS_SPEC = FlagSpec('boolstatus')

# Future directions:
# run --builtin, run --command, run --proc:
#   to "replace" 'builtin' and # 'command'


APPEND_SPEC = FlagSpec('append')

SHVAR_SPEC = FlagSpec('shvar')
#SHVAR_SPEC.Flag('-temp', args.String,
#    help='Push a NAME=val binding')
#SHVAR_SPEC.Flag('-env', args.String,
#    help='Push a NAME=val binding and set the -x flag')

PP_SPEC = FlagSpec('pp')

# --verbose?
FORK_SPEC = FlagSpec('fork')
FORKWAIT_SPEC = FlagSpec('forkwait')

# Might want --list at some point
MODULE_SPEC = FlagSpec('module')

RUNPROC_SPEC = FlagSpec('runproc')
RUNPROC_SPEC.ShortFlag('-h', args.Bool, help='Show all procs')

WRITE_SPEC = FlagSpec('write')
WRITE_SPEC.LongFlag(
    '--sep', args.String, default='\n',
    help='Characters to separate each argument')
WRITE_SPEC.LongFlag(
    '--end', args.String, default='\n',
    help='Characters to terminate the whole invocation')
WRITE_SPEC.ShortFlag(
    '-n', args.Bool,
    help="Omit newline (synonym for -end '')")
WRITE_SPEC.LongFlag(
    '--qsn', args.Bool, default=False,
    help='Write elements in QSN format')

# x means I want \x00
# u means I want \u{1234}
# raw is utf-8
# might also want: maybe?
WRITE_SPEC.LongFlag(
    '--unicode', ['raw', 'u', 'x',], default='raw',
    help='Encode QSN with these options.  '
         'x assumes an opaque byte string, while raw and u try to '
         'decode UTF-8.')

PUSH_REGISTERS_SPEC = FlagSpec('push-registers')

FOPEN_SPEC = FlagSpec('fopen')

#
# Tea
#

TEA_MAIN_SPEC = FlagSpec('tea_main')
TEA_MAIN_SPEC.ShortFlag('-n', args.Bool)  # Parse
TEA_MAIN_SPEC.ShortFlag('-c', args.String)  # Command snippet
TEA_MAIN_SPEC.LongFlag('--translate', args.Bool)

