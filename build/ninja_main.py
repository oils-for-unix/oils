#!/usr/bin/env python2
"""
build/NINJA_main.py - invoked by ./NINJA-config.sh
"""
from __future__ import print_function

import cStringIO
import os
import sys

from build import ninja_lib
from asdl import NINJA_subgraph as asdl_subgraph
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
    f = open(BUILD_NINJA, 'w')
  else:
    f = cStringIO.StringIO()  # thrown away

  n = ninja_syntax.Writer(f)
  ru = ninja_lib.Rules(n)

  ### Create the graph.  TODO: Add other dirs.

  asdl_subgraph.NinjaGraph(ru)

  n.newline()
  n.newline()

  build_subgraph.NinjaGraph(ru)

  n.newline()
  n.newline()

  # //mycpp/runtime defined first
  mycpp_subgraph.NinjaGraph(ru)

  n.newline()
  n.newline()

  cpp_subgraph.NinjaGraph(ru)

  n.newline()
  n.newline()

  if action == 'ninja':
    log('  (%s) -> %s', argv[0], BUILD_NINJA)

  elif action == 'shell':
    from cpp.NINJA_subgraph import OSH_EVAL_UNITS_ALL
    cc_sources = OSH_EVAL_UNITS_ALL

    out = '_build/oil-native.sh'
    with open(out, 'w') as f:
      cpp_subgraph.ShellFunctions(cc_sources, f, argv[0])
    log('  (%s) -> %s', argv[0], out)

  elif action == 'tarball-manifest':
    from cpp.NINJA_subgraph import OSH_EVAL_UNITS_ALL

    cc_sources = OSH_EVAL_UNITS_ALL
    cpp_subgraph.TarballManifest(cc_sources)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
