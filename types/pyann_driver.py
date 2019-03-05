#!/usr/bin/python
"""
pyann_driver.py: Collect types
"""
import unittest

from pyannotate_runtime import collect_types

#from asdl import typed_arith_parse_test
from asdl import format_test
from osh import arith_parse_test
from osh import bool_parse_test
from osh import cmd_parse_test
from osh import word_parse_test
from frontend import lex_test
from frontend import lexer_test

import glob


def main():
  #typed_arith_parse_test.main()

  loader = unittest.TestLoader()

  modules = [
      arith_parse_test, bool_parse_test, cmd_parse_test, word_parse_test]

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

  collect_types.dump_stats('type_info.json')


if __name__ == '__main__':
  main()
