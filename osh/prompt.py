"""
prompt.py: A LIBRARY for prompt evaluation.

User interface details should go in core/ui.py.
"""
from __future__ import print_function

import time as time_

from _devbuild.gen.id_kind_asdl import Id, Id_t
from _devbuild.gen.runtime_asdl import value, value_e, value_t
from _devbuild.gen.syntax_asdl import (
    loc, command_t, source, CompoundWord
)
from core import alloc
from core import main_loop
from core import error
from core import pyos
from core import state
from core import ui
from frontend import consts
from frontend import match
from frontend import reader
from mycpp import mylib
from osh import word_
from pylib import os_path

import libc  # gethostname()
import posix_ as posix

from typing import Dict, List, Tuple, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from core.state import Mem
  from frontend.parse_lib import ParseContext
  from osh.cmd_eval import CommandEvaluator
  from osh.word_eval import AbstractWordEvaluator

#
# Prompt Evaluation
#

PROMPT_ERROR = r'<Error: unbalanced \[ and \]> '

class _PromptEvaluatorCache(object):
  """Cache some values we don't expect to change for the life of a process."""

  def __init__(self):
    # type: () -> None
    self.cache = {}  # type: Dict[str, str]
    self.euid = -1  # invalid value

  def _GetEuid(self):
    # type: () -> int
    """Cached lookup."""
    if self.euid == -1:
      self.euid = posix.geteuid()
    return self.euid

  def Get(self, name):
    # type: (str) -> str
    if name in self.cache:
      return self.cache[name]

    if name == '$':  # \$
      value = '#' if self._GetEuid() == 0 else '$'
    elif name == 'hostname':  # for \h and \H
      value = libc.gethostname()
    elif name == 'user':  # for \u
      value = pyos.GetUserName(self._GetEuid())  # recursive call for caching
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
  def __init__(self, lang, version_str, parse_ctx, mem):
    # type: (str, str, ParseContext, Mem) -> None
    self.word_ev = None  # type: AbstractWordEvaluator

    assert lang in ('osh', 'ysh'), lang
    self.lang = lang
    self.version_str = version_str
    self.parse_ctx = parse_ctx
    self.mem = mem
    self.cache = _PromptEvaluatorCache()  # Cache to save syscalls / libc calls.

    # These caches should reduce memory pressure a bit.  We don't want to
    # reparse the prompt twice every time you hit enter.
    self.tokens_cache = {}  # type: Dict[str, List[Tuple[Id_t, str]]]
    self.parse_cache = {}  # type: Dict[str, CompoundWord]
 
  def CheckCircularDeps(self):
    # type: () -> None
    assert self.word_ev is not None

  def _ReplaceBackslashCodes(self, tokens):
    # type: (List[Tuple[Id_t, str]]) -> str
    ret = []  # type: List[str]
    non_printing = 0
    for id_, s in tokens:
      # BadBacklash means they should have escaped with \\.  TODO: Make it an error.
      # 'echo -e' has a similar issue.
      if id_ in (Id.PS_Literals, Id.PS_BadBackslash):
        ret.append(s)

      elif id_ == Id.PS_Octal3:
        i = int(s[1:], 8)
        ret.append(chr(i % 256))

      elif id_ == Id.PS_LBrace:
        non_printing += 1
        ret.append('\x01')

      elif id_ == Id.PS_RBrace:
        non_printing -= 1
        if non_printing < 0:  # e.g. \]\[
          return PROMPT_ERROR

        ret.append('\x02')

      elif id_ == Id.PS_Subst:  # \u \h \w etc.
        ch = s[1]
        if ch == '$':  # So the user can tell if they're root or not.
          r = self.cache.Get('$')

        elif ch == 'u':
          r = self.cache.Get('user')

        elif ch == 'h':
          hostname = self.cache.Get('hostname')
          # foo.com -> foo
          r, _ = mylib.split_once(hostname, '.')

        elif ch == 'H':
          r = self.cache.Get('hostname')

        elif ch == 's':
          r = self.lang

        elif ch == 'v':
          r = self.version_str

        elif ch == 'A':
          now = time_.time()
          r = time_.strftime('%H:%M', time_.localtime(now))

        elif ch == 'D':  # \D{%H:%M} is the only one with a suffix
          now = time_.time()
          fmt = s[3:-1]  # \D{%H:%M}
          if len(fmt) == 0:
            # In bash y.tab.c uses %X when string is empty
            # This doesn't seem to match exactly, but meh for now.
            fmt = '%X'
          r = time_.strftime(fmt, time_.localtime(now))

        elif ch == 'w':
          try:
            pwd = state.GetString(self.mem, 'PWD')
            home = state.MaybeString(self.mem, 'HOME')  # doesn't have to exist
            # Shorten to ~/mydir
            r = ui.PrettyDir(pwd, home)
          except error.Runtime as e:
            r = '<Error: %s>' % e.UserErrorString()

        elif ch == 'W':
          val = self.mem.GetValue('PWD')
          if val.tag() == value_e.Str:
            str_val = cast(value.Str, val)
            r = os_path.basename(str_val.s)
          else:
            r = '<Error: PWD is not a string> '

        else:
          r = consts.LookupCharPrompt(ch)

          # TODO: Handle more codes
          # R(r'\\[adehHjlnrstT@AuvVwW!#$\\]', Id.PS_Subst),
          if r is None:
            r = r'<Error: \%s not implemented in $PS1> ' % ch

        # See comment above on bash hack for $.
        ret.append(r.replace('$', '\\$'))

      else:
        raise AssertionError('Invalid token %r %r' % (id_, s))

    # mismatched brackets, see https://github.com/oilshell/oil/pull/256
    if non_printing != 0:
      return PROMPT_ERROR

    return ''.join(ret)

  def EvalPrompt(self, UP_val):
    # type: (value_t) -> str
    """Perform the two evaluations that bash does.  Used by $PS1 and ${x@P}."""
    if UP_val.tag() != value_e.Str:
      return ''  # e.g. if the user does 'unset PS1'

    val = cast(value.Str, UP_val)

    # Parse backslash escapes (cached)
    tokens = self.tokens_cache.get(val.s)
    if tokens is None:
      tokens = match.Ps1Tokens(val.s)
      self.tokens_cache[val.s] = tokens

    # Replace values.
    ps1_str = self._ReplaceBackslashCodes(tokens)

    # Parse it like a double-quoted word (cached).  TODO: This could be done on
    # mem.SetValue(), so we get the error earlier.
    # NOTE: This is copied from the PS4 logic in Tracer.
    ps1_word = self.parse_cache.get(ps1_str)
    if ps1_word is None:
      w_parser = self.parse_ctx.MakeWordParserForPlugin(ps1_str)
      try:
        ps1_word = w_parser.ReadForPlugin()
      except error.Parse as e:
        ps1_word = word_.ErrorWord(
            "<ERROR: Can't parse PS1: %s>" % e.UserErrorString())
      self.parse_cache[ps1_str] = ps1_word

    # Evaluate, e.g. "${debian_chroot}\u" -> '\u'
    val2 = self.word_ev.EvalForPlugin(ps1_word)
    return val2.s

  def EvalFirstPrompt(self):
    # type: () -> str
    if self.lang == 'osh':
      val = self.mem.GetValue('PS1')
      return self.EvalPrompt(val)
    else:
      # TODO: If the lang is Oil, we should use a better prompt language than
      # $PS1!!!
      return self.lang + '$ '

