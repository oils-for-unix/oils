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

class ParseContext(object):
  """Context shared between the mutually recursive Command and Word parsers.

  In constrast, STATE is stored in the CommandParser and WordParser instances.
  """

  def __init__(self, arena, aliases):
    self.arena = arena
    self.aliases = aliases

  def MakeParser(self, line_reader):
    line_lexer = lexer.LineLexer(match.MATCHER, '', self.arena)
    lx = lexer.Lexer(line_lexer, line_reader)
    w_parser = word_parse.WordParser(self, lx, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lx, line_reader, self.arena,
                                       aliases=self.aliases)
    return w_parser, c_parser

  def MakeWordParserForHereDoc(self, line_reader):
    line_lexer = lexer.LineLexer(match.MATCHER, '', self.arena)
    lx = lexer.Lexer(line_lexer, line_reader)
    return word_parse.WordParser(self, lx, line_reader)

  def MakeParserForCommandSub(self, line_reader, lexer):
    """To parse command sub, we want a fresh word parser state.

    It's a new instance based on same lexer and arena.
    """
    w_parser = word_parse.WordParser(self, lexer, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lexer, line_reader,
                                      self.arena)
    return c_parser

  def MakeWordParserForPlugin(self, code_str, arena):
    """FOr $PS1, etc.

    NOTE: Uses its own arena!  I think that does nothing though?
    """
    line_reader = reader.StringLineReader(code_str, arena)
    line_lexer = lexer.LineLexer(match.MATCHER, '', arena)
    lx = lexer.Lexer(line_lexer, line_reader)
    return word_parse.WordParser(self, lx, line_reader)

  # TODO: We could reuse w_parser with ResetInputObjects() each time.  That's
  # what the REPL does.
  #
  # NOTE: It probably needs to take a VirtualLineReader for $PS1, $PS2, ...
  # values.
  def MakeParserForCompletion(self, code_str, arena):
    """Parser for partial lines.

    NOTE: Uses its own arena!
    """
    # NOTE: We don't need to use a arena here?  Or we need a "scratch arena" that
    # doesn't interfere with the rest of the program.
    line_reader = reader.StringLineReader(code_str, arena)
    line_lexer = lexer.LineLexer(match.MATCHER, '', arena)  # AtEnd() is true
    lx = lexer.Lexer(line_lexer, line_reader)
    w_parser = word_parse.WordParser(self, lx, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lx, line_reader, arena)
    return w_parser, c_parser

  # Another parser instantiation:
  # - For Array Literal in word_parse.py WordParser:
  #   w_parser = WordParser(self.lexer, self.line_reader)
