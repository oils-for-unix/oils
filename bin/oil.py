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

import atexit
import errno

from asdl import runtime

from core import alloc
from core import dev
from core import completion
from core import main_loop
from core import process
from core import ui
from core import util
from core.meta import runtime_asdl

from osh import builtin
from osh import builtin_comp
from osh import cmd_exec
from osh import expr_eval
from osh import split
from osh import state
from osh import word_eval

from frontend import args
from frontend import reader
from frontend import parse_lib

from pylib import os_path

from oil_lang import cmd_exec as oil_cmd_exec

from tools import deps
from tools import osh2oil
from tools import readlink

value_e = runtime_asdl.value_e
builtin_e = runtime_asdl.builtin_e

# Set in Modules/main.c.
HAVE_READLINE = posix.environ.get('_HAVE_READLINE') != ''
if HAVE_READLINE:
  import readline
else:
  readline = None

log = util.log

_tlog('after imports')


def DefineCommonFlags(spec):
  """Common flags between OSH and Oil."""
  spec.ShortFlag('-c', args.Str, quit_parsing_flags=True)  # command string
  spec.LongFlag('--help')
  spec.LongFlag('--version')


OSH_SPEC = args.FlagsAndOptions()

DefineCommonFlags(OSH_SPEC)

OSH_SPEC.ShortFlag('-i')  # interactive

# TODO: -h too
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

# This flag has is named like bash's equivalent.  We got rid of --norc because
# it can simply by --rcfile /dev/null.
OSH_SPEC.LongFlag('--rcfile', args.Str)

builtin.AddOptionsToArgSpec(OSH_SPEC)


def _InitDefaultCompletions(ex, complete_builtin, comp_lookup):
  # register builtins and words
  complete_builtin(['-E', '-A', 'command'])
  # register path completion
  # Add -o filenames?  Or should that be automatic?
  complete_builtin(['-D', '-A', 'file'])

  # TODO: Move this into demo/slow-completion.sh
  if 1:
    # Something for fun, to show off.  Also: test that you don't repeatedly hit
    # the file system / network / coprocess.
    A1 = completion.TestAction(['foo.py', 'foo', 'bar.py'])
    A2 = completion.TestAction(['m%d' % i for i in xrange(5)], delay=0.1)
    C1 = completion.UserSpec([A1, A2], [], [], lambda candidate: True)
    comp_lookup.RegisterName('slowc', completion.Options([]), C1)


def _MaybeWriteHistoryFile(history_filename):
  if not readline:
    return
  try:
    readline.write_history_file(history_filename)
  except IOError:
    pass


def _InitReadline(readline_mod, history_filename, root_comp, debug_f):
  assert readline_mod

  try:
    readline_mod.read_history_file(history_filename)
  except IOError:
    pass

  # The 'atexit' module is a small wrapper around sys.exitfunc.
  atexit.register(_MaybeWriteHistoryFile, history_filename)
  readline_mod.parse_and_bind("tab: complete")

  # How does this map to C?
  # https://cnswww.cns.cwru.edu/php/chet/readline/readline.html#SEC45

  complete_cb = completion.ReadlineCallback(readline_mod, root_comp, debug_f)
  readline_mod.set_completer(complete_cb)

  # http://web.mit.edu/gnu/doc/html/rlman_2.html#SEC39
  # "The basic list of characters that signal a break between words for the
  # completer routine. The default value of this variable is the characters
  # which break words for completion in Bash, i.e., " \t\n\"\\'`@$><=;|&{(""

  # This determines the boundaries you get back from get_begidx() and
  # get_endidx() at completion time!
  # We could be more conservative and set it to ' ', but then cases like
  # 'ls|w<TAB>' would try to complete the whole thing, intead of just 'w'.
  #
  # Note that this should not affect the OSH completion algorithm.  It only
  # affects what we pass back to readline and what readline displays to the
  # user!
  readline_mod.set_completer_delims(util.READLINE_DELIMS)
  # TODO: Disable READLINE_DELIMS because it causes problems with quoting.
  #readline_mod.set_completer_delims('')


def _ShowVersion():
  util.ShowAppVersion('Oil')


def SourceStartupFile(rc_path, lang, parse_ctx, ex):
  # Right now this is called when the shell is interactive.  (Maybe it should
  # be called on login_shel too.)
  #
  # Terms:
  # - interactive shell: Roughly speaking, no args or -c, and isatty() is true
  #   for stdin and stdout.
  # - login shell: Started from the top level, e.g. from init or ssh.
  #
  # We're not going to copy everything bash does because it's too complex, but
  # for reference:
  # https://www.gnu.org/software/bash/manual/bash.html#Bash-Startup-Files
  # Bash also has --login.

  arena = parse_ctx.arena
  try:
    arena.PushSource(rc_path)
    with open(rc_path) as f:
      rc_line_reader = reader.FileLineReader(f, arena)
      if lang == 'osh':
        rc_c_parser = parse_ctx.MakeOshParser(rc_line_reader)
      else:
        rc_c_parser = parse_ctx.MakeOilParser(rc_line_reader)
      try:
        status = main_loop.Batch(ex, rc_c_parser, arena)
      finally:
        arena.PopSource()
  except IOError as e:
    if e.errno != errno.ENOENT:
      raise


