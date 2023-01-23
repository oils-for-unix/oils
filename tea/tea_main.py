#!/usr/bin/env python2
"""
tea_main.py
"""
from __future__ import print_function

import sys

from _devbuild.gen import arg_types
from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.syntax_asdl import source
from frontend import flag_spec
from frontend import parse_lib
from frontend import reader
from core import alloc
from core import error
from core import optview
from core.pyerror import e_usage
from core import pyutil
from core import state
from core import ui
from mycpp import mylib
from mycpp.mylib import print_stderr

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
  try:
    attrs = flag_spec.Parse('tea_main', arg_r)
  except error.Usage as e:
    print_stderr('tea usage error: %s' % e.msg)
    return 2
  arg = arg_types.tea_main(attrs.attrs)

  arena = alloc.Arena()
  errfmt = ui.ErrorFormatter(arena)

  if arg.c is not None:
    arena.PushSource(source.CFlag())
    line_reader = reader.StringLineReader(arg.c, arena)  # type: reader._Reader
  else:
    script_name = arg_r.Peek()
    if script_name is None:
      arena.PushSource(source.Stdin())
      f = mylib.Stdin()  # type: mylib.LineReader
    else:
      arena.PushSource(source.MainFile(script_name))
      try:
        # Hack for type checking.  core/shell.py uses fd_state.Open().
        f = cast('mylib.LineReader', open(script_name))
      except IOError as e:
        print_stderr("tea: Couldn't open %r: %s" %
                     (script_name, posix.strerror(e.errno)))
        return 2
    line_reader = reader.FileLineReader(f, arena)

  # Dummy value; not respecting aliases!
  aliases = {}  # type: Dict[str, str]

  loader = pyutil.GetResourceLoader()
  oil_grammar = pyutil.LoadOilGrammar(loader)

  # Not used in Tea, but OK...
  opt0_array = state.InitOpts()
  no_stack = None  # type: List[bool]  # for mycpp
  opt_stacks = [no_stack] * option_i.ARRAY_SIZE  # type: List[List[bool]]
  parse_opts = optview.Parse(opt0_array, opt_stacks)

  # parse `` and a[x+1]=bar differently
  parse_ctx = parse_lib.ParseContext(arena, parse_opts, aliases, oil_grammar)

  if arg.n:
    try:
      parse_ctx.ParseTeaModule(line_reader)
      status = 0
    except error.Parse as e:
      errfmt.PrettyPrintError(e)
      status = 2
  else:
    e_usage("Tea doesn't run anything yet.  Pass -n to parse.")

  return status
