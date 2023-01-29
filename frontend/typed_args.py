#!/usr/bin/env python2
"""
typed_args.py
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    ArgList, command_t, expr_e, expr_t, expr__BlockArg, command_sub
)
from core.pyerror import e_usage
from mycpp.mylib import tagswitch

from typing import Optional, cast, TYPE_CHECKING


def DoesNotAccept(arg_list):
  # type: (Optional[ArgList]) -> None
  if arg_list is not None:
    e_usage('got unexpected typed args', arg_list.left.span_id)


def RequiredExpr(arg_list):
  # type: (Optional[ArgList]) -> Optional[expr_t]
  if arg_list is None:
    e_usage('Expected an expression')

  n = len(arg_list.positional)
  if n == 0:
    e_usage('Expected an expression', arg_list.left.span_id)

  elif n == 1:
    return arg_list.positional[0]

  else:
    e_usage('Too many typed args (expected one expression)', arg_list.left.span_id)


def GetOneBlock(arg_list):
  # type: (Optional[ArgList]) -> Optional[command_t]

  if arg_list is None:
    return None

  n = len(arg_list.positional)
  if n == 0:
    return None

  elif n == 1:
    arg = arg_list.positional[0]
    UP_arg = arg

    # Could we somehow consolidate these?
    with tagswitch(arg) as case:
      if case(expr_e.BlockArg):  # cd /tmp { echo hi }
        arg = cast(expr__BlockArg, UP_arg)
        return arg.block

      # TODO: we need an expr_ev for cd /tmp (myblock)
      elif case(expr_e.CommandSub):  # cd /tmp (^(echo hi))
        arg = cast(command_sub, UP_arg)
        return arg.child

      else:
        e_usage('Expected block argument', arg_list.left.span_id)

  else:
    e_usage('Too many typed args (expected one block)', arg_list.left.span_id)
