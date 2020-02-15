#!/usr/bin/env python2
"""
arg_gen.py
"""
from __future__ import print_function

import sys

from frontend import arg_def
from osh import builtin_assign
from osh import builtin_bracket
from osh import builtin_misc
from osh import builtin_process
from osh import builtin_printf
from osh import builtin_pure


def main(argv):

  specs = arg_def.All()
  for n in sorted(specs):
    print(n)
    print(specs[n])

  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  # TODO: Generate statically typed records and parsing functions
  # Could we convert flag_val = Bool | Int | Str to
  # a native value?  Or do we generate somethign else?
  #
  # Don't forget we also want completion of flags, which we don't have yet.

  # TODO: This should also generate snippets that go in the official docs?
  # woven in with make_help.py?
  # Does it generate markdown?
  #
  # read FLAGS* NAME*
  #
  # Flags:
  #
  # -a array  OK
  # -d delim
  # -e        Use readline
  #
  # exit status and examples.
  # I guess it's indented 4?

  if action == 'cpp':
    pass

  elif action == 'mypy':
    pass

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
