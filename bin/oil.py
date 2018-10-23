#!/usr/bin/python -S
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
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
from __future__ import print_function

import posix
import sys
import time  # for perf measurement

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
    pid = posix.getpid()  # TODO: Maybe remove PID later.
    print('[%d] %.3f %s' % (pid, (time.time() - start_time) * 1000, msg))
else:
  def _tlog(msg):
    pass

_tlog('before imports')

import errno
#import traceback  # for debugging

# Set in Modules/main.c.
HAVE_READLINE = posix.environ.get('_HAVE_READLINE') != ''

from osh import parse_lib

from core import alloc
from core import args
from core import builtin
from core import completion
from core import cmd_exec
from core import dev
from core import legacy
from core import main_loop
from core import os_path
from core import process
from core import reader
from core import state
from core import word_eval
from core import ui
from core import util

if HAVE_READLINE:
  import readline
else:
  readline = None

from tools import deps
from tools import osh2oil
from tools import readlink

log = util.log

_tlog('after imports')


def _ShowVersion():
  util.ShowAppVersion('Oil')


OSH_SPEC = args.FlagsAndOptions()
OSH_SPEC.ShortFlag('-c', args.Str, quit_parsing_flags=True)  # command string
OSH_SPEC.ShortFlag('-i')  # interactive

# TODO: -h too
OSH_SPEC.LongFlag('--help')
OSH_SPEC.LongFlag('--version')
# the output format when passing -n
OSH_SPEC.LongFlag('--ast-format',
              ['text', 'abbrev-text', 'html', 'abbrev-html', 'oheap', 'none'],
              default='abbrev-text')

OSH_SPEC.LongFlag('--print-status')  # TODO: Replace with a shell hook
OSH_SPEC.LongFlag('--hijack-shebang')  # TODO: Implement this
OSH_SPEC.LongFlag('--debug-file', args.Str)
OSH_SPEC.LongFlag('--xtrace-to-debug-file')

# For benchmarks/*.sh
OSH_SPEC.LongFlag('--parser-mem-dump', args.Str)
OSH_SPEC.LongFlag('--runtime-mem-dump', args.Str)

# For bash compatibility
OSH_SPEC.LongFlag('--norc')

builtin.AddOptionsToArgSpec(OSH_SPEC)


