#!/usr/bin/python
"""
match.py - match with generated re2c code or Python regexes.
"""

import os

#from core import util
from osh import lex
from osh.meta import Id, IdInstance

# bin/osh should work without compiling fastlex?  But we want all the unit
# tests to run with a known version of it.
if os.environ.get('FASTLEX') == '0':  # For manual testing
  fastlex = None
else:
  try:
    import fastlex
  except ImportError:
    fastlex = None

if fastlex:
  re = None  # Shouldn't use re module in this case
else:
  import re


def _LongestMatch(re_list, line, start_pos):
  # Simulate the EOL handling in re2c.
  if start_pos >= len(line):
    return Id.Eol_Tok, start_pos

  matches = []
  for regex, tok_type in re_list:
    m = regex.match(line, start_pos)  # left-anchored
    if m:
      matches.append((m.end(0), tok_type, m.group(0)))
  if not matches:
    raise AssertionError('no match at position %d: %r' % (start_pos, line))
  end_pos, tok_type, tok_val = max(matches, key=lambda m: m[0])
  #util.log('%s %s', tok_type, end_pos)
  return tok_type, end_pos


def _CompileAll(pat_list):
  result = []
  for is_regex, pat, token_id in pat_list:
    if not is_regex:
      pat = re.escape(pat)  # turn $ into \$
    result.append((re.compile(pat), token_id))
  return result


class _MatchOshToken_Slow(object):
  """An abstract matcher that doesn't depend on OSH."""
  def __init__(self, lexer_def):
    self.lexer_def = {}
    for lex_mode, pat_list in lexer_def.items():
      self.lexer_def[lex_mode] = _CompileAll(pat_list)

  def __call__(self, lex_mode, line, start_pos):
    """Returns (id, end_pos)."""
    re_list = self.lexer_def[lex_mode]

    return _LongestMatch(re_list, line, start_pos)
  

def _MatchOshToken_Fast(lex_mode, line, start_pos):
  """Returns (Id, end_pos)."""
  tok_type, end_pos = fastlex.MatchOshToken(lex_mode.enum_id, line, start_pos)
  # IMPORTANT: We're reusing Id instances here.  Ids are very common, so this
  # saves memory.
  return IdInstance(tok_type), end_pos


class SimpleLexer(object):
  """Lexer for echo -e, which interprets C-escaped strings."""
  def __init__(self, match_func):
    self.match_func = match_func

  def Tokens(self, line):
    """Yields tokens."""
    pos = 0
    # NOTE: We're not using Eol_Tok like LineLexer.  We probably should.  And
    # then the consumers of the ECHO_E_DEF and GLOB_DEF should use it.  Get rid
    # of Glob_Eof.
    n = len(line)
    while pos != n:
      # NOTE: Need longest-match semantics to find \377 vs \.
      tok_type, end_pos = self.match_func(line, pos)
      yield tok_type, line[pos:end_pos]
      pos = end_pos


class _MatchTokenSlow(object):
  def __init__(self, pat_list):
    self.pat_list = _CompileAll(pat_list)

  def __call__(self, line, start_pos):
    return _LongestMatch(self.pat_list, line, start_pos)


def _MatchEchoToken_Fast(line, start_pos):
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchEchoToken(line, start_pos)
  return IdInstance(tok_type), end_pos


def _MatchGlobToken_Fast(line, start_pos):
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchGlobToken(line, start_pos)
  return IdInstance(tok_type), end_pos


if fastlex:
  MATCHER = _MatchOshToken_Fast
  ECHO_MATCHER = _MatchEchoToken_Fast
  GLOB_MATCHER = _MatchGlobToken_Fast
  IsValidVarName = fastlex.IsValidVarName
else:
  MATCHER = _MatchOshToken_Slow(lex.LEXER_DEF)
  ECHO_MATCHER = _MatchTokenSlow(lex.ECHO_E_DEF)
  GLOB_MATCHER = _MatchTokenSlow(lex.GLOB_DEF)

  # Used by osh/cmd_parse.py to validate for loop name.  Note it must be
  # anchored on the right.
  _VAR_NAME_RE = re.compile(lex.VAR_NAME_RE + '$')

  def IsValidVarName(s):
    return _VAR_NAME_RE.match(s)

ECHO_LEXER = SimpleLexer(ECHO_MATCHER)
GLOB_LEXER = SimpleLexer(GLOB_MATCHER)
