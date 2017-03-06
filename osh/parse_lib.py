"""
parse_lib.py - Consolidate various parser instantiations here.
"""

import sys

from core import lexer
from core import reader

from osh import lex
from osh import word_parse
from osh import cmd_parse


def InitLexer(s, arena=None):
  """For tests only."""
  line_lexer = lexer.LineLexer(lex.LEXER_DEF, '', arena=arena)
  line_reader = reader.StringLineReader(s, arena=arena)
  lx = lexer.Lexer(line_lexer, line_reader)
  return line_reader, lx


# TODO:
# - Does it make sense to create ParseState objects?  They have no dependencies
#   -- just pure data.  Or just recreate them every time?  One issue is that
#   you need somewhere to store the side effects -- errors for parsers, and the
#   actual values for the evaluators/executors.

def MakeParserForTop(line_reader, arena=None):
  """Top level parser."""
  # AtEnd() is true
  line_lexer = lexer.LineLexer(lex.LEXER_DEF, '', arena=arena)
  lx = lexer.Lexer(line_lexer, line_reader)
  w_parser = word_parse.WordParser(lx, line_reader)
  c_parser = cmd_parse.CommandParser(w_parser, lx, line_reader)
  return w_parser, c_parser


# TODO: We could reuse w_parser with Reset() each time.  That's what the REPL
# does.
# But LineLexer and Lexer are also stateful!  So that might not be worth it.
# Hm the REPL only does line_reader.Reset()?
def MakeParserForCompletion(code_str):
  """Parser for partial lines."""
  # NOTE: We don't need to use a arena here?  Or we need a "scratch arena" that
  # doesn't interfere with the rest of the program.
  line_reader = reader.StringLineReader(code_str)
  line_lexer = lexer.LineLexer(lex.LEXER_DEF, '')  # AtEnd() is true
  lx = lexer.Lexer(line_lexer, line_reader)
  w_parser = word_parse.WordParser(lx, line_reader)
  c_parser = cmd_parse.CommandParser(w_parser, lx, line_reader)
  return w_parser, c_parser


def MakeParserForExecutor(code_str):
  """Parser for source / eval."""
  _, c_parser = MakeParserForCompletion(code_str)
  return c_parser


# TODO: This has to take an arena so it gets the spans.
def MakeWordParserForHereDoc(lines):
  line_reader = reader.VirtualLineReader(lines)
  line_lexer = lexer.LineLexer(lex.LEXER_DEF, '')
  lx = lexer.Lexer(line_lexer, line_reader)
  return word_parse.WordParser(lx, line_reader)


def MakeParserForCommandSub(line_reader, lexer):
  """To parse command sub, we want a fresh word parser state."""
  # new instance based on same lexer
  w_parser = word_parse.WordParser(lexer, line_reader)
  c_parser = cmd_parse.CommandParser(w_parser, lexer, line_reader)
  return c_parser


# More parser instantiations
# - For Array Literal -- instantiate WordParser
