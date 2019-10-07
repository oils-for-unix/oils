#!/usr/bin/python
"""
switch1.py

Idea from https://stackoverflow.com/a/30012053

This will translate more easily into C++ switch statements.
"""
from __future__ import print_function

import os
import sys

from mylib import log
from typing import List, Any


# This could go in pyutil.py or something
class Switch(object):
  """A ContextManager that translates to a C switch statement."""

  def __init__(self, value):
    # type: (int) -> None
    self.value = value

  def __enter__(self):
    # type: () -> Switch
    return self

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> bool
    return False  # Allows a traceback to occur

  def __call__(self, *values):
    # type: (*Any) -> bool
    return self.value in values



class typeswitch(object):
  """A ContextManager that translates to a C switch statement.
  
  Each case will have a static_cast<>.  It does nothing at mylib."""
  def __init__(self):
    # type: (int) -> None
    pass

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> bool
    return False  # Allows a traceback to occur


def run_tests():
  # type: () -> None
  x = 1
  x = 15

  # This style is shorter
  #
  # I like 'else' for default: better
  #
  # I think the MyPy AST can translate it.
  # just look at all the else_body -- and if the expression looks like case(),
  # then you can flatten it out.
  #
  # switch(x) {
  # case 0: {
  #   print("zero")
  #   }
  #   break;
  # case 1:
  # case 2: {
  #   print("one or two")
  #   print("...")
  #   }
  #   break;
  # default: {
  #   print("default")
  #   }
  #   break;
  # }

  with Switch(x) as case:
    if case(0):
      print('zero')

    elif case(1, 2):
      print('one or two')

    elif case(3, 4):
      print('three or four')

    else:
      print('default')

  # TODO: type switch will be more common.  We need to preserve instance() for
  # MyPy.
  # 'typeswitch' involves CASTING, while 'switch' does not.  'switch' is for
  # simple sum types (enums).
  # 
  # with typeswitch(node) as _:  # dummy for translation
  #   if isinstance(node, expr__Const):
  #     n = node                        # rename for casting?
  #     return n.i
  #
  #   elif isinstance(node, expr__Var):
  #     return self.mem[node.name]
  #
  #   elif isinstance(node, expr__Binary):
  #     return self.Eval(node.left) + self.Eval(node.right)
  #
  # switch (node.tag) {
  #   case expr_e::Const: {
  #     n = static_cast<expr__Const>(node);
  #     return n.i
  #   }
  #   case expr_e::Var: {
  #     n = static_cast<expr__Var>(node);
  #     return this->mem_[n.name]
  #   }
  # }

  node = 3
  #node = True
  with typeswitch() as _:
    if isinstance(node, bool):
      n = node
      log('bool %s', n)
    elif isinstance(node, int):
      n = node
      log('int %s', n)


def run_benchmarks():
  # type: () -> None
  log('TODO')


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
