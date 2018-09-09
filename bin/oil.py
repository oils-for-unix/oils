#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
"""
oil.py - A busybox-like binary for oil.

Based on argv[0], it acts like a few different programs.

Builtins that can be exposed:

- test / [ -- call BoolParser at runtime
- 'time' -- because it has format strings, etc.
- find/xargs equivalents (even if they are not compatible)
  - list/each/every

- echo: most likely don't care about this
"""

import os
import sys
import time  # for perf measurement

# TODO: Set PYTHONPATH from outside?
this_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(os.path.join(this_dir, '..'))

_trace_path = os.environ.get('_PY_TRACE')
if _trace_path:
  from benchmarks import pytrace
  _tracer = pytrace.Tracer()
  _tracer.Start()
else:
  _tracer = None

# Uncomment this to see startup time problems.
if os.environ.get('OIL_TIMING'):
  start_time = time.time()
  def _tlog(msg):
    pid = os.getpid()  # TODO: Maybe remove PID later.
    print('[%d] %.3f %s' % (pid, (time.time() - start_time) * 1000, msg))
else:
  def _tlog(msg):
    pass

_tlog('before imports')

import errno
#import traceback  # for debugging

# Set in Modules/main.c.
HAVE_READLINE = os.getenv('_HAVE_READLINE') != ''

from osh import parse_lib

from core import alloc
from core import args
from core import builtin
from core import cmd_exec
from core import legacy
from core import main_loop
from core import process
from core import reader
from core import state
from core import word_eval
from core import ui
from core import util

if HAVE_READLINE:
  import readline
  from core import completion
else:
  readline = None
  completion = None

from tools import deps
from tools import osh2oil
from tools import readlink

log = util.log

_tlog('after imports')


# bash --noprofile --norc uses 'bash-4.3$ '
OSH_PS1 = 'osh$ '


def _ShowVersion():
  util.ShowAppVersion('Oil')


