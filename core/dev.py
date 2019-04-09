#!/usr/bin/python
"""
dev.py - Devtools / introspection.
"""
from __future__ import print_function

import posix

from asdl import const
from core.util import log
from osh import word
from pylib import os_path

from typing import Dict, Any, TYPE_CHECKING
if TYPE_CHECKING:
  from core.util import _ErrorWithLocation
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
    span_id = word.SpanIdFromError(err)

    self.error = {
       'msg': err.UserErrorString(),
       'span_id': span_id,
    }

    if span_id != const.NO_INTEGER:
      span = ex.arena.GetLineSpan(span_id)
      path, line_num = ex.arena.GetDebugInfo(span.line_id)
      line = ex.arena.GetLine(span.line_id)

      # Could also do msg % args separately, but JavaScript won't be able to
      # render that.
      self.error['path'] = path
      self.error['line_num'] = line_num
      self.error['line'] = line

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
