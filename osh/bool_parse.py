#!/usr/bin/env python3
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
a list of Value instances.

TODO:
- Share parsing with "test / [".  That uses strings, while this uses words.
  Maybe call this CondParser then.

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

Other shell implementations:

bash has a recursive descent parser in parse.y:
parse_cond_command() / cond_expr() / ...
3 levels of precedence.

Bash manual: https://www.gnu.org/software/bash/manual/bash.html#Conditional-Constructs

Precedence table.  Not sure why this is all one table, since [[ and (( are
separate: http://tldp.org/LDP/abs/html/opprecedence.html 

mksh:
funcs.c: test_isop() / test_eval() /...
It is SHARED with [ using Test_env.

But mksh uses precedence climbing for the arithmetic parser.  Two different
algorithms!  See evalexpr() in expr.c.
"""

import sys

from core import base
from core.tokens import *
from core.bool_node import NotBNode, LogicalBNode, UnaryBNode, BinaryBNode
from osh.lex import LexMode
try:
  from core import libc
except ImportError:
  from core import fake_libc as libc


def LookupBKind(btype):
  """
  Return BKind.ATOM, BKind.UNARY ...

  TODO: Maybe separate this into a parse time and a runtime table.
  """
  bkind, _, _, _ = BOOLEAN_OP_TABLE[btype]
  return bkind


class CondParser(object):
  """Parses [[ at compile time and [ at runtime.
  """
  def __init__(self, w_parser):
    """
    Args:
      words: Words to parse as a conditional expression.  It must exclude the
      beginning [[ word, but include the last ]] word (for EOF)

    TODO: Pass w_parser instead of list of words.
    """
    self.w_parser = w_parser
    # Either one word or two words for lookahead
    self.words = []

    self.cur_word = None
    self.btype = BType.UNDEFINED_TOK
    self.bkind = BKind.UNDEFINED

    self.error_stack = []

  def Error(self):
    return self.error_stack

  def AddErrorContext(self, msg, *args, token=None, word=None):
    err = base.MakeError(msg, *args, token=token, word=word)
    self.error_stack.append(err)

  def _NextOne(self, lex_state=LexMode.DBRACKET):
    #print('_Next', self.cur_word)
    n = len(self.words)
    if n == 2:
      assert lex_state == LexMode.DBRACKET
      self.words[0] = self.words[1]
      self.cur_word = self.words[0]
      del self.words[1]
    elif n in (0, 1):
      w = self.w_parser.ReadWord(lex_state)
      if not w:
        err = self.w_parser.Error()
        self.error_stack.extend(err)
        return False
      if n == 0:
        self.words.append(w)
      else:
        self.words[0] = w
      self.cur_word = w

    self.btype = self.cur_word.BType()
    self.bkind = LookupBKind(self.btype)
    return True

  def _Next(self, lex_state=LexMode.DBRACKET):
    """
    Advance to the next token, skipping newlines.  We don't do handle newlines
    in the lexer because we want the newline after ]] to be OP_NEWLINE rather
    than WS_NEWLINE.  It's more complicated if it's WS_NEWLINE -- we might have
    to unread tokens, etc.
    """
    while True:
      w = self._NextOne(lex_state=lex_state)
      if not w:
        return False
      if self.btype != BType.NEWLINE_TOK:
        break
    return True

  def AtEnd(self):
    return self.btype == BType.Eof_TOK

  def _LookAhead(self):
    n = len(self.words)
    if n != 1:
      raise AssertionError(self.words)

    w = self.w_parser.ReadWord(LexMode.DBRACKET)
    self.words.append(w)  # Save it for _Next()
    return w

  def Parse(self):
    if not self._Next(): return None

    node = self.ParseExpr()
    if not self.AtEnd():
      self.AddErrorContext("Unexpected extra word %r", self.cur_word,
          word=self.cur_word)
      return None
    return node

  def ParseExpr(self):
    """
    Expr    : Term (OR Term)*

    Right associative:

    Expr    : Term (OR Expr)?

    Do you want this?  I think it is fine.  It's right recursion, not left
    recursion.  I want left associativity though.

    Left associative:

    Expr    : Expr OR Term | Term
    # http://programmers.stackexchange.com/questions/260123/bnf-parsing-rule-for-left-associativity

    This is left recursive.  Answer: look ahead for OR.  If it's there, parse
    Expr.  Otherwise parse term.

    Another option:
    You can just do it iteratively, accumulate nodes.  And then add the end,
    make
    """
    left = self.ParseTerm()
    if self.btype == BType.LOGICAL_BINARY_OR:
      if not self._Next(): return None
      right = self.ParseExpr()
      return LogicalBNode(BType.LOGICAL_BINARY_OR, left, right)
    else:
      return left

  def ParseTerm(self):
    """
    Term    : Negated (AND Negated)*

    Right associative:

    Term    : Negated (AND Term)?

    Left associative:
    
    Term    : Term AND Negated | Negated
    """
    left = self.ParseNegatedFactor()
    if self.btype == BType.LOGICAL_BINARY_AND:
      if not self._Next(): return None
      right = self.ParseTerm()
      return LogicalBNode(BType.LOGICAL_BINARY_AND, left, right)
    else:
      return left

  def ParseNegatedFactor(self):
    """
    Negated : '!'? Factor
    """
    if self.btype == BType.LOGICAL_UNARY_NOT:
      if not self._Next(): return None
      child = self.ParseFactor()
      return NotBNode(child)
    else:
      return self.ParseFactor()

  def ParseFactor(self):
    """
    Factor  : WORD
            | UNARY_OP WORD
            | WORD BINARY_OP WORD 
            | '(' Expr ')'
    """
    #print('ParseFactor %s %s' % (self.bkind, self.btype))
    if self.bkind == BKind.UNARY:
      # Just save the type and not the token itself?
      op = self.btype
      if not self._Next(): return None
      word  = self.cur_word
      if not self._Next(): return None
      node = UnaryBNode(op, word)
      return node

    if self.bkind == BKind.ATOM:
      # Peek ahead another token.
      t2 = self._LookAhead()
      t2_btype = t2.BType()
      t2_bkind = LookupBKind(t2_btype)
      if t2_bkind == BKind.BINARY:
        left = self.cur_word

        if not self._Next(): return None
        op = self.btype

        # TODO: Need to change to LexMode.BASH_REGEX.
        # _Next(lex_state) then?
        is_regex = t2_btype == BType.BINARY_STRING_TILDE_EQUAL
        if is_regex:
          if not self._Next(lex_state=LexMode.BASH_REGEX): return None
        else:
          if not self._Next(): return None

        right = self.cur_word
        if is_regex:
          ok, regex_str, unused_quoted = right.EvalStatic()
          # doesn't contain $foo, etc.
          if ok and not libc.regex_parse(regex_str):
            self.AddErrorContext("Invalid regex: %r" % regex_str, word=right)
            return None

        if not self._Next(): return None
        return BinaryBNode(op, left, right)
      else:
        # [[ foo ]] is implicit Implicit [[ -n foo ]]
        op = BType.UNARY_STRING_n
        word = self.cur_word
        if not self._Next(): return None
        return UnaryBNode(op, word)

    if self.btype == BType.PAREN_LEFT:
      if not self._Next(): return None
      node = self.ParseExpr()
      if self.btype != BType.PAREN_RIGHT:
        raise RuntimeError("Expected ), got %s", self.cur_word)
      if not self._Next(): return None
      return node

    # TODO: A proper error, e.g. for "&&"
    raise AssertionError("Unexpected token: %s" % self.cur_word)


def main(argv):
  import bool_eval
  import bool_parse_test
  import cmd_exec
  import word_eval

  p = bool_parse_test._MakeParser(argv[1])
  node = p.ParseExpr()
  assert p.AtEnd()
  print('node:', node)

  mem = cmd_exec.Mem('', [])
  exec_opts = cmd_exec.ExecOpts()
  ev = word_eval.CompletionEvaluator(mem, exec_opts)

  ok, b = bool_eval.BEval(node, ev)
  print('result:', ok, b)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except NotImplementedError:
    raise
  except RuntimeError as e:
    print('FATAL: %r' % e, file=sys.stderr)
    sys.exit(1)
