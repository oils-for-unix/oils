#!/usr/bin/env python2
"""
location.py - Library to get source location info from nodes.

This makes syntax errors nicer.

TODO: Move some of osh/word_ here.
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    loc, loc_t, loc_e,
    CompoundWord, SimpleVarSub, Token,
    command, command_e, command_t,
    BraceGroup,
    arith_expr_e, arith_expr_t,
)
from _devbuild.gen.runtime_asdl import lvalue
from asdl import runtime
from mycpp.mylib import log
from mycpp.mylib import tagswitch
from osh import word_

from typing import cast, TYPE_CHECKING


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
        return word_.LeftMostSpanForPart(loc_.p)
      else:
        return runtime.NO_SPID

    elif case(loc_e.Word):
      loc_ = cast(loc.Word, UP_location)
      if loc_.w:
        return word_.LeftMostSpanForWord(loc_.w)
      else:
        return runtime.NO_SPID

    else:
      raise AssertionError()

  raise AssertionError()


def LocForCommand(node):
  # type: (command_t) -> loc_t
  """
  like word_.LeftMostSpanForWord
  """
  UP_node = node # type: command_t
  tag = node.tag()

  if tag == command_e.Sentence:
    node = cast(command.Sentence, UP_node)
    #log("node.child %s", node.child)
    return node.terminator  # & or ;

  if tag == command_e.Simple:
    node = cast(command.Simple, UP_node)
    # It should have either words or redirects, e.g. '> foo'
    if len(node.words):
      return loc.Word(node.words[0])
    elif len(node.redirects):
      return node.redirects[0].op

  if tag == command_e.ShAssignment:
    node = cast(command.ShAssignment, UP_node)
    return loc.Span(node.spids[0])

  if tag == command_e.Pipeline:
    node = cast(command.Pipeline, UP_node)
    return loc.Span(node.spids[0])  # first |
  if tag == command_e.AndOr:
    node = cast(command.AndOr, UP_node)
    return loc.Span(node.spids[0])  # first && or ||
  if tag == command_e.DoGroup:
    node = cast(command.DoGroup, UP_node)
    return loc.Span(node.spids[0])  # do spid
  if tag == command_e.BraceGroup:
    node = cast(BraceGroup, UP_node)
    return node.left  # { spid
  if tag == command_e.Subshell:
    node = cast(command.Subshell, UP_node)
    return loc.Span(node.spids[0])  # ( spid
  if tag == command_e.WhileUntil:
    node = cast(command.WhileUntil, UP_node)
    return loc.Span(node.spids[0])  # while spid
  if tag == command_e.If:
    node = cast(command.If, UP_node)
    return loc.Span(node.arms[0].spids[0])  # if spid is in FIRST arm.
  if tag == command_e.Case:
    node = cast(command.Case, UP_node)
    return loc.Span(node.spids[0])  # case keyword spid
  if tag == command_e.TimeBlock:
    node = cast(command.TimeBlock, UP_node)
    return loc.Span(node.spids[0])  # time keyword spid

  # We never have this case?
  #if node.tag == command_e.CommandList:
  #  pass

  return loc.Missing


def LocForArithExpr(node):
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
