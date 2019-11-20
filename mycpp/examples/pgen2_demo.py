#!/usr/bin/env python2
"""
pgen2_demo.py
"""
from __future__ import print_function

import os
import sys

from _devbuild.gen import arith_nt
from _devbuild.gen.syntax_asdl import source__Stdin

from core import alloc
from core import error
from frontend import reader
from frontend import lexer
from oil_lang import expr_parse
from oil_lang import expr_to_ast

from mycpp import mylib
from mycpp.mylib import log

from typing import Dict, Optional, TYPE_CHECKING
if TYPE_CHECKING:
  from pgen2.grammar import Grammar
  from frontend.parse_lib import ParseContext


def ParseDemo(oil_grammar):
  # type: (Grammar) -> None

  arena = alloc.Arena()
  arena.PushSource(source__Stdin(''))

  parse_ctx = None  # type: ParseContext
  e_parser = expr_parse.ExprParser(parse_ctx, oil_grammar)

  line_lexer = lexer.LineLexer('', arena)
  line_reader = reader.StringLineReader('1 + 2*3', arena)
  lex = lexer.Lexer(line_lexer, line_reader)

  try:
    pnode, _ = e_parser.Parse(lex, arith_nt.arith_expr)
  except error.Parse as e:
    #ui.PrettyPrintError(e, arena)
    log("Parse Error (TODO: print it)")
    return

  # TODO: Fill this in.  Oil uses parse_lib.MakeGrammarNames()
  #
  # terminals: _Id_str?  Doesn't work in mycpp
  # nonterminals: gr.number2symbol.  Is this ever used at runtime?
  #
  # Dict[int,str] should really be a List[str] then?

  if 0:
    names = {}  # type: Dict[int, str]
    printer = expr_parse.ParseTreePrinter(names)
    printer.Print(pnode)
    # NOTE: Could also transform

  # This only works for Oil
  if 0:
    tr = expr_to_ast.Transformer(oil_grammar)
    node = tr.Expr(pnode)

    assert node is not None

    tree = node.AbbreviatedTree()
    fmt.PrintTree(tree, mylib.Stdout())


def run_tests():
  # type: () -> None

  if mylib.CPP:
    # TODO: Initialize this
    gr = None  # type: Optional[Grammar]
  else:
    # And then cppgen_pass.py gets rid of all the "else" blocks

    from pgen2 import grammar

    # We're finding a bad os.pyi ?
    repo_root = os.environ['HOME'] + '/git/oilshell/oil'  # type: ignore
    gr = grammar.Grammar()
    f = open(repo_root + '/_devbuild/gen/arith.marshal')
    contents = f.read()
    gr.loads(contents)
    f.close()

  ParseDemo(gr)
  print('done')


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
