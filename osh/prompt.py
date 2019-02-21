#!/usr/bin/python
"""
prompt.py: A LIBRARY for prompt evaluation.

User interface details should go in core/ui.py.
"""
from __future__ import print_function

import sys

import posix
import pwd

from core.meta import runtime_asdl, syntax_asdl, Id
from frontend import match
from pylib import os_path

value_e = runtime_asdl.value_e
word = syntax_asdl.word
word_part = syntax_asdl.word_part

import libc  # gethostname()

#
# Prompt Evaluation
#

# Global instance set by main().  TODO: Use dependency injection.
PROMPT = None

# NOTE: word_compile._ONE_CHAR has some of the same stuff.
_ONE_CHAR = {
  'a' : '\a',
  'e' : '\x1b',
  'r': '\r',
  'n': '\n',
  '\\' : '\\',
}


def _GetUserName(uid):
  try:
    e = pwd.getpwuid(uid)
  except KeyError:
    return "<ERROR: Couldn't determine user name for uid %d>" % uid
  else:
    return e.pw_name


class _PromptEvaluatorCache(object):
  """Cache some values we don't expect to change for the life of a process."""

  def __init__(self):
    self.cache = {}

  def Get(self, name):
    if name in self.cache:
      return self.cache[name]

    if name == 'euid':  # for \$ and \u
      value = posix.geteuid()
    elif name == 'hostname':  # for \h and \H
      value = libc.gethostname()
    elif name == 'user':  # for \u
      value = _GetUserName(self.Get('euid'))  # recursive call for caching
    else:
      raise AssertionError(name)

    self.cache[name] = value
    return value


class Evaluator(object):
  """Evaluate the prompt mini-language.

  bash has a very silly algorithm:
  1. replace backslash codes, except any $ in those values get quoted into \$.
  2. Parse the word as if it's in a double quoted context, and then evaluate
  the word.

  Haven't done this from POSIX: POSIX:
  http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html

  The shell shall replace each instance of the character '!' in PS1 with the
  history file number of the next command to be typed. Escaping the '!' with
  another '!' (that is, "!!" ) shall place the literal character '!' in the
  prompt.
  """
  def __init__(self, lang, arena, parse_ctx, ex, mem):
    assert lang in ('osh', 'oil'), lang
    self.lang = lang
    self.arena = arena
    self.parse_ctx = parse_ctx
    self.ex = ex
    self.mem = mem

    # The default prompt is osh$ or oil$ for now.  bash --noprofile --norc ->
    # 'bash-4.3$ '
    self.default_prompt = lang + '$ '
    self.cache = _PromptEvaluatorCache()  # Cache to save syscalls / libc calls.

    # These caches should reduce memory pressure a bit.  We don't want to
    # reparse the prompt twice every time you hit enter.
    self.tokens_cache = {}  # string -> list of tokens
    self.parse_cache = {}  # string -> CompoundWord.

  def _ReplaceBackslashCodes(self, tokens):
    ret = []
    non_printing = 0
    for id_, value in tokens:
      # BadBacklash means they should have escaped with \\, but we can't 
      # make this an error.
      if id_ in (Id.PS_Literals, Id.PS_BadBackslash):
        ret.append(value)

      elif id_ == Id.PS_Octal3:
        i = int(value[1:], 8)
        ret.append(chr(i % 256))

      elif id_ == Id.PS_LBrace:
        non_printing += 1

      elif id_ == Id.PS_RBrace:
        non_printing -= 1

      elif id_ == Id.PS_Subst:  # \u \h \w etc.
        char = value[1:]
        if char == '$':  # So the user can tell if they're root or not.
          r = '#' if self.cache.Get('euid') == 0 else '$'

        elif char == 'u':
          r = self.cache.Get('user')

        elif char == 'h':
          r = self.cache.Get('hostname').split('.')[0]

        elif char == 'H':
          r = self.cache.Get('hostname')

        elif char == 'w':
          # TODO: This should shorten to ~foo when applicable.
          val = self.mem.GetVar('PWD')
          if val.tag == value_e.Str:
            r = val.s
          else:
            r = '<Error: PWD is not a string>'

        elif char == 'W':
          val = self.mem.GetVar('PWD')
          if val.tag == value_e.Str:
            r = os_path.basename(val.s)
          else:
            r = '<Error: PWD is not a string>'

        elif char in _ONE_CHAR:
          r = _ONE_CHAR[char]

        else:
          r = '<\%s not implemented in $PS1> $' % char

        # See comment above on bash hack for $.
        ret.append(r.replace('$', '\\$'))

      else:
        raise AssertionError('Invalid token %r' % id_)

    return ''.join(ret)

  def EvalPrompt(self, val):
    """Perform the two evaluations that bash does.  Used by $PS1 and ${x@P}."""
    if val.tag != value_e.Str:
      return self.default_prompt  # no evaluation necessary

    # Parse backslash escapes (cached)
    try:
      tokens = self.tokens_cache[val.s]
    except KeyError:
      tokens = list(match.PS1_LEXER.Tokens(val.s))
      self.tokens_cache[val.s] = tokens

    # Replace values.
    ps1_str = self._ReplaceBackslashCodes(tokens)

    # Parse it like a double-quoted word (cached).
    # NOTE: This is copied from the PS4 logic in Tracer.
    try:
      ps1_word = self.parse_cache[ps1_str]
    except KeyError:
      w_parser = self.parse_ctx.MakeWordParserForPlugin(ps1_str, self.arena)
      try:
        ps1_word = w_parser.ReadForPlugin()
      except Exception as e:
        error_str = '<ERROR: cannot parse PS1>'
        t = syntax_asdl.token(Id.Lit_Chars, error_str, const.NO_INTEGER)
        ps1_word = word.CompoundWord([word_part.LiteralPart(t)])
      self.parse_cache[ps1_str] = ps1_word

    # Evaluate, e.g. "${debian_chroot}\u" -> '\u'
    # TODO: Handle runtime errors like unset variables, etc.
    val2 = self.ex.word_ev.EvalWordToString(ps1_word)
    return val2.s

  def FirstPromptEvaluator(self):
    if self.lang == 'osh':
      val = self.mem.GetVar('PS1')
      return self.EvalPrompt(val)
    else:
      # TODO: If the lang is Oil, we should use a better prompt language than
      # $PS1!!!
      return self.default_prompt
