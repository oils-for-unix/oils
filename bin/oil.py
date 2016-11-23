#!/usr/bin/env python3
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

import errno
import optparse
import os
import re
import sys
import traceback  # for debugging

# TODO: Set PTYHONPATH from outside?
this_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(os.path.join(this_dir, '..'))

from osh import word_parse  # for tracing
from osh import cmd_parse  # for tracing
from osh import parse_lib

from core import lexer  # for tracing

from core import builtin
from core import completion
from core import cmd_exec
from core.pool import Pool
from core import reader
from core.tokens import Id
from core import word_eval
from core import ui
from core import util


class UsageError(RuntimeError):
  """ Exception for incorrect command line usage. """


def TestLexer(lexer):
  from word_parse import Id, LexMode
  while True:
    t = lexer.Peek()
    print(t)
    if t.type == Id.Eof_Real:
      break
    lexer.Next(LexMode.OUTER)


def TestWordParser(w_parser):
  from word_parse import WordKind
  while True:
    w = w_parser.Peek()  # This calls lexer.ReadOuter, which callls GetLine?
    print('word', w)
    #if w.Kind() == WordKind.NEWLINE:
    if w.Kind() == WordKind.Eof:
      break
    print('next')
    w_parser.Next()


def InteractiveLoop(opts, ex, c_parser, w_parser, line_reader):
  while True:
    try:
      w = c_parser.Peek()
    except KeyboardInterrupt:
      print('Ctrl-C')
      break

    if w is None:
      raise RuntimeError('Failed parse: %s' % c_parser.Error())
    c_id = w.CommandId()
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
        raise RuntimeError('failed parse: %s' % c_parser.Error())

      if opts.print_ast:
        node.PrintTree(sys.stdout)
        sys.stdout.write('\n\n')
        sys.stdout.flush()

      status, cflow = ex.ExecuteTop(node)

      if opts.print_status:
        print('STATUS', repr(status), cflow)

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


def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser()

  p.add_option(
      '-c', dest='command', default='',
      help='Shell command to run')
  p.add_option(
      '-i', dest='interactive', default=False, action='store_true',
      help="Force the shell to run interactively (don't test for stdin TTY)")

  # TODO:
  # - Make this --print=ast,status
  # - And maybe --dump=tokens,words,nodes ?
  p.add_option(
      '--print-ast', dest='print_ast', action='store_true', default=False,
      help='Print AST before execution')
  p.add_option(
      '--print-status', dest='print_status', action='store_true',
      default=False,
      help='Print command status after execution')
  p.add_option(
      '--trace', dest='trace', action='append', default=[],
      help='Method calls to trace: lexer|wp|cp')
  p.add_option(
      '--no-exec', dest='do_exec', action='store_false', default=True,
      help="Don't execute anything (useful with --print-ast)")

  # TODO:
  # --dump / --debug outputs:
  #   1. tokens themselves, with char ranges
  #   2. words, with token ranges
  #   3. nodes, with word ranges

  # maybe need --trace too
  return p


