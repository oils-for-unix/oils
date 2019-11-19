"""
match.py - match with generated re2c code or Python regexes.
"""

from _devbuild.gen.id_kind_asdl import Id, Id_t
from _devbuild.gen.types_asdl import lex_mode_t
from frontend import lex

from typing import Iterator, Tuple, Callable, Dict, List, Any, TYPE_CHECKING

# bin/osh should work without compiling fastlex?  But we want all the unit
# tests to run with a known version of it.
try:
  import fastlex
except ImportError:
  fastlex = None

if fastlex:
  # Shouldn't use re module in this case
  re = None
else:
  import re  # type: ignore


if TYPE_CHECKING:
  SRE_Pattern = Any  # Do we need a .pyi file for re or _sre?
  SimpleMatchFunc = Callable[[str, int], Tuple[Id_t, int]]
  LexerPairs = List[Tuple[SRE_Pattern, Id_t]]


def _LongestMatch(re_list, line, start_pos):
  # type: (LexerPairs, str, int) -> Tuple[Id_t, int]

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
  # type: (List[Tuple[bool, str, Id_t]]) -> LexerPairs
  result = []
  for is_regex, pat, token_id in pat_list:
    if not is_regex:
      pat = re.escape(pat)  # type: ignore  # turn $ into \$
    result.append((re.compile(pat), token_id))  # type: ignore
  return result


class _MatchOshToken_Slow(object):
  """An abstract matcher that doesn't depend on OSH."""
  def __init__(self, lexer_def):
    # type: (Dict[lex_mode_t, List[Tuple[bool, str, Id_t]]]) -> None
    self.lexer_def = {}  # type: Dict[lex_mode_t, LexerPairs]
    for lex_mode, pat_list in lexer_def.items():
      self.lexer_def[lex_mode] = _CompileAll(pat_list)

  def __call__(self, lex_mode, line, start_pos):
    # type: (lex_mode_t, str, int) -> Tuple[Id_t, int]
    """Returns (id, end_pos)."""
    re_list = self.lexer_def[lex_mode]

    return _LongestMatch(re_list, line, start_pos)


def _MatchOshToken_Fast(lex_mode, line, start_pos):
  # type: (lex_mode_t, str, int) -> Tuple[Id_t, int]
  """Returns (Id, end_pos)."""
  tok_type, end_pos = fastlex.MatchOshToken(lex_mode, line, start_pos)
  # IMPORTANT: We're reusing Id instances here.  Ids are very common, so this
  # saves memory.
  return tok_type, end_pos


class _MatchTokenSlow(object):
  def __init__(self, pat_list):
    # type: (List[Tuple[bool, str, Id_t]]) -> None
    self.pat_list = _CompileAll(pat_list)

  def __call__(self, line, start_pos):
    # type: (str, int) -> Tuple[Id_t, int]
    return _LongestMatch(self.pat_list, line, start_pos)


def _MatchEchoToken_Fast(line, start_pos):
  # type: (str, int) -> Tuple[Id_t, int]
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchEchoToken(line, start_pos)
  return tok_type, end_pos

def _MatchGlobToken_Fast(line, start_pos):
  # type: (str, int) -> Tuple[Id_t, int]
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchGlobToken(line, start_pos)
  return tok_type, end_pos

def _MatchPS1Token_Fast(line, start_pos):
  # type: (str, int) -> Tuple[Id_t, int]
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchPS1Token(line, start_pos)
  return tok_type, end_pos

def _MatchHistoryToken_Fast(line, start_pos):
  # type: (str, int) -> Tuple[Id_t, int]
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchHistoryToken(line, start_pos)
  return tok_type, end_pos

def _MatchBraceRangeToken_Fast(line, start_pos):
  # type: (str, int) -> Tuple[Id_t, int]
  """Returns (id, end_pos)."""
  tok_type, end_pos = fastlex.MatchBraceRangeToken(line, start_pos)
  return tok_type, end_pos


if fastlex:
  OneToken = _MatchOshToken_Fast
  ECHO_MATCHER = _MatchEchoToken_Fast
  GLOB_MATCHER = _MatchGlobToken_Fast
  PS1_MATCHER = _MatchPS1Token_Fast
  HISTORY_MATCHER = _MatchHistoryToken_Fast
  BRACE_RANGE_MATCHER = _MatchBraceRangeToken_Fast
  IsValidVarName = fastlex.IsValidVarName
  ShouldHijack = fastlex.ShouldHijack
else:
  OneToken = _MatchOshToken_Slow(lex.LEXER_DEF)
  ECHO_MATCHER = _MatchTokenSlow(lex.ECHO_E_DEF)
  GLOB_MATCHER = _MatchTokenSlow(lex.GLOB_DEF)
  PS1_MATCHER = _MatchTokenSlow(lex.PS1_DEF)
  HISTORY_MATCHER = _MatchTokenSlow(lex.HISTORY_DEF)
  BRACE_RANGE_MATCHER = _MatchTokenSlow(lex.BRACE_RANGE_DEF)

  # Used by osh/cmd_parse.py to validate for loop name.  Note it must be
  # anchored on the right.
  _VAR_NAME_RE = re.compile(lex.VAR_NAME_RE + '$')  # type: ignore

  def IsValidVarName(s):
    # type: (str) -> bool
    return bool(_VAR_NAME_RE.match(s))

  _SHOULD_HIJACK_RE = re.compile(lex.SHOULD_HIJACK_RE + '$')  # type: ignore

  def ShouldHijack(s):
    # type: (str) -> bool
    return bool(_SHOULD_HIJACK_RE.match(s))


class SimpleLexer(object):

  def __init__(self, match_func, s):
    # type: (SimpleMatchFunc, str) -> None
    self.match_func = match_func
    self.s = s
    self.pos = 0

  def Next(self):
    # type: () -> Tuple[Id_t, str]
    """
    Note: match_func will return Id.Eol_Tok repeatedly the terminating NUL
    """
    tok_id, end_pos = self.match_func(self.s, self.pos)
    val = self.s[self.pos:end_pos]
    self.pos = end_pos
    return tok_id, val

  def Tokens(self):
    # type: () -> List[Tuple[Id_t, str]]
    tokens = [] # type: List[Tuple[Id_t, str]]
    while True:
      tok_id, val = self.Next()
      if tok_id == Id.Eol_Tok:  # NUL terminator
        break
      tokens.append((tok_id, val))
    return tokens


# Iterated over in osh/builtin_pure.py
def EchoLexer(s):
  # type: (str) -> SimpleLexer
  return SimpleLexer(ECHO_MATCHER, s)


def BraceRangeLexer(s):
  # type: (str) -> SimpleLexer
  return SimpleLexer(BRACE_RANGE_MATCHER, s)


def GlobLexer(s):
  # type: (str) -> SimpleLexer
  return SimpleLexer(GLOB_MATCHER, s)


# These tokens are "slurped"

def HistoryTokens(s):
  # type: (str) -> List[Tuple[Id_t, str]]
  lex = SimpleLexer(HISTORY_MATCHER, s)
  return lex.Tokens()


def Ps1Tokens(s):
  # type: (str) -> List[Tuple[Id_t, str]]
  lex = SimpleLexer(PS1_MATCHER, s)
  return lex.Tokens()
