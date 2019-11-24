#!/usr/bin/env python2
"""
pyann_driver.py: Collect types
"""
import unittest

from pyannotate_runtime import collect_types

#from asdl import typed_arith_parse_test
from asdl import format_test
from core import comp_ui_test
from osh import arith_parse_test
from osh import bool_parse_test
from osh import cmd_parse_test
from osh import word_parse_test
from frontend import lex_test
from frontend import lexer_test

import glob

def TopLevel():
  """Copy some metaprogramming that only happens at the top level."""
  # from core/meta.py
  from core.meta import (
      _ID_TO_KIND_INTEGERS, BOOL_ARG_TYPES, TEST_UNARY_LOOKUP,
      TEST_BINARY_LOOKUP, TEST_OTHER_LOOKUP,
      types_asdl
  )
  from core import id_kind

  ID_SPEC = id_kind.IdSpec(_ID_TO_KIND_INTEGERS, BOOL_ARG_TYPES)

  id_kind.AddKinds(ID_SPEC)
  id_kind.AddBoolKinds(ID_SPEC, types_asdl.bool_arg_type_e)  # must come second
  id_kind.SetupTestBuiltin(ID_SPEC,
                           TEST_UNARY_LOOKUP, TEST_BINARY_LOOKUP,
                           TEST_OTHER_LOOKUP,
                           types_asdl.bool_arg_type_e)

  from osh import arith_parse
  spec = arith_parse.MakeShellSpec()


def Match():
  from frontend.match import _MatchOshToken_Slow, _MatchTokenSlow
  from frontend import lex
  MATCHER = _MatchOshToken_Slow(lex.LEXER_DEF)
  ECHO_MATCHER = _MatchTokenSlow(lex.ECHO_E_DEF)
  GLOB_MATCHER = _MatchTokenSlow(lex.GLOB_DEF)
  PS1_MATCHER = _MatchTokenSlow(lex.PS1_DEF)
  HISTORY_MATCHER = _MatchTokenSlow(lex.HISTORY_DEF)


def Arith():
  from osh.arith_parse import MakeShellSpec
  SPEC = MakeShellSpec()


def main():
  loader = unittest.TestLoader()

  g = glob.glob
  py = g('frontend/*_test.py') + g('osh/*_test.py') + g('core/*_test.py') + g('')
  # hangs
  py.remove('core/process_test.py')

  modules = []
  for p in py:
    mod_name = p[:-3].replace('/', '.')
    print(mod_name)
    modules.append(__import__(mod_name, fromlist=['.']))

  for m in modules:
    print(m)

  suites = [loader.loadTestsFromModule(m) for m in modules]

  suite = unittest.TestSuite()
  for s in suites:
    suite.addTest(s)

  runner = unittest.TextTestRunner()

  collect_types.init_types_collection()
  with collect_types.collect():
    runner.run(suite)
    if 0:
      TopLevel()
      Match()
      Arith()

  collect_types.dump_stats('type_info.json')


if __name__ == '__main__':
  main()
