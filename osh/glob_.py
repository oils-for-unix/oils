"""
glob_.py
"""

import libc

from _devbuild.gen.id_kind_asdl import Id, Id_t
from _devbuild.gen.syntax_asdl import (
    compound_word, Token, word_part_e,
    glob_part_e, glob_part, glob_part_t,
    glob_part__Literal, glob_part__Operator, glob_part__CharClass,
)
from core import util
#from core.util import log
from frontend import match

from typing import List, Tuple, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from osh.state import ExecOpts
  from frontend.match import SimpleLexer


def LooksLikeGlob(s):
  # type: (str) -> bool
  """Does this string look like a glob pattern?

  Like other shells, OSH avoids calls to glob() unless there are glob
  metacharacters.

  TODO: Reference lib/glob /   glob_pattern functions in bash
  $ grep glob_pattern lib/glob/*

  Used:
  1. in Globber below
  2. for the slow path / fast path of prefix/suffix/patsub ops.
  """
  left_bracket = False
  i = 0
  n = len(s)
  while i < n:
    c = s[i]
    if c == '\\':
      i += 1
    elif c == '*' or c == '?':
      return True
    elif c == '[':
      left_bracket = True
    elif c == ']' and left_bracket:
      # It has at least one pair of balanced [].  Not bothering to check stray
      # [ or ].
      return True
    i += 1
  return False


def LooksLikeStaticGlob(w):
  # type: (compound_word) -> bool
  """Like LooksLikeGlob, but for static words."""

  left_bracket = False
  for part in w.parts:
    if part.tag_() == word_part_e.Literal:
      id_ = cast(Token, part).id
      if id_ in (Id.Lit_Star, Id.Lit_QMark):
        return True
      elif id_ == Id.Lit_LBracket:
        left_bracket = True
      elif id_ == Id.Lit_RBracket and left_bracket:
        return True
  return False


# Glob Helpers for WordParts.
# NOTE: Escaping / doesn't work, because it's not a filename character.
# ! : - are metachars within character classes
GLOB_META_CHARS = r'\*?[]-:!'

def GlobEscape(s):
  # type: (str) -> str
  """
  For SingleQuoted, DoubleQuoted, and EscapedLiteral
  """
  return util.BackslashEscape(s, GLOB_META_CHARS)


def EreCharClassEscape(s):
  # type: (str) -> str

  # \ is escaping
  # ^ would invert it at the front,
  # - is range
  #
  # ] would close it -- but there is a weird posix rule where it has to be put
  # FIRST.  Like []abc].
  return util.BackslashEscape(s, r'\^-')


ERE_META_CHARS = r'\?*+{}^$.()|'

def ExtendedRegexEscape(s):
  # type: (str) -> str
  """
  Quoted parts need to be regex-escaped when quoted, e.g. [[ $a =~ "{" ]].  I
  don't think libc has a function to do this.  Escape these characters:

  https://www.gnu.org/software/sed/manual/html_node/ERE-syntax.html
  """
  return util.BackslashEscape(s, ERE_META_CHARS)



def GlobUnescape(s):  # used by cmd_exec
  # type: (str) -> str
  """Remove glob escaping from a string.

  Used when there is no glob match.
  TODO: Can probably get rid of this, as long as you save the original word.

  Complicated example: 'a*b'*.py, which will be escaped to a\*b*.py.  So in
  word_eval _JoinElideEscape and EvalWordToString you have to build two
  'parallel' strings -- one escaped and one not.
  """
  unescaped = []  # type: List[str]
  i = 0
  n = len(s)
  while i < n:
    c = s[i]
    if c == '\\':
      assert i != n - 1, 'Trailing backslash: %r' % s
      i += 1
      c2 = s[i]
      if c2 in GLOB_META_CHARS:
        unescaped.append(c2)
      else:
        raise AssertionError("Unexpected escaped character %r" % c2)
    else:
      unescaped.append(c)
    i += 1
  return ''.join(unescaped)


# For ${x//foo*/y}, we need to glob patterns, but fnmatch doesn't give you the
# positions of matches.  So we convert globs to regexps.

