"""
parse_lib.py - Consolidate various parser instantiations here.
"""

from core import lexer
from core import reader
from core import tdop

from osh import arith_parse
from osh import cmd_parse
from frontend import match
from osh import word_parse
from core.meta import types

from frontend import oil_parse

lex_mode_e = types.lex_mode_e


def InitLexer(s, arena):
  """For tests only."""
  match_func = match.MATCHER
  line_lexer = lexer.LineLexer(match_func, '', arena)
  line_reader = reader.StringLineReader(s, arena)
  lx = lexer.Lexer(line_lexer, line_reader)
  return line_reader, lx


class ParseContext(object):
  """Context shared between the mutually recursive Command and Word parsers.

  In constrast, STATE is stored in the CommandParser and WordParser instances.
  """

  def __init__(self, arena, aliases):
    self.arena = arena
    self.aliases = aliases

  def MakeOshParser(self, line_reader):
    line_lexer = lexer.LineLexer(match.MATCHER, '', self.arena)
    lx = lexer.Lexer(line_lexer, line_reader)
    w_parser = word_parse.WordParser(self, lx, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lx, line_reader)
    return w_parser, c_parser

  def MakeOilParser(self, line_reader):
    # Same lexer as Oil?  It just doesn't start in the OUTER state?
    line_lexer = lexer.LineLexer(match.MATCHER, '', self.arena)
    lx = lexer.Lexer(line_lexer, line_reader)
    c_parser = oil_parse.OilParser(self, lx, line_reader)
    return c_parser

  def MakeWordParserForHereDoc(self, line_reader):
    line_lexer = lexer.LineLexer(match.MATCHER, '', self.arena)
    lx = lexer.Lexer(line_lexer, line_reader)
    return word_parse.WordParser(self, lx, line_reader)

  def MakeArithParser(self, code_str, arena):
    """
    NOTE: We want to add tokens to a different arena, so we don't mess up the
    translation.
    """
    line_reader = reader.StringLineReader(code_str, arena)
    line_lexer = lexer.LineLexer(match.MATCHER, '', arena)
    lx = lexer.Lexer(line_lexer, line_reader)
    w_parser = word_parse.WordParser(self, lx, line_reader,
                                     lex_mode=lex_mode_e.ARITH)
    a_parser = tdop.TdopParser(arith_parse.SPEC, w_parser)
    return a_parser

  def MakeParserForCommandSub(self, line_reader, lexer, eof_id):
    """To parse command sub, we want a fresh word parser state.

    It's a new instance based on same lexer and arena.
    """
    w_parser = word_parse.WordParser(self, lexer, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lexer, line_reader,
                                       eof_id=eof_id)
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
    # NOTE: We don't need to use a arena here?  Or we need a "scratch arena"
    # that doesn't interfere with the rest of the program.
    line_reader = reader.StringLineReader(code_str, arena)
    line_lexer = lexer.LineLexer(match.MATCHER, '', arena)  # AtEnd() is true
    lx = lexer.Lexer(line_lexer, line_reader)
    w_parser = word_parse.WordParser(self, lx, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lx, line_reader,
                                       arena=arena)
    return w_parser, c_parser

  # Another parser instantiation:
  # - For Array Literal in word_parse.py WordParser:
  #   w_parser = WordParser(self.lexer, self.line_reader)
