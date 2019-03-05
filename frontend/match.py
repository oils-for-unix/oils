#!/usr/bin/python
"""
match.py - match with generated re2c code or Python regexes.
"""

import posix

#from core import util
from frontend import lex
from core.meta import Id, IdInstance

from _devbuild.gen.id_kind_asdl import Id_t
from _devbuild.gen.types_asdl import lex_mode_t

from typing import Iterator, Tuple

# bin/osh should work without compiling fastlex?  But we want all the unit
# tests to run with a known version of it.
try:
  import fastlex
except ImportError:
  fastlex = None  # type: ignore

if fastlex:
  # Shouldn't use re module in this case
  re = None
else:
  import re  # type: ignore


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
  # type: (lex_mode_t, str, int) -> Tuple[Id_t, int]
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
    # type: (str) -> Iterator[Tuple[Id_t, str]]
    """Yields tokens."""
    pos = 0
    while True:
      tok_type, end_pos = self.match_func(line, pos)
      # core/lexer_gen.py always inserts this.  We're always parsing lines.
      if tok_type == Id.Eol_Tok:
        break
      yield tok_type, line[pos:end_pos]
      pos = end_pos


class _MatchTokenSlow(object):
  def __init__(self, pat_list):
    self.pat_list = _CompileAll(pat_list)

  def __call__(self, line, start_pos):
    return _LongestMatch(self.pat_list, line, start_pos)


def _MatchEchoToken_Fast(line, start_pos):
  # type: (str, int) -> Tuple[Id_t, int]
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchEchoToken(line, start_pos)
  return IdInstance(tok_type), end_pos

def _MatchGlobToken_Fast(line, start_pos):
  # type: (str, int) -> Tuple[Id_t, int]
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchGlobToken(line, start_pos)
  return IdInstance(tok_type), end_pos

def _MatchPS1Token_Fast(line, start_pos):
  # type: (str, int) -> Tuple[Id_t, int]
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchPS1Token(line, start_pos)
  return IdInstance(tok_type), end_pos

def _MatchHistoryToken_Fast(line, start_pos):
  # type: (str, int) -> Tuple[Id_t, int]
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchHistoryToken(line, start_pos)
  return IdInstance(tok_type), end_pos


if fastlex:
  MATCHER = _MatchOshToken_Fast
  ECHO_MATCHER = _MatchEchoToken_Fast
  GLOB_MATCHER = _MatchGlobToken_Fast
  PS1_MATCHER = _MatchPS1Token_Fast
  HISTORY_MATCHER = _MatchHistoryToken_Fast
  IsValidVarName = fastlex.IsValidVarName
else:
  MATCHER = _MatchOshToken_Slow(lex.LEXER_DEF)
  ECHO_MATCHER = _MatchTokenSlow(lex.ECHO_E_DEF)
  GLOB_MATCHER = _MatchTokenSlow(lex.GLOB_DEF)
  PS1_MATCHER = _MatchTokenSlow(lex.PS1_DEF)
  HISTORY_MATCHER = _MatchTokenSlow(lex.HISTORY_DEF)

  # Used by osh/cmd_parse.py to validate for loop name.  Note it must be
  # anchored on the right.
  _VAR_NAME_RE = re.compile(lex.VAR_NAME_RE + '$')  # type: ignore

  def IsValidVarName(s):  # type: ignore # duplicates a MyPy name?
    return _VAR_NAME_RE.match(s)

ECHO_LEXER = SimpleLexer(ECHO_MATCHER)
GLOB_LEXER = SimpleLexer(GLOB_MATCHER)
PS1_LEXER = SimpleLexer(PS1_MATCHER)
HISTORY_LEXER = SimpleLexer(HISTORY_MATCHER)