def OshMain(argv0, argv, login_shell):

  arg_r = args.Reader(argv)
  try:
    opts = OSH_SPEC.Parse(arg_r)
  except args.UsageError as e:
    ui.usage('osh usage error: %s', e)
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

  if arg_r.AtEnd():
    dollar0 = argv0
    has_main = False
  else:
    dollar0 = arg_r.Peek()  # the script name, or the arg after -c
    has_main = True

  pool = alloc.Pool()
  arena = pool.NewArena()

  # NOTE: has_main is only for ${BASH_SOURCE[@} and family.  Could be a
  # required arg.
  mem = state.Mem(dollar0, argv[arg_r.i + 1:], posix.environ, arena,
                  has_main=has_main)
  funcs = {}

  comp_lookup = completion.CompletionLookup()

  fd_state = process.FdState()
  exec_opts = state.ExecOpts(mem, readline)
  builtin.SetExecOpts(exec_opts, opts.opt_changes)
  aliases = {}  # feedback between runtime and parser

  parse_ctx = parse_lib.ParseContext(arena, aliases)

  if opts.debug_file:
    debug_f = util.DebugFile(fd_state.Open(opts.debug_file, mode='w'))
  else:
    debug_f = util.NullDebugFile()
  debug_f.log('Debug file is %s', opts.debug_file)

  # Controlled by env variable, flag, or hook?
  dumper = dev.CrashDumper(posix.environ.get('OSH_CRASH_DUMP_DIR', ''))
  if opts.xtrace_to_debug_file:
    trace_f = debug_f
  else:
    trace_f = util.DebugFile(sys.stderr)
  devtools = dev.DevTools(dumper, debug_f, trace_f)

  ex = cmd_exec.Executor(mem, fd_state, funcs, comp_lookup, exec_opts,
                         parse_ctx, devtools)

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

  # Needed in non-interactive shells for @P
  prompt = ui.Prompt(arena, parse_ctx, ex)
  ui.PROMPT = prompt

  if opts.c is not None:
    arena.PushSource('<command string>')
    line_reader = reader.StringLineReader(opts.c, arena)
    if opts.i:  # -c and -i can be combined
      exec_opts.interactive = True
  elif opts.i:  # force interactive
    arena.PushSource('<stdin -i>')
    line_reader = reader.InteractiveLineReader(arena, prompt)
    exec_opts.interactive = True
  else:
    try:
      script_name = arg_r.Peek()
    except IndexError:
      if sys.stdin.isatty():
        arena.PushSource('<interactive>')
        line_reader = reader.InteractiveLineReader(arena, prompt)
        exec_opts.interactive = True
      else:
        arena.PushSource('<stdin>')
        line_reader = reader.FileLineReader(sys.stdin, arena)
    else:
      arena.PushSource(script_name)
      try:
        f = fd_state.Open(script_name)
      except OSError as e:
        util.error("Couldn't open %r: %s", script_name, posix.strerror(e.errno))
        return 1
      line_reader = reader.FileLineReader(f, arena)

  # TODO: assert arena.NumSourcePaths() == 1
  # TODO: .rc file needs its own arena.
  w_parser, c_parser = parse_ctx.MakeParser(line_reader)

  if exec_opts.interactive:
    # NOTE: We're using a different evaluator here.  The completion system can
    # also run functions... it gets the Executor through Executor._Complete.
    if HAVE_READLINE:
      splitter = legacy.SplitContext(mem)  # TODO: share with executor.
      ev = word_eval.CompletionWordEvaluator(mem, exec_opts, splitter, arena)
      progress_f = ui.StatusLine()
      var_action = completion.VariablesActionInternal(ex.mem)
      root_comp = completion.RootCompleter(ev, comp_lookup, var_action,
                                           parse_ctx, progress_f, debug_f)
      completion.Init(readline, root_comp, debug_f)

      from core import comp_builtins
      # register builtins and words
      comp_builtins.Complete(['-E', '-A', 'command'], ex, comp_lookup)
      # register path completion
      comp_builtins.Complete(['-D', '-A', 'file'], ex, comp_lookup)

      # TODO: Move this into demo/slow-completion.sh
      if 1:
        # Something for fun, to show off.  Also: test that you don't repeatedly hit
        # the file system / network / coprocess.
        A1 = completion.WordsAction(['foo.py', 'foo', 'bar.py'])
        A2 = completion.WordsAction(['m%d' % i for i in xrange(5)], delay=0.1)
        C1 = completion.ChainedCompleter([A1, A2])
        comp_lookup.RegisterName('slowc', C1)

    return main_loop.Interactive(opts, ex, c_parser, arena)

  # TODO: Remove this after removing it from benchmarks/osh-runtime.  It's no
  # longer relevant with main_loop.
  if opts.parser_mem_dump:
    # This might be superstition, but we want to let the value stabilize
    # after parsing.  bash -c 'cat /proc/$$/status' gives different results
    # with a sleep.
    time.sleep(0.001)
    input_path = '/proc/%d/status' % posix.getpid()
    with open(input_path) as f, open(opts.parser_mem_dump, 'w') as f2:
      contents = f.read()
      f2.write(contents)
      log('Wrote %s to %s (--parser-mem-dump)', input_path,
          opts.parser_mem_dump)

  nodes_out = [] if exec_opts.noexec else None

  _tlog('Execute(node)')
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
    input_path = '/proc/%d/status' % posix.getpid()
    with open(input_path) as f, open(opts.runtime_mem_dump, 'w') as f2:
      contents = f.read()
      f2.write(contents)
      log('Wrote %s to %s (--runtime-mem-dump)', input_path,
          opts.runtime_mem_dump)

  # NOTE: We haven't closed the file opened with fd_state.Open
  return status


# TODO: Does oil have the same -o syntax?  I probably want something else.

OIL_SPEC = args.FlagsAndOptions()
# TODO: -h too
OIL_SPEC.LongFlag('--help')
OIL_SPEC.LongFlag('--version')
#builtin.AddOptionsToArgSpec(OIL_SPEC)


def OilMain(argv):
  arg_r = args.Reader(argv)
  try:
    opts = OIL_SPEC.Parse(arg_r)
  except args.UsageError as e:
    ui.usage('oil usage error: %s', e)
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
      util.error("Couldn't open %r: %s", script_name, posix.strerror(e.errno))
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

  b = os_path.basename(argv[0])
  main_name, ext = os_path.splitext(b)
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


# Called from Python-2.7.13/Modules/main.c.
def _cpython_main_hook():
  main(sys.argv)


if __name__ == '__main__':
  # NOTE: This could end up as opy.InferTypes(), opy.GenerateCode(), etc.
  if posix.environ.get('CALLGRAPH') == '1':
    from opy import callgraph
    callgraph.Walk(main, sys.modules)
  else:
    main(sys.argv)
