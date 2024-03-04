#!/usr/bin/env python2
"""
word_test.py: Tests for word_.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import word_part_e

from core import test_lib
from mycpp.mylib import log
from osh import cmd_parse  # reparse input
from osh.cmd_parse_test import assertParseSimpleCommand
from osh.word_parse_test import _assertReadWord

from osh import word_  # module under test


def _DetectAssign(test, word_str, expected):
    # TODO: This function could be moved to test_lib.
    log('-' * 80)
    w = _assertReadWord(test, word_str)

    actual = word_.DetectShAssignment(w)
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

    parse_ctx = test_lib.InitParseContext()

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
            ('a[]=$foo$bar', (Id.Lit_ArrayLhsOpen, Id.Lit_ArrayLhsClose, 2)),
            ('a[]+=$foo$bar', (Id.Lit_ArrayLhsOpen, Id.Lit_ArrayLhsClose, 2)),
            ('s=1', (Id.Lit_VarLike, None, 1)),
            ('s+=1', (Id.Lit_VarLike, None, 1)),
            ('a[x]=1', (Id.Lit_ArrayLhsOpen, Id.Lit_ArrayLhsClose, 3)),
            ('a[x]+=1', (Id.Lit_ArrayLhsOpen, Id.Lit_ArrayLhsClose, 3)),
            ('a[x++]+=1', (Id.Lit_ArrayLhsOpen, Id.Lit_ArrayLhsClose, 5)),
            ('a=(1 2 3)', (Id.Lit_VarLike, None, 1)),
            ('a+=(1 2 3)', (Id.Lit_VarLike, None, 1)),

            # Empty on RHS
            ('s=', (Id.Lit_VarLike, None, 1)),
            ('a[x]=', (Id.Lit_ArrayLhsOpen, Id.Lit_ArrayLhsClose, 3)),

            # Tilde sub
            ('s=~foo', (Id.Lit_VarLike, None, 1)),
            ('a[x]=~', (Id.Lit_ArrayLhsOpen, Id.Lit_ArrayLhsClose, 3)),
        ]
        for word_str, expected in CASES:
            _DetectAssign(self, word_str, expected)

        # These don't parse, as they shouldn't.  But not the best error message.
        #w = assertReadWord(self, 'a[x]=(1 2 3)')
        #w = assertReadWord(self, 'a[x]+=(1 2 3)')

    TILDE_WORDS = [
        # These are tilde subs
        (True, '~'),
        (True, '~/'),
        (True, '~/zz'),
        (True, '~andy'),
        (True, '~andy/'),
        (True, '~andy/zz'),

        # These are not
        (False, '~bob#'),
        (False, '~bob#/'),
        (False, '~bob#/zz'),
        (False, ''),
        (False, 'foo'),
    ]

    def testTildeDetect(self):
        for expected, word_str in self.TILDE_WORDS:
            w = _assertReadWord(self, word_str)
            detected = word_.TildeDetect(w)
            print(detected)

            if detected:
                self.assertEqual(word_part_e.TildeSub, detected.parts[0].tag())
                self.assertEqual(True, expected)
            else:
                self.assertEqual(False, expected)

    def testTildeDetectAssignColons(self):
        # x=~a:~b: etc.

        words = [w for _, w in self.TILDE_WORDS]
        assign_str = ':'.join(words)
        w = _assertReadWord(self, assign_str)
        word_.TildeDetectAssign(w)
        print(w)

        actual = 0
        for part in w.parts:
            if part.tag() == word_part_e.TildeSub:
                actual += 1

        log('tilde sub parts = %d', actual)

        expected = sum(expected for expected, _ in self.TILDE_WORDS)
        self.assertEqual(expected, actual)

        print('')

    def testFastStrEval(self):
        node = assertParseSimpleCommand(self, "ls 'my dir' $x foo/$bar ")

        self.assertEqual(4, len(node.words))

        ls_w = node.words[0]
        w1 = node.words[1]
        w2 = node.words[2]
        w3 = node.words[3]

        self.assertEqual('ls', word_.FastStrEval(ls_w))
        self.assertEqual('my dir', word_.FastStrEval(w1))
        self.assertEqual(None, word_.FastStrEval(w2))
        self.assertEqual(None, word_.FastStrEval(w3))

        # Special case for [ ]
        node = assertParseSimpleCommand(self, '[ a -lt b ]')
        self.assertEqual('[', word_.FastStrEval(node.words[0]))
        self.assertEqual('a', word_.FastStrEval(node.words[1]))
        self.assertEqual('-lt', word_.FastStrEval(node.words[2]))
        self.assertEqual('b', word_.FastStrEval(node.words[3]))
        self.assertEqual(']', word_.FastStrEval(node.words[4]))


if __name__ == '__main__':
    unittest.main()
