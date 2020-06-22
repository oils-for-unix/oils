#!/usr/bin/env python2
"""
flag_def.py
"""
from __future__ import print_function

from frontend import args
from frontend.flag_spec import FlagSpec, FlagSpecAndMore, _FlagSpecAndMore
from frontend import option_def

#
# Definitions for builtin_assign
#

EXPORT_SPEC = FlagSpec('export_', typed=True)
EXPORT_SPEC.ShortFlag('-n')
EXPORT_SPEC.ShortFlag('-f')  # stubbed
EXPORT_SPEC.ShortFlag('-p')


READONLY_SPEC = FlagSpec('readonly', typed=True)

# TODO: Check the consistency of -a and -A against values, here and below.
READONLY_SPEC.ShortFlag('-a')
READONLY_SPEC.ShortFlag('-A')
READONLY_SPEC.ShortFlag('-p')


NEW_VAR_SPEC = FlagSpec('new_var', typed=True)

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


UNSET_SPEC = FlagSpec('unset', typed=True)
UNSET_SPEC.ShortFlag('-v')
UNSET_SPEC.ShortFlag('-f')
#UNSET_SPEC.ShortFlag('-z', args.String)

#
# Definitions for builtin_meta
#

# Unused because there are no flags!  Just --.
EVAL_SPEC = FlagSpec('eval', typed=True)
EVAL_SPEC = FlagSpec('source', typed=True)

COMMAND_SPEC = FlagSpec('command', typed=True)
COMMAND_SPEC.ShortFlag('-v')
# COMMAND_SPEC.ShortFlag('-V')  # Another verbose mode.

TYPE_SPEC = FlagSpec('type', typed=True)
TYPE_SPEC.ShortFlag('-f')
TYPE_SPEC.ShortFlag('-t')
TYPE_SPEC.ShortFlag('-p')
TYPE_SPEC.ShortFlag('-P')


#
# Definitions for builtin_pure
#

ALIAS_SPEC = FlagSpec('alias', typed=True)  # no flags yet
UNALIAS_SPEC = FlagSpec('unalias', typed=True)  # no flags yet

SHOPT_SPEC = FlagSpec('shopt', typed=True)
SHOPT_SPEC.ShortFlag('-s')  # set
SHOPT_SPEC.ShortFlag('-u')  # unset
SHOPT_SPEC.ShortFlag('-o')  # use 'set -o' names
SHOPT_SPEC.ShortFlag('-p')  # print
SHOPT_SPEC.ShortFlag('-q')  # query option settings


HASH_SPEC = FlagSpec('hash', typed=True)
HASH_SPEC.ShortFlag('-r')


ECHO_SPEC = FlagSpec('echo', typed=True)
ECHO_SPEC.ShortFlag('-e')  # no backslash escapes
ECHO_SPEC.ShortFlag('-n')

#
# osh/builtin_printf.py
#


PRINTF_SPEC = FlagSpec('printf', typed=True)
PRINTF_SPEC.ShortFlag('-v', args.String)

#
# osh/builtin_misc.py
#

READ_SPEC = FlagSpec('read', typed=True)
READ_SPEC.ShortFlag('-r')
READ_SPEC.ShortFlag('-n', args.Int)
READ_SPEC.ShortFlag('-a', args.String)  # name of array to read into
READ_SPEC.ShortFlag('-d', args.String)


MAPFILE_SPEC = FlagSpec('mapfile', typed=True)


CD_SPEC = FlagSpec('cd', typed=True)
CD_SPEC.ShortFlag('-L')
CD_SPEC.ShortFlag('-P')


DIRS_SPEC = FlagSpec('dirs', typed=True)
DIRS_SPEC.ShortFlag('-c')
DIRS_SPEC.ShortFlag('-l')
DIRS_SPEC.ShortFlag('-p')
DIRS_SPEC.ShortFlag('-v')


PWD_SPEC = FlagSpec('pwd', typed=True)
PWD_SPEC.ShortFlag('-L')
PWD_SPEC.ShortFlag('-P')


HELP_SPEC = FlagSpec('help', typed=True)
# Use Oil flags?  -index?
#HELP_SPEC.ShortFlag('-i')  # show index
# Note: bash has help -d -m -s, which change the formatting


HISTORY_SPEC = FlagSpec('history', typed=True)
HISTORY_SPEC.ShortFlag('-c')
HISTORY_SPEC.ShortFlag('-d', args.Int)

#
# osh/builtin_process.py
#

WAIT_SPEC = FlagSpec('wait', typed=True)
WAIT_SPEC.ShortFlag('-n')


TRAP_SPEC = FlagSpec('trap', typed=True)
TRAP_SPEC.ShortFlag('-p')
TRAP_SPEC.ShortFlag('-l')

#
# FlagSpecAndMore
#

#
# set and shopt
#

def _AddShellOptions(spec):
  # type: (_FlagSpecAndMore) -> None
  """Shared between 'set' builtin and the shell's own arg parser."""
  for opt in option_def.All():
    if opt.builtin == 'set':
      spec.Option(opt.short_flag, opt.name)
    elif opt.builtin == 'shopt':
      # unimplemented options are accepted in bin/osh and in shopt -s foo
      spec.ShoptOption(opt.name)
    else:
      # 'interactive' Has a cell for internal use, but isn't allowed to be
      # modified.
      pass

  # Add strict:all, etc.
  for name in option_def.META_OPTIONS:
    spec.ShoptOption(name)


OSH_SPEC = FlagSpecAndMore('main', typed=True)

OSH_SPEC.ShortFlag('-c', args.String, quit_parsing_flags=True)  # command string
OSH_SPEC.LongFlag('--help')
OSH_SPEC.LongFlag('--version')

OSH_SPEC.ShortFlag('-i')  # interactive

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

# For benchmarks/*.sh
OSH_SPEC.LongFlag('--parser-mem-dump', args.String)
OSH_SPEC.LongFlag('--runtime-mem-dump', args.String)

# This flag has is named like bash's equivalent.  We got rid of --norc because
# it can simply by --rcfile /dev/null.
OSH_SPEC.LongFlag('--rcfile', args.String)

_AddShellOptions(OSH_SPEC)


SET_SPEC = FlagSpecAndMore('set')
_AddShellOptions(SET_SPEC)
