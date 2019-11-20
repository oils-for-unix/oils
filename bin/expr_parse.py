#!/usr/bin/env python2
"""
expr_parse.py -- Demo for translation.

types/run.sh expr-parse
"""
from __future__ import print_function

import sys

from _devbuild.gen import grammar_nt
from _devbuild.gen.syntax_asdl import source
from asdl import format as fmt
from core import alloc
from core import error
from core import meta
from core import pyutil
from core import ui
from frontend import reader
from frontend import lexer
from oil_lang import expr_parse
from oil_lang import expr_to_ast

from typing import List


def main(argv):
  # type: (List[str]) -> int
  arena = alloc.Arena()
  arena.PushSource(source.Stdin(''))

  loader = pyutil.GetResourceLoader()
  oil_grammar = meta.LoadOilGrammar(loader)

  parse_ctx = None
  e_parser = expr_parse.ExprParser(parse_ctx, oil_grammar)

  line_lexer = lexer.LineLexer('', arena)
  line_reader = reader.FileLineReader(sys.stdin, arena)
  lex = lexer.Lexer(line_lexer, line_reader)

  try:
    pnode, _ = e_parser.Parse(lex, grammar_nt.command_expr)
  except error.Parse as e:
    ui.PrettyPrintError(e, arena)
    return 2

  #print(pnode)
  tr = expr_to_ast.Transformer(oil_grammar)
  node = tr.Expr(pnode)

  assert node is not None

  tree = node.AbbreviatedTree()
  #tree = node.PrettyTree()

  ast_f = fmt.DetectConsoleOutput(sys.stdout)
  fmt.PrintTree(tree, ast_f)
  ast_f.write('\n')

  return 0


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
