#!/usr/bin/env python2
"""
lexer_main.py
"""
from __future__ import print_function

import os
import sys

from core import alloc
from frontend import lexer
from frontend import match

from core.util import log

from typing import cast


def run_tests():
  # type: () -> None

  arena = alloc.Arena()
  # MATCHER = _MatchOshToken__Fast which wraps
  #  fastlex.MatchOshToken (Python) which wraps
  #  MatchOshToken (inline C function)
  #
  # So we want to generate our own C fucntion I think.
  #
  # Should take lex_mode_t, Str*, int, and return Tuple2<Id_t, int>
  # I guess.
  # 
  # But Id_t has to be a raw integer now?

  # MatchFunc = Callable[[lex_mode_t, str, int], Tuple[Id_t, int]]
  # So instead of match.MATCHER, you define a C++ function, textually include
  # it at build time, and then pass it in.
  #
  # It should include osh-lex.h and call that inline function.
  #
  # TODO: generate id_kind
  # and lex_mode_e from types
  # T
  # This should start going in
  #
  # _devbuild/mycpp/
  # _devbuild/gen-mycpp/
  #   syntax_asdl.h
  #   types_asdl.h
  #   id_kind_asdl.h
  #   runtime_asdl.h

   
  line_lexer = lexer.LineLexer('', arena)
  print('lexer_main.py')



def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
