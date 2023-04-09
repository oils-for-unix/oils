"""
core/shell_native.py -- Subset of core/shell.py that we translate to C++.

TODO: consolidate with core/shell.py.
"""
from __future__ import print_function

from _devbuild.gen.option_asdl import builtin_i
from _devbuild.gen.runtime_asdl import cmd_value

from asdl import runtime

from core import dev
from core import process
from mycpp.mylib import log
unused1 = log
from core import state
from core import ui
from core import vm

from frontend import flag_def  # side effect: flags are defined!
unused2 = flag_def
from frontend import parse_lib

from osh import builtin_assign
from osh import builtin_bracket
from osh import builtin_meta
from osh import builtin_misc
from osh import builtin_process
from osh import builtin_process2  # can be translated
from osh import builtin_pure
from osh import cmd_eval
from osh import split

from mycpp import mylib

from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv, Proc
  from core import optview


def MakeBuiltinArgv(argv1):
  # type: (List[str]) -> cmd_value__Argv
  argv = ['']  # dummy for argv[0]
  argv.extend(argv1)
  # no location info
  return cmd_value.Argv(argv, [runtime.NO_SPID] * len(argv), None)


def AddPure(b, mem, procs, modules, mutable_opts, aliases, search_path, errfmt):
  # type: (Dict[int, vm._Builtin], state.Mem, Dict[str, Proc], Dict[str, bool], state.MutableOpts, Dict[str, str], state.SearchPath, ui.ErrorFormatter) -> None
  b[builtin_i.set] = builtin_pure.Set(mutable_opts, mem)

  b[builtin_i.alias] = builtin_pure.Alias(aliases, errfmt)
  b[builtin_i.unalias] = builtin_pure.UnAlias(aliases, errfmt)

  b[builtin_i.hash] = builtin_pure.Hash(search_path)
  b[builtin_i.getopts] = builtin_pure.GetOpts(mem, errfmt)

  true_ = builtin_pure.Boolean(0)
  b[builtin_i.colon] = true_  # a "special" builtin 
  b[builtin_i.true_] = true_
  b[builtin_i.false_] = builtin_pure.Boolean(1)

  b[builtin_i.shift] = builtin_assign.Shift(mem)

  b[builtin_i.type] = builtin_meta.Type(procs, aliases, search_path, errfmt)
  b[builtin_i.module] = builtin_pure.Module(modules, mem.exec_opts, errfmt)


def AddIO(b, mem, dir_stack, exec_opts, splitter, parse_ctx, errfmt):
  # type: (Dict[int, vm._Builtin], state.Mem, state.DirStack, optview.Exec, split.SplitContext, parse_lib.ParseContext, ui.ErrorFormatter) -> None
  b[builtin_i.echo] = builtin_pure.Echo(exec_opts)

  b[builtin_i.cat] = builtin_misc.Cat()  # for $(<file)

  # test / [ differ by need_right_bracket
  b[builtin_i.test] = builtin_bracket.Test(False, exec_opts, mem, errfmt)
  b[builtin_i.bracket] = builtin_bracket.Test(True, exec_opts, mem, errfmt)

  b[builtin_i.pushd] = builtin_misc.Pushd(mem, dir_stack, errfmt)
  b[builtin_i.popd] = builtin_misc.Popd(mem, dir_stack, errfmt)
  b[builtin_i.dirs] = builtin_misc.Dirs(mem, dir_stack, errfmt)
  b[builtin_i.pwd] = builtin_misc.Pwd(mem, errfmt)

  b[builtin_i.times] = builtin_misc.Times()


def AddProcess(
    b,  # type: Dict[int, vm._Builtin]
    mem,  # type: state.Mem
    shell_ex,  # type: vm._Executor
    ext_prog,  # type: process.ExternalProgram
    fd_state,  # type: process.FdState
    job_state,  # type: process.JobState
    waiter,  # type: process.Waiter
    tracer,  # type: dev.Tracer
    search_path,  # type: state.SearchPath
    errfmt  # type: ui.ErrorFormatter
    ):
    # type: (...) -> None

  # Process
  b[builtin_i.exec_] = builtin_process2.Exec(mem, ext_prog, fd_state,
                                            search_path, errfmt)
  b[builtin_i.umask] = builtin_process2.Umask()
  b[builtin_i.wait] = builtin_process2.Wait(waiter, job_state, mem, tracer,
                                            errfmt)

  b[builtin_i.jobs] = builtin_process.Jobs(job_state)
  b[builtin_i.fg] = builtin_process.Fg(job_state, waiter)
  b[builtin_i.bg] = builtin_process.Bg(job_state)

  b[builtin_i.fork] = builtin_process.Fork(shell_ex)
  b[builtin_i.forkwait] = builtin_process.ForkWait(shell_ex)


def AddMeta(builtins, shell_ex, mutable_opts, mem, procs, aliases, search_path,
            errfmt):
  # type: (Dict[int, vm._Builtin], vm._Executor, state.MutableOpts, state.Mem, Dict[str, Proc], Dict[str, str], state.SearchPath, ui.ErrorFormatter) -> None
  """Builtins that run more code."""

  builtins[builtin_i.builtin] = builtin_meta.Builtin(shell_ex, errfmt)
  builtins[builtin_i.command] = builtin_meta.Command(shell_ex, procs, aliases,
                                                     search_path)
  builtins[builtin_i.runproc] = builtin_meta.RunProc(shell_ex, procs, errfmt)
  builtins[builtin_i.boolstatus] = builtin_meta.BoolStatus(shell_ex, errfmt)


def AddBlock(builtins, mem, mutable_opts, dir_stack, cmd_ev, shell_ex, hay_state, errfmt):
  # type: (Dict[int, vm._Builtin], state.Mem, state.MutableOpts, state.DirStack, cmd_eval.CommandEvaluator, vm._Executor, state.Hay, ui.ErrorFormatter) -> None
  # These builtins take blocks, and thus need cmd_ev.
  builtins[builtin_i.cd] = builtin_misc.Cd(mem, dir_stack, cmd_ev, errfmt)
  builtins[builtin_i.shopt] = builtin_pure.Shopt(mutable_opts, cmd_ev)
  builtins[builtin_i.try_] = builtin_meta.Try(mutable_opts, mem, cmd_ev, shell_ex, errfmt)
  if mylib.PYTHON:
    builtins[builtin_i.hay] = builtin_pure.Hay(hay_state, mutable_opts, mem, cmd_ev)
    builtins[builtin_i.haynode] = builtin_pure.HayNode(hay_state, mem, cmd_ev)


def InitAssignmentBuiltins(mem, procs, errfmt):
  # type: (state.Mem, Dict[str, Proc], ui.ErrorFormatter) -> Dict[int, vm._AssignBuiltin]

  assign_b = {}  # type: Dict[int, vm._AssignBuiltin]

  new_var = builtin_assign.NewVar(mem, procs, errfmt)
  assign_b[builtin_i.declare] = new_var
  assign_b[builtin_i.typeset] = new_var
  assign_b[builtin_i.local] = new_var

  assign_b[builtin_i.export_] = builtin_assign.Export(mem, errfmt)
  assign_b[builtin_i.readonly] = builtin_assign.Readonly(mem, errfmt)

  return assign_b
