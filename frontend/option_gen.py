#!/usr/bin/env python2
"""
option_gen.py
"""
from __future__ import print_function

import sys

from asdl.visitor import FormatLines
from frontend import option_def


def main(argv):
  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  # TODO:
  # generate builtin::echo, etc.
  # 
  # And in Python do the same.


  if action == 'cpp':
    pass

  elif action == 'cc-tables':
    pass

  elif action == 'py-tables':
    pass

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
