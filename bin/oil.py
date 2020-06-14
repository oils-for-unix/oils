#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
oil.py - A busybox-like binary for oil.

Based on argv[0], it acts like a few different programs.

Note: could also expose some other binaries for a smaller POSIX system?
- 'test' / '['
- 'time'  -- has some differnt flags
"""
from __future__ import print_function

import posix_ as posix
import sys
import time  # for perf measurement
from typing import List

_trace_path = posix.environ.get('_PY_TRACE')
if _trace_path:
  from benchmarks import pytrace
  _tracer = pytrace.Tracer()
  _tracer.Start()
else:
  _tracer = None

# Uncomment this to see startup time problems.
if posix.environ.get('OIL_TIMING'):
  start_time = time.time()
  def _tlog(msg):
    # type: (str) -> None
    pid = posix.getpid()  # TODO: Maybe remove PID later.
    print('[%d] %.3f %s' % (pid, (time.time() - start_time) * 1000, msg))
else:
  def _tlog(msg):
    # type: (str) -> None
    pass

_tlog('before imports')

# Needed for oil.ovm app bundle build, since there is an functino-local import
# to break a circular build dep in frontend/consts.py.
from _devbuild.gen import id_kind
_ = id_kind
from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.syntax_asdl import source
# Hack because we don't want libcmark.so dependency for build/dev.sh minimal
try:
  from _devbuild.gen import help_index  # generated file
except ImportError:
  help_index = None

from core import alloc
from core import error
from core import main
from core import main_loop
from core import meta
from core import optview
from core import pyutil
from core import ui
from core.util import log
from frontend import args
from frontend import reader
from frontend import parse_lib
from osh import builtin_misc
from pylib import os_path
from tools import deps
from tools import osh2oil
from tools import readlink

try:
  import line_input
except ImportError:
  line_input = None


_tlog('after imports')


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
  try:
    script_name = argv[1]
    arena.PushSource(source.MainFile(script_name))
  except IndexError:
    arena.PushSource(source.Stdin())
    f = sys.stdin
  else:
    try:
      f = open(script_name)
    except IOError as e:
      ui.Stderr("oshc: Couldn't open %r: %s", script_name,
                posix.strerror(e.errno))
      return 2

  aliases = {}  # Dummy value; not respecting aliases!

  loader = pyutil.GetResourceLoader()
  oil_grammar = meta.LoadOilGrammar(loader)

  opt_array = [False] * option_i.ARRAY_SIZE
  parse_opts = optview.Parse(opt_array)
  # parse `` and a[x+1]=bar differently
  parse_ctx = parse_lib.ParseContext(arena, parse_opts, aliases, oil_grammar)
  parse_ctx.Init_OnePassParse(True)

  line_reader = reader.FileLineReader(f, arena)
  c_parser = parse_ctx.MakeOshParser(line_reader)

  try:
    node = main_loop.ParseWholeFile(c_parser)
  except error.Parse as e:
    ui.PrettyPrintError(e, arena)
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


def TeaMain(argv0, argv):
  # type: (str, List[str]) -> int
  arena = alloc.Arena()
  try:
    script_name = argv[0]
    arena.PushSource(source.MainFile(script_name))
  except IndexError:
    arena.PushSource(source.Stdin())
    f = sys.stdin
  else:
    try:
      f = open(script_name)
    except IOError as e:
      ui.Stderr("tea: Couldn't open %r: %s", script_name,
                posix.strerror(e.errno))
      return 2

  aliases = {}  # Dummy value; not respecting aliases!

  loader = pyutil.GetResourceLoader()
  oil_grammar = meta.LoadOilGrammar(loader)

  # Not used in tea, but OK...
  opt_array = [False] * option_i.ARRAY_SIZE
  parse_opts = optview.Parse(opt_array)

  # parse `` and a[x+1]=bar differently
  parse_ctx = parse_lib.ParseContext(arena, parse_opts, aliases, oil_grammar)

  line_reader = reader.FileLineReader(f, arena)

  try:
    parse_ctx.ParseTeaModule(line_reader)
    status = 0
  except error.Parse as e:
    ui.PrettyPrintError(e, arena)
    status = 2

  return status


# TODO: Hook up these applets and all valid applets to completion
# APPLETS = ['osh', 'osh', 'oil', 'readlink']


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

    if first_arg in ('-h', '--help'):
      errfmt = None  # not needed here
      help_builtin = builtin_misc.Help(loader, help_index, errfmt)
      help_builtin.Run(main.MakeBuiltinArgv(['bundle-usage']))
      sys.exit(0)

    if first_arg in ('-V', '--version'):
      pyutil.ShowAppVersion('Oil', loader)
      sys.exit(0)

    main_name = first_arg

  argv0 = arg_r.Peek()
  assert argv0 is not None
  arg_r.Next()

  login_shell = False
  if main_name.startswith('-'):
    login_shell = True
    main_name = main_name[1:]

  if main_name in ('osh', 'sh'):
    # TODO:
    # - Initialize a different shell if line_input isn't present
    # - Also think about the pure interpreter.  osh-pure, oil-pure?
    #   - osh-eval, oil-eval ?
    #   - osh --pure -c 'echo hi' ?
    # m = main.Flow(...)
    # m.Run(argv0, ...)
    if line_input:
      pass
    status = main.ShellMain('osh', argv0, arg_r, posix.environ, login_shell,
                            loader, line_input)

    _tlog('done osh main')
    return status

  elif main_name == 'oshc':
    main_argv = arg_r.Rest()
    try:
      return OshCommandMain(main_argv)
    except error.Usage as e:
      ui.Stderr('oshc usage error: %s', e.msg)
      return 2

  elif main_name == 'oil':
    return main.ShellMain('oil', argv0, arg_r, posix.environ, login_shell,
                          loader, line_input)

  elif main_name == 'tea':
    main_argv = arg_r.Rest()
    return TeaMain(argv0, main_argv)

  # For testing latency
  elif main_name == 'true':
    return 0
  elif main_name == 'false':
    return 1
  elif main_name == 'readlink':
    main_argv = arg_r.Rest()
    return readlink.main(main_argv)
  else:
    raise error.Usage('Invalid applet name %r.' % main_name)


def main_(argv):
  # type: (List[str]) -> int
  try:
    return AppBundleMain(argv)
  except NotImplementedError as e:
    raise
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
    # test this with prlimit --nproc=1 --pid=$$
    ui.Stderr('osh I/O error: %s', posix.strerror(e.errno))
    return 2  # dash gives status 2
  finally:
    _tlog('Exiting main_()')
    if _trace_path:
      _tracer.Stop(_trace_path)


# Called from Python-2.7.13/Modules/main.c.
def _cpython_main_hook():
  sys.exit(main_(sys.argv))


if __name__ == '__main__':
  pyann_out = posix.environ.get('PYANN_OUT')

  if pyann_out:
    from pyannotate_runtime import collect_types

    collect_types.init_types_collection()
    with collect_types.collect():
      status = main_(sys.argv)
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
    sys.exit(main_(sys.argv))
