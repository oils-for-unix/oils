#!/usr/bin/env python2
"""
oils_cpp.py - A busybox-like binary for OSH and YSH (formerly Oil).

This is the main program that is translated to C++ by mycpp.

Based on argv[0], it acts like a few different programs.
- true, false
- readlink

We could could also expose some other binaries for a smaller POSIX system:

- test / '['
- printf, echo
- cat
- 'time' -- different usage
"""
from __future__ import print_function

import posix_ as posix
import sys

from asdl import runtime
from core import error
from core import shell
from core import pyos
from core import pyutil
from core import shell_native
from core.pyerror import log
from frontend import args
from frontend import py_readline
from mycpp import mylib
from mycpp.mylib import print_stderr
from osh import builtin_misc
from pylib import os_path
from tools import tools_main

if mylib.PYTHON:
  from tea import tea_main
  from tools import readlink

import fanos

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
  from core import ui


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

    command, arg = mylib.split_once(msg, ' ')
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

  # TODO: Do we need span IDs here?
  arg_r = args.Reader(argv, spids=[runtime.NO_SPID] * len(argv))

  login_shell = False

  # Are we running the C++ bundle or the Python bundle directly, without a
  # symlink?
  if main_name == 'oils_cpp' or (main_name == 'oil' and len(ext)):
    arg_r.Next()
    first_arg = arg_r.Peek()
    if first_arg is None:
      raise error.Usage('Missing required applet name.')

    # Special flags to the top level binary: bin/oil.py --help, ---caper, etc.
    if first_arg in ('-h', '--help'):
      errfmt = None  # type: ui.ErrorFormatter
      help_builtin = builtin_misc.Help(loader, errfmt)
      help_builtin.Run(shell_native.MakeBuiltinArgv(['bundle-usage']))
      return 0

    if first_arg in ('-V', '--version'):
      pyutil.ShowAppVersion('Oil', loader)
      return 0

    # This has THREE dashes since it isn't a normal flag
    if first_arg == '---caper':
      return CaperDispatch()

    applet = first_arg
  else:
    applet = main_name

    if applet.startswith('-'):
      login_shell = True
      applet = applet[1:]

  readline = py_readline.MaybeGetReadline()

  environ = pyos.Environ()

  if applet in ('ysh', 'oil'):
    return shell.Main('oil', arg_r, environ, login_shell, loader, readline)

  elif applet.endswith('sh'):  # sh, osh, bash imply OSH
    return shell.Main('osh', arg_r, environ, login_shell, loader, readline)

  elif applet == 'oshc':
    # TODO: ysh-format is probably the only thing we will expose.

    arg_r.Next()
    main_argv = arg_r.Rest()
    try:
      if mylib.PYTHON:
        return tools_main.OshCommandMain(main_argv)
      else:
        print_stderr('oshc not translated')
        return 2
    except error.Usage as e:
      print_stderr('oshc usage error: %s' % e.msg)
      return 2

  elif applet == 'tea':
    arg_r.Next()
    if mylib.PYTHON:
      return tea_main.Main(arg_r)
    else:
      print_stderr('tea not translated')
      return 2

  # For testing latency
  elif applet == 'true':
    return 0
  elif applet == 'false':
    return 1
  elif applet == 'readlink':
    if mylib.PYTHON:
      # TODO: Move this to 'internal readlink' (issue #1013)
      main_argv = arg_r.Rest()
      return readlink.main(main_argv)
    else:
      print_stderr('readlink not translated')
      return 2

  else:
    raise error.Usage("Invalid applet %r" % applet)


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

    # Oil code shouldn't throw RuntimeError, but the Python interpreter can,
    # e.g. on stack overflow (or MemoryError).
    log('FATAL RuntimeError: %s', e.message)

    return 1

  except KeyboardInterrupt:
    print('')
    return 130  # 128 + 2

  except (IOError, OSError) as e:
    if 0:
      import traceback
      traceback.print_exc()

    # test this with prlimit --nproc=1 --pid=$$
    print_stderr('osh I/O error: %s' % posix.strerror(e.errno))
    return 2  # dash gives status 2


if __name__ == '__main__':
  sys.exit(main(sys.argv))
