#!/usr/bin/env python2
"""
location.py - Library to get source location info from nodes.

This makes syntax errors nicer.

TODO: Move some of osh/word_ here.
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    command_e, command_t, command__Pipeline, command__AndOr,
    command__DoGroup, command__BraceGroup, command__Subshell,
    command__WhileUntil, command__If, command__Case, command__TimeBlock,
)
from asdl import runtime
from core.util import log

from typing import cast

def SpanForCommand(node):
  # type: (command_t) -> int
  """
  like word_.LeftMostSpanForWord
  """
  UP_node = node # type: command_t
  tag = node.tag_()
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
    node = cast(command__BraceGroup, UP_node)
    return node.spids[0]  # { spid
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
