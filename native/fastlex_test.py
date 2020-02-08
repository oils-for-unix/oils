#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
fastlex_test.py: Tests for fastlex
"""
from __future__ import print_function

import unittest

from core.util import log
from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.types_asdl import lex_mode_e

import fastlex  # module under test


# NOTE: This is just like _MatchOshToken_Fast in frontend/match.py
def MatchOshToken(lex_mode, line, start_pos):
  tok_type, end_pos = fastlex.MatchOshToken(lex_mode, line, start_pos)
  #log('tok_type = %d, id = %s', tok_type, tok_type)
  return tok_type, end_pos


def TokenizeLineOuter(line):
  start_pos = 0
  while True:
    tok_type, end_pos = MatchOshToken(lex_mode_e.ShCommand, line, start_pos)
    tok_val = line[start_pos:end_pos]
    print('TOK: %s %r\n' % (tok_type, tok_val))
    start_pos = end_pos

    if tok_type == Id.Eol_Tok:
      break


class LexTest(unittest.TestCase):

  def testMatchOshToken(self):
    print(dir(fastlex))
    print(MatchOshToken(lex_mode_e.Comment, 'line', 3))
    print()

    # Need to be able to pass NUL bytes for EOF.
    line = 'end of line\n'
    TokenizeLineOuter(line)
    line = 'end of file\0'
    TokenizeLineOuter(line)

  def testMatchOption(self):
    log('MatchOption')
    CASES = [
        ('', False),
        ('pipefail', True),
        ('foo', False),
        ('pipefai', False),
        ('pipefail_', False),
        ('strict_errexit', True),
    ]
    for s, expected_bool in CASES:
      result = fastlex.MatchOption(s)
      self.assertEqual(expected_bool, bool(result))
      log('case %r, result = %s', s, result)

  def testOutOfBounds(self):
    print(MatchOshToken(lex_mode_e.ShCommand, 'line', 3))
    # It's an error to point to the end of the buffer!  Have to be one behind
    # it.
    return
    print(MatchOshToken(lex_mode_e.ShCommand, 'line', 4))
    print(MatchOshToken(lex_mode_e.ShCommand, 'line', 5))

  def testBug(self):
    code_str = '-n'
    expected = Id.BoolUnary_n

    tok_type, end_pos = MatchOshToken(lex_mode_e.DBracket, code_str, 0)
    print('--- %s expected, got %s' % (expected, tok_type))

    self.assertEqual(expected, tok_type)

  def testIsValidVarName(self):
    self.assertEqual(True, fastlex.IsValidVarName('abc'))
    self.assertEqual(True, fastlex.IsValidVarName('foo_bar'))
    self.assertEqual(True, fastlex.IsValidVarName('_'))

    self.assertEqual(False, fastlex.IsValidVarName(''))
    self.assertEqual(False, fastlex.IsValidVarName('-x'))
    self.assertEqual(False, fastlex.IsValidVarName('x-'))
    self.assertEqual(False, fastlex.IsValidVarName('var_name-foo'))


if __name__ == '__main__':
  unittest.main()
