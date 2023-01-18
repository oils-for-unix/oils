#!/usr/bin/env python2
"""
oils_cpp.py
"""
from __future__ import print_function

import posix_ as posix
import sys

from core import error
from core import shell
from core import pyutil
from core.pyutil import stderr_line
from core import shell_native
from core.pyerror import log
from frontend import args
from frontend import py_readline
from mycpp import mylib
from osh import builtin_misc
from pylib import os_path
from tools import tools_main

if mylib.PYTHON:
  from tea import tea_main
  from tools import readlink

import fanos

from typing import List


def CaperDispatch():
  # type: () -> int
  log('Running Oil in ---caper mode')
  fd_out = []  # type: List[int]
  while True:
    try:
      msg = fanos.recv(0, fd_out)
    except ValueError as e:
      # TODO: recv() needs to detect EOF condition.  Should it return ''
      # like sys.stdin.readline(), or something else?
      # Should that be distinguished from '0:,' ?   with None perhaps?
      log('FANOS error: %s', e)
      fanos.send(1, 'ERROR %s' % e)
      continue

    log('msg = %r', msg)

    command, arg = msg.split(' ', 1)
    if command == 'GETPID':
      pass
    elif command == 'CHDIR':
      pass
    elif command == 'SETENV':
      pass
    elif command == 'MAIN':
      argv = ['TODO']
      # I think we need to factor the oil.{py,ovm} condition out and call it like this:
      # MainDispatch(main_name, argv) or
      # MainDispatch(main_name, arg_r)
      pass

    # fanos.send(1, reply)

  return 0  # Does this fail?


# TODO: Hook up valid applets (including these) to completion
# APPLETS = ['osh', 'osh', 'oil', 'readlink', 'true', 'false']


def AppBundleMain(argv):
  # type: (List[str]) -> int

  # NOTE: This has a side effect of deleting _OVM_* from the environment!
  loader = pyutil.GetResourceLoader()

  b = os_path.basename(argv[0])
  main_name, ext = os_path.splitext(b)

  arg_r = args.Reader(argv)
  if main_name == 'oil' and ext:  # oil.py or oil.ovm
    arg_r.Next()
    first_arg = arg_r.Peek()
    if first_arg is None:
      raise error.Usage('Missing required applet name.')

    # Special flags to the top level binary: bin/oil.py --help, ---caper, etc.
    if first_arg in ('-h', '--help'):
      errfmt = None  # not needed here
      help_builtin = builtin_misc.Help(loader, errfmt)
      help_builtin.Run(shell_native.MakeBuiltinArgv(['bundle-usage']))
      return 0

    if first_arg in ('-V', '--version'):
      pyutil.ShowAppVersion('Oil', loader)
      return 0

    # This has THREE dashes since it isn't a normal flag
    if first_arg == '---caper':
      return CaperDispatch()

    main_name = first_arg

  login_shell = False
  if main_name.startswith('-'):
    login_shell = True
    main_name = main_name[1:]

  readline = py_readline.MaybeGetReadline()

  if main_name.endswith('sh'):  # sh, osh, bash imply OSH
    status = shell.Main('osh', arg_r, posix.environ, login_shell,
                        loader, readline)
    return status

  elif main_name == 'oshc':
    arg_r.Next()
    main_argv = arg_r.Rest()
    try:
      if mylib.PYTHON:
        status = tools_main.OshCommandMain(main_argv)
      else:
        stderr_line('oshc not implemented')
        status = 2
      return status
    except error.Usage as e:
      stderr_line('oshc usage error: %s', e.msg)
      return 2

  elif main_name == 'oil':
    return shell.Main('oil', arg_r, posix.environ, login_shell,
                      loader, readline)

  elif main_name == 'tea':
    arg_r.Next()
    return tea_main.Main(arg_r)

  # For testing latency
  elif main_name == 'true':
    return 0
  elif main_name == 'false':
    return 1
  elif main_name == 'readlink':
    # TODO: Move this to 'internal readlink' (issue #1013)
    main_argv = arg_r.Rest()
    return readlink.main(main_argv)
  else:
    raise error.Usage('Invalid applet name %r.' % main_name)


def main(argv):
  # type: (List[str]) -> int

  try:
    return AppBundleMain(argv)
  except error.Usage as e:
    #builtin.Help(['oil-usage'], util.GetResourceLoader())
    log('oil: %s', e.msg)
    return 2
  except RuntimeError as e:
    if 0:
      import traceback
      traceback.print_exc()
    # NOTE: The Python interpreter can cause this, e.g. on stack overflow.
    log('FATAL: %r', e)
    return 1
  except KeyboardInterrupt:
    print()
    return 130  # 128 + 2
  except (IOError, OSError) as e:
    if 0:
      import traceback
      traceback.print_exc()

    # test this with prlimit --nproc=1 --pid=$$
    stderr_line('osh I/O error: %s', posix.strerror(e.errno))
    return 2  # dash gives status 2

if __name__ == '__main__':
  sys.exit(main(sys.argv))
