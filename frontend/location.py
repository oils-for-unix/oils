#!/usr/bin/env python2
"""
location.py - Library to get source location info from nodes.

This makes syntax errors nicer.

TODO: Move some of osh/word_ here.
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import command_e, command_t
from asdl import runtime
from core.util import log


def SpanForCommand(node):
  # type: (command_t) -> Int
  """
  like word_.LeftMostSpanForWord
  """
  if node.tag == command_e.Pipeline:
    return node.spids[0]  # first |
  if node.tag == command_e.AndOr:
    return node.spids[0]  # first && or ||
  if node.tag == command_e.DoGroup:
    return node.spids[0]  # do spid
  if node.tag == command_e.BraceGroup:
    return node.spids[0]  # { spid
  if node.tag == command_e.Subshell:
    return node.spids[0]  # ( spid
  if node.tag == command_e.WhileUntil:
    return node.spids[0]  # while spid
  if node.tag == command_e.If:
    return node.arms[0].spids[0]  # if spid is in FIRST arm.
  if node.tag == command_e.Case:
    return node.spids[0]  # case keyword spid
  if node.tag == command_e.TimeBlock:
    return node.spids[0]  # time keyword spid

  # We never have this case?
  #if node.tag == command_e.CommandList:
  #  pass

  return runtime.NO_SPID
