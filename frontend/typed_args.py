#!/usr/bin/env python2
"""
typed_args.py
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    loc, ArgList, BlockArg, command_t, expr_e, expr_t, command_sub
)
from core.pyerror import e_usage
from mycpp.mylib import tagswitch

from typing import Optional, cast, TYPE_CHECKING


def DoesNotAccept(arg_list):
  # type: (Optional[ArgList]) -> None
  if arg_list is not None:
    e_usage('got unexpected typed args', arg_list.left)


def RequiredExpr(arg_list):
  # type: (Optional[ArgList]) -> Optional[expr_t]
  if arg_list is None:
    e_usage('Expected an expression', loc.Missing())

  n = len(arg_list.positional)
  if n == 0:
    e_usage('Expected an expression', arg_list.left)

  elif n == 1:
    return arg_list.positional[0]

  else:
    e_usage('Too many typed args (expected one expression)', arg_list.left)


def GetOneBlock(arg_list):
  # type: (Optional[ArgList]) -> Optional[command_t]
  """Returns the first block arg, if any.

  For cd { }, shopt { }, etc.

  Errors:
    - the first arg isn't a block
    - more than 1 arg
  """

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
        arg = cast(BlockArg, UP_arg)
        return arg.brace_group

      # TODO: we need an expr_ev for cd /tmp (myblock)
      elif case(expr_e.CommandSub):  # cd /tmp (^(echo hi))
        arg = cast(command_sub, UP_arg)
        return arg.child

      else:
        e_usage('Expected block argument', arg_list.left)

  else:
    e_usage('Too many typed args (expected one block)', arg_list.left)


def GetLiteralBlock(arg_list):
  # type: (Optional[ArgList]) -> Optional[BlockArg]
  """Returns the first block literal arg, if any.

  For Hay evaluation.

  Errors:
    - more than 1 arg
  """

  if arg_list is None:
    return None

  n = len(arg_list.positional)
  if n == 0:
    return None

  elif n == 1:
    arg = arg_list.positional[0]
    if arg.tag_() == expr_e.BlockArg:
      return cast(BlockArg, arg)
    else:
      return None

  else:
    e_usage('Too many typed args (expected one block)', arg_list.left)
