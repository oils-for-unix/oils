"""
dev.py - Devtools / introspection.
"""
from __future__ import print_function

from _devbuild.gen.option_asdl import option_i, builtin_i, builtin_t
from _devbuild.gen.runtime_asdl import (
    value, value_e, value__Str, value__MaybeStrArray, value__AssocArray,
    lvalue, lvalue_e, lvalue__Named, lvalue__Indexed, lvalue__Keyed,
    cmd_value__Assign, scope_e, trace_e, trace_t, trace__External
)
from _devbuild.gen.syntax_asdl import assign_op_e

from asdl import runtime
from core import error
from core import optview
from core import state
from core import ui
from core.pyerror import log
from frontend import location
from osh import word_
from qsn_ import qsn
from pylib import os_path
from mycpp import mylib
from mycpp.mylib import tagswitch, iteritems

import yajl

import posix_ as posix

from typing import List, Dict, Optional, Any, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import assign_op_t, compound_word
  from _devbuild.gen.runtime_asdl import lvalue_t, value_t, scope_t
  from core import alloc
  from core.error import _ErrorWithLocation
  from core.util import _DebugFile
  from frontend.parse_lib import ParseContext
  from core.state import MutableOpts, Mem
  from osh.word_eval import NormalWordEvaluator
  from osh.cmd_eval import CommandEvaluator


class CrashDumper(object):
  """
  Controls if we collect a crash dump, and where we write it to.

  An object that can be serialized to JSON.

  trap CRASHDUMP upload-to-server

  # it gets written to a file first
  upload-to-server() {
    local path=$1
    curl -X POST https://osh-trace.oilshell.org  < $path
  }

  Things to dump:
  CommandEvaluator
    functions, aliases, traps, completion hooks, fd_state, dir_stack
  
  debug info for the source?  Or does that come elsewhere?
  
  Yeah I think you sould have two separate files.
  - debug info for a given piece of code (needs hash)
    - this could just be the raw source files?  Does it need anything else?
    - I think it needs a hash so the VM dump can refer to it.
  - vm dump.
  - Combine those and you get a UI.
  
  One is constant at build time; the other is constant at runtime.
  """
  def __init__(self, crash_dump_dir):
    # type: (str) -> None
    self.crash_dump_dir = crash_dump_dir
    # whether we should collect a dump, at the highest level of the stack
    self.do_collect = bool(crash_dump_dir)
    self.collected = False  # whether we have anything to dump

    self.var_stack = None
    self.argv_stack = None
    self.debug_stack = None
    self.error = None  # type: Dict[str, Any]

  def MaybeRecord(self, cmd_ev, err):
    # type: (CommandEvaluator, _ErrorWithLocation) -> None
    """
    Collect data for a crash dump.

    Args:
      cmd_ev: CommandEvaluator instance
      error: _ErrorWithLocation (ParseError or error.FatalRuntime)
    """
    if not self.do_collect:  # Either we already did it, or there is no file
      return

    if mylib.PYTHON:  # can't translate yet due to dynamic typing
      self.var_stack, self.argv_stack, self.debug_stack = cmd_ev.mem.Dump()
      span_id = location.GetSpanId(err.location)

      self.error = {
         'msg': err.UserErrorString(),
         'span_id': span_id,
      }

      if span_id != runtime.NO_SPID:
        span = cmd_ev.arena.GetToken(span_id)
        line_id = span.line_id

        # Could also do msg % args separately, but JavaScript won't be able to
        # render that.
        self.error['source'] = ui.GetLineSourceString(cmd_ev.arena, line_id)
        self.error['line_num'] = cmd_ev.arena.GetLineNumber(line_id)
        self.error['line'] = cmd_ev.arena.GetLine(line_id)

      # TODO: Collect functions, aliases, etc.

      self.do_collect = False
      self.collected = True

  def MaybeDump(self, status):
    # type: (int) -> None
    """Write the dump as JSON.

    User can configure it two ways:
    - dump unconditionally -- a daily cron job.  This would be fine.
    - dump on non-zero exit code

    OIL_FAIL
    Maybe counters are different than failure

    OIL_CRASH_DUMP='function alias trap completion stack' ?
    OIL_COUNTER_DUMP='function alias trap completion'
    and then
    I think both of these should dump the (path, mtime, checksum) of the source
    they ran?  And then you can match those up with source control or whatever?
    """
    if not self.collected:
      return

    if mylib.PYTHON:  # can't translate due to open()

      my_pid = posix.getpid()  # Get fresh PID here

      # Other things we need: the reason for the crash!  _ErrorWithLocation is
      # required I think.
      d = {
          'var_stack': self.var_stack,
          'argv_stack': self.argv_stack,
          'debug_stack': self.debug_stack,
          'error': self.error,
          'status': status,
          'pid': my_pid,
      }

      path = os_path.join(self.crash_dump_dir, '%d-osh-crash-dump.json' % my_pid)
      json_str = yajl.dumps(d, indent=2)
      with open(path, 'w') as f:
        print(json_str, file=f)
      log('[%d] Wrote crash dump to %s', my_pid, path)


