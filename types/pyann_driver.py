#!/usr/bin/python
"""
unit_test_types.py : Collect types
"""
import unittest

from pyannotate_runtime import collect_types

#from asdl import typed_arith_parse_test
from asdl import format_test
from osh import cmd_parse_test
from frontend import lex_test
from frontend import lexer_test


if __name__ == '__main__':
  collect_types.init_types_collection()
  with collect_types.collect():
    #typed_arith_parse_test.main()

    loader = unittest.TestLoader()
    suites = [
        loader.loadTestsFromModule(m) for m in [lex_test, lexer_test]
    ]

    suite = unittest.TestSuite()
    for s in suites:
      suite.addTest(s)

    runner = unittest.TextTestRunner()
    runner.run(suite)

  collect_types.dump_stats('type_info.json')
