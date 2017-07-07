#!/usr/bin/python
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
import time
start_time = time.time()

# Uncomment this to see startup time problems.
if os.environ.get('OIL_TIMING'):
  def tlog(msg):
    print('%.3f' % ((time.time() - start_time) * 1000), msg)
else:
  def tlog(msg):
    pass

tlog('before imports')

import errno
import re
import sys
import traceback  # for debugging

# TODO: Set PYTHONPATH from outside?
this_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(os.path.join(this_dir, '..'))

# Set in Modules/main.c.
HAVE_READLINE = os.getenv('_HAVE_READLINE') != ''

from asdl import format as fmt
from asdl import encode

from osh import word_parse  # for tracing
from osh import cmd_parse  # for tracing

from osh import ast_ as ast
from osh import parse_lib

from core import alloc
from core import args
from core import builtin
from core import cmd_exec
from core.id_kind import Id
from core import lexer  # for tracing
from core import reader
from core import state
from core import word
from core import word_eval
from core import ui
from core import util

if HAVE_READLINE:
  from core import completion
else:
  completion = None

from tools import osh2oil

log = util.log

tlog('after imports')

class UsageError(RuntimeError):
  """ Exception for incorrect command line usage. """


def InteractiveLoop(opts, ex, c_parser, w_parser, line_reader):
  # Is this correct?  Are there any non-ANSI terminals?  I guess you can pass
  # -i but redirect stdout.
  if opts.ast_output == '-':
    ast_f = fmt.DetectConsoleOutput(sys.stdout)
  elif opts.ast_output == '-':
    f = open(opts.ast_output, 'w')  # implicitly closed when the process ends
    ast_f = fmt.DetectConsoleOutput(f)
  else:
    ast_f = None

  while True:
    try:
      w = c_parser.Peek()
    except KeyboardInterrupt:
      print('Ctrl-C')
      break

    if w is None:
      raise RuntimeError('Failed parse: %s' % c_parser.Error())
    c_id = word.CommandId(w)
    if c_id == Id.Op_Newline:
      print('nothing to execute')
    elif c_id == Id.Eof_Real:
      print('EOF')
      break
    else:
      node = c_parser.ParseCommandLine()

      # TODO: Need an error for an empty command, which we ignore?  GetLine
      # could do that in the first position?
      # ParseSimpleCommand fails with '\n' token?
      if not node:
        # TODO: PrintError here
        raise RuntimeError('failed parse: %s' % c_parser.Error())

      if ast_f:
        ast.PrettyPrint(node)

      status = ex.Execute(node)

      if opts.print_status:
        print('STATUS', repr(status))

    # Reset prompt and clear memory.  TODO: If there are any function
    # definitions ANYWHERE in the node, you should not clear the underlying
    # memory.  We still need to execute those strings!
    line_reader.Reset()

    # Reset internal newline state.
    # NOTE: It would actually be correct to reinitialize all objects (except
    # Env) on every iteration.  But we know that the w_parser is the only thing
    # that needs to be reset, for now.
    w_parser.Reset()
    c_parser.Reset()


# bash --noprofile --norc uses 'bash-4.3$ '
OSH_PS1 = 'osh$ '


