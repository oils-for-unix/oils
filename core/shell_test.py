#!/usr/bin/env python
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

from core import alloc
from core import reader
from core import test_lib

# These may move around
from osh import parse_lib
from osh.word_parse import *
from osh.cmd_parse import CommandParser

from core import cmd_exec_test  # for InitExecutor.  TODO: testutil?
from core import util

trace = True
trace = False
if trace:
  state = util.TraceState()
  #util.WrapMethods(CommandParser, state)
  #util.WrapMethods(WordParser, state)
  #util.WrapMethods(Lexer, state)


class LineReaderTest(unittest.TestCase):

  def testGetLine(self):
    r = reader.StringLineReader('foo\nbar')  # no trailing newline
    self.assertEqual((-1, 'foo\n'), r.GetLine())
    self.assertEqual((-1, 'bar\n'), r.GetLine())

    # Keep returning EOF after exhausted
    self.assertEqual((-1, None), r.GetLine())
    self.assertEqual((-1, None), r.GetLine())


def ParseAndExecute(code_str):
  arena = test_lib.MakeArena('<shell_test.py>')

  line_reader, lexer = parse_lib.InitLexer(code_str, arena=arena)
  w_parser = WordParser(lexer, line_reader)
  c_parser = CommandParser(w_parser, lexer, line_reader, arena=arena)

  node = c_parser.ParseWholeFile()
  if not node:
    raise AssertionError()

  print(node)
  ex = cmd_exec_test.InitExecutor()
  status = ex.Execute(node)

  # TODO: Can we capture output here?
  return status


class ExecutorTest(unittest.TestCase):

  def testBuiltin(self):
    print(ParseAndExecute('echo hi'))


if __name__ == '__main__':
  unittest.main()
