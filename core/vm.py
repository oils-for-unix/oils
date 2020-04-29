#!/usr/bin/env python2
"""
vm.py: Library for executing shell.
"""
from __future__ import print_function

from mycpp import mylib

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.id_kind_asdl import Id_t
  from _devbuild.gen.runtime_asdl import cmd_value__Argv, redirect
  from _devbuild.gen.syntax_asdl import (
      command_t, command__Pipeline, command__Subshell
  )
  from osh.sh_expr_eval import ArithEvaluator
  from osh.sh_expr_eval import BoolEvaluator
  from oil_lang.expr_eval import OilEvaluator
  from osh.word_eval import NormalWordEvaluator
  from osh.cmd_eval import CommandEvaluator
  from osh import prompt
  from core import dev


if mylib.PYTHON:
  def InitCircularDeps(arith_ev, bool_ev, expr_ev, word_ev, cmd_ev, shell_ex, prompt_ev, tracer):
    # type: (ArithEvaluator, BoolEvaluator, OilEvaluator, NormalWordEvaluator, CommandEvaluator, _Executor, prompt.Evaluator, dev.Tracer) -> None
    arith_ev.word_ev = word_ev
    bool_ev.word_ev = word_ev

    expr_ev.shell_ex = shell_ex
    expr_ev.word_ev = word_ev

    word_ev.arith_ev = arith_ev
    word_ev.expr_ev = expr_ev
    word_ev.prompt_ev = prompt_ev
    word_ev.shell_ex = shell_ex

    cmd_ev.shell_ex = shell_ex
    cmd_ev.arith_ev = arith_ev
    cmd_ev.bool_ev = bool_ev
    cmd_ev.expr_ev = expr_ev
    cmd_ev.word_ev = word_ev
    cmd_ev.tracer = tracer

    shell_ex.cmd_ev = cmd_ev

    prompt_ev.word_ev = word_ev

    arith_ev.CheckCircularDeps()
    bool_ev.CheckCircularDeps()
    expr_ev.CheckCircularDeps()
    word_ev.CheckCircularDeps()
    cmd_ev.CheckCircularDeps()
    shell_ex.CheckCircularDeps()
    prompt_ev.CheckCircularDeps()


class _Executor(object):

  def __init__(self):
    # type: () -> None
    self.cmd_ev = None  # type: CommandEvaluator

  def CheckCircularDeps(self):
    # type: () -> None
    pass

  def RunSimpleCommand(self, cmd_val, do_fork, call_procs=True):
    # type: (cmd_value__Argv, bool, bool) -> int
    return 0

  def RunBackgroundJob(self, node):
    # type: (command_t) -> int
    return 0

  def RunPipeline(self, node):
    # type: (command__Pipeline) -> int
    return 0

  def RunSubshell(self, node):
    # type: (command__Subshell) -> int
    return 0

  def RunCommandSub(self, node):
    # type: (command_t) -> str
    return ''

  def RunProcessSub(self, node, op_id):
    # type: (command_t, Id_t) -> str
    return ''

  def Time(self):
    # type: () -> None
    pass

  def PushRedirects(self, redirects):
    # type: (List[redirect]) -> bool
    return True

  def PopRedirects(self):
    # type: () -> None
    pass

