#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
id_kind_test.py: Tests for id_kind.py
"""

import unittest

import id_kind
from id_kind import Id, IdName, Kind

from tokens import Token


class TokensTest(unittest.TestCase):

  def testId(self):
    print(dir(Id))
    print(Id.Op_Newline)
    print(Id.Undefined_Tok)

  def testTokens(self):
    print(Id.Op_Newline)
    print(Token(Id.Op_Newline, '\n'))

    print(IdName(Id.Op_Newline))

    print(Kind.Eof)
    print(Kind.Left)
    print('--')
    for name in dir(Kind):
      if name[0].isupper():
        print(name, getattr(Kind, name))

    # Make sure we're not exporting too much
    print(dir(id_kind))

    # 206 out of 256 tokens now
    print(len(id_kind._ID_NAMES))

    t = Token(Id.Arith_Plus, '+')
    self.assertEqual(Kind.Arith, t.Kind())
    t = Token(Id.Arith_CaretEqual, '^=')
    self.assertEqual(Kind.Arith, t.Kind())
    t = Token(Id.Arith_RBrace, '}')
    self.assertEqual(Kind.Arith, t.Kind())

    t = Token(Id.BoolBinary_DEqual, '==')
    self.assertEqual(Kind.BoolBinary, t.Kind())

  def testLexerPairs(self):
    lookup = dict(id_kind.ID_SPEC.LexerPairs(Kind.BoolUnary))
    print(lookup)
    self.assertEqual(Id.BoolUnary_a, lookup['\-a'])
    self.assertEqual(Id.BoolUnary_z, lookup['\-z'])

    lookup2 = dict(id_kind.ID_SPEC.LexerPairs(Kind.BoolBinary))
    self.assertEqual(Id.BoolBinary_eq, lookup2['\-eq'])


def PrintBoolTable():
  for i, (logical, arity, arg_type) in id_kind.BOOL_OPS.items():
    row = (id_kind.IdName(i), logical, arity, arg_type)
    print('\t'.join(str(c) for c in row))


if __name__ == '__main__':
  import sys
  if len(sys.argv) > 1 and sys.argv[1] == 'stats':
    k = id_kind._kind_sizes
    print('STATS: %d tokens in %d groups: %s' % (sum(k), len(k), k))
    # Thinking about switching
    big = [i for i in k if i > 8]
    print('%d BIG groups: %s' % (len(big), sorted(big)))

    PrintBoolTable()

  else:
    unittest.main()
