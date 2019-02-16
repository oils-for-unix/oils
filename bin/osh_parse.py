#!/usr/bin/python
"""
osh_parse.py
"""
from __future__ import print_function

import sys

from asdl import format as fmt
from core import alloc
from core import main_loop
from core import ui
from core import util
from frontend import parse_lib
from frontend import reader


def main(argv):
  pool = alloc.Pool()
  arena = pool.NewArena()
  arena.PushSource('<stdin>')

  line_reader = reader.FileLineReader(sys.stdin, arena)
  aliases = {}  # Dummy value; not respecting aliases!
  # parse `` and a[x+1]=bar differently
  parse_ctx = parse_lib.ParseContext(arena, aliases, one_pass_parse=True)
  c_parser = parse_ctx.MakeOshParser(line_reader)

  try:
    node = main_loop.ParseWholeFile(c_parser)
  except util.ParseError as e:
    ui.PrettyPrintError(e, arena)
    return 2
  assert node is not None

  if True:
    tree = node.AbbreviatedTree()
  else:
    tree = node.PrettyTree()

  ast_f = fmt.DetectConsoleOutput(sys.stdout)
  fmt.PrintTree(tree, ast_f)
  ast_f.write('\n')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
