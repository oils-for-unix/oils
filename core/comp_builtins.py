#!/usr/bin/python
"""
comp_builtins.py - Completion builtins
"""

from core import args
from core import builtin

COMPLETE_SPEC = builtin.BUILTIN_DEF.Register('complete')
COMPLETE_SPEC.ShortFlag('-p', help='Print existing completions')
COMPLETE_SPEC.ShortFlag('-F', args.Str, help='Register a completion function')


def Complete(argv, ex, funcs, completion, comp_lookup):
  """complete builtin - register a completion function.

  NOTE: It's a member of Executor because it creates a ShellFuncAction, which
  needs an Executor.
  """
  arg, i = COMPLETE_SPEC.Parse(argv)

  command = argv[i]  # e.g. 'grep'
  func_name = arg.F

  # NOTE: bash doesn't actually check the name until completion time, but
  # obviously it's better to check here.
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
  return 0


COMPGEN_SPEC = builtin.BUILTIN_DEF.Register('compgen')
COMPGEN_SPEC.ShortFlag('-A', args.Str)


def CompGen(argv, funcs):
  arg, i = COMPGEN_SPEC.Parse(argv)
  status = 0

  if arg.A:
    if arg.A == 'function':
      for func_name in sorted(funcs):
        print(func_name)
    else:
      raise args.UsageError('compgen: %s: invalid action name' % arg.A)
  else:
    util.warn('*** command without -A not implemented ***')
    status = 1

  return status