def ShellMain(lang, argv0, argv, login_shell):
  """Used by bin/osh and bin/oil.

  Args:
    lang: 'osh' or 'oil'
    argv0, argv: So we can also invoke bin/osh as 'oil.ovm osh'.  Like busybox.
    login_shell: Was - on the front?
  """
  # Differences between osh and oil:
  # - --help?  I guess Oil has a SUPERSET of OSH options.
  # - oshrc vs oilrc
  # - the parser and executor
  # - Change the prompt in the interactive shell?

  assert lang in ('osh', 'oil'), lang

  arg_r = args.Reader(argv)
  try:
    opts = OSH_SPEC.Parse(arg_r)
  except args.UsageError as e:
    ui.usage('osh usage error: %s', e)
    return 2

  if opts.help:
    loader = util.GetResourceLoader()
    builtin.Help(['%s-usage' % lang], loader)
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

  fd_state = process.FdState()
  exec_opts = state.ExecOpts(mem, readline)
  builtin.SetExecOpts(exec_opts, opts.opt_changes)
  aliases = {}  # feedback between runtime and parser

  parse_ctx = parse_lib.ParseContext(arena, aliases)  # For main_loop

  # Three ParseContext instances SHARE aliases.  TODO: Complete aliases.
  comp_arena = pool.NewArena()
  comp_arena.PushSource('<completion>')
  trail1 = parse_lib.Trail()
  comp_ctx = parse_lib.ParseContext(comp_arena, aliases, trail=trail1)

  hist_arena = pool.NewArena()
  hist_arena.PushSource('<history>')
  trail2 = parse_lib.Trail()
  hist_ctx = parse_lib.ParseContext(hist_arena, aliases, trail=trail2)

  # Deps helps manages dependencies.  These dependencies are circular:
  # - ex and word_ev, arith_ev -- for command sub, arith sub
  # - arith_ev and word_ev -- for $(( ${a} )) and $x$(( 1 )) 
  # - ex and builtins (which execute code, like eval)
  # - prompt_ev needs word_ev for $PS1, which needs prompt_ev for @P
  exec_deps = cmd_exec.Deps()

  if opts.debug_file:
    debug_f = util.DebugFile(fd_state.Open(opts.debug_file, mode='w'))
  else:
    debug_f = util.NullDebugFile()
  exec_deps.debug_f = debug_f

  debug_f.log('Debug file is %s', opts.debug_file)

  splitter = split.SplitContext(mem)
  exec_deps.splitter = splitter

  # Controlled by env variable, flag, or hook?
  exec_deps.dumper = dev.CrashDumper(posix.environ.get('OSH_CRASH_DUMP_DIR', ''))

  if opts.xtrace_to_debug_file:
    trace_f = debug_f
  else:
    trace_f = util.DebugFile(sys.stderr)
  exec_deps.trace_f = trace_f

  # TODO: Separate comp_state and comp_lookup.
  comp_state = completion.State()
  comp_lookup = completion.Lookup()

  builtins = {  # Lookup
      builtin_e.HISTORY: builtin.History(readline),

      builtin_e.COMPOPT: builtin_comp.CompOpt(comp_state),
      builtin_e.COMPADJUST: builtin_comp.CompAdjust(mem),
  }
  ex = cmd_exec.Executor(mem, fd_state, funcs, builtins, exec_opts,
                         parse_ctx, exec_deps)
  exec_deps.ex = ex

  word_ev = word_eval.NormalWordEvaluator(mem, exec_opts, exec_deps, arena)
  exec_deps.word_ev = word_ev

  arith_ev = expr_eval.ArithEvaluator(mem, exec_opts, word_ev, arena)
  exec_deps.arith_ev = arith_ev
  word_ev.arith_ev = arith_ev  # Another circular dependency

  bool_ev = expr_eval.BoolEvaluator(mem, exec_opts, word_ev, arena)
  exec_deps.bool_ev = bool_ev

  tracer = cmd_exec.Tracer(parse_ctx, exec_opts, mem, word_ev, trace_f)
  exec_deps.tracer = tracer

  # HACK for circular deps
  ex.word_ev = word_ev
  ex.arith_ev = arith_ev
  ex.bool_ev = bool_ev
  ex.tracer = tracer

  spec_builder = builtin_comp.SpecBuilder(ex, parse_ctx, word_ev, splitter)
  # Add some builtins that depend on the executor!
  complete_builtin = builtin_comp.Complete(spec_builder, comp_lookup)  # used later
  builtins[builtin_e.COMPLETE] = complete_builtin
  builtins[builtin_e.COMPGEN] = builtin_comp.CompGen(spec_builder)

  if lang == 'oil':
    # The Oil executor wraps an OSH executor?  It needs to be able to source
    # it.
    ex = oil_cmd_exec.OilExecutor(ex)

  # PromptEvaluator rendering is needed in non-interactive shells for @P.
  prompt_ev = ui.PromptEvaluator(lang, arena, parse_ctx, ex, mem)
  exec_deps.prompt_ev = prompt_ev
  word_ev.prompt_ev = prompt_ev  # HACK for circular deps

  # History evaluation is a no-op if readline is None.
  hist_ev = reader.HistoryEvaluator(readline, hist_ctx, debug_f)

  # Calculate ~/.config/oil/oshrc or oilrc
  # Use ~/.config/oil to avoid cluttering the user's home directory.  Some
  # users may want to ln -s ~/.config/oil/oshrc ~/oshrc or ~/.oshrc.

  # https://unix.stackexchange.com/questions/24347/why-do-some-applications-use-config-appname-for-their-config-data-while-other
  home_dir = mem.GetVar('HOME')
  assert home_dir.tag == value_e.Str, home_dir
  rc_path = opts.rcfile or os_path.join(home_dir.s, '.config/oil', lang + 'rc')

  history_filename = os_path.join(home_dir.s, '.config/oil', 'history_' + lang)

  if opts.c is not None:
    arena.PushSource('<command string>')
    line_reader = reader.StringLineReader(opts.c, arena)
    if opts.i:  # -c and -i can be combined
      exec_opts.interactive = True

  elif opts.i:  # force interactive
    arena.PushSource('<stdin -i>')
    # interactive shell only
    line_reader = reader.InteractiveLineReader(arena, prompt_ev, hist_ev)
    exec_opts.interactive = True

  else:
    try:
      script_name = arg_r.Peek()
    except IndexError:
      if sys.stdin.isatty():
        arena.PushSource('<interactive>')
        # interactive shell only
        line_reader = reader.InteractiveLineReader(arena, prompt_ev, hist_ev)
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

  # Do we also need to call this for a login_shell?  Or are those always
  # interactive?
  if exec_opts.interactive:
    SourceStartupFile(rc_path, lang, parse_ctx, ex)

  # TODO: assert arena.NumSourcePaths() == 1
  # TODO: .rc file needs its own arena.
  if lang == 'osh':
    c_parser = parse_ctx.MakeOshParser(line_reader)
  else:
    c_parser = parse_ctx.MakeOilParser(line_reader)

  if exec_opts.interactive:
    # NOTE: We're using a different evaluator here.  The completion system can
    # also run functions... it gets the Executor through Executor._Complete.
    if readline:
      ev = word_eval.CompletionWordEvaluator(mem, exec_opts, exec_deps, arena)
      progress_f = ui.StatusLine()
      root_comp = completion.RootCompleter(ev, mem, comp_lookup, comp_state,
                                           comp_ctx, progress_f, debug_f)
      _InitReadline(readline, history_filename, root_comp, debug_f)
      _InitDefaultCompletions(ex, complete_builtin, comp_lookup)

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

  # Only print nodes if the whole parse succeeded.
  if nodes_out is not None and status == 0:
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

  # NOTE: This doesn't cause any spec tests to fail, but it could.
  if posix.environ.get('ASDL_TYPE_CHECK'):
    log('NOTE: Performed %d ASDL_TYPE_CHECKs.', runtime.NUM_TYPE_CHECKS)

  # NOTE: We haven't closed the file opened with fd_state.Open
  return status


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
  c_parser = parse_ctx.MakeOshParser(line_reader)

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
    status = ShellMain('osh', argv0, main_argv, login_shell)
    _tlog('done osh main')
    return status
  elif main_name == 'oshc':
    return OshCommandMain(main_argv)

  elif main_name == 'oil':
    return ShellMain('oil', argv0, main_argv, login_shell)
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
  if posix.environ.get('RESOLVE') == '1':
    from opy import resolve
    resolve.Walk(dict(sys.modules))

  elif posix.environ.get('CALLGRAPH') == '1':
    # NOTE: This could end up as opy.InferTypes(), opy.GenerateCode(), etc.
    from opy import callgraph
    callgraph.Walk(main, sys.modules)
  else:
    main(sys.argv)