def OshMain(argv):
  spec = args.FlagsAndOptions()
  spec.ShortFlag('-c', args.Str, quit_parsing_flags=True)  # command string
  spec.ShortFlag('-i')  # interactive

  spec.LongFlag('--help')
  spec.LongFlag('--ast-output', args.Str)
  spec.LongFlag('--ast-format', ['text', 'abbrev-text', 'html', 'abbrev-html', 'oheap'])
  spec.LongFlag('--fix')
  spec.LongFlag('--debug-spans')
  spec.LongFlag('--print-status')
  spec.LongFlag('--trace', ['cmd-parse', 'word-parse', 'lexer'])  # NOTE: can only trace one now
  spec.LongFlag('--hijack-shebang')

  builtin.AddOptionsToArgSpec(spec)

  try:
    opts, opt_index = spec.Parse(argv)
  except args.UsageError as e:
    util.usage(str(e))
    return 2

  if opts.help:
    print('TODO: HELP')
    return 0

  trace_state = util.TraceState()
  if 'cmd-parse' == opts.trace:
    util.WrapMethods(cmd_parse.CommandParser, trace_state)
  if 'word-parse' == opts.trace:
    util.WrapMethods(word_parse.WordParser, trace_state)
  if 'lexer' == opts.trace:
    util.WrapMethods(lexer.Lexer, trace_state)

  if opt_index == len(argv):
    dollar0 = sys.argv[0]  # e.g. bin/osh
  else:
    dollar0 = argv[opt_index]  # the script name, or the arg after -c

  # TODO: Create a --parse action or 'osh parse' or 'oil osh-parse'
  # osh-fix
  # It uses a different memory-management model.  It's a batch program and not
  # an interactive program.

  pool = alloc.Pool()
  arena = pool.NewArena()

  # TODO: Maybe wrap this initialization sequence up in an oil_State, like
  # lua_State.
  status_lines = ui.MakeStatusLines()
  mem = state.Mem(dollar0, argv[opt_index + 1:], os.environ)
  builtins = builtin.Builtins()
  funcs = {}

  # Passed to Executor for 'complete', and passed to completion.Init
  if completion:
    comp_lookup = completion.CompletionLookup()
  else:
    # TODO: NullLookup?
    comp_lookup = None
  exec_opts = state.ExecOpts()
  builtin.SetExecOpts(exec_opts, opts.opt_changes)

  # TODO: How to get a handle to initialized builtins here?
  # tokens.py has it.  I think you just make a separate table, with
  # metaprogramming.
  ex = cmd_exec.Executor(
      mem, status_lines, funcs, completion, comp_lookup, exec_opts,
      parse_lib.MakeParserForExecutor, arena)

  # NOTE: The rc file can contain both commands and functions... ideally we
  # would only want to save nodes/lines for the functions.
  try:
    rc_path = 'oilrc'
    with open(rc_path) as f:
      contents = f.read()
    arena.AddSourcePath(rc_path)
    #print(repr(contents))

    rc_line_reader = reader.StringLineReader(contents, arena=arena)
    _, rc_c_parser = parse_lib.MakeParserForTop(rc_line_reader)
    rc_node = rc_c_parser.ParseWholeFile()
    if not rc_node:
      # TODO: Error should return a token, and then the token should have a
      # arena index, and then look that up in the arena.
      err = rc_c_parser.Error()
      ui.PrintErrorStack(err, arena, sys.stderr)
      return 2  # parse error is code 2

    status = ex.Execute(rc_node)
    #print('oilrc:', status, cflow, file=sys.stderr)
    # Ignore bad status?
  except IOError as e:
    if e.errno != errno.ENOENT:
      raise

  if opts.c is not None:
    arena.AddSourcePath('<command string>')
    line_reader = reader.StringLineReader(opts.c, arena=arena)
    interactive = False
  elif opts.i:  # force interactive
    arena.AddSourcePath('<stdin -i>')
    line_reader = reader.InteractiveLineReader(OSH_PS1, arena=arena)
    interactive = True
  else:
    try:
      script_name = argv[opt_index]
    except IndexError:
      if sys.stdin.isatty():
        arena.AddSourcePath('<interactive>')
        line_reader = reader.InteractiveLineReader(OSH_PS1, arena=arena)
        interactive = True
      else:
        arena.AddSourcePath('<stdin>')
        line_reader = reader.StringLineReader(sys.stdin.read(), arena=arena)
        interactive = False
    else:
      arena.AddSourcePath(script_name)
      with open(script_name) as f:
        line_reader = reader.StringLineReader(f.read(), arena=arena)
      interactive = False

  # TODO: assert arena.NumSourcePaths() == 1
  # TODO: .rc file needs its own arena.
  w_parser, c_parser = parse_lib.MakeParserForTop(line_reader, arena=arena)

  if interactive:
    # NOTE: We're using a different evaluator here.  The completion system can
    # also run functions... it gets the Executor through Executor._Complete.
    if HAVE_READLINE:
      ev = word_eval.CompletionWordEvaluator(mem, exec_opts)
      completion.Init(builtins, mem, funcs, comp_lookup, status_lines, ev)

    # TODO: Could instantiate "printer" instead of showing ops
    InteractiveLoop(opts, ex, c_parser, w_parser, line_reader)
    status = 0  # TODO: set code
  else:
    # Parse the whole thing up front
    #print('Parsing file')

    tlog('ParseWholeFile')
    # TODO: Do I need ParseAndEvalLoop?  How is it different than
    # InteractiveLoop?
    try:
      node = c_parser.ParseWholeFile()
    except util.ParseError as e:
      ui.PrettyPrintError(e, arena, sys.stderr)
      print('parse error: %s' % e.UserErrorString(), file=sys.stderr)
      return 2
    else:
      # TODO: Remove this older form of error handling.
      if not node:
        err = c_parser.Error()
        ui.PrintErrorStack(err, arena, sys.stderr)
        return 2  # parse error is code 2

    if opts.ast_output:

      if opts.ast_format == 'oheap':
        if opts.ast_output == '-':
          if sys.stdout.isatty():
            raise RuntimeError('ERROR: Not dumping binary data to a TTY.')
          f = sys.stdout
        else:
          f = open(opts.ast_output, 'wb')  # implicitly closed

        enc = encode.Params()
        out = encode.BinOutput(f)
        encode.EncodeRoot(node, enc, out)

      else:  # text output
        if opts.ast_output == '-':
          f = sys.stdout
        else:
          f = open(opts.ast_output, 'w')  # implicitly closed

        if opts.ast_format in ('text', 'abbrev-text'):
          ast_f = fmt.DetectConsoleOutput(f)
        elif opts.ast_format in ('html', 'abbrev-html'):
          ast_f = fmt.HtmlOutput(f)
        else:
          raise AssertionError
        abbrev_hook = (
            ast.AbbreviateNodes if 'abbrev-' in opts.ast_format else None)
        tree = fmt.MakeTree(node, abbrev_hook=abbrev_hook)
        ast_f.FileHeader()
        fmt.PrintTree(tree, ast_f)
        ast_f.FileFooter()
        ast_f.write('\n')

    if exec_opts.noexec:
      util.log("Execution skipped because 'noexec' is on ")
      status = 0
    else:
      tlog('Execute(node)')
      status = ex.Execute(node)

  if opts.fix:
    osh2oil.PrintAsOil(arena, node, opts.debug_spans)
  return status


