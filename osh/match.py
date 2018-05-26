#!/usr/bin/python
"""
match.py - match with generated re2c code or Python regexes.
"""

from core import lexer
from osh import lex
from osh.meta import Id, IdInstance

# bin/osh should work without compiling fastlex?  But we want all the unit
# tests to run with a known version of it.
try:
  import fastlex
except ImportError:
  fastlex = None


class _MatchToken_Slow(object):
  """An abstract matcher that doesn't depend on OSH."""
  def __init__(self, lexer_def):
    self.lexer_def = {}
    for state, pat_list in lexer_def.items():
      self.lexer_def[state] = lexer.CompileAll(pat_list)

  def __call__(self, lex_mode, line, start_pos):
    """Returns (id, end_pos)."""
    # Simulate the EOL handling in re2c.
    if start_pos >= len(line):
      return Id.Eol_Tok, start_pos

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


def _MatchToken_Fast(lex_mode, line, start_pos):
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchToken(lex_mode.enum_id, line, start_pos)
  # IMPORTANT: We're reusing Id instances here.  Ids are very common, so this
  # saves memory.
  return IdInstance(tok_type), end_pos


def MakeMatcher():
  if fastlex:
    return _MatchToken_Fast
  else:
    return _MatchToken_Slow(lex.LEXER_DEF)


if fastlex:
  IsValidVarName = fastlex.IsValidVarName
else:
  import re

# Used by osh/cmd_parse.py to validate for loop name.  Note it must be
# anchored on the right.
  _VAR_NAME_RE = re.compile(lex.VAR_NAME_RE + '$')

  def IsValidVarName(s):
    return _VAR_NAME_RE.match(s)
