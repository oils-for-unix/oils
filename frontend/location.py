#!/usr/bin/env python2
"""
location.py - Library to get source location info from nodes.

This makes syntax errors nicer.
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    loc, loc_t, loc_e,
    command, command_e, command_t,
    word, word_e, word_t,
    word_part, word_part_e, word_part_t,
    CompoundWord, SimpleVarSub, Token,
    ShArrayLiteral, SingleQuoted, DoubleQuoted, CommandSub, BracedVarSub,
    BraceGroup,
    arith_expr_e, arith_expr_t,
)
from _devbuild.gen.runtime_asdl import lvalue
from asdl import runtime
from mycpp.mylib import log
from mycpp.mylib import tagswitch

from typing import TYPE_CHECKING, cast, Optional


def LName(name):
  # type: (str) -> lvalue.Named
  """
  Wrapper for lvalue.Named() with location.  TODO: add locations and remove
  this.
  """
  return lvalue.Named(name, loc.Missing)


def GetSpanId(loc_):
  # type: (loc_t) -> int

  UP_location = loc_
  with tagswitch(loc_) as case:
    if case(loc_e.Missing):
      return runtime.NO_SPID

    elif case(loc_e.Token):
      tok = cast(Token, UP_location)
      if tok:
        return tok.span_id
      else:
        return runtime.NO_SPID

    elif case(loc_e.Span):
      loc_ = cast(loc.Span, UP_location)
      return loc_.span_id

    elif case(loc_e.WordPart):
      loc_ = cast(loc.WordPart, UP_location)
      if loc_.p:
        return OfWordPartLeft(loc_.p)
      else:
        return runtime.NO_SPID

    elif case(loc_e.Word):
      loc_ = cast(loc.Word, UP_location)
      if loc_.w:
        return OfWordLeft(loc_.w)
      else:
        return runtime.NO_SPID

    else:
      raise AssertionError()

  raise AssertionError()


def TokenForCommand(node):
  # type: (command_t) -> Optional[Token]
  """
  Used in pipe_locs, for _CheckStatus(), _StrictErrExit, etc.
  """
  UP_node = node # type: command_t
  tag = node.tag()

  if tag == command_e.Sentence:
    node = cast(command.Sentence, UP_node)
    #log("node.child %s", node.child)
    return node.terminator  # & or ;

  if tag == command_e.Simple:
    node = cast(command.Simple, UP_node)
    return node.blame_tok

  if tag == command_e.ShAssignment:
    node = cast(command.ShAssignment, UP_node)
    return node.var

  if tag == command_e.Pipeline:
    node = cast(command.Pipeline, UP_node)
    if len(node.ops):
      return node.ops[0]  # first | or |&
    else:
      assert node.negated is not None
      return node.negated  # ! false

  if tag == command_e.AndOr:
    node = cast(command.AndOr, UP_node)
    return node.ops[0]  # first && or ||

  if tag == command_e.DoGroup:
    node = cast(command.DoGroup, UP_node)
    return node.left  # 'do' token
  if tag == command_e.BraceGroup:
    node = cast(BraceGroup, UP_node)
    return node.left  # { token
  if tag == command_e.Subshell:
    node = cast(command.Subshell, UP_node)
    return node.left  # ( token

  if tag == command_e.WhileUntil:
    node = cast(command.WhileUntil, UP_node)
    return node.keyword  # while
  if tag == command_e.If:
    node = cast(command.If, UP_node)
    return node.if_kw
  if tag == command_e.Case:
    node = cast(command.Case, UP_node)
    return node.case_kw
  if tag == command_e.TimeBlock:
    node = cast(command.TimeBlock, UP_node)
    return node.keyword

  # We never have this case?
  #if node.tag == command_e.CommandList:
  #  pass

  return None


def OfCommand(node):
  # type: (command_t) -> loc_t
  tok = TokenForCommand(node)
  if tok:
    return tok
  else:
    return loc.Missing


def OfArithExpr(node):
  # type: (arith_expr_t) -> loc_t
  UP_node = node
  with tagswitch(node) as case:
    if case(arith_expr_e.VarSub):
      vsub = cast(SimpleVarSub, UP_node)
      return vsub.left
    elif case(arith_expr_e.Word):
      w = cast(CompoundWord, UP_node)
      return loc.Word(w)

  return loc.Missing


def OfWordPartLeft(part):
  # type: (word_part_t) -> int
  """
  Span ID wrapper to remove
  """
  tok = LeftTokenForWordPart(part)
  if tok:
    return tok.span_id
  else:
    return runtime.NO_SPID


def LeftTokenForWordPart(part):
  # type: (word_part_t) -> Optional[Token]
  UP_part = part
  with tagswitch(part) as case:
    if case(word_part_e.ShArrayLiteral):
      part = cast(ShArrayLiteral, UP_part)
      return part.left

    elif case(word_part_e.AssocArrayLiteral):
      part = cast(word_part.AssocArrayLiteral, UP_part)
      return part.left

    elif case(word_part_e.Literal):
      tok = cast(Token, UP_part)
      return tok

    elif case(word_part_e.EscapedLiteral):
      part = cast(word_part.EscapedLiteral, UP_part)
      return part.token

    elif case(word_part_e.SingleQuoted):
      part = cast(SingleQuoted, UP_part)
      return part.left

    elif case(word_part_e.DoubleQuoted):
      part = cast(DoubleQuoted, UP_part)
      return part.left

    elif case(word_part_e.SimpleVarSub):
      part = cast(SimpleVarSub, UP_part)
      return part.left

    elif case(word_part_e.BracedVarSub):
      part = cast(BracedVarSub, UP_part)
      return part.left

    elif case(word_part_e.CommandSub):
      part = cast(CommandSub, UP_part)
      return part.left_token

    elif case(word_part_e.TildeSub):
      part = cast(word_part.TildeSub, UP_part)
      return part.token

    elif case(word_part_e.ArithSub):
      part = cast(word_part.ArithSub, UP_part)
      return part.left

    elif case(word_part_e.ExtGlob):
      part = cast(word_part.ExtGlob, UP_part)
      return part.op

    elif case(word_part_e.BracedRange):
      part = cast(word_part.BracedRange, UP_part)
      return part.blame_tok

    elif case(word_part_e.BracedTuple):
      part = cast(word_part.BracedTuple, UP_part)
      # TODO: Derive token from part.words[0]
      return None

    elif case(word_part_e.Splice):
      part = cast(word_part.Splice, UP_part)
      return part.blame_tok

    elif case(word_part_e.ExprSub):
      part = cast(word_part.ExprSub, UP_part)
      return part.left  # $[

    # TODO: remove inline function calls from YSH
    elif case(word_part_e.FuncCall):
      part = cast(word_part.FuncCall, UP_part)
      return part.name  # @f(x) or $f(x)

    else:
      raise AssertionError(part.tag())


def _OfWordPartRight(part):
  # type: (word_part_t) -> int
  UP_part = part
  with tagswitch(part) as case:
    if case(word_part_e.ShArrayLiteral):
      part = cast(ShArrayLiteral, UP_part)
      return part.right.span_id

    elif case(word_part_e.AssocArrayLiteral):
      part = cast(word_part.AssocArrayLiteral, UP_part)
      return part.right.span_id

    elif case(word_part_e.Literal):
      # Just use the token
      tok = cast(Token, UP_part)
      return tok.span_id

    elif case(word_part_e.EscapedLiteral):
      part = cast(word_part.EscapedLiteral, UP_part)
      return part.token.span_id

    elif case(word_part_e.SingleQuoted):
      part = cast(SingleQuoted, UP_part)
      return part.right.span_id  # right '

    elif case(word_part_e.DoubleQuoted):
      part = cast(DoubleQuoted, UP_part)
      return part.right.span_id  # right "

    elif case(word_part_e.SimpleVarSub):
      part = cast(SimpleVarSub, UP_part)
      # left and right are the same for $myvar
      return part.left.span_id

    elif case(word_part_e.BracedVarSub):
      part = cast(BracedVarSub, UP_part)
      spid = part.right.span_id
      assert spid != runtime.NO_SPID
      return spid

    elif case(word_part_e.CommandSub):
      part = cast(CommandSub, UP_part)
      return part.right.span_id

    elif case(word_part_e.TildeSub):
      return runtime.NO_SPID

    elif case(word_part_e.ArithSub):
      part = cast(word_part.ArithSub, UP_part)
      return part.right.span_id

    elif case(word_part_e.ExtGlob):
      part = cast(word_part.ExtGlob, UP_part)
      return part.right.span_id

    elif case(word_part_e.BracedRange):
      part = cast(word_part.BracedRange, UP_part)
      return part.blame_tok.span_id

    elif case(word_part_e.BracedTuple):
      part = cast(word_part.BracedTuple, UP_part)
      # TODO: Derive token from part.words[0]
      return runtime.NO_SPID

    elif case(word_part_e.Splice):
      part = cast(word_part.Splice, UP_part)
      return part.blame_tok.span_id

    elif case(word_part_e.ExprSub):
      part = cast(word_part.ExprSub, UP_part)
      return part.right.span_id

    # TODO: remove inline function calls from YSH
    elif case(word_part_e.FuncCall):
      part = cast(word_part.FuncCall, UP_part)
      return runtime.NO_SPID

    else:
      raise AssertionError(part.tag())


def OfWordLeft(w):
  # type: (word_t) -> int
  UP_w = w
  with tagswitch(w) as case:
    if case(word_e.Compound):
      w = cast(CompoundWord, UP_w)
      if len(w.parts):
        return OfWordPartLeft(w.parts[0])
      else:
        # This is possible for empty brace sub alternative {a,b,}
        return runtime.NO_SPID

    elif case(word_e.Token):
      tok = cast(Token, UP_w)
      return tok.span_id

    elif case(word_e.BracedTree):
      w = cast(word.BracedTree, UP_w)
      # This should always have one part?
      return OfWordPartLeft(w.parts[0])

    elif case(word_e.String):
      w = cast(word.String, UP_w)
      return w.span_id  # See _StringWordEmitter in osh/builtin_bracket.py

    else:
      raise AssertionError(w.tag())

  raise AssertionError('for -Wreturn-type in C++')


def OfWordRight(w):
  # type: (word_t) -> int
  """Needed for here doc delimiters."""
  UP_w = w
  with tagswitch(w) as case:
    if case(word_e.Compound):
      w = cast(CompoundWord, UP_w)
      if len(w.parts) == 0:
        # TODO: Use Empty instead
        raise AssertionError("Compound shouldn't be empty")
      else:
        end = w.parts[-1]
        return _OfWordPartRight(end)

    elif case(word_e.Token):
      tok = cast(Token, UP_w)
      return tok.span_id

    else:
      raise AssertionError(w.tag())

  raise AssertionError('for -Wreturn-type in C++')
