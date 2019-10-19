#!/usr/bin/env python2
"""
pgen2_demo.py
"""
from __future__ import print_function

import os
import sys

from _devbuild.gen import arith_nt
from _devbuild.gen.syntax_asdl import source

from core import alloc
from core import util
from frontend import reader
from frontend import lexer
from oil_lang import expr_parse

from mycpp import mylib
from mycpp.mylib import log

from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from pgen2.grammar import Grammar


def ParseDemo(oil_grammar):
  # type: (Grammar) -> None

  arena = alloc.Arena()
  arena.PushSource(source.Stdin(''))

  parse_ctx = None
  e_parser = expr_parse.ExprParser(parse_ctx, oil_grammar)

  line_lexer = lexer.LineLexer('', arena)
  line_reader = reader.StringLineReader('1 + 2*3', arena)
  lex = lexer.Lexer(line_lexer, line_reader)

  try:
    pnode, _ = e_parser.Parse(lex, arith_nt.arith_expr)
  except util.ParseError as e:
    #ui.PrettyPrintError(e, arena)
    print(e)
    return

  print(pnode)
  # NOTE: Could also transform


def run_tests():
  # type: () -> None

  if mylib.CPP:
    # TODO: Initialize this
    gr = None
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


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
