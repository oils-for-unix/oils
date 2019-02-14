#!/usr/bin/python
"""
unit_test_types.py : Collect types
"""
import unittest

from pyannotate_runtime import collect_types

from asdl import typed_arith_parse_test
from asdl import format_test


if __name__ == '__main__':
  collect_types.init_types_collection()
  with collect_types.collect():
    #typed_arith_parse_test.main()
    unittest.main(format_test)
  collect_types.dump_stats('type_info.json')
