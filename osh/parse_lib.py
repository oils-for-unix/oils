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


# New API:
# - MakeParser(reader, arena) - for top level, 'source'
#   - eval: MakeParser(StringLineReader(), arena)
#   - source: MakeParser(FileLineReader(), arena)
# - MakeParserForCommandSub(reader, lexer) -- arena is inside lexer/reader
# - MakeParserForCompletion(code_str)  # no arena?  no errors?
# - MakeWordParserForHereDoc(lines, arena)  # arena is lost
#   - althoguh you want to AddLine
#   - line_id = arena.AddLine()


# NOTE:
# - Does it make sense to create ParseState objects?  They have no dependencies
#   -- just pure data.  Or just recreate them every time?  One issue is that
#   you need somewhere to store the side effects -- errors for parsers, and the
#   actual values for the evaluators/executors.

def MakeParser(line_reader, arena):
  """Top level parser."""
  line_lexer = lexer.LineLexer(match.MATCHER, '', arena)
  lx = lexer.Lexer(line_lexer, line_reader)
  w_parser = word_parse.WordParser(lx, line_reader)
  c_parser = cmd_parse.CommandParser(w_parser, lx, line_reader, arena)
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


def MakeWordParserForHereDoc(lines, arena):
  line_reader = reader.VirtualLineReader(lines, arena)
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
