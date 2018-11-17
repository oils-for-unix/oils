#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
ui.py - User interface constructs.
"""
from __future__ import print_function

import posix
import pwd
import sys

from asdl import const
from asdl import encode
from asdl import format as fmt
from core import dev
from osh import ast_lib
from frontend import match
from core.meta import ast, runtime, Id

import libc  # gethostname()

value_e = runtime.value_e



def Clear():
  sys.stdout.write('\033[2J')  # clear screen
  sys.stdout.write('\033[2;0H')  # Move to 2,0  (below status bar)
  sys.stdout.flush()


class StatusLine(object):
  """For optionally displaying the progress of slow completions."""

  def __init__(self, row_num=3, width=80):
    # NOTE: '%-80s' % msg doesn't do this, because it doesn't pad at the end
    self.width = width
    self.row_num = row_num

  def _FormatMessage(self, msg):
    max_width = self.width - 4  # two spaces on each side
    # Truncate if necessary.  TODO: could display truncation char?
    msg = msg[:max_width]

    num_end_spaces = max_width - len(msg) + 2  # at least 2 spaces at the end

    to_print = '  %s%s' % (msg, ' ' * num_end_spaces)
    return to_print

  def Write(self, msg, *args):
    if args:
      msg = msg % args

    sys.stdout.write('\033[s')  # save
    # TODO: When there is more than one option for completion, we scroll past
    # this.
    # TODO: Should status line be BELOW, and disappear after readline?
    # Or really it should be at the right margin?  At hit Ctrl-C to cancel?

    sys.stdout.write('\033[%d;0H' % self.row_num)  # Move the cursor

    sys.stdout.write('\033[7m')  # reverse video

    # Make sure you draw the same number of spaces
    # TODO: detect terminal width

    sys.stdout.write(self._FormatMessage(msg))

    sys.stdout.write('\033[0m')  # remove attributes

    sys.stdout.write('\033[u')  # restore
    sys.stdout.flush()


class TestStatusLine(object):
  def __init__(self):
    pass

  def Write(self, msg, *args):
    """NOTE: We could use logging?"""
    if args:
      msg = msg % args
    print('\t' + msg)


#
# Prompt handling
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


class _PromptCache(object):
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


class Prompt(object):
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
    self.cache = _PromptCache()  # Cache to save syscalls / libc calls.

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
          r = self.cache.Get('hostname')

        elif char == 'w':
          # TODO: This should shorten to ~foo when applicable.
          val = self.mem.GetVar('PWD')
          if val.tag == value_e.Str:
            r = val.s
          else:
            r = '<Error: PWD is not a string>'

        elif char in _ONE_CHAR:
          r = _ONE_CHAR[char]

        else:
          raise NotImplementedError(char)

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
        ps1_word = w_parser.ReadPS()
      except Exception as e:
        error_str = '<ERROR: cannot parse PS1>'
        t = ast.token(Id.Lit_Chars, error_str, const.NO_INTEGER)
        ps1_word = ast.CompoundWord([ast.LiteralPart(t)])
      self.parse_cache[ps1_str] = ps1_word

    # Evaluate, e.g. "${debian_chroot}\u" -> '\u'
    val2 = self.ex.word_ev.EvalWordToString(ps1_word)
    return val2.s

  def FirstPrompt(self):
    if self.lang == 'osh':
      val = self.mem.GetVar('PS1')
      return self.EvalPrompt(val)
    else:
      # TODO: If the lang is Oil, we should use a better prompt language than
      # $PS1!!!
      return self.default_prompt


def PrintFilenameAndLine(span_id, arena, f=sys.stderr):
  line_span = arena.GetLineSpan(span_id)
  line_id = line_span.line_id
  line = arena.GetLine(line_id)
  path, line_num = arena.GetDebugInfo(line_id)
  col = line_span.col
  length = line_span.length

  # TODO: If the line is blank, it would be nice to print the last non-blank
  # line too?
  print('Line %d of %r' % (line_num, path), file=f)
  print('  ' + line.rstrip(), file=f)
  f.write('  ')
  # preserve tabs
  for c in line[:col]:
    f.write('\t' if c == '\t' else ' ')
  f.write('^')
  f.write('~' * (length-1))
  f.write('\n')


def PrettyPrintError(parse_error, arena, f=sys.stderr):
  span_id = dev.SpanIdFromError(parse_error)

  # TODO: Should there be a special span_id of 0 for EOF?  const.NO_INTEGER
  # means there is no location info, but 0 could mean that the location is EOF.
  # So then you query the arena for the last line in that case?
  # Eof_Real is the ONLY token with 0 span, because it's invisible!
  # Well Eol_Tok is a sentinel with a span_id of const.NO_INTEGER.  I think
  # that is OK.
  # Problem: the column for Eof could be useful.

  if span_id == const.NO_INTEGER:  # Any clause above might return this.
    # This is usually a bug.
    print('*** Error has no source location info ***', file=f)
  else:
    PrintFilenameAndLine(span_id, arena, f=f)

  print(parse_error.UserErrorString(), file=f)


def PrintAst(nodes, opts):
  if len(nodes) == 1:
    node = nodes[0]
  else:
    node = ast.CommandList(nodes)

  if opts.ast_format == 'none':
    print('AST not printed.', file=sys.stderr)
  elif opts.ast_format == 'oheap':
    # TODO: Make this a separate flag?
    if sys.stdout.isatty():
      raise RuntimeError('ERROR: Not dumping binary data to a TTY.')
    f = sys.stdout

    enc = encode.Params()
    out = encode.BinOutput(f)
    encode.EncodeRoot(node, enc, out)

  else:  # text output
    f = sys.stdout

    if opts.ast_format in ('text', 'abbrev-text'):
      ast_f = fmt.DetectConsoleOutput(f)
    elif opts.ast_format in ('html', 'abbrev-html'):
      ast_f = fmt.HtmlOutput(f)
    else:
      raise AssertionError
    abbrev_hook = (
        ast_lib.AbbreviateNodes if 'abbrev-' in opts.ast_format else None)
    tree = fmt.MakeTree(node, abbrev_hook=abbrev_hook)
    ast_f.FileHeader()
    fmt.PrintTree(tree, ast_f)
    ast_f.FileFooter()
    ast_f.write('\n')


def usage(msg, *args):
  """For user-facing usage errors."""
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)
