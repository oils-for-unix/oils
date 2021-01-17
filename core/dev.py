"""
dev.py - Devtools / introspection.
"""
from __future__ import print_function

from _devbuild.gen.option_asdl import option_i, builtin_i, builtin_t
from _devbuild.gen.runtime_asdl import (
    value_e, value__Str, value__MaybeStrArray, value__AssocArray,
    lvalue_e, lvalue__Named, lvalue__Indexed, lvalue__Keyed,
    cmd_value__Assign, trace_e, trace_t, trace_msg
)
from _devbuild.gen.syntax_asdl import assign_op_e

from asdl import runtime
from core import error
from core import optview
from core import state
from qsn_ import qsn
from core.pyerror import log
from osh import word_
from pylib import os_path
from mycpp import mylib
from mycpp.mylib import switch, tagswitch, iteritems

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
  #from osh.cmd_eval import CommandEvaluator


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

  def MaybeCollect(self, cmd_ev, err):
    # type: (Any, _ErrorWithLocation) -> None
    # TODO: Any -> CommandEvaluator
    """
    Args:
      cmd_ev: CommandEvaluator instance
      error: _ErrorWithLocation (ParseError or FatalRuntimeError)
    """
    if not self.do_collect:  # Either we already did it, or there is no file
      return

    if mylib.PYTHON:  # can't translate yet due to dynamic typing
      self.var_stack, self.argv_stack, self.debug_stack = cmd_ev.mem.Dump()
      span_id = word_.SpanIdFromError(err)

      self.error = {
         'msg': err.UserErrorString(),
         'span_id': span_id,
      }

      if span_id != runtime.NO_SPID:
        span = cmd_ev.arena.GetLineSpan(span_id)
        line_id = span.line_id

        # Could also do msg % args separately, but JavaScript won't be able to
        # render that.
        self.error['source'] = cmd_ev.arena.GetLineSourceString(line_id)
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
      with open(path, 'w') as f:
        import json
        json.dump(d, f, indent=2)
        #print(repr(d), file=f)
      log('[%d] Wrote crash dump to %s', my_pid, path)


class ctx_Tracer(object):
  """A stack for tracing synchronous constructs."""

  def __init__(self, tracer, what, argv):
    # type: (Tracer, trace_t, Optional[List[str]]) -> None
    with switch(what) as case:
      if case(trace_e.Proc):
        label = 'proc'
      elif case(trace_e.Eval):
        label = 'eval'
      elif case(trace_e.Source):
        label = 'source'
      elif case(trace_e.Pipeline):
        label = 'pipeline'
      else:
        raise AssertionError()

    tracer.PushMessage(label, argv)
    self.tracer = tracer
    self.label = label

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.tracer.PopMessage(self.label)


def _PrintValue(val, buf):
  # type: (value_t, mylib.BufWriter) -> None

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
  for i, arg in enumerate(argv):
    if i != 0:
      buf.write(' ')
    buf.write(qsn.maybe_shell_encode(arg))
  buf.write('\n')