def OshMain(argv):
  (opts, argv) = Options().parse_args(argv)

  state = util.TraceState()
  if 'cp' in opts.trace:
    util.WrapMethods(cmd_parse.CommandParser, state)
  if 'wp' in opts.trace:
    util.WrapMethods(word_parse.WordParser, state)
  if 'lexer' in opts.trace:
    util.WrapMethods(lexer.Lexer, state)

  if len(argv) >= 2:
    dollar0 = argv[0]
  else:
    dollar0 = ''

  pool = Pool()  # for lines, nodes, etc.

  # TODO: Maybe wrap this initialization sequence up in an oil_State, like
  # lua_State.
  status_lines = ui.MakeStatusLines()
  mem = cmd_exec.Mem(dollar0, argv[1:])
  builtins = builtin.Builtins(status_lines[0])
  funcs = {}

  # Passed to Executor for 'complete', and passed to completion.Init
  comp_lookup = completion.CompletionLookup()
  exec_opts = cmd_exec.ExecOpts()

  # TODO: How to get a handle to initialized builtins here?
  # tokens.py has it.  I think you just make a separate table, with
  # metaprogramming.
  ex = cmd_exec.Executor(
      mem, builtins, funcs, comp_lookup, exec_opts,
      parse_lib.MakeParserForExecutor)

  # NOTE: The rc file can contain both commands and functions... ideally we
  # would only want to save nodes/lines for the functions.
  try:
    rc_path = 'oilrc'
    with open(rc_path) as f:
      contents = f.read()
    pool.AddSourcePath(rc_path)
    #print(repr(contents))

    rc_line_reader = reader.StringLineReader(contents, pool=pool)
    _, rc_c_parser = parse_lib.MakeParserForTop(rc_line_reader)
    rc_node = rc_c_parser.ParseFile()
    if not rc_node:
      # TODO: Error should return a token, and then the token should have a
      # pool index, and then look that up in the pool.
      err = rc_c_parser.Error()
      ui.PrintError(err, pool, sys.stderr)
      return 2  # parse error is code 2

    status, cflow = ex.Execute(rc_node)
    #print('oilrc:', status, cflow, file=sys.stderr)
    # Ignore bad status?  What about cflow?
  except IOError as e:
    if e.errno != errno.ENOENT:
      raise

  if opts.command:
    pool.AddSourcePath('<-c arg>')
    line_reader = reader.StringLineReader(opts.command, pool=pool)
    interactive = False
  elif opts.interactive:  # force interactive
    pool.AddSourcePath('<stdin -i>')
    line_reader = reader.InteractiveLineReader(pool=pool)
    interactive = True
  else:
    try:
      script_name = argv[0]
    except IndexError:
      if sys.stdin.isatty():
        pool.AddSourcePath('<interactive>')
        line_reader = reader.InteractiveLineReader(pool=pool)
        interactive = True
      else:
        pool.AddSourcePath('<stdin>')
        line_reader = reader.StringLineReader(sys.stdin.read(), pool=pool)
        interactive = False
    else:
      pool.AddSourcePath(script_name)
      with open(script_name) as f:
        line_reader = reader.StringLineReader(f.read(), pool=pool)
      interactive = False

  # TODO: assert pool.NumSourcePaths() == 1

  tokens_out = []
  words_out = []
  w_parser, c_parser = parse_lib.MakeParserForTop(line_reader,
      tokens_out=tokens_out, words_out=words_out)

  if interactive:
    # NOTE: We're using a different evaluator here.  The completion system can
    # also run functions... it gets the Executor through Executor._Complete.
    ev = word_eval.CompletionEvaluator(mem, exec_opts)
    completion.Init(builtins, mem, funcs, comp_lookup, status_lines, ev)

    # TODO: Could instantiate "printer" instead of showing ops
    InteractiveLoop(opts, ex, c_parser, w_parser, line_reader)
    status = 0  # TODO: set code
  else:
    # Parse the whole thing up front
    #print('Parsing file')

    # TODO: Do I need ParseAndEvalLoop?  How is it different than
    # InteractiveLoop?
    node = c_parser.ParseFile()
    if not node:
      err = c_parser.Error()
      ui.PrintError(err, pool, sys.stderr)
      return 2  # parse error is code 2

    if opts.print_ast:
      node.PrintTree(sys.stdout)
      sys.stdout.write('\n\n')
      sys.stdout.flush()

    if opts.do_exec:
      status, cflow = ex.Execute(node)
    else:
      util.log('Execution skipped because --no-exec was passed')
      status = 0

  # TODO: Have a mode to just parse
  #print('T', tokens_out)
  #print('W', words_out)

  return status


def WokMain(main_argv):
  raise NotImplementedError('wok')


def BoilMain(main_argv):
  raise NotImplementedError('boil')


def main(argv):
  b = os.path.basename(argv[0])
  main_name, _ = os.path.splitext(b)

  if main_name in ('oil', 'oil_main'):
    try:
      main_name = argv[1]
    except IndexError:
      raise UsageError('Missing name of main()')
    main_argv = argv[2:]
  else:
    main_argv = argv[1:]

  if main_name in ('osh', 'sh'):
    return OshMain(main_argv)
  elif main_name == 'wok':
    return WokMain(main_argv)
  elif main_name == 'boil':
    return BoilMain(main_argv)
  else:
    raise UsageError('Invalid main %r' % main_name)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except NotImplementedError as e:
    raise
  except UsageError as e:
    print('Usage: oil MAIN [OPTION]... [ARG]...', file=sys.stderr)
    print(str(e), file=sys.stderr)
    sys.exit(2)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
