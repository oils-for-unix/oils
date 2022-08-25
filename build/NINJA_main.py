#!/usr/bin/env python2
"""
NINJA_config.py
"""
from __future__ import print_function

import os
import sys

from build import NINJA_subgraph as build_subgraph
from cpp import NINJA_subgraph as cpp_subgraph
from mycpp import NINJA_subgraph as mycpp_subgraph

from vendor import ninja_syntax


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


# The file Ninja runs by default.
BUILD_NINJA = 'build.ninja'

# Tasks that invoke Ninja
TASK_SH = 'TASK.sh'


def main(argv):
  try:
    action = argv[1]
  except IndexError:
    action = 'ninja'

  if action == 'ninja':
    n = ninja_syntax.Writer(open(BUILD_NINJA, 'w'))

    build_subgraph.NinjaGraph(n)

    n.newline()
    n.newline()

    cpp_subgraph.NinjaGraph(n)

    n.newline()
    n.newline()

    mycpp_subgraph.NinjaGraph(n)

    log('%s: Wrote %s', argv[0], BUILD_NINJA)


  elif action == 'shell':
    out = '_build/oil-native.sh'
    with open(out, 'w') as f:
      cpp_subgraph.ShellFunctions(f, argv[0])
    log('%s: Wrote %s', argv[0], out)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
