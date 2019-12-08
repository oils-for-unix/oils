#!/usr/bin/env python2
"""
osh_parse.py
"""
from __future__ import print_function

import sys

from _devbuild.gen.syntax_asdl import source, source_t, command, command_t
from asdl import format as fmt
from core import alloc
from core import error
#from core import main_loop
from core import meta
from core import pyutil
from core.util import log
from core import ui
from frontend import parse_lib
from frontend import reader
from mycpp import mylib

_ = log

from typing import List, Dict, TYPE_CHECKING
if TYPE_CHECKING:
  from osh.cmd_parse import CommandParser
  from pgen2.grammar import Grammar


# TEMP: Copied from core/main_loop.py
def ParseWholeFile(c_parser):
  # type: (CommandParser) -> command_t
  """Parse an entire shell script.

  This uses the same logic as Batch().
  """
  children = []  # type: List[command_t]
  while True:
    node = c_parser.ParseLogicalLine()  # can raise ParseError
    if node is None:  # EOF
      c_parser.CheckForPendingHereDocs()  # can raise ParseError
      break
    children.append(node)

  if len(children) == 1:
    return children[0]
  else:
    return command.CommandList(children)


def main(argv):
  # type: (List[str]) -> int
  arena = alloc.Arena()

  parse_opts = parse_lib.OilParseOptions()
  # Dummy value; not respecting aliases!
  aliases = {}  # type: Dict[str, str]
  # parse `` and a[x+1]=bar differently

  oil_grammar = None  # type: Grammar
  if mylib.PYTHON:
    loader = pyutil.GetResourceLoader()
    oil_grammar = meta.LoadOilGrammar(loader)

  parse_ctx = parse_lib.ParseContext(arena, parse_opts, aliases, oil_grammar)

  pretty_print = True

  if len(argv) == 1:
    line_reader = reader.FileLineReader(mylib.Stdin(), arena)
    src = source.Stdin('')  # type: source_t

  elif len(argv) == 2:
    path = argv[1]
    f = mylib.open(path)
    line_reader = reader.FileLineReader(f, arena)
    src = source.MainFile(path)

  elif len(argv) == 3:
    if argv[1] == '-c':
      # This path is easier to run through GDB
      line_reader = reader.StringLineReader(argv[2], arena)
      src = source.CFlag()

    elif argv[1] == '-n':  # For benchmarking, allow osh_parse -n file.txt
      path = argv[2]
      f = mylib.open(path)
      line_reader = reader.FileLineReader(f, arena)
      src = source.MainFile(path)
      # This is like --ast-format none, which benchmarks/osh-helper.sh passes.
      pretty_print = False

    else:
      raise AssertionError()

  else:
    raise AssertionError()

  arena.PushSource(src)

  c_parser = parse_ctx.MakeOshParser(line_reader)

  try:
    #node = main_loop.ParseWholeFile(c_parser)
    node = ParseWholeFile(c_parser)
  except error.Parse as e:
    ui.PrettyPrintError(e, arena)
    return 2
  assert node is not None

  # C++ doesn't have the abbreviations yet (though there are some differences
  # like omitting spids)
  #tree = node.AbbreviatedTree()
  if pretty_print:
    tree = node.PrettyTree()

    ast_f = fmt.DetectConsoleOutput(mylib.Stdout())
    fmt.PrintTree(tree, ast_f)
    ast_f.write('\n')

  return 0


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
