#!/usr/bin/env python
"""
glob_.py
"""

try:
  import libc
except ImportError:
  from benchmarks import fake_libc as libc

from osh.meta import glob as glob_ast
from core import util
log = util.log

glob_part_e = glob_ast.glob_part_e


def LooksLikeGlob(s):
  """
  TODO: Reference lib/glob /   glob_pattern functions in bash
  grep glob_pattern lib/glob/*

  NOTE: Dash has CTLESC = -127.
  Does that mean a string is an array of ints or shorts?  Not bytes?
  How does it handle unicode/utf-8 then?
  Nope it's using it with char* p.
  So it dash only ASCII or what?  TODO: test it

  Still need this for slow path / fast path of prefix/suffix/patsub ops.
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
      return True
    i += 1
  return False


# Glob Helpers for WordParts.
# NOTE: Escaping / doesn't work, because it's not a filename character.
# ! : - are metachars within character classes
GLOB_META_CHARS = r'\*?[]-:!'

def GlobEscape(s):
  """
  For SingleQuotedPart, DoubleQuotedPart, and EscapedLiteralPart
  """
  escaped = ''
  for c in s:
    if c in GLOB_META_CHARS:
      escaped += '\\'
    escaped += c
  return escaped


# We need to handle glob patterns, but fnmatch doesn't give you the positions
# of matches.  So we convert globs to regexps.

# Problems:
# - What about unicode?  Do we have to set any global variables?  We want it to
# always use utf-8?
# - Character class for glob is different than char class for regex?  According
# to the standard, anyway.
# - Honestly I would like a more principled parser for globs!  Can re2c do
# better here?

class GlobParser(object):
  """
  Parses glob patterns. Can convert directly to libc extended regexp or output
  an intermediate AST (defined at osh/glob.asdl).
  """

  def Parse(self, glob_pat):
    """Parses a glob pattern into AST form (defined at osh/glob.asdl).

    Returns:
      A 2-tuple of (<glob AST>, <error message>).

      If the pattern is not actually a glob, the first element is None. The
      second element is None unless there was an error during parsing.
    """
    try:
      return self._ParseUnsafe(glob_pat)

    except RuntimeError as e:
      return None, str(e)

  def _ParseUnsafe(self, glob_pat):
    """
    Parses a glob pattern into AST form.

    Raises:
      RuntimeError: if glob is invalid
    """
    is_glob = False
    i = 0
    n = len(glob_pat)
    parts = []
    while i < n:
      c = glob_pat[i]
      if c == '\\':  # glob escape like \* or \?
        i += 1
        parts.append(glob_ast.Literal(glob_pat[i]))

      elif c == '*':
        is_glob = True
        parts.append(glob_ast.Star())

      elif c == '?':
        is_glob = True
        parts.append(glob_ast.QMark())

      elif c == '[':
        is_glob = True
        char_class_expr, i = self.ParseCharClassExpr(glob_pat, i)
        parts.append(char_class_expr)

      else:
        parts.append(glob_ast.Literal(c))

      i += 1

    if is_glob:
      return glob_ast.glob(parts), None

    return None, None

  def ParseCharClassExpr(self, glob_pat, start_i):
    """Parses a character class expression, e.g. [abc], [[:space:]], [!a-z]

    Returns:
      A 2-tuple of (<CharClassExpr instance>, <next parse index>)

    Raises:
      RuntimeError: If error during parsing the character class.
    """
    i = start_i
    if glob_pat[i] != '[':
      raise RuntimeError('invalid CharClassExpr start!')

    i += 1
    # NOTE: Both ! and ^ work for negation in globs
    # https://www.gnu.org/software/bash/manual/html_node/Pattern-Matching.html#Pattern-Matching
    negated = glob_pat[i] in '!^'
    if negated:
      i += 1

    in_posix_class = False
    expr_body = []
    n = len(glob_pat)

    # NOTE: special case: ] is matched iff it's the first char in the expression
    if glob_pat[i] == ']':
      expr_body.append(']')
      i += 1

    while i < n:
      c = glob_pat[i]
      if c == ']':
        if not in_posix_class:
          break
        in_posix_class = False

      elif c == '[':
        if in_posix_class:
          raise RuntimeError('invalid character [ in CharClassExpr')
        in_posix_class = (glob_pat[i+1] == ':')

      elif c == '\\':
        expr_body.append(c)
        i += 1
        c = glob_pat[i]

      expr_body.append(c)
      i += 1

    else:
      raise RuntimeError('unclosed CharClassExpr!')

    return glob_ast.CharClassExpr(negated, ''.join(expr_body)), i

  def ASTToExtendedRegex(self, ast):
    if not ast:
      return None

    out = []
    for part in ast.parts:
      if part.tag == glob_part_e.Literal:
        if part.s in '.|^$()+*?[]{}\\':
          out.append('\\')
        out.append(part.s)

      elif part.tag == glob_part_e.Star:
        out.append('.*')

      elif part.tag == glob_part_e.QMark:
        out.append('.')

      elif part.tag == glob_part_e.CharClassExpr:
        out.append('[')
        if part.negated:
          out.append('^')
        out.append(part.body + ']')

    return ''.join(out)

  def GlobToExtendedRegex(self, glob_pat):
    ast, err = self.Parse(glob_pat)
    return self.ASTToExtendedRegex(ast), err


def _GlobUnescape(s):  # used by cmd_exec
  """Remove glob escaping from a string.

  Used when there is no glob match.
  TODO: Can probably get rid of this, as long as you save the original word.

  Complicated example: 'a*b'*.py, which will be escaped to a\*b*.py.  So in
  word_eval _JoinElideEscape and EvalWordToString you have to build two
  'parallel' strings -- one escaped and one not.
  """
  unescaped = ''
  i = 0
  n = len(s)
  while i < n:
    c = s[i]
    if c == '\\':
      assert i != n - 1, 'Trailing backslash: %r' % s
      i += 1
      c2 = s[i]
      if c2 in GLOB_META_CHARS:
        unescaped += c2
      else:
        raise AssertionError("Unexpected escaped character %r" % c2)
    else:
      unescaped += c
    i += 1
  return unescaped


class Globber(object):
  def __init__(self, exec_opts):
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
    """Given a string that could be a glob, return a list of strings."""
    # e.g. don't glob 'echo' because it doesn't look like a glob
    if not LooksLikeGlob(arg):
      u = _GlobUnescape(arg)
      return [u]
    if self.exec_opts.noglob:
      return [arg]

    try:
      #g = glob.glob(arg)  # Bad Python glob
      # PROBLEM: / is significant and can't be escaped!  Have to avoid
      # globbing it.
      g = libc.glob(arg)
    except Exception as e:
      # - [C\-D] is invalid in Python?  Regex compilation error.
      # - [:punct:] not supported
      print("Error expanding glob %r: %s" % (arg, e))
      raise
    #log('glob %r -> %r', arg, g)

    if g:
      return g
    else:  # Nothing matched
      if self.exec_opts.failglob:
        # TODO: Make the command return status 1.
        raise NotImplementedError
      if self.exec_opts.nullglob:
        return []
      else:
        # Return the original string
        u = _GlobUnescape(arg)
        return [u]
