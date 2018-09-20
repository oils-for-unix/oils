#!/usr/bin/python
from __future__ import print_function
"""
dev.py - Devtools / introspection.
"""

import os
from core import state
from core import util

# TODO: Move Tracer here.


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
  """
  def __init__(self, crash_dump_dir):
    self.crash_dump_dir = crash_dump_dir
    # whether we should collect a dump, at the highest level of the stack
    self.do_collect = bool(crash_dump_dir)
    self.collected = False  # whether we have anything to dump

    self.var_stack = []
    self.argv_stack = []
    self.debug_stack = []

    # Things to dump:
    # Executor
    #   functions, aliases, traps, completion hooks
    #   dir_stack -- minor thing
    #
    # state.Mem()
    #  _ArgFrame
    #  _StackFrame
    # func names
    #
    # debug info for the source?  Or does that come elsewhere?
    #
    # Yeah I think you sould have two separate files.
    # - debug info for a given piece of code (needs hash)
    #   - this could just be the raw source files?  Does it need anything else?
    #   - I think it needs a hash so the VM dump can refer to it.
    # - vm dump.
    # - Combine those and you get a UI.
    #
    # One is constant at build time; the other is constant at runtime.

  def MaybeCollect(self, ex):
    if not self.do_collect:  # Either we already did it, or there is no file
      return

    # Copy stack
    self.var_stack, self.argv_stack, self.debug_stack = ex.mem.Dump()

    # TODO: Also do functions, aliases, etc.

    self.do_collect = False
    self.collected = True

  def AddFrame(self):
    frame = {}
    self.stack.append(frame)
    return frame

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

    d = {
        'var_stack': self.var_stack,
        'argv_stack': self.argv_stack,
        'debug_stack': self.debug_stack,
    }
    path = os.path.join(self.crash_dump_dir, 'osh-crash-dump.json')
    with open(path, 'w') as f:
      import json
      json.dump(d, f, indent=2)
      #print(repr(d), file=f)
    util.log('Wrote crash dump to %s', path)
