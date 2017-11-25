"""
parse_lib.py - Consolidate various parser instantiations here.
"""

import sys

from core import lexer
from core import reader
from core.id_kind import Id

from osh import lex
from osh import word_parse
from osh import cmd_parse

# bin/osh should work without compiling fastlex?  But we want all the unit
# tests to run with a known version of it.
try:
  import fastlex
except ImportError:
  fastlex = None


class MatchToken_Slow(object):
  """An abstract matcher that doesn't depend on OSH."""
  def __init__(self, lexer_def):
    self.lexer_def = {}
    for state, pat_list in lexer_def.items():
      self.lexer_def[state] = lexer.CompileAll(pat_list)

  def __call__(self, lex_mode, line, start_pos):
    """Returns (id, end_pos)."""
    re_list = self.lexer_def[lex_mode]
    matches = []
    for regex, tok_type in re_list:
      m = regex.match(line, start_pos)  # left-anchored
      if m:
        matches.append((m.end(0), tok_type, m.group(0)))
    if not matches:
      raise AssertionError('no match at position %d: %r' % (start_pos, line))
    end_pos, tok_type, tok_val = max(matches, key=lambda m: m[0])
    return tok_type, end_pos


def MatchToken_Fast(lex_mode, line, start_pos):
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchToken(lex_mode.enum_id, line, start_pos)
  return Id(tok_type), end_pos


def _MakeMatcher():
  # NOTE: Could have an environment variable to control this for speed?
  #return MatchToken_Slow(lex.LEXER_DEF)

  if fastlex:
    return MatchToken_Fast
  else:
    return MatchToken_Slow(lex.LEXER_DEF)


def InitLexer(s, arena=None):
  """For tests only."""
  match_func = _MakeMatcher()
  line_lexer = lexer.LineLexer(match_func, '', arena=arena)
  line_reader = reader.StringLineReader(s, arena=arena)
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


# TODO:
# - Does it make sense to create ParseState objects?  They have no dependencies
#   -- just pure data.  Or just recreate them every time?  One issue is that
#   you need somewhere to store the side effects -- errors for parsers, and the
#   actual values for the evaluators/executors.

def MakeParser(line_reader, arena):
  """Top level parser."""
  # AtEnd() is true
  line_lexer = lexer.LineLexer(_MakeMatcher(), '', arena=arena)
  lx = lexer.Lexer(line_lexer, line_reader)
  w_parser = word_parse.WordParser(lx, line_reader)
  c_parser = cmd_parse.CommandParser(w_parser, lx, line_reader, arena=arena)
  return w_parser, c_parser


# TODO: We could reuse w_parser with Reset() each time.  That's what the REPL
# does.
# But LineLexer and Lexer are also stateful!  So that might not be worth it.
# Hm the REPL only does line_reader.Reset()?
#
# NOTE: It probably needs to take a VirtualLineReader for $PS1, $PS2, ...
# values.
def MakeParserForCompletion(code_str, arena=None):
  """Parser for partial lines."""
  # NOTE: We don't need to use a arena here?  Or we need a "scratch arena" that
  # doesn't interfere with the rest of the program.
  line_reader = reader.StringLineReader(code_str)
  line_lexer = lexer.LineLexer(_MakeMatcher(), '', arena=arena)  # AtEnd() is true
  lx = lexer.Lexer(line_lexer, line_reader)
  w_parser = word_parse.WordParser(lx, line_reader)
  c_parser = cmd_parse.CommandParser(w_parser, lx, line_reader, arena=arena)
  return w_parser, c_parser


def MakeWordParserForHereDoc(lines, arena):
  line_reader = reader.VirtualLineReader(lines, arena)
  line_lexer = lexer.LineLexer(_MakeMatcher(), '', arena=arena)
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


# More parser instantiations
# - For Array Literal -- instantiate WordParser
