#!/usr/bin/env python2
"""
vm.py: Library for executing shell.
"""
from __future__ import print_function

from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from osh.sh_expr_eval import ArithEvaluator
  from osh.sh_expr_eval import BoolEvaluator
  from oil_lang.expr_eval import OilEvaluator
  from osh.word_eval import NormalWordEvaluator
  from osh.cmd_eval import CommandEvaluator
  from osh import prompt
  from core import dev
  from core import executor


def InitCircularDeps(arith_ev, bool_ev, expr_ev, word_ev, cmd_ev, shell_ex, prompt_ev, tracer):
  # type: (ArithEvaluator, BoolEvaluator, OilEvaluator, NormalWordEvaluator, CommandEvaluator, executor.ShellExecutor, prompt.Evaluator, dev.Tracer) -> None
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
