#!/usr/bin/env python3
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
from core.id_kind import Id, IdName
from core.tokens import Token


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


def FindLongestMatch(re_list, s, pos):
  """Finds the FIRST match.

  NOTE: max() appears to find the FIRST max, which we rely on.
  """
  matches = []
  for regex, tok_type in re_list:
    m = regex.match(s, pos)  # left-anchored
    if m:
      matches.append((m.end(0), tok_type, m.group(0)))
  if not matches:
    raise AssertionError('no match at position %d: %r' % (pos, s))
  end_index, tok_type, tok_val = max(matches, key=lambda m: m[0])
  return end_index, tok_type, tok_val


class LineLexer(object):
  def __init__(self, lexer_def, line):
    # Compile all regexes
    self.lexer_def = {}
    for state, pat_list in lexer_def.items():
      self.lexer_def[state] = CompileAll(pat_list)

    self.Reset(line, -1)  # Invalid pool index to start

  def Reset(self, line, pool_index):
    self.line = line
    self.line_pos = 0
    self.pool_index = pool_index

  def MaybeUnreadOne(self):
    """Return True if we can unread one character, or False otherwise.

    NOTE: Only call this when you know the last token was exactly on character!
    """
    if self.line_pos == 0:
      return False
    else:
      self.line_pos -= 1
      return True

  def LookAhead(self, lex_mode):
    """Look ahead for a non-space token, using the given lexical state."""
    pos = self.line_pos
    #print('Look ahead from pos %d, line %r' % (pos,self.line))
    while True:
      if pos == len(self.line):
        t = Token(Id.Eof_Real, '')
        return t

      re_list = self.lexer_def[lex_mode]
      end_index, tok_type, tok_val = FindLongestMatch(
          re_list, self.line, pos)
      # NOTE: Instead of hard-coding this token, we could pass it in.  This one
      # only appears in OUTER state!  LookAhead(lex_mode, past_token_type)
      if tok_type != Id.WS_Space:
        break
      pos = end_index

    return Token(tok_type, tok_val)

  def AtEnd(self):
    return self.line_pos == len(self.line)

  def Read(self, lex_mode):
    if self.AtEnd():
      raise AssertionError('EOF')

    re_list = self.lexer_def[lex_mode]

    end_index, tok_type, tok_val = FindLongestMatch(
        re_list, self.line, self.line_pos)

    t = Token(tok_type, tok_val)
    # TODO: Add this back once pool is threaded everywhere
    #assert self.pool_index != -1
    t.pool_index = self.pool_index
    t.col = self.line_pos
    t.length = len(tok_val)

    self.line_pos = end_index
    return t


class Lexer(object):
  """
  Read lines from the line_reader, split them into tokens with line_lexer,
  returning them in a stream.
  """
  def __init__(self, line_lexer, line_reader, tokens_out=None):
    """
    Args:
      line_lexer: Underlying object to get tokens from
      line_reader: get new lines from here
    """
    self.line_lexer = line_lexer
    self.line_reader = line_reader
    self.was_line_cont = False  # last token was line continuation?

    self.pool_index = -1  # Invalid one

    self.translation_stack = []
    # TODO: Move this to pool?
    # [] if we want to save an array of all tokens, or None if we don't.
    self.tokens_out = tokens_out

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
    old_s = IdName(old_id)
    new_s = IdName(new_id)
    #print('* Lexer.PushHint %s => %s' % (old_s, new_s))
    self.translation_stack.append((old_id, new_id))

  def _Read(self, lex_mode):
    if self.line_lexer.AtEnd():
      pool_index, line = self.line_reader.GetLine()

      if line is None:  # no more lines
        t = Token(Id.Eof_Real, '')
        # No line number.  I guess we are showing the last line of the file.
        t.pool_index = self.pool_index - 1
        t.col = 0
        t.length = 0
        return t

      self.line_lexer.Reset(line, pool_index)

    t = self.line_lexer.Read(lex_mode)

    # e.g. translate ) or ` into EOF
    if self.translation_stack:
      old_id, new_id = self.translation_stack[-1]  # top
      if t.id == old_id:
        new_s = IdName(new_id)
        #print('==> TRANSLATING %s ==> %s' % (t, new_s))
        self.translation_stack.pop()
        #print(self.translation_stack)
        t.id = new_id

    return t

  # TODO: Collapse newlines here instead of in the WordParser?
  def Read(self, lex_mode):
    while True:
      t = self._Read(lex_mode)
      if self.tokens_out is not None:
        self.tokens_out.append(t)

      self.was_line_cont = (t.id == Id.Ignored_LineCont)

      # TODO: Change to ALL IGNORED types, once you have SPACE_TOK.  This means
      # we don't have to handle them in the VS_1/VS_2/etc. states.
      if t.id != Id.Ignored_LineCont:
        break

    #print("T", t, lex_mode)
    return t
