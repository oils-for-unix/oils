#!/usr/bin/env python2
"""
lexer_main.py
"""
from __future__ import print_function

import os
import sys

from _devbuild.gen.types_asdl import lex_mode_e

from core import alloc
from frontend import lexer
from frontend import match

from core.util import log

from typing import cast


def run_tests():
  # type: () -> None

  arena = alloc.Arena()
  line_lexer = lexer.LineLexer('echo hi', arena)

  # Works!
  tok = line_lexer.Read(lex_mode_e.ShCommand)
  log("tok.val = '%s'", tok.val)
  tok = line_lexer.Read(lex_mode_e.ShCommand)
  log("tok.val = '%s'", tok.val)
  tok = line_lexer.Read(lex_mode_e.ShCommand)
  log("tok.val = '%s'", tok.val)

  # TODO: how to print Id_t?  With %r or something?


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
