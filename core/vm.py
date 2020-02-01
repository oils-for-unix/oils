#!/usr/bin/env python2
"""
vm.py: Library for executing shell.
"""
from __future__ import print_function

from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from osh.sh_expr_eval import ArithEvaluator
  from osh.sh_expr_eval import BoolEvaluator
  from oil_lang.expr_eval import OilEvalutor
  from osh.word_eval import _WordEvaluator
  from osh.cmd_exec import Executor
  from osh import prompt
  from core import dev


def InitCircularDeps(arith_ev, bool_ev, expr_ev, word_ev, ex, prompt_ev, tracer):
  # type: (ArithEvaluator, BoolEvaluator, OilEvalutor, _WordEvaluator, Executor, prompt.Evaluator, dev.Tracer) -> None
  arith_ev.word_ev = word_ev
  bool_ev.word_ev = word_ev

  expr_ev.ex = ex
  expr_ev.word_ev = word_ev

  word_ev.arith_ev = arith_ev
  word_ev.expr_ev = expr_ev
  word_ev.prompt_ev = prompt_ev
  word_ev.ex = ex

  ex.arith_ev = arith_ev
  ex.bool_ev = bool_ev
  ex.expr_ev = expr_ev
  ex.word_ev = word_ev
  ex.tracer = tracer

  arith_ev.CheckCircularDeps()
  bool_ev.CheckCircularDeps()
  expr_ev.CheckCircularDeps()
  word_ev.CheckCircularDeps()
  ex.CheckCircularDeps()
