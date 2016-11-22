#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
"""
tokens_test.py: Tests for tokens.py
"""

import unittest

import tokens
from tokens import Id, BType, TokenTypeToName, TokenKind, BKind

from lexer import Token


class TokensTest(unittest.TestCase):

  def testId(self):
    print(dir(Id))
    print(Id.Op_Newline)
    print(Id.Undefined_Tok)

  def testTokens(self):
    print(Id.Op_Newline)
    print(Token(Id.Op_Newline, '\n'))

    print(TokenTypeToName(Id.Op_Newline))

    print(TokenKind.Eof)
    print(TokenKind.Left)
    print('--')
    for name in dir(TokenKind):
      if name[0].isupper():
        print(name, getattr(TokenKind, name))

    # Make sure we're not exporting too much
    print(dir(tokens))

    # 144 out of 256 tokens now
    print(len(tokens._TOKEN_TYPE_NAMES))

    t = Token(Id.Arith_Plus, '+')
    self.assertEqual(TokenKind.Arith, t.Kind())
    t = Token(Id.Arith_CaretEqual, '^=')
    self.assertEqual(TokenKind.Arith, t.Kind())
    t = Token(Id.Arith_RBrace, '}')
    self.assertEqual(TokenKind.Arith, t.Kind())

  def testBTokens(self):
    print(BType)

    print('')
    print(dir(BType))
    print('')
    print(dir(BKind))
    print('')

    from pprint import pprint
    pprint(tokens._BTOKEN_TYPE_NAMES)


def PrintBoolTable():
  for i, (kind, logical, arity, arg_type) in enumerate(BOOLEAN_OP_TABLE):
    row = (BTokenTypeToName(i), logical, arity, arg_type)
    print('\t'.join(str(c) for c in row))

  print(dir(BKind))


if __name__ == '__main__':
  import sys
  if len(sys.argv) > 1 and sys.argv[1] == 'stats':
    k = tokens._kind_sizes
    print('STATS: %d tokens in %d groups: %s' % (sum(k), len(k), k))
    # Thinking about switching
    big = [i for i in k if i > 8]
    print('%d BIG groups: %s' % (len(big), big))

    a = len(tokens._TokenDef.Arith)
    print(a)

    print('BType:', len(tokens._BTOKEN_TYPE_NAMES))

    PrintBoolTable()

  else:
    unittest.main()
