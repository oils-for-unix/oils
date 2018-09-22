#!/usr/bin/python
"""
comp_builtins.py - Completion builtins
"""

import os

from core import args
from core import completion
from core import util

log = util.log


def _DefineOptions(spec):
  """Common -o options for complete and compgen."""

  # bashdefault, default, filenames, nospace are used in git
  spec.Option(None, 'bashdefault',
      help='If nothing matches, perform default bash completions')
  spec.Option(None, 'default',
      help="If nothing matches, use readline's default filename completion")
  spec.Option(None, 'filenames',
      help="The completion function generates filenames and should be "
           "post-processed")
  spec.Option(None, 'nospace',
      help="Don't append a space to words completed at the end of the line")

def _DefineActions(spec):
  """Common -A actions for complete and compgen."""

  # NOTE: git-completion.bash uses -f and -v. 
  # My ~/.bashrc on Ubuntu uses -d, -u, -j, -v, -a, -c, -b
  spec.InitActions()
  spec.Action(None, 'function')
  spec.Action('a', 'alias')
  spec.Action('b', 'binding')
  spec.Action('c', 'command')
  spec.Action('d', 'directory')
  spec.Action('f', 'file')
  spec.Action('j', 'job')
  spec.Action('u', 'user')
  spec.Action('v', 'variable')
  spec.Action(None, 'helptopic')  # help
  spec.Action(None, 'setopt')  # set -o
  spec.Action(None, 'shopt')  # shopt -s
  spec.Action(None, 'signal')  # kill -s


# git-completion.sh uses complete -o and complete -F
COMPLETE_SPEC = args.FlagsAndOptions()

_DefineOptions(COMPLETE_SPEC)
_DefineActions(COMPLETE_SPEC)

COMPLETE_SPEC.ShortFlag('-E',
    help='Define the compspec for an empty line')
COMPLETE_SPEC.ShortFlag('-D',
    help='Define the compspec that applies when nothing else matches')
COMPLETE_SPEC.ShortFlag('-F', args.Str, help='Complete with this function')


def Complete(argv, ex, funcs, comp_lookup):
  """complete builtin - register a completion function.

  NOTE: It's a member of Executor because it creates a ShellFuncAction, which
  needs an Executor.
  """
  arg_r = args.Reader(argv)
  arg = COMPLETE_SPEC.Parse(arg_r)
  # TODO: process arg.opt_changes
  #log('arg %s', arg)

  commands = arg_r.Rest()
  if not commands:
    raise args.UsageError('missing required commands')

  for command in commands:
    # NOTE: bash doesn't actually check the name until completion time, but
    # obviously it's better to check here.
    if arg.F:
      func_name = arg.F
      func = funcs.get(func_name)
      if func is None:
        print('Function %r not found' % func_name)
        return 1

      chain = completion.ShellFuncAction(ex, func)
      comp_lookup.RegisterName(command, chain)

      # TODO: Some feedback would be nice?
      # Should we show an error like this?  Or maybe a warning?  Maybe
      # comp_lookup has readline_mod?
      # util.error('Oil was not built with readline/completion.')
    else:
      pass

    return 0


COMPGEN_SPEC = args.FlagsAndOptions()  # for -o and -A

_DefineOptions(COMPGEN_SPEC)
_DefineActions(COMPGEN_SPEC)


def CompGen(argv, funcs, mem):
  """Print completions on stdout."""

  arg_r = args.Reader(argv)
  arg = COMPGEN_SPEC.Parse(arg_r)
  status = 0

  if arg_r.AtEnd():
    prefix = ''
  else:
    prefix = arg_r.Peek()
    arg_r.Next()
    if not arg_r.AtEnd():
      raise args.UsageError('Extra arguments')

  matched = False

  if 'function' in arg.actions:
    for func_name in sorted(funcs):
      if func_name.startswith(prefix):
        print(func_name)
        matched = True

  # Useful command to see what bash has:
  # env -i -- bash --norc --noprofile -c 'compgen -v'
  if 'variable' in arg.actions:
    for var_name in mem.VarsWithPrefix(prefix):
      print(var_name)
      matched = True

  if 'file' in arg.actions:
    # git uses compgen -f, which is the same as compgen -A file
    # TODO: listing '.' could be a capability?
    for filename in os.listdir('.'):
      if filename.startswith(prefix):
        print(filename)
        matched = True

  if not arg.actions:
    util.warn('*** command without -A not implemented ***')
    return 1

  return 0 if matched else 1


COMPOPT_SPEC = args.FlagsAndOptions()  # for -o
_DefineOptions(COMPOPT_SPEC)


def CompOpt(argv):
  arg_r = args.Reader(argv)
  arg = COMPOPT_SPEC.Parse(arg_r)

  # NOTE: This is supposed to fail if a completion isn't being generated?
  # The executor should have a mode?


  log('arg %s', arg)
  return 0