# Problems:
# - What about unicode?  Do we have to set any global variables?  We want it to
#   always use utf-8?

class _GlobParser(object):

  def __init__(self, lexer):
    # type: (SimpleLexer) -> None
    self.lexer = lexer
    self.token_type = Id.Undefined_Tok
    self.token_val = ''
    self.warnings = []  # type: List[str]

  def _Next(self):
    # type: () -> None
    """Move to the next token."""
    self.token_type, self.token_val = self.lexer.Next()

  def _ParseCharClass(self):
    # type: () -> List[glob_part_t]
    """
    Returns:
      a CharClass if the parse suceeds, or a Literal if fails.  In the latter
      case, we also append a warning.
    """
    first_token = glob_part.Literal(self.token_type, self.token_val)
    balance = 1  # We already saw a [
    tokens = []  # type: List[Tuple[Id_t, str]]

    # NOTE: There is a special rule where []] and [[] are valid globs.  Also
    # [^[] and sometimes [^]], although that one is ambiguous!
    # And [[:space:]] and [[.class.]] has to be taken into account too.  I'm
    # punting on this now because the rule isn't clear and consistent between
    # shells.

    while True:
      self._Next()

      if self.token_type == Id.Eol_Tok:
        # TODO: location info
        self.warnings.append('Malformed character class; treating as literal')
        parts = [first_token]  # type: List[glob_part_t]
        for (id_, s) in tokens:
          parts.append(glob_part.Literal(id_, s))
        return parts

      if self.token_type == Id.Glob_LBracket:
        balance += 1
      elif self.token_type == Id.Glob_RBracket:
        balance -= 1

      if balance == 0:
        break
      tokens.append((self.token_type, self.token_val))  # Don't append the last ]

    negated = False
    if len(tokens):
      id1, _ = tokens[0]
      # NOTE: Both ! and ^ work for negation in globs
      # https://www.gnu.org/software/bash/manual/html_node/Pattern-Matching.html#Pattern-Matching
      # TODO: Warn about the one that's not recommended?
      if id1 in (Id.Glob_Bang, Id.Glob_Caret):
        negated = True
        tokens = tokens[1:]
    #strs = [s for _, s in tokens]
    return [glob_part.CharClass(negated, [s for _, s in tokens])]

  def Parse(self):
    # type: () -> Tuple[List[glob_part_t], List[str]]
    """
    Returns:
      regex string (or None if it's not a glob)
      A list of warnings about the syntax
    """
    parts = []  # type: List[glob_part_t]

    while True:
      self._Next()
      id_ = self.token_type
      s = self.token_val

      #util.log('%s %r', self.token_type, self.token_val)
      if id_ == Id.Eol_Tok:
        break

      if id_ in (Id.Glob_Star, Id.Glob_QMark):
        parts.append(glob_part.Operator(id_))

      elif id_ == Id.Glob_LBracket:
        # Could return a Literal or a CharClass
        parts.extend(self._ParseCharClass())

      else: # Glob_{Bang,Caret,CleanLiterals,OtherLiteral,RBracket,EscapedChar,
            #       BadBackslash}
        parts.append(glob_part.Literal(id_, s))

      # Also check for warnings.  TODO: location info.
      if id_ == Id.Glob_RBracket:
        self.warnings.append('Got unescaped right bracket')
      if id_ == Id.Glob_BadBackslash:
        self.warnings.append('Got unescaped trailing backslash')

    return parts, self.warnings


_REGEX_CHARS_TO_ESCAPE = '.|^$()+*?[]{}\\'

