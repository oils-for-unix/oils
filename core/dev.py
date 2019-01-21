#!/usr/bin/python
"""
dev.py - Devtools / introspection.
"""
from __future__ import print_function

from asdl import const
from core import util
from osh import word
from pylib import os_path

def SpanIdFromError(error):
  #print(parse_error)
  if error.span_id != const.NO_INTEGER:
    return error.span_id
  if error.token:
    return error.token.span_id
  if error.part:
    return word.LeftMostSpanForPart(error.part)
  if error.word:
    return word.LeftMostSpanForWord(error.word)

  return const.NO_INTEGER


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
    self.crash_dump_dir = crash_dump_dir
    # whether we should collect a dump, at the highest level of the stack
    self.do_collect = bool(crash_dump_dir)
    self.collected = False  # whether we have anything to dump

    self.var_stack = None
    self.argv_stack = None
    self.debug_stack = None
    self.error = None

  def MaybeCollect(self, ex, error):
    """
    Args:
      ex: Executor instance
      error: _ErrorWithLocation (ParseError or FatalRuntimeError)
    """
    if not self.do_collect:  # Either we already did it, or there is no file
      return

    self.var_stack, self.argv_stack, self.debug_stack = ex.mem.Dump()
    span_id = SpanIdFromError(error)

    self.error = {
       'msg': error.UserErrorString(),
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

    # Other things we need: the reason for the crash!  _ErrorWithLocation is
    # required I think.
    d = {
        'var_stack': self.var_stack,
        'argv_stack': self.argv_stack,
        'debug_stack': self.debug_stack,
        'error': self.error,
        'status': status,
    }

    # TODO: Add PID here
    path = os_path.join(self.crash_dump_dir, 'osh-crash-dump.json')
    with open(path, 'w') as f:
      import json
      json.dump(d, f, indent=2)
      #print(repr(d), file=f)
    util.log('Wrote crash dump to %s', path)
