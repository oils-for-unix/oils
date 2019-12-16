# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
lexer.py - Library for lexing.
"""

from _devbuild.gen.syntax_asdl import Token, line_span
from _devbuild.gen.types_asdl import lex_mode_t
from _devbuild.gen.id_kind_asdl import Id_t, Id, Kind
from asdl import runtime
from core.util import log
from mycpp import mylib
from frontend import lookup
from frontend import match

from typing import Callable, List, Tuple, Optional, Counter, TYPE_CHECKING
if TYPE_CHECKING:
  from core.alloc import Arena
  from frontend.reader import _Reader


# Special immutable tokens
_EOL_TOK = Token(Id.Eol_Tok, runtime.NO_SPID, None)


class LineLexer(object):
  def __init__(self, line, arena):
    # type: (str, Arena) -> None
    self.arena = arena

    self.arena_skip = False  # For MaybeUnreadOne
    self.last_span_id = runtime.NO_SPID  # For MaybeUnreadOne

    self.Reset(line, -1, 0)  # Invalid line_id to start

  def __repr__(self):
    # type: () -> str
    return '<LineLexer at pos %d of line %r (id = %d)>' % (
        self.line_pos, self.line, self.line_id)

  def Reset(self, line, line_id, line_pos):
    # type: (str, int, int) -> None
    #assert line, repr(line)  # can't be empty or None
    self.line = line
    self.line_id = line_id
    self.line_pos = line_pos

  def MaybeUnreadOne(self):
    # type: () -> bool
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
    # type: () -> int
    """Create a new span ID for syntax errors involving the EOF token."""
    if self.line_id == -1:
      # When line_id == -1, this means there are ZERO lines.  Add a dummy line
      # 0 so the span_id has a source to display errors.
      line_id = self.arena.AddLine('', 0)
    else:
      line_id = self.line_id
    return self.arena.AddLineSpan(line_id, self.line_pos, 0)

  def LookAhead(self, lex_mode):
    # type: (lex_mode_t) -> Id_t
    """Look ahead for a non-space token, using the given lexer mode.

    Does NOT advance self.line_pos.

    Called with at least the following modes:
      lex_mode_e.Arith -- for ${a[@]} vs ${a[1+2]}
      lex_mode_e.VSub_1
      lex_mode_e.ShCommand
    """
    pos = self.line_pos
    n = len(self.line)
    #print('Look ahead from pos %d, line %r' % (pos,self.line))
    while True:
      if pos == n:
        # We don't allow lookahead while already at end of line, because it
        # would involve interacting with the line reader, and we never need
        # it.  In the OUTER mode, there is an explicit newline token, but
        # ARITH doesn't have it.
        return Id.Unknown_Tok

      tok_type, end_pos = match.OneToken(lex_mode, self.line, pos)

      # NOTE: Instead of hard-coding this token, we could pass it in.  This
      # one only appears in OUTER state!  LookAhead(lex_mode, past_token_type)
      if tok_type != Id.WS_Space:
        break
      pos = end_pos

    return tok_type

  def Read(self, lex_mode):
    # type: (lex_mode_t) -> Token
    # Inner loop optimization
    line = self.line
    line_pos = self.line_pos

    tok_type, end_pos = match.OneToken(lex_mode, line, line_pos)
    if tok_type == Id.Eol_Tok:  # Do NOT add a span for this sentinel!
      return _EOL_TOK

    # Save on allocations!  We often don't look at the token value.
    # TODO: can inline this function with formula on 16-bit Id.
    kind = lookup.LookupKind(tok_type)

    # Whitelist doesn't work well?  Use blacklist for now.
    # - Kind.KW is sometimes a literal in a word
    # - Kind.Right is for " in here docs.  Lexer isn't involved.
    # - Got an error with Kind.Left too that I don't understand
    # if kind in (Kind.Lit, Kind.VSub, Kind.Redir, Kind.Char, Kind.Backtick, Kind.KW, Kind.Right):

    if kind in (Kind.Arith, Kind.Op, Kind.WS, Kind.Ignored, Kind.Eof):
      tok_val = None  # type: Optional[str]
    else:
      tok_val = line[line_pos:end_pos]
    # NOTE: We're putting the arena hook in LineLexer and not Lexer because we
    # want it to be "low level".  The only thing fabricated here is a newline
    # added at the last line, so we don't end with \0.

    if self.arena_skip:  # make another token from the last span
      assert self.last_span_id != runtime.NO_SPID
      span_id = self.last_span_id
      self.arena_skip = False
    else:
      tok_len = end_pos - line_pos
      span_id = self.arena.AddLineSpan(self.line_id, line_pos, tok_len)
      self.last_span_id = span_id
    #log('LineLexer.Read() span ID %d for %s', span_id, tok_type)

    t = Token(tok_type, span_id, tok_val)
    self.line_pos = end_pos
    return t


class Lexer(object):
  """
  Read lines from the line_reader, split them into tokens with line_lexer,
  returning them in a stream.
  """
  def __init__(self, line_lexer, line_reader):
    # type: (LineLexer, _Reader) -> None
    """
    Args:
      line_lexer: Underlying object to get tokens from
      line_reader: get new lines from here
    """
    self.line_lexer = line_lexer
    self.line_reader = line_reader
    self.line_id = -1  # Invalid one
    self.translation_stack = []  # type: List[Tuple[Id_t, Id_t]]
    self.emit_comp_dummy = False

  def ResetInputObjects(self):
    # type: () -> None
    self.line_lexer.Reset('', -1, 0)

  def MaybeUnreadOne(self):
    # type: () -> bool
    return self.line_lexer.MaybeUnreadOne()

  def LookAhead(self, lex_mode):
    # type: (lex_mode_t) -> Id_t
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

  def EmitCompDummy(self):
    # type: () -> None
    """Emit Id.Lit_CompDummy right before EOF, for completion."""
    self.emit_comp_dummy = True

  def PushHint(self, old_id, new_id):
    # type: (Id_t, Id_t) -> None
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
    # type: (lex_mode_t) -> Token
    """Read from the normal line buffer, not an alias."""
    t = self.line_lexer.Read(lex_mode)
    if t.id == Id.Eol_Tok:  # hit \0, read a new line
      line_id, line, line_pos = self.line_reader.GetLine()

      if line is None:  # no more lines
        span_id = self.line_lexer.GetSpanIdForEof()
        if self.emit_comp_dummy:
          id_ = Id.Lit_CompDummy
          self.emit_comp_dummy = False  # emit EOF the next time
        else:
          id_ = Id.Eof_Real
        t = Token(id_, span_id, '')
        return t

      self.line_lexer.Reset(line, line_id, line_pos)  # fill with a new line
      t = self.line_lexer.Read(lex_mode)

    # e.g. translate ) or ` into EOF
    if len(self.translation_stack):
      old_id, new_id = self.translation_stack[-1]  # top
      if t.id == old_id:
        #print('==> TRANSLATING %s ==> %s' % (t, new_s))
        self.translation_stack.pop()
        t.id = new_id

    return t

  def Read(self, lex_mode):
    # type: (lex_mode_t) -> Token
    while True:
      t = self._Read(lex_mode)
      # TODO: Change to ALL IGNORED types, once you have SPACE_TOK.  This means
      # we don't have to handle them in the VSub_1/VSub_2/etc. states.
      if t.id != Id.Ignored_LineCont:
        break

    #ID_HIST[t.id] += 1
    #log('> Read() Returning %s', t)
    return t


if 0:  # mylib.PYTHON: not: breaks tarball build
  import collections
  ID_HIST = collections.Counter()  # type: Counter[Id_t]
