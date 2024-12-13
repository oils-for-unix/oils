#!/usr/bin/env python
"""
glob_.py
"""

import re

try:
  import libc
except ImportError:
  from benchmarks import fake_libc as libc

from core import util
log = util.log


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

# TODO: Use this for ${s//pat*/__}
# NOTE: Is [!abc] negation rather than [^abc] ?
# What about unicode?  Do we have to set any global variables.

def GlobToExtendedRegex(g):
  """Convert a glob to a libc extended regexp.

  Returns:
    A ERE string, or None if it's the pattern is a constant string rather than
    a glob.
  """
  raise NotImplementedError


def GlobToPythonRegex(s, greedy=True):
  """Convert a glob to a libc extended regexp.

  Args:
    greedy: whether * should be '.*' (greedy) or '.*?' (non-greedy)

  NOTE: character classes aren't supported.

  Returns:
    A Python regex string, or None if it's the pattern is a constant string
    rather than a glob.

    regex, err?
  """
  star_pat = '.*' if greedy else '.*?'

  is_glob = False
  err = None

  i = 0
  n = len(s)
  out = []
  while i < n:
    c = s[i]
    if c == '\\':  # glob escape like \* or \?
      i += 1
      out.append(s[i])
    elif c == '*':
      is_glob = True
      out.append(star_pat)
    elif c == '?':
      is_glob = True
      out.append('.')
    # TODO: Should we enter a different state and parse these?
    elif c == '[':
      err = True  # TODO: better error
      break
    elif c == ']':
      err = True
    else:
      # e.g. . -> \.
      out.append(re.escape(c))

    i += 1

  if err:
    return None, err
  else:
    if is_glob:
      regex = ''.join(out)
    else:
      regex = None
    return regex, err


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
      g = libc.glob(arg, 0)
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