class ctx_Tracer(object):
  """A stack for tracing synchronous constructs."""

  def __init__(self, tracer, label, argv):
    # type: (Tracer, str, Optional[List[str]]) -> None
    self.arg = None  # type: Optional[str]
    if label == 'proc':
      self.arg = argv[0]
    elif label == 'source':
      self.arg = argv[1]

    tracer.PushMessage(label, argv)
    self.label = label
    self.tracer = tracer

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.tracer.PopMessage(self.label, self.arg)


def _PrintShValue(val, buf):
  # type: (value_t, mylib.BufWriter) -> None
  """Using maybe_shell_encode() for legacy xtrace_details."""

  # NOTE: This is a bit like _PrintVariables for declare -p
  result = '?'
  UP_val = val
  with tagswitch(val) as case:
    if case(value_e.Str):
      val = cast(value__Str, UP_val)
      result = qsn.maybe_shell_encode(val.s)

    elif case(value_e.MaybeStrArray):
      val = cast(value__MaybeStrArray, UP_val)
      parts = ['(']
      for s in val.strs:
        parts.append(qsn.maybe_shell_encode(s))
      parts.append(')')
      result = ' '.join(parts)

    elif case(value_e.AssocArray):
      val = cast(value__AssocArray, UP_val)
      parts = ['(']
      for k, v in iteritems(val.d):
        parts.append('[%s]=%s' % (
            qsn.maybe_shell_encode(k), qsn.maybe_shell_encode(v)))
      parts.append(')')
      result = ' '.join(parts)

  buf.write(result)


def _PrintArgv(argv, buf):
  # type: (List[str], mylib.BufWriter) -> None
  """Uses QSN encoding without $ for xtrace_rich."""
  for arg in argv:
    buf.write(' ')
    buf.write(qsn.maybe_encode(arg))
  buf.write('\n')


