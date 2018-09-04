"""
parse_lib.py - Consolidate various parser instantiations here.
"""

from core import lexer
from core import reader

from osh import cmd_parse
from osh import match
from osh import word_parse


def InitLexer(s, arena):
  """For tests only."""
  match_func = match.MATCHER
  line_lexer = lexer.LineLexer(match_func, '', arena)
  line_reader = reader.StringLineReader(s, arena)
  lx = lexer.Lexer(line_lexer, line_reader)
  return line_reader, lx


# API:
# - MakeParser(reader, arena) - for top level, 'source'
#   - eval: MakeParser(StringLineReader(), arena)
#   - source: MakeParser(FileLineReader(), arena)
# - MakeParserForCommandSub(line_reader, lexer) -- arena is inside line_reader
# - MakeParserForCompletion(code_str, arena)
# - MakeWordParserForHereDoc(line_reader, arena)
# - MakeWordParserForPlugin(code_str, arena)
#
# TODO:
#
# class ParseState
#   def __init__(self):
#      self.arena
#      self.aliases  # need to be threaded through
#      self.line_reader
#
#   def MakeParser(...)
#   def MakeParserForCommandSub(...)
#
# When does line_reader change?
# - here docs
# - aliases
#
# WordParser gets the line_reader from either parse_state OR an explicit
# argument!
#
# self.parse_state.MakeParser(...)
#
# instead of CommandParser and WordParser holding the arena.
# NOTE: arith parser and bool parser never need to instantiate parsers
# only word/command parser have this dependency.
#
# common thing: word parser does not use arena OR aliases.  But it needs to
# create a command parser.


def MakeParser(line_reader, arena, aliases):
  """Top level parser."""
  line_lexer = lexer.LineLexer(match.MATCHER, '', arena)
  lx = lexer.Lexer(line_lexer, line_reader)
  w_parser = word_parse.WordParser(lx, line_reader)
  c_parser = cmd_parse.CommandParser(w_parser, lx, line_reader, arena,
                                     aliases=aliases)
  return w_parser, c_parser


# TODO: We could reuse w_parser with Reset() each time.  That's what the REPL
# does.
# But LineLexer and Lexer are also stateful!  So that might not be worth it.
# Hm the REPL only does line_reader.Reset()?
#
# NOTE: It probably needs to take a VirtualLineReader for $PS1, $PS2, ...
# values.
def MakeParserForCompletion(code_str, arena):
  """Parser for partial lines."""
  # NOTE: We don't need to use a arena here?  Or we need a "scratch arena" that
  # doesn't interfere with the rest of the program.
  line_reader = reader.StringLineReader(code_str, arena)
  line_lexer = lexer.LineLexer(match.MATCHER, '', arena)  # AtEnd() is true
  lx = lexer.Lexer(line_lexer, line_reader)
  w_parser = word_parse.WordParser(lx, line_reader)
  c_parser = cmd_parse.CommandParser(w_parser, lx, line_reader, arena)
  return w_parser, c_parser


def MakeWordParserForHereDoc(line_reader, arena):
  line_lexer = lexer.LineLexer(match.MATCHER, '', arena)
  lx = lexer.Lexer(line_lexer, line_reader)
  return word_parse.WordParser(lx, line_reader)


def MakeWordParserForPlugin(code_str, arena):
  line_reader = reader.StringLineReader(code_str, arena)
  line_lexer = lexer.LineLexer(match.MATCHER, '', arena)
  lx = lexer.Lexer(line_lexer, line_reader)
  return word_parse.WordParser(lx, line_reader)


def MakeParserForCommandSub(line_reader, lexer):
  """To parse command sub, we want a fresh word parser state.

  It's a new instance based on same lexer and arena.
  """
  arena = line_reader.arena
  w_parser = word_parse.WordParser(lexer, line_reader)
  c_parser = cmd_parse.CommandParser(w_parser, lexer, line_reader, arena)
  return c_parser


# Another parser instantiation:
# - For Array Literal in word_parse.py WordParser:
#   w_parser = WordParser(self.lexer, self.line_reader)
