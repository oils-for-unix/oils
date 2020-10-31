#!/usr/bin/env python2
"""
tea_main.py
"""
from __future__ import print_function

import sys

from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.syntax_asdl import source
from frontend import parse_lib
from frontend import reader
from core import alloc
from core import error
from core import optview
from core import pyutil
from core.pyutil import stderr_line
from core import state
from core import ui
from mycpp import mylib

import posix_ as posix

from typing import List, Dict, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from frontend import args


def Main(arg_r):
  # type: (args.Reader) -> int
  """
  Usage:
    tea myprog.tea                      # Run the script
    tea -c 'func main() { echo "hi" }'  # Run this snippet.  Not common since
                                        # there's no top level statementes!
                                        # Use bin/oil for that.
    tea -n -c 'var x = 1'               # Parse it

    # Compile to C++.  Produce myprog.cc and myprog.h.
    tea --cpp-out myprog myprog.tea lib.tea
  """
  argv = arg_r.Rest()
  arena = alloc.Arena()
  try:
    script_name = argv[0]
    arena.PushSource(source.MainFile(script_name))
  except IndexError:
    arena.PushSource(source.Stdin())
    f = mylib.Stdin()  # type: mylib.LineReader
  else:
    try:
      # Hack for type checking.  core/shell.py uses fd_state.Open().
      f = cast('mylib.LineReader', open(script_name))
    except IOError as e:
      stderr_line("tea: Couldn't open %r: %s", script_name,
                  posix.strerror(e.errno))
      return 2

  # Dummy value; not respecting aliases!
  aliases = {}  # type: Dict[str, str]

  loader = pyutil.GetResourceLoader()
  oil_grammar = pyutil.LoadOilGrammar(loader)

  # Not used in tea, but OK...
  opt0_array = state.InitOpts()
  no_stack = None  # type: List[bool]  # for mycpp
  opt_stacks = [no_stack] * option_i.ARRAY_SIZE  # type: List[List[bool]]
  parse_opts = optview.Parse(opt0_array, opt_stacks)

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
