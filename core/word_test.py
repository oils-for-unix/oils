#!/usr/bin/env python
from __future__ import print_function
"""
word_test.py: Tests for word.py
"""

import unittest

from osh import word_parse_test
from osh.meta import Id
from core.util import log

from core import word  # module under test


def _Detect(test, word_str, expected):
  # TODO: This function could be moved to test_lib.
  log('-'*80)
  arena, w = word_parse_test._assertReadWordWithArena(test, word_str)

  actual = word.DetectAssignment(w)
  left_token, close_token, part_offset = actual

  expected_left, expected_close, expected_part_offset = expected

  print(left_token, close_token, part_offset)
  print()

  if expected_left is None:
    test.assertEqual(None, left_token)
  else:
    test.assertEqual(expected_left, left_token.id)

  if expected_close is None:
    test.assertEqual(None, close_token)
  else:
    test.assertEqual(expected_left, left_token.id)

  test.assertEqual(expected_part_offset, part_offset)

  # Test that we can reparse niput
  from osh import cmd_parse
  from osh import parse_lib
  from core import alloc

  parse_ctx = parse_lib.ParseContext(arena, {})

  if left_token and left_token.id in (Id.Lit_VarLike, Id.Lit_ArrayLhsOpen):
    more_env = []
    preparsed = (left_token, close_token, part_offset, w)
    try:
      cmd_parse._AppendMoreEnv([preparsed], more_env)
    except Exception as e:
      log('Error: %s', e)
    else:
      log('more_env: %s', more_env)

    try:
      assign_pair = cmd_parse._MakeAssignPair(parse_ctx, preparsed)
    except Exception as e:
      log('Error: %s', e)
    else:
      log('assign_pair: %s', assign_pair)


class WordTest(unittest.TestCase):

  def testDetectLocation(self):
    CASES = [
        ('foobar', (None, None, 0)),
        ('a[x', (None, None, 0)),

        # Empty is not valid, there has to be at least one token.
        ('a[]=$foo$bar', (None, None, 0)),
        ('a[]+=$foo$bar', (None, None, 0)),

        ('s=1', (Id.Lit_VarLike, None, 1)),
        ('s+=1', (Id.Lit_VarLike, None, 1)),
        ('a[x]=1', (Id.Lit_ArrayLhsOpen, Id.Lit_ArrayLhsClose, 3)),
        ('a[x]+=1', (Id.Lit_ArrayLhsOpen, Id.Lit_ArrayLhsClose, 3)),
        ('a[x++]+=1', (Id.Lit_ArrayLhsOpen, Id.Lit_ArrayLhsClose, 5)),

        ('a=(1 2 3)', (Id.Lit_VarLike, None, 1)),
        ('a+=(1 2 3)', (Id.Lit_VarLike, None, 1)),

        # EmptyWord on RHS
        ('s=', (Id.Lit_VarLike, None, 1)),
        ('a[x]=', (Id.Lit_ArrayLhsOpen, Id.Lit_ArrayLhsClose, 3)),

        # Tilde sub
        ('s=~foo', (Id.Lit_VarLike, None, 1)),
        ('a[x]=~', (Id.Lit_ArrayLhsOpen, Id.Lit_ArrayLhsClose, 3)),
    ]
    for word_str, expected in CASES:
      _Detect(self, word_str, expected)

    # These don't parse, as they shouldn't.  But not the best error message.
    #w = assertReadWord(self, 'a[x]=(1 2 3)')
    #w = assertReadWord(self, 'a[x]+=(1 2 3)')


if __name__ == '__main__':
  unittest.main()
