#!/usr/bin/env python2
"""
tools_main.py
"""
from __future__ import print_function

import posix_ as posix

from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.syntax_asdl import source

from core import alloc
from core import error
from core import main_loop
from core import optview
from core import pyutil
from core import state
from core import ui
from frontend import reader
from frontend import parse_lib
from mycpp import mylib
from mycpp.mylib import print_stderr
from tools import deps
from tools import osh2oil

from typing import List, Dict

# TODO: Hook up to completion.
SUBCOMMANDS = [
    'translate', 'arena', 'spans', 'format', 'deps', 'undefined-vars',
    'parse-glob', 'parse-printf',
]

def OshCommandMain(argv):
  # type: (List[str]) -> int
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
    f = mylib.Stdin()
  else:
    try:
      # TODO: fd_state.Open() or something similar
      f = open(script_name)
    except IOError as e:
      print_stderr("oshc: Couldn't open %r: %s" %
                   (script_name, posix.strerror(e.errno)))
      return 2

  # Dummy value; not respecting aliases!
  aliases = {}  # type: Dict[str, str]

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
    if mylib.PYTHON:
      deps.Deps(node)

  elif action == 'undefined-vars':  # could be environment variables
    raise NotImplementedError()

  else:
    raise AssertionError  # Checked above

  return 0


