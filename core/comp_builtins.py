#!/usr/bin/python
"""
comp_builtins.py - Completion builtins
"""

from core import args
from core import util

log = util.log


def _DefineOptions(spec):
  spec.Option(None, 'bashdefault')  # used in git
  spec.Option(None, 'default')  # used in git
  spec.Option(None, 'filenames')  # used in git
  spec.Option(None, 'nospace')  # used in git


# git-completion.sh uses complete -o and complete -F
COMPLETE_SPEC = args.FlagsAndOptions()
COMPLETE_SPEC.ShortFlag('-F', args.Str, help='Register a completion function')
_DefineOptions(COMPLETE_SPEC)


def Complete(argv, ex, funcs, completion, comp_lookup):
  """complete builtin - register a completion function.

  NOTE: It's a member of Executor because it creates a ShellFuncAction, which
  needs an Executor.
  """
  arg, i = COMPLETE_SPEC.Parse_OLD(argv)
  # TODO: process arg.opt_changes
  log('arg %s', arg)

  command = argv[i]  # e.g. 'grep'

  # NOTE: bash doesn't actually check the name until completion time, but
  # obviously it's better to check here.
  if arg.F:
    func_name = arg.F
    func = funcs.get(func_name)
    if func is None:
      print('Function %r not found' % func_name)
      return 1

    if completion:
      chain = completion.ShellFuncAction(ex, func)
      comp_lookup.RegisterName(command, chain)
      # TODO: Some feedback would be nice?
    else:
      util.error('Oil was not built with readline/completion.')
  else:
    pass

  return 0


COMPGEN_SPEC = args.FlagsAndOptions()  # for -o and -A
COMPGEN_SPEC.InitActions()
COMPGEN_SPEC.Action(None, 'function')
COMPGEN_SPEC.Action('f', 'file')
COMPGEN_SPEC.Action('v', 'variable')
_DefineOptions(COMPGEN_SPEC)


def CompGen(argv, funcs):
  # state = args.State(argv)
  # state.Rest() -> []
  # state.AtEnd()

  arg, i = COMPGEN_SPEC.Parse_OLD(argv)
  status = 0

  if 'function' in arg.actions:
    for func_name in sorted(funcs):
      print(func_name)

  if 'file' in arg.actions:
    # bash uses compgen -f, which is the same as compgen -A file
    raise NotImplementedError

  # Useful command to see what bash has:
  # env -i -- bash --norc --noprofile -c 'compgen -v'
  if 'variable' in arg.actions:
      # bash uses compgen -v, which is the same as compgen -A variable
      raise NotImplementedError

  if not arg.actions:
    util.warn('*** command without -A not implemented ***')
    status = 1

  return status


COMPOPT_SPEC = args.FlagsAndOptions()  # for -o
_DefineOptions(COMPOPT_SPEC)


def CompOpt(argv):
  arg, i = COMPOPT_SPEC.Parse_OLD(argv)
  log('arg %s', arg)
  return 0

