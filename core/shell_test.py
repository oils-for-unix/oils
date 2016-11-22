#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
shell_test.py
"""

import unittest
import sys

from core import reader

# These may move around
from osh import parse_lib
from osh.word_parse import *
from osh.cmd_parse import CommandParser

from core.cmd_node import *
from core import cmd_exec_test  # for InitExecutor.  TODO: testutil?
from core import util

trace = True
trace = False
if trace:
  state = util.TraceState()
  #util.WrapMethods(CommandParser, state)
  #util.WrapMethods(WordParser, state)
  #util.WrapMethods(Lexer, state)


class PrinterTest(unittest.TestCase):

  def testWordParts(self):
    # Tokens use <> ?
    t1 = Token(Id.Lit_Chars, 'echo')
    t2 = Token(Id.Op_Newline, '\n')
    print(t1)
    print(t2)

    # Word parts use {}

    l1 = LiteralPart(t1)
    print(l1)

    l2 = LiteralPart(t2)
    print(l2)

    l3 = LiteralPart(Token(Id.Lit_Chars, 'foo'))
    print(l3)

    l4 = LiteralPart(Token(Id.Lit_LBrace, '{'))
    print(l4)

    command_list = SimpleCommandNode()
    command_list.words = [l1, l3]

    t = Token(Id.Left_CommandSub, '$(')
    cs_part = CommandSubPart(t, command_list)
    print(cs_part)

    vs_part = VarSubPart('foo')
    print(vs_part)

    # A part that contains other parts
    dq = DoubleQuotedPart()
    dq.parts.append(l1)
    dq.parts.append(cs_part)

    print(dq)

    # Word

    cw = CompoundWord()
    cw.parts = [l1, dq]
    print(cw)

    tw = TokenWord(t2)
    print(tw)


class LineReaderTest(unittest.TestCase):

  def testGetLine(self):
    r = reader.StringLineReader('foo\nbar')  # no trailing newline
    self.assertEqual((-1, 'foo\n'), r.GetLine())
    self.assertEqual((-1, 'bar\n'), r.GetLine())

    # Keep returning EOF after exhausted
    self.assertEqual((-1, None), r.GetLine())
    self.assertEqual((-1, None), r.GetLine())


def ParseAndExecute(code_str):
  line_reader, lexer = parse_lib.InitLexer(code_str)
  w_parser = WordParser(lexer, line_reader)
  c_parser = CommandParser(w_parser, lexer, line_reader)

  node = c_parser.ParseFile()
  if not node:
    raise AssertionError()

  print(node)
  ex = cmd_exec_test.InitExecutor()
  status, cflow = ex.Execute(node)

  # TODO: Can we capture output here?
  return status


class ExecutorTest(unittest.TestCase):

  def testBuiltin(self):
    print(ParseAndExecute('echo hi'))


if __name__ == '__main__':
  unittest.main()
