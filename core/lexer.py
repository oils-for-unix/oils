#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
lexer.py - Library for lexing.
"""

import re

from core import util
from core.id_kind import Id

from osh import ast_ as ast


def C(pat, tok_type):
  """ Create a constant mapping like C('$*', VSub_Star) """
  return (False, pat, tok_type)


def R(pat, tok_type):
  """ Create a constant mapping like C('$*', VSub_Star) """
  return (True, pat, tok_type)


def CompileAll(pat_list):
  result = []
  for is_regex, pat, token_id in pat_list:
    if not is_regex:
      pat = re.escape(pat)  # turn $ into \$
    result.append((re.compile(pat), token_id))
  return result


class LineLexer(object):
  def __init__(self, match_func, line, arena=None):
    # Compile all regexes
    self.match_func = match_func
    self.arena = arena

    self.arena_skip = False  # For MaybeUnreadOne
    self.last_span_id = 0  # For MaybeUnreadOne

    self.Reset(line, -1)  # Invalid arena index to start

  def Reset(self, line, line_id):
    self.line = line
    self.line_pos = 0
    self.line_id = line_id

  def MaybeUnreadOne(self):
    """Return True if we can unread one character, or False otherwise.

    NOTE: Only call this when you know the last token was exactly on character!
    """
    if self.line_pos == 0:
      return False
    else:
      self.line_pos -= 1
      self.arena_skip = True  # don't add the next token to the arena
      return True

  def GetSpanIdForEof(self):
    assert self.arena, self.arena  # This is mandatory now?
    # zero length is special!
    line_span = ast.line_span(self.line_id, self.line_pos, 0)
    return self.arena.AddLineSpan(line_span)

  def LookAhead(self, lex_mode):
    """Look ahead for a non-space token, using the given lexer mode.

    Does NOT advance self.line_pos.

    Called with at least the following modes:
      lex_mode_e.ARITH -- for ${a[@]} vs ${a[1+2]}
      lex_mode_e.VS_1
      lex_mode_e.OUTER
    """
    pos = self.line_pos
    #print('Look ahead from pos %d, line %r' % (pos,self.line))
    while True:
      if pos == len(self.line):
        # We don't allow lookahead while already at end of line, because it
        # would involve interacting with the line reader, and we never need
        # it.  In the OUTER mode, there is an explicit newline token, but
        # ARITH doesn't have it.
        t = ast.token(Id.Unknown_Tok, '', 0)  # no span ID
        return t

      tok_type, end_pos = self.match_func(lex_mode, self.line, pos)
      tok_val = self.line[pos:end_pos]
      # NOTE: Instead of hard-coding this token, we could pass it in.  This
      # one only appears in OUTER state!  LookAhead(lex_mode, past_token_type)
      if tok_type != Id.WS_Space:
        break
      pos = end_pos

    return ast.token(tok_type, tok_val, 0)  # no span ID

  def AtEnd(self):
    return self.line_pos == len(self.line)

  def Read(self, lex_mode):
    if self.AtEnd():
      raise AssertionError('EOF')

    tok_type, end_pos = self.match_func(lex_mode, self.line, self.line_pos)
    tok_val = self.line[self.line_pos:end_pos]

    # NOTE: tok_val is redundant, but even in osh.asdl we have some separation
    # between data needed for formatting and data needed for execution.  Could
    # revisit this later.

    # TODO: Add this back once arena is threaded everywhere
    #assert self.line_id != -1
    line_span = ast.line_span(self.line_id, self.line_pos, len(tok_val))

    # NOTE: We're putting the arena hook in LineLexer and not Lexer because we
    # want it to be "low level".  The only thing fabricated here is a newline
    # added at the last line, so we don't end with \0.

    if self.arena is not None:
      if self.arena_skip:
        assert self.last_span_id != 0
        span_id = self.last_span_id
        self.arena_skip = False
      else:
        span_id = self.arena.AddLineSpan(line_span)
        self.last_span_id = span_id
    else:
      # Completion parser might not have arena?
      # We should probably get rid of this.
      span_id = 0

    t = ast.token(tok_type, tok_val, span_id)

    self.line_pos = end_pos
    return t


class Lexer(object):
  """
  Read lines from the line_reader, split them into tokens with line_lexer,
  returning them in a stream.
  """
  def __init__(self, line_lexer, line_reader):
    """
    Args:
      line_lexer: Underlying object to get tokens from
      line_reader: get new lines from here
    """
    self.line_lexer = line_lexer
    self.line_reader = line_reader
    self.was_line_cont = False  # last token was line continuation?

    self.line_id = -1  # Invalid one
    self.translation_stack = []

  def MaybeUnreadOne(self):
    return self.line_lexer.MaybeUnreadOne()

  def LookAhead(self, lex_mode):
    """Look ahead in the current line for the next non-space token.

    NOTE: Limiting lookahead to the current line makes the code a lot simpler
    at the cost of a rare (and superfluous) corner case.  This is not
    recognized as a function:

    foo\
    () {}

    Of course, this is the proper way to break it:

    foo()
    {}
    """
    return self.line_lexer.LookAhead(lex_mode)

  def PushHint(self, old_id, new_id):
    """
    Use cases:
    Id.Op_RParen -> Id.Right_Subshell -- disambiguate
    Id.Op_RParen -> Id.Eof_RParen

    Problems for $() nesting.

    - posix:
      - case foo) and case (foo)
      - func() {}
      - subshell ( )
    - bash extensions:
      - precedence in [[,   e.g.  [[ (1 == 2) && (2 == 3) ]]
      - arrays: a=(1 2 3), a+=(4 5)
    """
    self.translation_stack.append((old_id, new_id))

  def _Read(self, lex_mode):
    if self.line_lexer.AtEnd():
      line_id, line = self.line_reader.GetLine()

      if line is None:  # no more lines
        span_id = self.line_lexer.GetSpanIdForEof()
        t = ast.token(Id.Eof_Real, '', span_id)
        return t

      self.line_lexer.Reset(line, line_id)

    t = self.line_lexer.Read(lex_mode)

    # e.g. translate ) or ` into EOF
    if self.translation_stack:
      old_id, new_id = self.translation_stack[-1]  # top
      if t.id == old_id:
        #print('==> TRANSLATING %s ==> %s' % (t, new_s))
        self.translation_stack.pop()
        #print(self.translation_stack)
        t.id = new_id

    return t

  # TODO: Collapse newlines here instead of in the WordParser?
  def Read(self, lex_mode):
    while True:
      t = self._Read(lex_mode)

      self.was_line_cont = (t.id == Id.Ignored_LineCont)

      # TODO: Change to ALL IGNORED types, once you have SPACE_TOK.  This means
      # we don't have to handle them in the VS_1/VS_2/etc. states.
      if t.id != Id.Ignored_LineCont:
        break

    #print("T", t, lex_mode)
    return t
