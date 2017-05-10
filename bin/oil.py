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

import time
start_time = time.time()

# Uncomment this to see startup time problems.
def tlog(msg):
  #print('%.3f' % ((time.time() - start_time) * 1000), msg)
  pass

tlog('before imports')

import errno
import optparse
import os
import re
import sys
import traceback  # for debugging

# TODO: Set PTYHONPATH from outside?
this_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(os.path.join(this_dir, '..'))

from asdl import format as fmt
from asdl import encode

from osh import word_parse  # for tracing
from osh import cmd_parse  # for tracing
from core import lexer  # for tracing

from osh import ast_ as ast
from osh import parse_lib
from osh import fix

from core import builtin
from core import completion
from core import cmd_exec
from core.alloc import Pool
from core import reader
from core.id_kind import Id
from core import word
from core import word_eval
from core import ui
from core import util

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


def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser()

  # NOTE: default command is None because empty string is valid.
  p.add_option(
      '-c', dest='command', default=None,
      help='Shell command to run')
  p.add_option(
      '-i', dest='interactive', default=False, action='store_true',
      help="Force the shell to run interactively (don't test for stdin TTY)")

  # TODO:
  # - Make this --print=ast,status
  # - And maybe --dump=tokens,words,nodes ?
  p.add_option(
      '--ast-output', dest='ast_output', default='',
      help='Print the AST to this file; - for stdout')
  p.add_option(
      '--ast-format', dest='ast_format', default='abbrev-text',
      choices=['text', 'abbrev-text', 'html', 'abbrev-html', 'oheap'],
      help='What format to use for the AST (text or html)')
  p.add_option(
      '--fix', dest='fix', action='store_true',
      default=False,
      help='Fix code')
  p.add_option(
      '--debug-spans', dest='debug_spans', action='store_true',
      help='Print a debug representation of line spans.  '
           'Must use --fix.')
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
  p.add_option(
      '--hijack-shebang', dest='hijack_shebang', action='append',
      metavar='/bin/foo',
      help="Before executing programs, look for this shebang line, and "
           "substitute it with Oil.  For porting.")

  # TODO:
  # --dump / --debug outputs:
  #   1. tokens themselves, with char ranges
  #   2. words, with token ranges
  #   3. nodes, with word ranges

  # maybe need --trace too
  return p


# bash --noprofile --norc uses 'bash-4.3$ '
OSH_PS1 = 'osh$ '


def OshMain(argv):
  (opts, argv) = Options().parse_args(argv)

  state = util.TraceState()
  if 'cp' in opts.trace:
    util.WrapMethods(cmd_parse.CommandParser, state)
  if 'wp' in opts.trace:
    util.WrapMethods(word_parse.WordParser, state)
  if 'lexer' in opts.trace:
    util.WrapMethods(lexer.Lexer, state)

  if len(argv) == 0:
    dollar0 = sys.argv[0]  # e.g. bin/osh
  else:
    dollar0 = argv[0]  # the script name

  # TODO: Create a --parse action or 'osh parse' or 'oil osh-parse'
  # osh-fix
  # It uses a different memory-management model.  It's a batch program and not
  # an interactive program.

  pool = Pool()
  arena = pool.NewArena()

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
    arena.AddSourcePath(rc_path)
    #print(repr(contents))

    rc_line_reader = reader.StringLineReader(contents, arena=arena)
    _, rc_c_parser = parse_lib.MakeParserForTop(rc_line_reader)
    rc_node = rc_c_parser.ParseWholeFile()
    if not rc_node:
      # TODO: Error should return a token, and then the token should have a
      # arena index, and then look that up in the arena.
      err = rc_c_parser.Error()
      ui.PrintError(err, arena, sys.stderr)
      return 2  # parse error is code 2

    status = ex.Execute(rc_node)
    #print('oilrc:', status, cflow, file=sys.stderr)
    # Ignore bad status?
  except IOError as e:
    if e.errno != errno.ENOENT:
      raise

  if opts.command is not None:
    arena.AddSourcePath('<-c arg>')
    line_reader = reader.StringLineReader(opts.command, arena=arena)
    interactive = False
  elif opts.interactive:  # force interactive
    arena.AddSourcePath('<stdin -i>')
    line_reader = reader.InteractiveLineReader(OSH_PS1, arena=arena)
    interactive = True
  else:
    try:
      script_name = argv[0]
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
    ev = word_eval.CompletionWordEvaluator(mem, exec_opts)
    completion.Init(builtins, mem, funcs, comp_lookup, status_lines, ev)

    # TODO: Could instantiate "printer" instead of showing ops
    InteractiveLoop(opts, ex, c_parser, w_parser, line_reader)
    status = 0  # TODO: set code
  else:
    # Parse the whole thing up front
    #print('Parsing file')

    # TODO: Do I need ParseAndEvalLoop?  How is it different than
    # InteractiveLoop?
    node = c_parser.ParseWholeFile()
    if not node:
      err = c_parser.Error()
      ui.PrintError(err, arena, sys.stderr)
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

    if opts.do_exec:
      status = ex.Execute(node)
    else:
      util.log('Execution skipped because --no-exec was passed')
      status = 0

  if opts.fix:
    fix.PrintAsOil(arena, node, opts.debug_spans)
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
