#!/usr/bin/env python2
"""
location.py - Library to get source location info from nodes.

This makes syntax errors nicer.

TODO: Move some of osh/word_ here.
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    loc_t, loc_e, loc__Span, loc__WordPart, loc__Word,
    command_e, command_t, command__Simple, command__ShAssignment,
    command__Pipeline, command__AndOr, command__DoGroup, command__Sentence,
    command__Subshell, command__WhileUntil, command__If, command__Case,
    command__TimeBlock,
    BraceGroup,

    arith_expr_e, arith_expr_t, compound_word, Token,
)
from asdl import runtime
from core.pyerror import log
from mycpp.mylib import tagswitch
from osh import word_

from typing import cast, TYPE_CHECKING


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
      loc_ = cast(loc__Span, UP_location)
      return loc_.span_id

    elif case(loc_e.WordPart):
      loc_ = cast(loc__WordPart, UP_location)
      if loc_.p:
        return word_.LeftMostSpanForPart(loc_.p)
      else:
        return runtime.NO_SPID

    elif case(loc_e.Word):
      loc_ = cast(loc__Word, UP_location)
      if loc_.w:
        return word_.LeftMostSpanForWord(loc_.w)
      else:
        return runtime.NO_SPID

    else:
      raise AssertionError()

  raise AssertionError()


def SpanForCommand(node):
  # type: (command_t) -> int
  """
  like word_.LeftMostSpanForWord
  """
  UP_node = node # type: command_t
  tag = node.tag_()

  if tag == command_e.Sentence:
    node = cast(command__Sentence, UP_node)
    #log("node.child %s", node.child)
    return node.terminator.span_id  # & or ;

  if tag == command_e.Simple:
    node = cast(command__Simple, UP_node)
    # It should have either words or redirects, e.g. '> foo'
    if len(node.words):
      return word_.LeftMostSpanForWord(node.words[0])
    elif len(node.redirects):
      return node.redirects[0].op.span_id

  if tag == command_e.ShAssignment:
    node = cast(command__ShAssignment, UP_node)
    return node.spids[0]

  if tag == command_e.Pipeline:
    node = cast(command__Pipeline, UP_node)
    return node.spids[0]  # first |
  if tag == command_e.AndOr:
    node = cast(command__AndOr, UP_node)
    return node.spids[0]  # first && or ||
  if tag == command_e.DoGroup:
    node = cast(command__DoGroup, UP_node)
    return node.spids[0]  # do spid
  if tag == command_e.BraceGroup:
    node = cast(BraceGroup, UP_node)
    return node.left.span_id  # { spid
  if tag == command_e.Subshell:
    node = cast(command__Subshell, UP_node)
    return node.spids[0]  # ( spid
  if tag == command_e.WhileUntil:
    node = cast(command__WhileUntil, UP_node)
    return node.spids[0]  # while spid
  if tag == command_e.If:
    node = cast(command__If, UP_node)
    return node.arms[0].spids[0]  # if spid is in FIRST arm.
  if tag == command_e.Case:
    node = cast(command__Case, UP_node)
    return node.spids[0]  # case keyword spid
  if tag == command_e.TimeBlock:
    node = cast(command__TimeBlock, UP_node)
    return node.spids[0]  # time keyword spid

  # We never have this case?
  #if node.tag == command_e.CommandList:
  #  pass

  return runtime.NO_SPID


def SpanForArithExpr(node):
  # type: (arith_expr_t) -> int
  UP_node = node
  with tagswitch(node) as case:
    if case(arith_expr_e.VarRef):
      token = cast(Token, UP_node)
      return token.span_id
    elif case(arith_expr_e.Word):
      w = cast(compound_word, UP_node)
      return word_.LeftMostSpanForWord(w)

  return runtime.NO_SPID
