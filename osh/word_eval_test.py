#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
word_eval_test.py: Tests for word_eval.py
"""
from __future__ import print_function

import unittest

from core import error
from core import test_lib
from core import util
from osh import word_eval
from osh.cmd_parse_test import assertParseSimpleCommand


def InitEvaluator():
    word_ev = test_lib.InitWordEvaluator()
    test_lib.SetLocalString(word_ev.mem, 'x', '- -- ---')
    test_lib.SetLocalString(word_ev.mem, 'y', 'y yy')
    test_lib.SetLocalString(word_ev.mem, 'empty', '')
    test_lib.SetLocalString(word_ev.mem, 'binding', 'spam=eggs')
    test_lib.SetLocalString(word_ev.mem, 'binding_with_spaces',
                            'x=green eggs and ham')

    word_ev.mem.SetArgv(['x', 'foo', 'spam=eggs'])
    return word_ev


class RegexTest(unittest.TestCase):
    def testSplitAssignArg(self):
        CASES = [
            ('s', ['s', '', '']),
            ('value', ['value', '', '']),
            ('s!', None),
            ('!', None),
            ('=s', None),
            ('s=', ['s', '=', '']),
            ('s=val', ['s', '=', 'val']),
            ('s=+', ['s', '=', '+']),
            ('s+=val!', ['s', '+=', 'val!']),
            ('s+=+', ['s', '+=', '+']),
        ]

        for s, expected in CASES:
            actual = util.simple_regex_search(word_eval.ASSIGN_ARG_RE, s)
            if actual is None:
                self.assertEqual(expected, actual)  # no match
            else:
                _, var_name, _, op, value = actual
                self.assertEqual(expected[0], var_name)
                self.assertEqual(expected[1], op)
                self.assertEqual(expected[2], value)


class WordEvalTest(unittest.TestCase):
    def testEvalWordSequence_Errors(self):
        CASES = [
            'readonly a[x]=1',
            'readonly $binding a[x]=1',
            # There's no word elision!  This will be a parse error
            'declare $empty',
        ]

        for case in CASES:
            print()
            print('\t%s' % case)
            node = assertParseSimpleCommand(self, case)
            ev = InitEvaluator()
            try:
                argv = ev.EvalWordSequence2(node.words, allow_assign=True)
            except error.FatalRuntime:
                pass
            else:
                self.fail("%r should have raised ParseError", case)

    def testEvalWordSequence(self):
        node = assertParseSimpleCommand(self, 'ls foo')
        self.assertEqual(2, len(node.words), node.words)
        print()
        print()

        CASES = [
            'ls [$x] $y core/a*.py',
            'local a=1',

            # What to do about these?
            # Resolve second word then?
            'builtin local a=1',
            'command local a=1',
            'typeset -"$@"',
            # array=(b c)',
            'local a=(1 2) "$@"',  # static then dynamic
            'readonly "$@" a=(1 2)',  # dynamic then static
            'declare -rx foo=bar spam=eggs a=(1 2)',
            'declare $binding',
            'declare $binding_with_spaces',

            # This can be parsed, but the builtin should reject it
            'export a=(1 2)',
            'export A=(["k"]=v)',

            # Hard test cases:
            #
            # command export foo=bar
            # builtin export foo=bar
            #
            # b=builtin c=command e=export binding='foo=bar'
            # $c $e $binding
            # $b $e $binding
        ]

        for case in CASES:
            print()
            print('\t%s' % case)
            node = assertParseSimpleCommand(self, case)
            ev = InitEvaluator()
            argv = ev.EvalWordSequence2(node.words, allow_assign=True)

            print()
            print('\tcmd_value:')
            print(argv)
            print()


if __name__ == '__main__':
    unittest.main()