PROMPT_COMMAND = 'PROMPT_COMMAND'

class UserPlugin(object):
  """For executing PROMPT_COMMAND and caching its parse tree.

  Similar to core/dev.py:Tracer, which caches $PS4.
  """
  def __init__(self, mem, parse_ctx, cmd_ev, errfmt):
    # type: (Mem, ParseContext, CommandEvaluator, ui.ErrorFormatter) -> None
    self.mem = mem
    self.parse_ctx = parse_ctx
    self.cmd_ev = cmd_ev
    self.errfmt = errfmt

    self.arena = parse_ctx.arena
    self.parse_cache = {}  # type: Dict[str, command_t]

  def Run(self):
    # type: () -> None
    val = self.mem.GetValue(PROMPT_COMMAND)
    if val.tag() != value_e.Str:
      return

    # PROMPT_COMMAND almost never changes, so we try to cache its parsing.
    # This avoids memory allocations.
    prompt_cmd = cast(value.Str, val).s
    node = self.parse_cache.get(prompt_cmd)
    if node is None:
      line_reader = reader.StringLineReader(prompt_cmd, self.arena)
      c_parser = self.parse_ctx.MakeOshParser(line_reader)

      # NOTE: This is similar to CommandEvaluator.ParseTrapCode().
      src = source.Variable(PROMPT_COMMAND, loc.Missing)
      with alloc.ctx_Location(self.arena, src):
        try:
          node = main_loop.ParseWholeFile(c_parser)
        except error.Parse as e:
          self.errfmt.PrettyPrintError(e)
          return  # don't execute

      self.parse_cache[prompt_cmd] = node

    # Save this so PROMPT_COMMAND can't set $?
    with state.ctx_Registers(self.mem):
      # Catches fatal execution error
      self.cmd_ev.ExecuteAndCatch(node)
