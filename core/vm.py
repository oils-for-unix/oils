"""
vm.py: Library for executing shell.
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import CompoundStatus
from typing import List, Any, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import (
      cmd_value__Argv, cmd_value__Assign, redirect
  )
  from _devbuild.gen.syntax_asdl import (
      command_t, command__Pipeline, command_sub
  )
  from osh import sh_expr_eval
  from osh.sh_expr_eval import ArithEvaluator
  from osh.sh_expr_eval import BoolEvaluator
  from oil_lang.expr_eval import OilEvaluator
  from osh.word_eval import NormalWordEvaluator
  from osh.cmd_eval import CommandEvaluator
  from osh import prompt
  from core import dev
  from core import state


def InitUnsafeArith(mem, word_ev, unsafe_arith):
  # type: (state.Mem, NormalWordEvaluator, sh_expr_eval.UnsafeArith) -> None
  """Wire up circular dependencies for UnsafeArith."""
  if 0:
    mem.unsafe_arith = unsafe_arith  # for 'declare -n' nameref expansion of a[i]

  word_ev.unsafe_arith = unsafe_arith  # for ${!ref} expansion of a[i]


def InitCircularDeps(arith_ev, bool_ev, expr_ev, word_ev, cmd_ev, shell_ex, prompt_ev, tracer):
  # type: (ArithEvaluator, BoolEvaluator, OilEvaluator, NormalWordEvaluator, CommandEvaluator, _Executor, prompt.Evaluator, dev.Tracer) -> None
  """Wire up mutually recursive evaluators and runtime objects."""
  arith_ev.word_ev = word_ev
  bool_ev.word_ev = word_ev

  if expr_ev:  # for pure OSH
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
  tracer.word_ev = word_ev

  arith_ev.CheckCircularDeps()
  bool_ev.CheckCircularDeps()
  if expr_ev:
    expr_ev.CheckCircularDeps()
  word_ev.CheckCircularDeps()
  cmd_ev.CheckCircularDeps()
  shell_ex.CheckCircularDeps()
  prompt_ev.CheckCircularDeps()
  tracer.CheckCircularDeps()


class _Executor(object):

  def __init__(self):
    # type: () -> None
    self.cmd_ev = None  # type: CommandEvaluator

  def CheckCircularDeps(self):
    # type: () -> None
    pass

  def RunBuiltin(self, builtin_id, cmd_val):
    # type: (int, cmd_value__Argv) -> int
    """
    The 'builtin' builtin in osh/builtin_meta.py needs this.
    """
    return 0

  def RunSimpleCommand(self, cmd_val, do_fork, call_procs=True):
    # type: (cmd_value__Argv, bool, bool) -> int
    return 0

  def RunBackgroundJob(self, node):
    # type: (command_t) -> int
    return 0

  def RunPipeline(self, node, status_out):
    # type: (command__Pipeline, CompoundStatus) -> None
    pass

  def RunSubshell(self, node):
    # type: (command_t) -> int
    return 0

  def RunCommandSub(self, cs_part):
    # type: (command_sub) -> str
    return ''

  def RunProcessSub(self, cs_part):
    # type: (command_sub) -> str
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

  def PushProcessSub(self):
    # type: () -> None
    pass

  def PopProcessSub(self, compound_st):
    # type: (CompoundStatus) -> None
    pass


#
# Abstract base classes
#


class _AssignBuiltin(object):
  """Interface for assignment builtins."""

  def __init__(self):
    # type: () -> None
    """Empty constructor for mycpp."""
    pass

  def Run(self, cmd_val):
    # type: (cmd_value__Assign) -> int
    raise NotImplementedError()


class _Builtin(object):
  """All builtins except 'command' obey this interface.

  Assignment builtins use cmd_value__Assign; others use cmd_value__Argv.
  """

  def __init__(self):
    # type: () -> None
    """Empty constructor for mycpp."""
    pass

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    raise NotImplementedError()


class ctx_Redirect(object):
  """For closing files.

  This is asymmetric because if PushRedirects fails, then we don't execute the
  command at all.

  Example:
    { seq 3 > foo.txt; echo 4; } > bar.txt 
  """
  def __init__(self, shell_ex):
    # type: (_Executor) -> None
    self.shell_ex = shell_ex

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.shell_ex.PopRedirects()


class ctx_ProcessSub(object):
  """For waiting on processes started during word evaluation.

  Example:
    diff <(seq 3) <(seq 4) > >(tac)
  """
  def __init__(self, shell_ex, process_sub_status):
    # type: (_Executor, CompoundStatus) -> None
    shell_ex.PushProcessSub()
    self.shell_ex = shell_ex
    self.process_sub_status = process_sub_status

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None

    # Wait and return array to set _process_sub_status
    self.shell_ex.PopProcessSub(self.process_sub_status)
