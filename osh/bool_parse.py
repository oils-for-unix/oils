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
from _devbuild.gen.id_kind_asdl import Id_str  # for debugging
from _devbuild.gen.types_asdl import lex_mode_t, lex_mode_e
from _devbuild.gen.syntax_asdl import (loc, word_t, word_e, bool_expr,
                                       bool_expr_t, Token)
from core.error import p_die
from display import ui
from frontend import consts
from mycpp import mylib
from mycpp.mylib import log
from osh import word_

from typing import Optional, Tuple, TYPE_CHECKING
if TYPE_CHECKING:
    from osh.word_parse import WordEmitter

# import libc  # for regex_parse

_ = log


class BoolParser(object):
    """Parses [[ at compile time and [ at runtime."""

    def __init__(self, w_parser):
        # type: (WordEmitter) -> None
        self.w_parser = w_parser

        self.cur_word = None  # type: Optional[word_t]
        self.bool_id = Id.Undefined_Tok
        self.bool_kind = Kind.Undefined

        # Lookahead words
        self.ahead1 = None  # type: Optional[word_t]
        self.ahead2 = None  # type: Optional[word_t]

    if mylib.PYTHON:
        # For unit tests only

        def _Dump(self):
            # type: () -> None
            log('cur_word = %s', self.cur_word)
            log('bool_id = %s', Id_str(self.bool_id))
            log('ahead1 = %s', self.ahead1)
            log('ahead2 = %s', self.ahead2)
            log('    ///')

        def _TestAtEnd(self):
            # type: () -> bool
            return self.bool_id == Id.Lit_DRightBracket

    def _NextOne(self, lex_mode=lex_mode_e.DBracket):
        # type: (lex_mode_t) -> None
        """
        Sets self.cur_word, self.bool_id, self.bool_kind

        Tries to maintain a "buffer" self.words of length 1, unless there is lookahead
        """
        if self.ahead2:
            self.cur_word = self.ahead1
            self.ahead1 = self.ahead2
            self.ahead2 = None
        elif self.ahead1:  # look2 set
            self.cur_word = self.ahead1
            self.ahead1 = None
        else:
            self.cur_word = self.w_parser.ReadWord(lex_mode)  # may raise

        self.bool_id = word_.BoolId(self.cur_word)
        self.bool_kind = consts.GetKind(self.bool_id)

        #log('bool_id %s %s %s', Id_str(self.bool_id), Kind_str(self.bool_kind), lex_mode)

    def _Next(self, lex_mode=lex_mode_e.DBracket):
        # type: (lex_mode_t) -> None
        """Advance to the next token, skipping newlines.

        We don't handle newlines in the lexer because we want the
        newline after ]] to be Id.Op_Newline rather than Id.WS_Newline.
        It's more complicated if it's Id.WS_Newline -- we might have to
        unread tokens, etc.
        """
        while True:
            self._NextOne(lex_mode=lex_mode)
            if self.bool_id != Id.Op_Newline:
                break

    def _LookAhead(self):
        # type: () -> word_t
        """
        TODO: change to LookAheadForBinary, with 2 tokens, for

        [ -f foo ]   # unary
        [ -f = -f ]  # binary
        [ -f = ]     # unary
        """
        w = self.w_parser.ReadWord(lex_mode_e.DBracket)  # may raise
        self.ahead1 = w
        return w

    def Parse(self):
        # type: () -> Tuple[bool_expr_t, Token]
        self._Next()

        node = self.ParseExpr()
        if self.bool_id != Id.Lit_DRightBracket:
            #p_die("Expected ]], got %r", self.cur_word, word=self.cur_word)
            # NOTE: This might be better as unexpected token, since ]] doesn't always
            # make sense.
            p_die('Expected ]]', loc.Word(self.cur_word))

        # Extract the ']]' keyword and return it's token for location tracking
        right = word_.LiteralToken(self.cur_word)
        assert right is not None

        return node, right

    def ParseForBuiltin(self):
        # type: () -> bool_expr_t
        """For test builtin."""
        self._Next()

        node = self.ParseExpr()
        if self.bool_id != Id.Eof_Real:
            p_die('Unexpected trailing word %s' % word_.Pretty(self.cur_word),
                  loc.Word(self.cur_word))

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
        if self.bool_id in (Id.Op_DPipe, Id.BoolUnary_o):
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
        if self.bool_id in (Id.Op_DAmp, Id.BoolUnary_a):
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
        if self.bool_id == Id.KW_Bang:
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
                | WORD =~ Regex
                | WORD BINARY_OP WORD
                | '(' Expr ')'

        Note: this grammar is ambiguous, and the design of the 'test' builtin
        is terrible in general.

        We roughly follow bash's ordering rules, which gives a result that
        almost all shells agree on:

        1. Look for ( first
        2. Then look ahead to see if you got Kind.BoolBinary, like =
        3. Then unary operators:        test -d /  [[ -d / ]]
        4. Then non-empty string tests: test foo   [[ foo ]]
        """
        if self.bool_id == Id.Op_LParen:
            self._Next()  # past (
            node = self.ParseExpr()  # type: bool_expr_t
            if self.bool_id != Id.Op_RParen:
                p_die('Expected ), got %s' % word_.Pretty(self.cur_word),
                      loc.Word(self.cur_word))
            self._Next()  # past )
            return node

        # Peek ahead another token.
        t2 = self._LookAhead()
        t2_bool_id = word_.BoolId(t2)
        t2_bool_kind = consts.GetKind(t2_bool_id)

        #log('t2 %s / t2_bool_id %s / t2_bool_kind %s', t2, t2_bool_id, t2_bool_kind)
        # Op for < and >, -a and -o pun
        if t2_bool_kind == Kind.BoolBinary or t2_bool_id in (Id.Op_Less,
                                                             Id.Op_Great):
            left = self.cur_word

            self._Next()
            op = self.bool_id

            if t2_bool_id == Id.BoolBinary_EqualTilde:
                self._Next(lex_mode=lex_mode_e.BashRegex)
            else:
                self._Next()

            right = self.cur_word
            self._Next()

            tilde = word_.TildeDetect(left)
            if tilde:
                left = tilde
            tilde = word_.TildeDetect(right)
            if tilde:
                right = tilde

            return bool_expr.Binary(op, left, right)

        if self.bool_kind == Kind.BoolUnary:
            # Just save the type and not the token itself?
            op = self.bool_id
            self._Next()
            w = self.cur_word
            # e.g. [[ -f < ]].  But [[ -f '<' ]] is OK

            tag = w.tag()
            if tag != word_e.Compound and tag != word_e.String:
                p_die('Invalid argument to unary operator', loc.Word(w))
            self._Next()

            tilde = word_.TildeDetect(w)
            if tilde:
                w = tilde

            node = bool_expr.Unary(op, w)
            return node

        # [[ foo ]]
        # Note: ( = ) and ( == ) may also hit this path, but they are NOT Kind.Word
        if self.bool_kind != Kind.Op:
            w = self.cur_word
            tilde = word_.TildeDetect(w)
            if tilde:
                w = tilde
            self._Next()
            return bool_expr.WordTest(w)

        # Error for [[ ) ]]
        # It's not WORD, UNARY_OP, or '('
        p_die(
            'Unexpected token in boolean expression (%s)' %
            ui.PrettyId(self.bool_id), loc.Word(self.cur_word))
