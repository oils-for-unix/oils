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

import os
import pwd
import socket  # socket.gethostname()
import sys

from asdl import const
from asdl import encode
from asdl import format as fmt
from core import dev
from osh import ast_lib
from osh import match
from osh.meta import ast, runtime, Id


# bash --noprofile --norc uses 'bash-4.3$ '
DEFAULT_PS1 = 'osh$ '


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

def get_var(ex,name):
    r = ex.mem.GetVar(name)
    if r.tag == runtime.value_e.Str:
        return r.s

    return ""

def get_username():
  uid = os.getuid()
  try:
    e = pwd.getpwuid(uid)
  except KeyError:
    return None
  else:
    return e.pw_name

class Prompt(object):
  REPLACEMENTS = {
    "u" : lambda ex: get_username(),
    "h" : lambda ex: socket.gethostname(),
    "w" : lambda ex: get_var(ex, "PWD"),
    "e" : lambda ex: "\033",
    "a" : lambda ex: "\007",
    "$" : lambda ex: "$",
  }

  def __init__(self, arena, parse_ctx, ex):
    self.ps1 = DEFAULT_PS1
    self.arena = arena
    self.parse_ctx = parse_ctx
    self.ex = ex

    self.prompt_str = self.ps1
    self.parse_cache = {}  # PS1 value -> CompoundWord.

  def Reset(self):
    self.prompt_str = self._EvalPS1()

  def PS1(self):
    val = self.ex.mem.GetVar('PS1')
    return self.EvalPS1(val)

  def EvalPS1(self, val):
    if val.tag != runtime.value_e.Str:
      return self.ps1

    s = val.s
    if s:
      ps1 = s
    else:
      ps1 = self.ps1

    try:
      ps1_word = self.parse_cache[ps1]
    except KeyError:
      w_parser = self.parse_ctx.MakeWordParserForPlugin(ps1, self.arena)

      try:
        ps1_word = w_parser.ReadPS()
      except Exception as e:
        error_str = '<ERROR: cannot parse PS1>'
        t = ast.token(Id.Lit_Chars, error_str, const.NO_INTEGER)
        ps1_word = ast.CompoundWord([ast.LiteralPart(t)])

    self.parse_cache[ps1] = ps1_word

    # e.g. "${debian_chroot}\u" -> '\u'
    val = self.ex.word_ev.EvalWordToString(ps1_word)
    decoded_string = self.ReplacePS1Variables(val.s)
    return decoded_string

  def GetPS1Replacement(self, sc):
    if sc in self.REPLACEMENTS:
      r = self.REPLACEMENTS[sc](self.ex)
      return r

    raise NotImplementedError(sc)

  def ReplacePS1Variables(self, s):
    ret = []
    non_printing = 0
    for id_, value in match.PS1_LEXER.Tokens(s):
      if id_ == Id.Char_Literals or id_ == Id.Char_Hex or id_ == Id.Char_BadBackslash:
        ret.append(value)
      elif id_ == Id.Char_OneChar:
        ret.append(self.GetPS1Replacement(value[1:]))
      elif id_ == Id.Char_Octal3:
          oct_value = int(value[1:], 8)
          ret.append(chr(oct_value % 256))
      elif id_ == Id.Lit_LBrace:
        non_printing += 1
      elif id_ == Id.Lit_RBrace:
        non_printing -= 1
      else:
        raise AssertionError('Invalid token %r' % id_)

    return "".join(ret)


class TestStatusLine(object):

  def __init__(self):
    pass

  def Write(self, msg, *args):
    """NOTE: We could use logging?"""
    if args:
      msg = msg % args
    print('\t' + msg)


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


# Set by main()
PROMPT = None