def OshMain(argv0, argv, login_shell):
  spec = args.FlagsAndOptions()
  spec.ShortFlag('-c', args.Str, quit_parsing_flags=True)  # command string
  spec.ShortFlag('-i')  # interactive

  # TODO: -h too
  spec.LongFlag('--help')
  spec.LongFlag('--version')
  # the output format when passing -n
  spec.LongFlag('--ast-format',
                ['text', 'abbrev-text', 'html', 'abbrev-html', 'oheap', 'none'],
                default='abbrev-text')

  spec.LongFlag('--print-status')  # TODO: Replace with a shell hook
  spec.LongFlag('--hijack-shebang')  # TODO: Implement this
  spec.LongFlag('--debug-file', args.Str)

  # For benchmarks/*.sh
  spec.LongFlag('--parser-mem-dump', args.Str)
  spec.LongFlag('--runtime-mem-dump', args.Str)

  builtin.AddOptionsToArgSpec(spec)

  try:
    opts, opt_index = spec.Parse(argv)
  except args.UsageError as e:
    util.usage(str(e))
    return 2

  if opts.help:
    loader = util.GetResourceLoader()
    builtin.Help(['osh-usage'], loader)
    return 0
  if opts.version:
    # OSH version is the only binary in Oil right now, so it's all one version.
    _ShowVersion()
    return 0

  # TODO: This should be in interactive mode only?
  builtin.RegisterSigIntHandler()

  if opt_index == len(argv):
    dollar0 = argv0
  else:
    dollar0 = argv[opt_index]  # the script name, or the arg after -c

  pool = alloc.Pool()
  arena = pool.NewArena()

  # TODO: Maybe wrap this initialization sequence up in an oil_State, like
  # lua_State.
  status_lines = ui.MakeStatusLines()
  mem = state.Mem(dollar0, argv[opt_index + 1:], os.environ, arena)
  funcs = {}

  # Passed to Executor for 'complete', and passed to completion.Init
  if completion:
    comp_lookup = completion.CompletionLookup()
  else:
    # TODO: NullLookup?
    comp_lookup = None

  fd_state = process.FdState()
  exec_opts = state.ExecOpts(mem)
  builtin.SetExecOpts(exec_opts, opts.opt_changes)
  aliases = {}  # feedback between runtime and parser

  parse_ctx = parse_lib.ParseContext(arena, aliases)

  if opts.debug_file:
    util.DEBUG_FILE = fd_state.Open(opts.debug_file, mode='w')
    util.Debug('Debug file is %s', util.DEBUG_FILE)

  ex = cmd_exec.Executor(mem, fd_state, status_lines, funcs, readline,
                         completion, comp_lookup, exec_opts, parse_ctx)

  # NOTE: The rc file can contain both commands and functions... ideally we
  # would only want to save nodes/lines for the functions.
  try:
    rc_path = 'oilrc'
    arena.PushSource(rc_path)
    with open(rc_path) as f:
      rc_line_reader = reader.FileLineReader(f, arena)
      _, rc_c_parser = parse_ctx.MakeParser(rc_line_reader)
      try:
        status = main_loop.Batch(ex, rc_c_parser, arena)
      finally:
        arena.PopSource()
  except IOError as e:
    if e.errno != errno.ENOENT:
      raise

  if opts.c is not None:
    arena.PushSource('<command string>')
    line_reader = reader.StringLineReader(opts.c, arena)
    if opts.i:  # -c and -i can be combined
      exec_opts.interactive = True
  elif opts.i:  # force interactive
    arena.PushSource('<stdin -i>')
    line_reader = reader.InteractiveLineReader(OSH_PS1, arena)
    exec_opts.interactive = True
  else:
    try:
      script_name = argv[opt_index]
    except IndexError:
      if sys.stdin.isatty():
        arena.PushSource('<interactive>')
        line_reader = reader.InteractiveLineReader(OSH_PS1, arena)
        exec_opts.interactive = True
      else:
        arena.PushSource('<stdin>')
        line_reader = reader.FileLineReader(sys.stdin, arena)
    else:
      arena.PushSource(script_name)
      try:
        f = fd_state.Open(script_name)
      except OSError as e:
        util.error("Couldn't open %r: %s", script_name, os.strerror(e.errno))
        return 1
      line_reader = reader.FileLineReader(f, arena)

  # TODO: assert arena.NumSourcePaths() == 1
  # TODO: .rc file needs its own arena.
  w_parser, c_parser = parse_ctx.MakeParser(line_reader)

  if exec_opts.interactive:
    # NOTE: We're using a different evaluator here.  The completion system can
    # also run functions... it gets the Executor through Executor._Complete.
    if HAVE_READLINE:
      splitter = legacy.SplitContext(mem)
      ev = word_eval.CompletionWordEvaluator(mem, exec_opts, splitter)
      status_out = completion.StatusOutput(status_lines, exec_opts)
      completion.Init(pool, builtin.BUILTIN_DEF, mem, funcs, comp_lookup,
                      status_out, ev, parse_ctx)

    return main_loop.Interactive(opts, ex, c_parser, arena)

  # Parse the whole thing up front
  #print('Parsing file')

  # Do this after parsing the entire file.  There could be another option to
  # do it before exiting runtime?
  if opts.parser_mem_dump:
    # This might be superstition, but we want to let the value stabilize
    # after parsing.  bash -c 'cat /proc/$$/status' gives different results
    # with a sleep.
    time.sleep(0.001)
    input_path = '/proc/%d/status' % os.getpid()
    with open(input_path) as f, open(opts.parser_mem_dump, 'w') as f2:
      contents = f.read()
      f2.write(contents)
      log('Wrote %s to %s (--parser-mem-dump)', input_path,
          opts.parser_mem_dump)

  nodes_out = [] if exec_opts.noexec else None

  _tlog('Execute(node)')
  #status = ex.ExecuteAndRunExitTrap(node)
  status = main_loop.Batch(ex, c_parser, arena, nodes_out=nodes_out)

  if nodes_out is not None:
    ui.PrintAst(nodes_out, opts)

  # NOTE: 'exit 1' is ControlFlow and gets here, but subshell/commandsub
  # don't because they call sys.exit().
  if opts.runtime_mem_dump:
    # This might be superstition, but we want to let the value stabilize
    # after parsing.  bash -c 'cat /proc/$$/status' gives different results
    # with a sleep.
    time.sleep(0.001)
    input_path = '/proc/%d/status' % os.getpid()
    with open(input_path) as f, open(opts.runtime_mem_dump, 'w') as f2:
      contents = f.read()
      f2.write(contents)
      log('Wrote %s to %s (--runtime-mem-dump)', input_path,
          opts.runtime_mem_dump)

  # NOTE: We haven't closed the file opened with fd_state.Open
  return status


