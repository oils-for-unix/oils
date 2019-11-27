#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
bool_parse.py - Parse boolean expressions.

In contrast to test / [, the parsing of [[ expressions is done BEFORE
evaluation.  So we are parsing a list of Word instances to an AST, rather than
a list of strings.

Grammar from http://compilers.iecc.com/crenshaw/tutor6.txt, adapted to ANTLR
syntax.

  Expr    : Term (OR Term)*
  Term    : Negated (AND Negated)*
  Negated : '!'? Factor
  Factor  : WORD
          | UNARY_OP WORD
          | WORD BINARY_OP WORD
          | '(' Expr ')'

OR = ||  -o
AND = &&  -a
WORD = any word
UNARY_OP: -z -n, etc.
BINARY_OP: -gt, -ot, ==, etc.
"""

from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.types_asdl import lex_mode_t, lex_mode_e
from _devbuild.gen.syntax_asdl import word_t, word_e, bool_expr, bool_expr_t
from core.util import p_die
from frontend import lookup
from osh import word_

from typing import List, Optional, Union, TYPE_CHECKING
if TYPE_CHECKING:
  from osh.word_parse import WordParser
  from osh.builtin_bracket import _StringWordEmitter

# import libc  # for regex_parse


class BoolParser(object):
  """Parses [[ at compile time and [ at runtime."""

  def __init__(self, w_parser):
    # type: (Union[WordParser, _StringWordEmitter]) -> None
    """
    Args:
      w_parser: WordParser
    """
    self.w_parser = w_parser
    # Either one word or two words for lookahead
    self.words = []  # type: List[word_t]

    self.cur_word = None  # type: Optional[word_t]
    self.op_id = Id.Undefined_Tok
    self.b_kind = Kind.Undefined

  def _NextOne(self, lex_mode=lex_mode_e.DBracket):
    # type: (lex_mode_t) -> None
    n = len(self.words)
    if n == 2:
      assert lex_mode == lex_mode_e.DBracket
      self.words[0] = self.words[1]
      self.cur_word = self.words[0]
      self.words.pop()
    elif n in (0, 1):
      w = self.w_parser.ReadWord(lex_mode)  # may raise
      if n == 0:
        self.words.append(w)
      else:
        self.words[0] = w
      self.cur_word = w

    assert self.cur_word is not None
    self.op_id = word_.BoolId(self.cur_word)
    self.b_kind = lookup.LookupKind(self.op_id)
    #log('--- word %s', self.cur_word)
    #log('op_id %s %s %s', self.op_id, self.b_kind, lex_mode)

  def _Next(self, lex_mode=lex_mode_e.DBracket):
    # type: (lex_mode_t) -> None
    """Advance to the next token, skipping newlines.

    We don't handle newlines in the lexer because we want the newline after ]]
    to be Id.Op_Newline rather than Id.WS_Newline.  It's more complicated if
    it's Id.WS_Newline -- we might have to unread tokens, etc.
    """
    while True:
      self._NextOne(lex_mode=lex_mode)
      if self.op_id != Id.Op_Newline:
        break

  def _LookAhead(self):
    # type: () -> word_t
    n = len(self.words)
    if n != 1:
      raise AssertionError(n)

    w = self.w_parser.ReadWord(lex_mode_e.DBracket)  # may raise
    self.words.append(w)  # Save it for _Next()
    return w

  def Parse(self):
    # type: () -> bool_expr_t
    self._Next()

    node = self.ParseExpr()
    if self.op_id != Id.Lit_DRightBracket:
      #p_die("Expected ]], got %r", self.cur_word, word=self.cur_word)
      # NOTE: This might be better as unexpected token, since ]] doesn't always
      # make sense.
      p_die('Expected ]]', word=self.cur_word)
    return node

  def _TestAtEnd(self):
    # type: () -> bool
    """For unit tests only."""
    return self.op_id == Id.Lit_DRightBracket

  def ParseForBuiltin(self):
    # type: () -> bool_expr_t
    """For test builtin."""
    self._Next()

    node = self.ParseExpr()
    if self.op_id != Id.Eof_Real:
      p_die('Unexpected trailing word %s', word_.Pretty(self.cur_word),
          word=self.cur_word)

    return node

  def ParseExpr(self):
    # type: () -> bool_expr_t
    """
    Iterative:
    Expr    : Term (OR Term)*

    Right recursion:
    Expr    : Term (OR Expr)?
    """
    left = self.ParseTerm()
    # [[ uses || but [ uses -o
    if self.op_id in (Id.Op_DPipe, Id.BoolUnary_o):
      self._Next()
      right = self.ParseExpr()
      return bool_expr.LogicalOr(left, right)
    else:
      return left

  def ParseTerm(self):
    # type: () -> bool_expr_t
    """
    Term    : Negated (AND Negated)*

    Right recursion:
    Term    : Negated (AND Term)?
    """
    left = self.ParseNegatedFactor()
    # [[ uses && but [ uses -a
    if self.op_id in (Id.Op_DAmp, Id.BoolUnary_a):
      self._Next()
      right = self.ParseTerm()
      return bool_expr.LogicalAnd(left, right)
    else:
      return left

  def ParseNegatedFactor(self):
    # type: () -> bool_expr_t
    """
    Negated : '!'? Factor
    """
    if self.op_id == Id.KW_Bang:
      self._Next()
      child = self.ParseFactor()
      return bool_expr.LogicalNot(child)
    else:
      return self.ParseFactor()

  def ParseFactor(self):
    # type: () -> bool_expr_t
    """
    Factor  : WORD
            | UNARY_OP WORD
            | WORD BINARY_OP WORD
            | '(' Expr ')'
    """
    if self.b_kind == Kind.BoolUnary:
      # Just save the type and not the token itself?
      op = self.op_id
      self._Next()
      w = self.cur_word
      # e.g. [[ -f < ]].  But [[ -f '<' ]] is OK

      tag = w.tag_()
      if tag != word_e.Compound and tag != word_e.String:
        p_die('Invalid argument to unary operator', word=w)
      self._Next()
      node = bool_expr.Unary(op, w)  # type: bool_expr_t
      return node

    if self.b_kind == Kind.Word:
      # Peek ahead another token.
      t2 = self._LookAhead()
      t2_op_id = word_.BoolId(t2)
      t2_b_kind = lookup.LookupKind(t2_op_id)

      #log('t2 %s / t2_op_id %s / t2_b_kind %s', t2, t2_op_id, t2_b_kind)
      # Op for < and >, -a and -o pun
      if t2_b_kind == Kind.BoolBinary or t2_op_id in (Id.Op_Less, Id.Op_Great):
        left = self.cur_word

        self._Next()
        op = self.op_id

        # TODO: Need to change to lex_mode_e.BashRegex.
        # _Next(lex_mode) then?
        is_regex = t2_op_id == Id.BoolBinary_EqualTilde
        if is_regex:
          self._Next(lex_mode=lex_mode_e.BashRegex)
        else:
          self._Next()

        right = self.cur_word
        if is_regex:
          # NOTE: StaticEval for checking regex syntax isn't enough.  We could
          # need to pass do_ere so that the quoted parts get escaped.
          #ok, s, unused_quoted = word_.StaticEval(right)
          pass

        self._Next()
        return bool_expr.Binary(op, left, right)
      else:
        # [[ foo ]]
        w = self.cur_word
        self._Next()
        return bool_expr.WordTest(w)

    if self.op_id == Id.Op_LParen:
      self._Next()
      node = self.ParseExpr()
      if self.op_id != Id.Op_RParen:
        p_die('Expected ), got %s', word_.Pretty(self.cur_word),
              word=self.cur_word)
      self._Next()
      return node

    # It's not WORD, UNARY_OP, or '('
    p_die('Unexpected token in boolean expression', word=self.cur_word)