class Tracer(object):
  """For shell's set -x, and Oil's hierarchical, parsable tracing.

  Default prefix is

  PS4='${X_indent}${X_punct}${X_pid} '

  X_punct is:

      + for a builtin
      > and < for proc calls, eval, and source (synchronous, stack-based)
        - for synchronous processes: subshell, semicolon
      | and . to begin and end a process (async), command sub
        - async processes: fork, elements of a pipeline, process sub

  Oil PID 1234: main.sh foo bar (try https://xtrace.oilshell.org/)
  + builtin cd /
  > proc foo
    > 1235 ls .
    < 1235 ls (status 0)
  < proc foo
  > 1236 subshell
    > 1236 proc bar
      > 1237 ls /nonexistent
      < 1237 ls (status 1)
    < 1236 proc bar
    + 1236 builtin cd /
  < 1236 subshell (status 0)
  > pipeline
    | PID 1234
    | PID 1235
    . PID 1235 (status 0)
    . PID 1234 (status 1)
  < pipeline (pipestatus now available)
  Oil exited (status 0)

  The first and last line are special.  We don't want to include the same PID
  on EVERY line.
  I guess the PID should appear on EVERY line?

  - TODO: Connect it somehow to tracers for other processes.  So you can make
    an HTML report offline.

  https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html#Bash-Variables

  Other hooks:

  - Command completion starts other processes
  - Oil stuff
    - BareDecl, VarDecl, PlaceMutation, Expr
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

    self.pid = -1  # PID to print as prefix

    # PS4 value -> compound_word.  PS4 is scoped.
    self.parse_cache = {}  # type: Dict[str, compound_word]

  def CheckCircularDeps(self):
    # type: () -> None
    assert self.word_ev is not None

  def _EvalPS4(self):
    # type: () -> str
    """The prefix of each line.

    TODO: XTRACE_PREFIX (or OIL_XTRACE_PREFIX) could be the same except for the
    "first char" behavior, which is replaced with indentation.

    BASH_XTRACEFD exists.
    """
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

    #print(ps4_word)

    # TODO: Repeat first character according process stack depth.  Where is
    # that stored?  In the executor itself?  It should be stored along with
    # the PID.  Need some kind of ShellProcessState or something.
    #
    # We should come up with a better mechanism.  Something like $PROC_INDENT
    # and $OIL_XTRACE_PREFIX.

    # Prevent infinite loop when PS4 has command sub!
    assert self.exec_opts.xtrace()  # We shouldn't call this unless it's on!
    with state.ctx_Option(self.mutable_opts, [option_i.xtrace], False):
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

    # TODO: Using a member variable and then clear() would probably save
    # pressure.  Tracing is in the inner loop.
    prefix = self._EvalPS4()

    buf = mylib.BufWriter()
    if self.exec_opts.xtrace_rich():
      buf.write(self.indents[self.ind])

    # Note: bash repeats the + for command sub, eval, source.  Other shells
    # don't do it.  Leave this out for now.
    buf.write(prefix)

    if self.pid != -1:
      buf.write(str(self.pid))
      buf.write(' ')

    return buf

  def _OilTraceBegin(self, ch):
    # type: (str) -> Optional[mylib.BufWriter]
    """For the stack printed by xtrace_rich"""
    if not self.exec_opts.xtrace() or not self.exec_opts.xtrace_rich():
      return None

    # TODO: change to _EvalPS4
    buf = mylib.BufWriter()
    buf.write(self.indents[self.ind])
    buf.write(ch)
    buf.write(' ')
    if self.pid != -1:
      buf.write(str(self.pid))
      buf.write(' ')
    return buf

  def _RichTraceBegin(self):
    # type: () -> Optional[mylib.BufWriter]
    """For the stack printed by xtrace_rich"""
    if not self.exec_opts.xtrace() or not self.exec_opts.xtrace_rich():
      return None

    # TODO: change to _EvalPS4
    buf = mylib.BufWriter()
    buf.write(self.indents[self.ind])
    return buf

  def _PrintPrefix(self, ch, label, buf):
    # type: (str, str, mylib.BufWriter) -> None
    buf.write(ch)
    buf.write(' ')
    if self.pid != -1:
      buf.write(str(self.pid))
      buf.write(' ')
    buf.write(label)

  def OnProcessStart(self, pid, msg):
    # type: (int, trace_msg) -> None
    """
    TODO:

    | for async (& and pipeline)
    > for synchronous (command sub, subshell and external)

    Also we need a description:
      pipeline, & fork, subshell, command.Simple with argv
    """
    buf = self._RichTraceBegin()
    if not buf:
      return

    with switch(msg.what) as case:
      # Synchronous cases
      if case(trace_e.External):
        self._PrintPrefix('>', 'command %d:' % pid, buf)
        if msg.argv is not None:
          buf.write(' ')
          _PrintArgv(msg.argv, buf)
      elif case(trace_e.Subshell):
        self._PrintPrefix('>', 'forkwait %d\n' % pid, buf)
        self._Inc()
      elif case(trace_e.CommandSub):
        self._PrintPrefix('>', 'command sub %d\n' % pid, buf)
        self._Inc()

      # Async cases
      # elif case(trace_e.PipelinePart):
      #   buf.write('part\n') 
      # elif case(trace_e.Fork):
      #   buf.write('&fork\n') 
      # elif case(trace_e.ProcessSub):
      #   buf.write('process sub\n') 
      # elif case(trace_e.HereDoc):
      #   buf.write('here doc\n') 

      else:
        self._PrintPrefix('|', 'process %d\n' % pid, buf)

    self.f.write(buf.getvalue())

  def OnProcessEnd(self, pid, status, msg):
    # type: (int, int, trace_msg) -> None
    ch = '<'
    with switch(msg.what) as case:
      if case(trace_e.External):
        label = 'command'
      elif case(trace_e.Subshell):
        label = 'forkwait'
        self._Dec()
      elif case(trace_e.CommandSub):
        label = 'command sub'
        self._Dec()
      elif case(trace_e.JobWait):  # async
        label = 'wait'
      else:
        label = 'process'
        ch = '.'

    buf = self._RichTraceBegin()
    if not buf:
      return

    self._PrintPrefix(ch, '%s %d: status %d\n' % (label, pid, status), buf)
    self.f.write(buf.getvalue())

  def SetProcess(self, pid):
    # type: (int) -> None
    """
    All trace lines have a PID prefix, except those from the root process.
    """
    self.pid = pid
    self._Inc()

  def PushMessage(self, label, argv):
    # type: (str, Optional[List[str]]) -> None
    """For synchronous constructs that aren't processes."""
    buf = self._RichTraceBegin()
    if buf:
      self._PrintPrefix('[', label, buf)
      if label == 'proc':
        buf.write(' ')
        _PrintArgv(argv, buf)
      elif label ==  'source':
        buf.write(' ')
        _PrintArgv(argv[1:], buf)
      else:
        buf.write('\n')
      self.f.write(buf.getvalue())

    self._Inc()

  def PopMessage(self, label):
    # type: (str) -> None
    """For synchronous constructs that aren't processes."""
    self.ind -= 1

    #log('pop')
    buf = self._RichTraceBegin()
    if buf:
      self._PrintPrefix(']', label, buf)
      buf.write('\n')
      self.f.write(buf.getvalue())

  def OnBuiltin(self, builtin_id, argv):
    # type: (builtin_t, List[str]) -> None
    if builtin_id in (builtin_i.eval, builtin_i.source):
      # Handled separately
      return

    buf = self._OilTraceBegin('+')
    if not buf:
      return

    buf.write('builtin ')
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

    tmp = [qsn.maybe_shell_encode(a) for a in argv]
    buf.write(' '.join(tmp))
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
        _PrintValue(pair.rval, buf)

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

    _PrintValue(val, buf)

    buf.write('\n')
    self.f.write(buf.getvalue())

  def OnControlFlow(self, keyword, arg):
    # type: (str, int) -> None

    # TODO: Include this in Oil tracing too?  It's always on?

    buf = self._ShTraceBegin()
    if not buf:
      return

    buf.write(keyword)
    if arg != 0:
      buf.write(' ')
      buf.write(str(arg))

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

    left_span = arena.GetLineSpan(left_spid)
    right_span = arena.GetLineSpan(right_spid)
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