def OilMain(argv):
  spec = args.FlagsAndOptions()
  # TODO: -h too
  spec.LongFlag('--help')
  spec.LongFlag('--version')
  #builtin.AddOptionsToArgSpec(spec)

  try:
    opts, opt_index = spec.Parse(argv)
  except args.UsageError as e:
    util.usage(str(e))
    return 2

  if opts.help:
    loader = util.GetResourceLoader()
    builtin.Help(['oil-usage'], loader)
    return 0
  if opts.version:
    # OSH version is the only binary in Oil right now, so it's all one version.
    _ShowVersion()
    return 0

  raise NotImplementedError('oil')
  return 0


def WokMain(main_argv):
  raise NotImplementedError('wok')


def BoilMain(main_argv):
  raise NotImplementedError('boil')


# TODO: Hook up to completion.
SUBCOMMANDS = [
    'translate', 'arena', 'spans', 'format', 'deps', 'undefined-vars'
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
    raise args.UsageError('oshc: Missing required subcommand.')

  if action not in SUBCOMMANDS:
    raise args.UsageError('oshc: Invalid subcommand %r.' % action)

  try:
    script_name = argv[1]
  except IndexError:
    script_name = '<stdin>'
    f = sys.stdin
  else:
    try:
      f = open(script_name)
    except IOError as e:
      util.error("Couldn't open %r: %s", script_name, os.strerror(e.errno))
      return 2

  pool = alloc.Pool()
  arena = pool.NewArena()
  arena.PushSource(script_name)

  line_reader = reader.FileLineReader(f, arena)
  aliases = {}  # Dummy value; not respecting aliases!
  parse_ctx = parse_lib.ParseContext(arena, aliases)
  _, c_parser = parse_ctx.MakeParser(line_reader)

  try:
    node = main_loop.ParseWholeFile(c_parser)
  except util.ParseError as e:
    ui.PrettyPrintError(e, arena, sys.stderr)
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
    raise NotImplementedError

  else:
    raise AssertionError  # Checked above

  return 0


# The valid applets right now.
# TODO: Hook up to completion.
APPLETS = ['osh', 'oshc']


def AppBundleMain(argv):
  login_shell = False

  b = os.path.basename(argv[0])
  main_name, ext = os.path.splitext(b)
  if main_name.startswith('-'):
    login_shell = True
    main_name = main_name[1:]

  if main_name == 'oil' and ext:  # oil.py or oil.ovm
    try:
      first_arg = argv[1]
    except IndexError:
      raise args.UsageError('Missing required applet name.')

    if first_arg in ('-h', '--help'):
      builtin.Help(['bundle-usage'], util.GetResourceLoader())
      sys.exit(0)

    if first_arg in ('-V', '--version'):
      _ShowVersion()
      sys.exit(0)

    main_name = first_arg
    if main_name.startswith('-'):  # TODO: Remove duplication above
      login_shell = True
      main_name = main_name[1:]
    argv0 = argv[1]
    main_argv = argv[2:]
  else:
    argv0 = argv[0]
    main_argv = argv[1:]

  if main_name in ('osh', 'sh'):
    status = OshMain(argv0, main_argv, login_shell)
    _tlog('done osh main')
    return status
  elif main_name == 'oshc':
    return OshCommandMain(main_argv)

  elif main_name == 'oil':
    return OilMain(main_argv)
  elif main_name == 'wok':
    return WokMain(main_argv)
  elif main_name == 'boil':
    return BoilMain(main_argv)

  # For testing latency
  elif main_name == 'true':
    return 0
  elif main_name == 'false':
    return 1
  elif main_name == 'readlink':
    return readlink.main(main_argv)
  else:
    raise args.UsageError('Invalid applet name %r.' % main_name)


def main(argv):
  try:
    sys.exit(AppBundleMain(argv))
  except NotImplementedError as e:
    raise
  except args.UsageError as e:
    #builtin.Help(['oil-usage'], util.GetResourceLoader())
    log('oil: %s', e)
    sys.exit(2)
  except RuntimeError as e:
    log('FATAL: %s', e)
    sys.exit(1)
  finally:
    _tlog('Exiting main()')
    if _trace_path:
      _tracer.Stop(_trace_path)


if __name__ == '__main__':
  # NOTE: This could end up as opy.InferTypes(), opy.GenerateCode(), etc.
  if os.getenv('CALLGRAPH') == '1':
    from opy import callgraph
    callgraph.Walk(main, sys.modules)
  else:
    main(sys.argv)

