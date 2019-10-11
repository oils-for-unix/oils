#!/usr/bin/env python2
"""
osh_parse.py
"""
from __future__ import print_function

import sys

from _devbuild.gen.syntax_asdl import source
from asdl import format as fmt
from core import alloc
from core import main_loop
from core import meta
from core import pyutil
from core import ui
from core import util
from frontend import parse_lib
from frontend import reader
from mycpp import mylib

from typing import List, Dict, Any


def main(argv):
  # type: (List[str]) -> int
  arena = alloc.Arena()
  arena.PushSource(source.Stdin(''))

  parse_opts = parse_lib.OilParseOptions()
  # Dummy value; not respecting aliases!
  aliases = {}  # type: Dict[str, Any]
  # parse `` and a[x+1]=bar differently

  loader = pyutil.GetResourceLoader()
  oil_grammar = meta.LoadOilGrammar(loader)

  parse_ctx = parse_lib.ParseContext(arena, parse_opts, aliases, oil_grammar,
                                     one_pass_parse=True)

  line_reader = reader.FileLineReader(mylib.Stdin(), arena)
  c_parser = parse_ctx.MakeOshParser(line_reader)

  try:
    node = main_loop.ParseWholeFile(c_parser)
  except util.ParseError as e:
    ui.PrettyPrintError(e, arena)
    return 2
  assert node is not None

  tree = node.AbbreviatedTree()
  #tree = node.PrettyTree()

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
