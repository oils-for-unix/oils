#!/usr/bin/env python3
"""
glob_.py
"""

import libc

from core.util import log


def LooksLikeGlob():
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
  pass


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


# TODO: Can probably get rid of this, as long as you save the original word.
def _GlobUnescape(s):  # used by cmd_exec
  """
  If there is no glob match, just unescape the string.
  """
  unescaped = ''
  i = 0
  n = len(s)
  while i < n:
    c = s[i]
    if c == '\\':
      assert i != n - 1, 'There should be no trailing single backslash!'
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


class Globber:
  def __init__(self, exec_opts):
    # TODO: separate into set_opts.glob_opts, and sh_opts.glob_opts?  Only if
    # other shels use the same options as bash though.

    # NOTE: Bash also respects the GLOBIGNORE variable, but no other shells do.
    # Could a default GLOBIGNORE to ignore flags on the file system be part of
    # the security solution?  It doesn't seem totally sound.

    self.noglob = False  # set -f

    # shopt: why the difference?  No command line switch I guess.
    self.dotglob = False  # dotfiles are matched
    self.failglob = False  # no matches is an error
    self.globstar = False  # ** for directories
    # globasciiranges - ascii or unicode char classes (unicode by default)
    # nocaseglob
    self.nullglob = False  # no matches evaluates to empty, otherwise
    # extglob: the !() syntax

    # TODO: Figure out which ones are in other shells, and only support those?
    # - Include globstar since I use it, and zsh has it.

  def Expand(self, arg):
    # TODO: Only try to glob if there are any glob metacharacters.
    # Or maybe it is a conservative "avoid glob" heuristic?
    #
    # Non-glob but with glob characters:
    # echo ][
    # echo []  # empty
    # echo []LICENSE  # empty
    # echo [L]ICENSE  # this one is good
    # So yeah you need to test the validity somehow.

    try:
      #g = glob.glob(arg)  # Bad Python glob
      # PROBLEM: / is significant and can't be escaped!  Hav eto avoid globbing it.
      g = libc.glob(arg)
    except Exception as e:
      # - [C\-D] is invalid in Python?  Regex compilation error.
      # - [:punct:] not supported
      print("Error expanding glob %r: %s" % (arg, e))
      raise
    #print('G', arg, g)

    #log('Globbing %s', arg)
    if g:
      return g
    else:
      u = _GlobUnescape(arg)
      return [u]
