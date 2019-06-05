#!/usr/bin/env python2
from __future__ import print_function
"""
opy_.py
"""

import os
import sys

from frontend import args
from core import pyutil
from core.util import log

from opy import opy_main

# TODO: move to quick ref?
_OPY_USAGE = 'Usage: opy_ MAIN [OPTION]... [ARG]...'


def _ShowVersion():
  pyutil.ShowAppVersion('OPy')


# Run the bytecode too.  Should this have an option to use byterun?
def OpyMain(argv0, main_argv):
  raise NotImplementedError("Can't run bytecode yet")


def AppBundleMain(argv):
  b = os.path.basename(argv[0])
  main_name, ext = os.path.splitext(b)

  if main_name in ('opy_', 'opy') and ext:  # opy_.py or opy.ovm
    try:
      first_arg = argv[1]
    except IndexError:
      raise args.UsageError('Missing required applet name.')

    # TODO: We don't have this
    if first_arg in ('-h', '--help'):
      #builtin.Help(['bundle-usage'], util.GetResourceLoader())
      raise NotImplementedError('OPy help not implemented')
      sys.exit(0)

    if first_arg in ('-V', '--version'):
      _ShowVersion()
      sys.exit(0)

    main_name = first_arg
    argv0 = argv[1]
    main_argv = argv[2:]
  else:
    argv0 = argv[0]
    main_argv = argv[1:]

  if main_name == 'opy':
    status = OpyMain(argv0, main_argv)
    return status
  elif main_name == 'opyc':
    return opy_main.OpyCommandMain(main_argv)

  else:
    raise args.UsageError('Invalid applet name %r.' % main_name)


def main(argv):
  try:
    sys.exit(AppBundleMain(argv))
  except args.UsageError as e:
    #print(_OPY_USAGE, file=sys.stderr)
    log('opy: %s', e)
    sys.exit(2)
  except RuntimeError as e:
    log('FATAL: %s', e)
    sys.exit(1)


if __name__ == '__main__':
  # NOTE: This could end up as opy.InferTypes(), opy.GenerateCode(), etc.
  if os.getenv('CALLGRAPH') == '1':
    from opy import callgraph
    callgraph.Walk(main, sys.modules)
  else:
    main(sys.argv)
