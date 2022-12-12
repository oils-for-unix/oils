#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
oil.py - A busybox-like binary for OSH and Oil.

Based on argv[0], it acts like a few different programs.
- true, false
- readlink

Note: could also expose some other binaries for a smaller POSIX system?
- test / '['
- printf, echo
- cat
- seq
- 'time' -- has some different flags
"""
from __future__ import print_function

import posix_ as posix
import sys
from typing import List

# Needed for oil.ovm app bundle build, since there is an functino-local import
# to break a circular build dep in frontend/consts.py.
from _devbuild.gen import id_kind
_ = id_kind
from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.syntax_asdl import source

from core import alloc
from core import error
from core import main_loop
from core import shell
from core import optview
from core import pyutil
from core.pyutil import stderr_line
from core import shell_native
from core import state
from core import ui
from core.pyerror import log
from frontend import args
from frontend import reader
from frontend import parse_lib
from osh import builtin_misc
from pylib import os_path
from tea import tea_main
from tools import deps
from tools import osh2oil
from tools import readlink


# TODO: Hook up to completion.
SUBCOMMANDS = [
    'translate', 'arena', 'spans', 'format', 'deps', 'undefined-vars',
    'parse-glob', 'parse-printf',
]

def OshCommandMain(argv):
  """Run an 'oshc' tool.

  'osh' is short for "osh compiler" or "osh command".

  TODO:
  - oshc --help

  oshc deps
    --path: the $PATH to use to find executables.  What about libraries?

    NOTE: we're leaving out su -c, find, xargs, etc.?  Those should generally
    run functions using the $0 pattern.
    --chained-command sudo

  TODO: Get rid of oshc, and change this to

  osh/oil --tool translate foo.py
  osh/oil --tool translate -c 'echo hi'
  osh/oil --tool parse-glob 'my-glob'

  Although it does ParseWholeFile, like -n.

  And then you can use the same -o options and so forth.  Also push this into
  core/shell_native.py.
  """
  try:
    action = argv[0]
  except IndexError:
    raise error.Usage('Missing required subcommand.')

  if action not in SUBCOMMANDS:
    raise error.Usage('Invalid subcommand %r.' % action)

  if action == 'parse-glob':
    # Pretty-print the AST produced by osh/glob_.py
    print('TODO:parse-glob')
    return 0

  if action == 'parse-printf':
    # Pretty-print the AST produced by osh/builtin_printf.py
    print('TODO:parse-printf')
    return 0

  arena = alloc.Arena()
  errfmt = ui.ErrorFormatter(arena)
  try:
    script_name = argv[1]
    arena.PushSource(source.MainFile(script_name))
  except IndexError:
    arena.PushSource(source.Stdin(''))
    f = sys.stdin
  else:
    try:
      f = open(script_name)
    except IOError as e:
      stderr_line("oshc: Couldn't open %r: %s", script_name,
                  posix.strerror(e.errno))
      return 2

  aliases = {}  # Dummy value; not respecting aliases!

  loader = pyutil.GetResourceLoader()
  oil_grammar = pyutil.LoadOilGrammar(loader)

  opt0_array = state.InitOpts()
  no_stack = None  # type: List[bool]  # for mycpp
  opt_stacks = [no_stack] * option_i.ARRAY_SIZE  # type: List[List[bool]]

  parse_opts = optview.Parse(opt0_array, opt_stacks)
  # parse `` and a[x+1]=bar differently
  parse_ctx = parse_lib.ParseContext(arena, parse_opts, aliases, oil_grammar)
  parse_ctx.Init_OnePassParse(True)

  line_reader = reader.FileLineReader(f, arena)
  c_parser = parse_ctx.MakeOshParser(line_reader)

  try:
    node = main_loop.ParseWholeFile(c_parser)
  except error.Parse as e:
    errfmt.PrettyPrintError(e)
    return 2
  assert node is not None

  f.close()

  # Columns for list-*
  # path line name
  # where name is the binary path, variable name, or library path.

  # bin-deps and lib-deps can be used to make an app bundle.
  # Maybe I should list them together?  'deps' can show 4 columns?
  #
  # path, line, type, name
  #
  # --pretty can show the LST location.

  # stderr: show how we're following imports?

  if action == 'translate':
    osh2oil.PrintAsOil(arena, node)

  elif action == 'arena':  # for debugging
    osh2oil.PrintArena(arena)

  elif action == 'spans':  # for debugging
    osh2oil.PrintSpans(arena)

  elif action == 'format':
    # TODO: autoformat code
    raise NotImplementedError(action)

  elif action == 'deps':
    deps.Deps(node)

  elif action == 'undefined-vars':  # could be environment variables
    raise NotImplementedError()

  else:
    raise AssertionError  # Checked above

  return 0


import fanos

def CaperDispatch():
  log('Running Oil in ---caper mode')
  fd_out = []
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

  readline = pyutil.MaybeGetReadline()

  if main_name.endswith('sh'):  # sh, osh, bash imply OSH
    status = shell.Main('osh', arg_r, posix.environ, login_shell,
                        loader, readline)
    return status

  elif main_name == 'oshc':
    arg_r.Next()
    main_argv = arg_r.Rest()
    try:
      return OshCommandMain(main_argv)
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


# Called from Python-2.7.13/Modules/main.c.
def _cpython_main_hook():
  sys.exit(main(sys.argv))


if __name__ == '__main__':
  if not pyutil.IsAppBundle():
    # For unmodified Python interpreters to simulate the OVM_MAIN patch
    import libc
    libc.cpython_reset_locale()

  pyann_out = posix.environ.get('PYANN_OUT')

  if pyann_out:
    from pyannotate_runtime import collect_types

    collect_types.init_types_collection()
    with collect_types.collect():
      status = main(sys.argv)
    collect_types.dump_stats(pyann_out)
    sys.exit(status)

  elif posix.environ.get('RESOLVE') == '1':
    from opy import resolve
    resolve.Walk(dict(sys.modules))

  elif posix.environ.get('CALLGRAPH') == '1':
    # NOTE: This could end up as opy.InferTypes(), opy.GenerateCode(), etc.
    from opy import callgraph
    callgraph.Walk(main, sys.modules)

  else:
    sys.exit(main(sys.argv))
