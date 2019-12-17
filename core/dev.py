"""
dev.py - Devtools / introspection.
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value_e
from _devbuild.gen.syntax_asdl import assign_op_e

from asdl import runtime
from asdl import pretty
from core import error
from core.util import log
from osh import word_
from pylib import os_path

import posix_ as posix

from typing import List, Dict, Any, TYPE_CHECKING
if TYPE_CHECKING:
  from core.error import _ErrorWithLocation
  from _devbuild.gen.syntax_asdl import assign_op_t
  from _devbuild.gen.runtime_asdl import lvalue_t, value_t, scope_t
  #from osh.cmd_exec import Executor


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
  Executor
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

  def MaybeCollect(self, ex, err):
    # type: (Any, _ErrorWithLocation) -> None
    # TODO: Any -> Executor
    """
    Args:
      ex: Executor instance
      error: _ErrorWithLocation (ParseError or FatalRuntimeError)
    """
    if not self.do_collect:  # Either we already did it, or there is no file
      return

    self.var_stack, self.argv_stack, self.debug_stack = ex.mem.Dump()
    span_id = word_.SpanIdFromError(err)

    self.error = {
       'msg': err.UserErrorString(),
       'span_id': span_id,
    }

    if span_id != runtime.NO_SPID:
      span = ex.arena.GetLineSpan(span_id)
      line_id = span.line_id

      # Could also do msg % args separately, but JavaScript won't be able to
      # render that.
      self.error['source'] = ex.arena.GetLineSourceString(line_id)
      self.error['line_num'] = ex.arena.GetLineNumber(line_id)
      self.error['line'] = ex.arena.GetLine(line_id)

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

  Bare minimum to debug problems:
    - argv and span ID of the SimpleCommand that corresponds to that
    - then print line number using arena
    - set -x doesn't print line numbers!  OH but you can do that with
      PS4=$LINENO
  """
  def __init__(self, parse_ctx, exec_opts, mem, word_ev, f):
    """
    Args:
      parse_ctx: For parsing PS4.
      exec_opts: For xtrace setting
      mem: for retrieving PS4
      word_ev: for evaluating PS4
    """
    self.parse_ctx = parse_ctx
    self.exec_opts = exec_opts
    self.mem = mem
    self.word_ev = word_ev
    self.f = f  # can be the --debug-file as well

    self.parse_cache = {}  # PS4 value -> compound_word.  PS4 is scoped.

  def _EvalPS4(self):
    """For set -x."""

    val = self.mem.GetVar('PS4')
    assert val.tag == value_e.Str

    s = val.s
    if s:
      first_char, ps4 = s[0], s[1:]
    else:
      first_char, ps4 = '+', ' '  # default

    # NOTE: This cache is slightly broken because aliases are mutable!  I think
    # that is more or less harmless though.
    try:
      ps4_word = self.parse_cache[ps4]
    except KeyError:
      # We have to parse this at runtime.  PS4 should usually remain constant.
      w_parser = self.parse_ctx.MakeWordParserForPlugin(ps4)

      try:
        ps4_word = w_parser.ReadForPlugin()
      except error.Parse as e:
        ps4_word = word_.ErrorWord("<ERROR: Can't parse PS4: %s>", e)
      self.parse_cache[ps4] = ps4_word

    #print(ps4_word)

    # TODO: Repeat first character according process stack depth.  Where is
    # that stored?  In the executor itself?  It should be stored along with
    # the PID.  Need some kind of ShellProcessState or something.
    #
    # We should come up with a better mechanism.  Something like $PROC_INDENT
    # and $OIL_XTRACE_PREFIX.

    # Prevent infinite loop when PS4 has command sub!
    assert self.exec_opts.xtrace  # We shouldn't call this unless it's on!
    self.exec_opts.xtrace = False
    try:
      prefix = self.word_ev.EvalForPlugin(ps4_word)
    finally:
      self.exec_opts.xtrace = True
    return first_char, prefix.s

  def OnSimpleCommand(self, argv):
    # type: (List[str]) -> None
    # NOTE: I think tracing should be on by default?  For post-mortem viewing.
    if not self.exec_opts.xtrace:
      return

    first_char, prefix = self._EvalPS4()
    cmd = ' '.join(pretty.String(a) for a in argv)
    self.f.log('%s%s%s', first_char, prefix, cmd)

  def OnShAssignment(self, lval, op, val, flags, lookup_mode):
    # type: (lvalue_t, assign_op_t, value_t, Any, scope_t) -> None
    # NOTE: I think tracing should be on by default?  For post-mortem viewing.
    if not self.exec_opts.xtrace:
      return

    first_char, prefix = self._EvalPS4()
    op_str = {assign_op_e.Equal: '=', assign_op_e.PlusEqual: '+='}[op]
    self.f.log('%s%s%s %s %s', first_char, prefix, lval, op_str, val)

  def Event(self):
    """
    Other events:

    - Function call events.  As opposed to external commands.
    - Process Forks.  Subshell, command sub, pipeline,
    - Command Completion -- you get the status code.
    - ShAssignments
      - We should desugar to SetVar like mksh
    """
    pass