def _GenerateERE(parts):
  # type: (List[glob_part_t]) -> str
  out = []  # type: List[str]

  for part in parts:
    tag = part.tag_()
    UP_part = part

    if tag == glob_part_e.Literal:
      part = cast(glob_part__Literal, UP_part)
      if part.id == Id.Glob_EscapedChar:
        assert len(part.s) == 2, part.s
        # The user could have escaped a char that doesn't need regex escaping,
        # like \b or something.
        c = part.s[1]
        if c in _REGEX_CHARS_TO_ESCAPE:
          out.append('\\')
        out.append(c)

      elif part.id == Id.Glob_CleanLiterals:
        out.append(part.s)  # e.g. 'py' doesn't need to be escaped

      elif part.id == Id.Glob_OtherLiteral:
        assert len(part.s) == 1, part.s
        c = part.s
        if c in _REGEX_CHARS_TO_ESCAPE:
          out.append('\\')
        out.append(c)

      # These are UNMATCHED ones not parsed in a glob class
      elif part.id == Id.Glob_LBracket:
        out.append('\\[')

      elif part.id == Id.Glob_RBracket:
        out.append('\\]')

      elif part.id == Id.Glob_BadBackslash:
        out.append('\\\\')

      else:
        raise AssertionError(part.id)

    elif tag == glob_part_e.Operator:
      part = cast(glob_part__Operator, UP_part)
      if part.op_id == Id.Glob_QMark:
        out.append('.')
      elif part.op_id == Id.Glob_Star:
        out.append('.*')
      else:
        raise AssertionError()

    elif tag == glob_part_e.CharClass:
      part = cast(glob_part__CharClass, UP_part)
      out.append('[')
      if part.negated:
        out.append('^')

      # Important: the character class is LITERALLY preserved, because we
      # assume glob char classes are EXACTLY the same as regex char classes,
      # including the escaping rules.
      for s in part.strs:
        out.append(s)
      out.append(']')

  return ''.join(out)


def GlobToERE(pat):
  # type: (str) -> Tuple[str, List[str]]
  lexer = match.GlobLexer(pat)
  p = _GlobParser(lexer)
  parts, warnings = p.Parse()

  # Vestigial: if there is nothing like * ? or [abc], then the whole string is
  # a literal, and we could use a more efficient mechanism.
  # But we would have to DEQUOTE before doing that.
  if 0:
    is_glob = False
    for p in parts:
      if p.tag in (glob_part_e.Operator, glob_part_e.CharClass):
        is_glob = True
  if 0:
    print('---')
    for p in parts:
      print(p)

  regex = _GenerateERE(parts)
  return regex, warnings


class Globber(object):
  def __init__(self, exec_opts):
    # type: (ExecOpts) -> None
    self.exec_opts = exec_opts

    # NOTE: Bash also respects the GLOBIGNORE variable, but no other shells
    # do.  Could a default GLOBIGNORE to ignore flags on the file system be
    # part of the security solution?  It doesn't seem totally sound.

    # shopt: why the difference?  No command line switch I guess.
    self.dotglob = False  # dotfiles are matched
    self.globstar = False  # ** for directories
    # globasciiranges - ascii or unicode char classes (unicode by default)
    # nocaseglob
    # extglob: the !() syntax

    # TODO: Figure out which ones are in other shells, and only support those?
    # - Include globstar since I use it, and zsh has it.

  def Expand(self, arg):
    # type: (str) -> List[str]
    """Given a string that could be a glob, return a list of strings."""
    # e.g. don't glob 'echo' because it doesn't look like a glob
    if not LooksLikeGlob(arg):
      u = GlobUnescape(arg)
      return [u]
    if self.exec_opts.noglob:
      return [arg]

    try:
      #g = glob.glob(arg)  # Bad Python glob
      # PROBLEM: / is significant and can't be escaped!  Have to avoid
      # globbing it.
      g = libc.glob(arg)
    except Exception as e:  # TODO: More specific exception
      # - [C\-D] is invalid in Python?  Regex compilation error.
      # - [:punct:] not supported
      print("Error expanding glob %r: %s" % (arg, e))
      raise
    #log('glob %r -> %r', arg, g)

    if len(g):
      return g
    else:  # Nothing matched
      if self.exec_opts.failglob:
        # TODO: Make the command return status 1.
        raise NotImplementedError()
      if self.exec_opts.nullglob:
        return []
      else:
        # Return the original string
        u = GlobUnescape(arg)
        return [u]
