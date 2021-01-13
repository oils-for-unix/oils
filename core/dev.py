"""
dev.py - Devtools / introspection.
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import (
    value_e, value__Str, value__MaybeStrArray, value__AssocArray,
    lvalue_e, lvalue__Named, lvalue__Indexed, lvalue__Keyed,
    cmd_value__Assign
)
from _devbuild.gen.syntax_asdl import assign_op_e

from asdl import runtime
from core import error
from core import optview
from qsn_ import qsn
from core.pyerror import log
from osh import word_
from pylib import os_path
from mycpp import mylib
from mycpp.mylib import tagswitch, iteritems

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

      # TODO: Add PID here
      path = os_path.join(self.crash_dump_dir, '%d-osh-crash-dump.json' % my_pid)
      with open(path, 'w') as f:
        import json
        json.dump(d, f, indent=2)
        #print(repr(d), file=f)
      log('[%d] Wrote crash dump to %s', my_pid, path)


class Tracer(object):
  """A tracer for this process.

  TODO: Connect it somehow to tracers for other processes.  So you can make an
  HTML report offline.

  https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html#Bash-Variables

  Other hooks:

  - Proc calls.  As opposed to external commands.
  - Process Forks.  Subshell, command sub, pipeline,
    - yeah bash doesn't have this, but we should have it
    - for subshells, pipelines and so forth
  - Command Completion -- you get the status code?
  - Oil stuff
    - BareDecl, VarDecl, PlaceMutation, Expr,

  Idea:
    shopt --set process_trace   is orthogonal to xtrace?
    It should show > < and details about external command vs. function
  """
  def __init__(self,
               parse_ctx,  # type: ParseContext
               exec_opts,  # type: optview.Exec
               mutable_opts,  # type: MutableOpts
               mem,  # type: Mem
               word_ev,  # type: NormalWordEvaluator
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
    self.word_ev = word_ev
    self.f = f  # can be stderr, the --debug-file, etc.

    self.X_indent = ''  # changed by process, proc, source, eval
    self.pid_stack = []  # type: List[int]

    # PS4 value -> compound_word.  PS4 is scoped.
    self.parse_cache = {}  # type: Dict[str, compound_word]

  def _EvalPS4(self):
    # type: () -> str
    """The prefix of each line.

    TODO: XTRACE_PREFIX (or OIL_XTRACE_PREFIX) could be the same except for the
    "first char" behavior, which is replaced with indentation.

    BASH_XTRACEFD exists.
    """
    # Change this to be the default?  Users can change it to '+ ' I guess?
    ps4 = '${X_indent}${X_punct}${X_tag} '

    ps4 = '+ '  # default
    val = self.mem.GetValue('PS4')
    if val.tag_() == value_e.Str:
      ps4 = cast(value__Str, val).s

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
    self.mutable_opts.set_xtrace(False)
    try:
      prefix = self.word_ev.EvalForPlugin(ps4_word)
    finally:
      self.mutable_opts.set_xtrace(True)
    return prefix.s

  def PushPid(self, pid):
    # type: (int) -> None
    """Print > and the description."""
    self.pid_stack.append(pid)

  def PopPid(self):
    # type: () -> None
    """Print < and the description."""
    self.pid_stack.pop()

  def _TraceBegin(self):
    # type: () -> Optional[mylib.BufWriter]
    if not self.exec_opts.xtrace():
      return None

    # TODO: Using a member variable and then clear() would probably save
    # pressure.  Tracing is in the inner loop.
    self.buf = mylib.BufWriter()
    prefix = self._EvalPS4()

    buf = mylib.BufWriter()

    # Note: bash repeats the + for command sub, eval, source.  Other shells
    # don't do it.  Leave this out for now.
    buf.write(prefix)
    return buf

  def _Value(self, val, buf):
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

  def OnSimpleCommand(self, argv):
    # type: (List[str]) -> None
    buf = self._TraceBegin()
    if not buf:
      return

    tmp = [qsn.maybe_shell_encode(a) for a in argv]
    buf.write(' '.join(tmp))
    buf.write('\n')
    self.f.write(buf.getvalue())

  def OnAssignBuiltin(self, cmd_val):
    # type: (cmd_value__Assign) -> None
    buf = self._TraceBegin()
    if not buf:
      return

    for arg in cmd_val.argv:
      buf.write(arg)
      buf.write(' ')

    for pair in cmd_val.pairs:
      buf.write(pair.var_name)
      buf.write('=')
      if pair.rval:
        self._Value(pair.rval, buf)
        buf.write(' ')

    buf.write('\n')
    self.f.write(buf.getvalue())

  def OnShAssignment(self, lval, op, val, flags, which_scopes):
    # type: (lvalue_t, assign_op_t, value_t, int, scope_t) -> None
    buf = self._TraceBegin()
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
    op_str = '+=' if op == assign_op_e.PlusEqual else '='
    buf.write(op_str)

    self._Value(val, buf)

    buf.write('\n')
    self.f.write(buf.getvalue())

  def OnControlFlow(self, keyword, arg):
    # type: (str, int) -> None
    buf = self._TraceBegin()
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
    buf = self._TraceBegin()
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
