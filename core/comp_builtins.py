#!/usr/bin/python
"""
comp_builtins.py - Completion builtins
"""

from core import args
from core import completion
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


def Complete(argv, ex, funcs, comp_lookup):
  """complete builtin - register a completion function.

  NOTE: It's a member of Executor because it creates a ShellFuncAction, which
  needs an Executor.
  """
  arg_r = args.Reader(argv)
  arg = COMPLETE_SPEC.Parse(arg_r)
  # TODO: process arg.opt_changes
  log('arg %s', arg)

  commands = arg_r.Rest()
  if not commands:
    raise args.UsageError('missing required commands')
  command = commands[0]  # TODO: loop over commands

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
COMPGEN_SPEC.InitActions()
COMPGEN_SPEC.Action(None, 'function')
COMPGEN_SPEC.Action('f', 'file')
COMPGEN_SPEC.Action('v', 'variable')
_DefineOptions(COMPGEN_SPEC)


def CompGen(argv, funcs):
  # state = args.State(argv)
  # state.Rest() -> []
  # state.AtEnd()

  arg_r = args.Reader(argv)
  arg = COMPGEN_SPEC.Parse(arg_r)
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
  arg_r = args.Reader(argv)
  arg = COMPOPT_SPEC.Parse(arg_r)
  log('arg %s', arg)
  return 0

