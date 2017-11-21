#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
libc_test.py: Tests for libc.py
"""

import unittest

from core.id_kind import Id
from osh import ast_ as ast

import fastlex  # module under test

lex_mode_e = ast.lex_mode_e


def MatchToken(lex_mode, line, s):
  tok_type, end_index = fastlex.MatchToken(lex_mode.enum_id, line, s)
  return Id(tok_type), end_index


class LexTest(unittest.TestCase):

  def testMatchToken(self):
    print(dir(fastlex))
    print lex_mode_e.COMMENT.enum_id
    result = MatchToken(lex_mode_e.COMMENT, 'line', 3)
    print result

    # Need to be able to pass NUL bytes for EOF.
    result = MatchToken(lex_mode_e.OUTER, 'end of file\0', 3)

    # TODO: Need to turn Id back?
    print result


if __name__ == '__main__':
  unittest.main()