class Tracer(object):
  """For shell's set -x, and Oil's hierarchical, parsable tracing.

  See doc/xtrace.md for details.

  - TODO: Connect it somehow to tracers for other processes.  So you can make
    an HTML report offline.
    - Could inherit SHX_*

  https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html#Bash-Variables

  Other hooks:

  - Command completion starts other processes
  - Oil command constructs: BareDecl, VarDecl, PlaceMutation, Expr
  """
  def __init__(self,
               parse_ctx,  # type: ParseContext
               exec_opts,  # type: optview.Exec
               mutable_opts,  # type: MutableOpts
               mem,  # type: Mem
               f,  # type: _DebugFile
               ):
    # type: (...) -> None
    """
    Args:
      parse_ctx: For parsing PS4.
      exec_opts: For xtrace setting
      mem: for retrieving PS4
      word_ev: for evaluating PS4
    """
    self.parse_ctx = parse_ctx
    self.exec_opts = exec_opts
    self.mutable_opts = mutable_opts
    self.mem = mem
    self.f = f  # can be stderr, the --debug-file, etc.

    self.word_ev = None  # type: NormalWordEvaluator

    self.ind = 0  # changed by process, proc, source, eval
    self.indents = ['']  # "pooled" to avoid allocations

    # PS4 value -> compound_word.  PS4 is scoped.
    self.parse_cache = {}  # type: Dict[str, compound_word]

    # Mutate objects to save allocations
    self.val_indent = value.Str('')
    self.val_punct = value.Str('')
    self.val_pid_str = value.Str('')  # mutated by SetProcess

    # Can these be global constants?  I don't think we have that in ASDL yet.
    self.lval_indent = lvalue.Named('SHX_indent')
    self.lval_punct = lvalue.Named('SHX_punct')
    self.lval_pid_str = lvalue.Named('SHX_pid_str')

  def CheckCircularDeps(self):
    # type: () -> None
    assert self.word_ev is not None

  def _EvalPS4(self, punct):
    # type: (str) -> str
    """The prefix of each line."""
    val = self.mem.GetValue('PS4')
    if val.tag_() == value_e.Str:
      ps4 = cast(value__Str, val).s
    else:
      ps4 = ''

    # NOTE: This cache is slightly broken because aliases are mutable!  I think
    # that is more or less harmless though.
    ps4_word = self.parse_cache.get(ps4)
    if ps4_word is None:
      # We have to parse this at runtime.  PS4 should usually remain constant.
      w_parser = self.parse_ctx.MakeWordParserForPlugin(ps4)

      try:
        ps4_word = w_parser.ReadForPlugin()
      except error.Parse as e:
        ps4_word = word_.ErrorWord(
            "<ERROR: Can't parse PS4: %s>" % e.UserErrorString())
      self.parse_cache[ps4] = ps4_word

    # Mutate objects to save allocations
    if self.exec_opts.xtrace_rich():
      self.val_indent.s = self.indents[self.ind] 
    else:
      self.val_indent.s = ''
    self.val_punct.s = punct

    # Prevent infinite loop when PS4 has command sub!
    assert self.exec_opts.xtrace()  # We shouldn't call this unless it's on

    # TODO: Remove allocation for [] ?
    with state.ctx_Option(self.mutable_opts, [option_i.xtrace], False):
      with state.ctx_Temp(self.mem):
        self.mem.SetValue(self.lval_indent, self.val_indent, scope_e.LocalOnly)
        self.mem.SetValue(self.lval_punct, self.val_punct, scope_e.LocalOnly)
        self.mem.SetValue(self.lval_pid_str, self.val_pid_str, scope_e.LocalOnly)
        prefix = self.word_ev.EvalForPlugin(ps4_word)
    return prefix.s

  def _Inc(self):
    # type: () -> None
    self.ind += 1
    if self.ind >= len(self.indents):  # make sure there are enough
      self.indents.append('  ' * self.ind)

  def _Dec(self):
    # type: () -> None
    self.ind -= 1

  def _ShTraceBegin(self):
    # type: () -> Optional[mylib.BufWriter]
    if not self.exec_opts.xtrace() or not self.exec_opts.xtrace_details():
      return None

    # Note: bash repeats the + for command sub, eval, source.  Other shells
    # don't do it.  Leave this out for now.
    prefix = self._EvalPS4('+')
    buf = mylib.BufWriter()
    buf.write(prefix)
    return buf

  def _RichTraceBegin(self, punct):
    # type: (str) -> Optional[mylib.BufWriter]
    """For the stack printed by xtrace_rich"""
    if not self.exec_opts.xtrace() or not self.exec_opts.xtrace_rich():
      return None

    prefix = self._EvalPS4(punct)
    buf = mylib.BufWriter()
    buf.write(prefix)
    return buf

  def OnProcessStart(self, pid, why):
    # type: (int, trace_t) -> None
    buf = self._RichTraceBegin('|')
    if not buf:
      return

    # TODO: ProcessSub and PipelinePart are commonly command.Simple, and also
    # Fork/ForkWait through the BraceGroup.  We could print those argv arrays.

    UP_why = why
    with tagswitch(why) as case:
      # Synchronous cases
      if case(trace_e.External):
        why = cast(trace__External, UP_why)
        buf.write('command %d:' % pid)
        _PrintArgv(why.argv, buf)

      # Everything below is the same.  Could use string literals?
      elif case(trace_e.ForkWait):
        buf.write('forkwait %d\n' % pid)
      elif case(trace_e.CommandSub):
        buf.write('command sub %d\n' % pid)

      # Async cases
      elif case(trace_e.ProcessSub):
        buf.write('proc sub %d\n' % pid)
      elif case(trace_e.HereDoc):
        buf.write('here doc %d\n' % pid)
      elif case(trace_e.Fork):
        buf.write('fork %d\n' % pid)
      elif case(trace_e.PipelinePart):
        buf.write('part %d\n' % pid)

      else:
        raise AssertionError()

    self.f.write(buf.getvalue())

  def OnProcessEnd(self, pid, status):
    # type: (int, int) -> None
    buf = self._RichTraceBegin(';')
    if not buf:
      return

    buf.write('process %d: status %d\n' % (pid, status))
    self.f.write(buf.getvalue())

  def SetProcess(self, pid):
    # type: (int) -> None
    """
    All trace lines have a PID prefix, except those from the root process.
    """
    self.val_pid_str.s = ' %d' % pid
    self._Inc()

  def PushMessage(self, label, argv):
    # type: (str, Optional[List[str]]) -> None
    """For synchronous constructs that aren't processes."""
    buf = self._RichTraceBegin('>')
    if buf:
      buf.write(label)
      if label == 'proc':
        _PrintArgv(argv, buf)
      elif label == 'source':
        _PrintArgv(argv[1:], buf)
      elif label == 'wait':
        _PrintArgv(argv[1:], buf)
      else:
        buf.write('\n')
      self.f.write(buf.getvalue())

    self._Inc()

  def PopMessage(self, label, arg):
    # type: (str, Optional[str]) -> None
    """For synchronous constructs that aren't processes."""
    self._Dec()

    buf = self._RichTraceBegin('<')
    if buf:
      buf.write(label)
      if arg is not None:
        buf.write(' ')
        buf.write(qsn.maybe_encode(arg))
      buf.write('\n')
      self.f.write(buf.getvalue())

  def PrintMessage(self, message):
    # type: (str) -> None
    """Used when receiving signals."""
    buf = self._RichTraceBegin('!')
    if not buf:
      return

    buf.write(message)
    buf.write('\n')
    self.f.write(buf.getvalue())

  def OnExec(self, argv):
    # type: (List[str]) -> None
    buf = self._RichTraceBegin('.')
    if not buf:
      return
    buf.write('exec')
    _PrintArgv(argv, buf)
    self.f.write(buf.getvalue())

  def OnBuiltin(self, builtin_id, argv):
    # type: (builtin_t, List[str]) -> None
    if builtin_id in (builtin_i.eval, builtin_i.source, builtin_i.wait):
      return  # These 3 builtins handled separately

    buf = self._RichTraceBegin('.')
    if not buf:
      return
    buf.write('builtin')
    _PrintArgv(argv, buf)
    self.f.write(buf.getvalue())

  #
  # Shell Tracing That Begins with _ShTraceBegin
  #

  def OnSimpleCommand(self, argv):
    # type: (List[str]) -> None
    """For legacy set -x.

    Called before we know if it's a builtin, external, or proc.
    """
    buf = self._ShTraceBegin()
    if not buf:
      return

    # Redundant with OnProcessStart (external), PushMessage (proc), and OnBuiltin
    if self.exec_opts.xtrace_rich():
      return

    # Legacy: Use SHELL encoding
    for i, arg in enumerate(argv):
      if i != 0:
        buf.write(' ')
      buf.write(qsn.maybe_shell_encode(arg))
    buf.write('\n')
    self.f.write(buf.getvalue())

  def OnAssignBuiltin(self, cmd_val):
    # type: (cmd_value__Assign) -> None
    buf = self._ShTraceBegin()
    if not buf:
      return

    for i, arg in enumerate(cmd_val.argv):
      if i != 0:
        buf.write(' ')
      buf.write(arg)

    for pair in cmd_val.pairs:
      buf.write(' ')
      buf.write(pair.var_name)
      buf.write('=')
      if pair.rval:
        _PrintShValue(pair.rval, buf)

    buf.write('\n')
    self.f.write(buf.getvalue())

  def OnShAssignment(self, lval, op, val, flags, which_scopes):
    # type: (lvalue_t, assign_op_t, value_t, int, scope_t) -> None
    buf = self._ShTraceBegin()
    if not buf:
      return

    left = '?'
    UP_lval = lval
    with tagswitch(lval) as case:
      if case(lvalue_e.Named):
        lval = cast(lvalue__Named, UP_lval)
        left = lval.name
      elif case(lvalue_e.Indexed):
        lval = cast(lvalue__Indexed, UP_lval)
        left = '%s[%d]' % (lval.name, lval.index)
      elif case(lvalue_e.Keyed):
        lval = cast(lvalue__Keyed, UP_lval)
        left = '%s[%s]' % (lval.name, qsn.maybe_shell_encode(lval.key))
    buf.write(left)

    # Only two possibilities here
    buf.write('+=' if op == assign_op_e.PlusEqual else '=')

    _PrintShValue(val, buf)

    buf.write('\n')
    self.f.write(buf.getvalue())

  def OnControlFlow(self, keyword, arg):
    # type: (str, int) -> None

    # This is NOT affected by xtrace_rich or xtrace_details.  Works in both.
    if not self.exec_opts.xtrace():
      return

    prefix = self._EvalPS4('+')
    buf = mylib.BufWriter()
    buf.write(prefix)

    buf.write(keyword)
    buf.write(' ')
    buf.write(str(arg))  # Note: 'return' is equivalent to 'return 0'
    buf.write('\n')

    self.f.write(buf.getvalue())

  def PrintSourceCode(self, left_spid, right_spid, arena):
    # type: (int, int, alloc.Arena) -> None
    """
    For (( )) and [[ ]].  Bash traces these.
    """
    buf = self._ShTraceBegin()
    if not buf:
      return

    left_span = arena.GetToken(left_spid)
    right_span = arena.GetToken(right_spid)
    line = arena.GetLine(left_span.line_id)
    start = left_span.col

    if left_span.line_id == right_span.line_id:
      end = right_span.col  # This is one spid PAST the end.
      buf.write(line[start:end])
    else:
      # Print first line only
      line = arena.GetLine(left_span.line_id)
      end = -1 if line.endswith('\n') else len(line)
      buf.write(line[start:end])
      buf.write(' ...')

    buf.write('\n')
    self.f.write(buf.getvalue())