def WokMain(main_argv):
  raise NotImplementedError('wok')


def BoilMain(main_argv):
  raise NotImplementedError('boil')


_OIL_USAGE = 'Usage: oil MAIN [OPTION]... [ARG]...'


def OilMain(argv):
  b = os.path.basename(argv[0])
  main_name, _ = os.path.splitext(b)

  if main_name in ('oil', 'oil_main'):
    try:
      first_arg = argv[1]
    except IndexError:
      raise UsageError('Missing name of main()')

    if first_arg in ('-h', '--help'):
      print(_OIL_USAGE, file=sys.stderr)
      sys.exit(0)

    main_name = first_arg
    main_argv = argv[2:]
  else:
    main_argv = argv[1:]

  if main_name in ('osh', 'sh'):
    status = OshMain(main_argv)
    tlog('done osh main')
    return status
  elif main_name == 'wok':
    return WokMain(main_argv)
  elif main_name == 'boil':
    return BoilMain(main_argv)
  elif main_name == 'true':
    return 0
  elif main_name == 'false':
    return 1
  else:
    raise UsageError('Invalid main %r' % main_name)


def main(argv):
  try:
    sys.exit(OilMain(argv))
  except NotImplementedError as e:
    raise
  except UsageError as e:
    print(_OIL_USAGE, file=sys.stderr)
    print(str(e), file=sys.stderr)
    sys.exit(2)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
  main(sys.argv)
