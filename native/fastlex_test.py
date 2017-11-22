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


def MatchToken(lex_mode, line, start_pos):
  tok_type, end_pos = fastlex.MatchToken(lex_mode.enum_id, line, start_pos)
  return Id(tok_type), end_pos


def TokenizeLineOuter(line):
  start_pos = 0
  while True:
    tok_type, end_pos = MatchToken(lex_mode_e.OUTER, line, start_pos)
    tok_val = line[start_pos:end_pos]
    print('TOK: %s %r\n' % (tok_type, tok_val))
    start_pos = end_pos

    if end_pos == len(line):
      break


class LexTest(unittest.TestCase):

  def testMatchToken(self):
    print(dir(fastlex))
    print MatchToken(lex_mode_e.COMMENT, 'line', 3)
    print

    # Need to be able to pass NUL bytes for EOF.
    line = 'end of line\n'
    TokenizeLineOuter(line)
    line = 'end of file\0'
    TokenizeLineOuter(line)

  def testOutOfBounds(self):
    print MatchToken(lex_mode_e.OUTER, 'line', 3)
    # It's an error to point to the end of the buffer!  Have to be one behind
    # it.
    return
    print MatchToken(lex_mode_e.OUTER, 'line', 4)
    print MatchToken(lex_mode_e.OUTER, 'line', 5)


if __name__ == '__main__':
  unittest.main()
