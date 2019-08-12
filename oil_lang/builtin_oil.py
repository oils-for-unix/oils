#!/usr/bin/env python2
"""
builtin_oil.py - Oil builtins.

See rfc/0024-oil-builtins.md for notes.

env: Should be in builtin_compat.py?

It's sort of like xargs too.
"""
from __future__ import print_function

import sys

from _devbuild.gen.runtime_asdl import value_e

from core.util import log
from frontend import args


# TODO: Enable it when oil-echo-builtin is enabled?  Because echo -n will be
# gone?
#
# or honestly echo -- @words might be ok?
#
# Change it to be consistent?  I think we don't want to have this one
# exception.

def Write(arg_vec):
  # TODO: this take cmd_value.Argv
  if len(arg_vec) != 2:
    raise args.UsageError('expects exactly 1 argument')
  sys.stdout.write(arg_vec.strs[1])
  return 0


class Push(object):
  """Push args onto an array.

  Note: this could also be in builtins_pure.py?
  """
  def __init__(self, mem, errfmt):
    self.mem = mem
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    arg_r = args.Reader(arg_vec.strs, spids=arg_vec.spids)
    arg_r.Next()  # skip 'push'

    var_name, var_spid = arg_r.ReadRequired2(
        'requires a variable name')

    val = self.mem.GetVar(var_name)
    # TODO: value.Obj too
    if val.tag != value_e.MaybeStrArray:
      self.errfmt.Print("%r isn't an array", var_name, span_id=var_spid)
      return 1

    underscore, u_spid = arg_r.ReadRequired2(
        'requires the _ separator')

    if underscore != '_':
      raise args.UsageError('requires the _ separator', span_id=u_spid)

    val.strs.extend(arg_r.Rest())
    return 0


class Use(object):
  """use lib, bin, env.  Respects namespaces."""

  def __init__(self, mem, errfmt):
    self.mem = mem
    self.errfmt = errfmt

  # TODO: It takes a block too
  def __call__(self, arg_vec):
    arg_r = args.Reader(arg_vec.strs, spids=arg_vec.spids)
    arg_r.Next()  # skip 'use'

    # TODO:
    # - Does shopt -s namespaces have to be on?
    #   - I don't think so?  It only affects 'procs', not funcs.

    arg = arg_r.Peek()

    # 'use bin' and 'use env' are for static analysis.  No-ops at runtime.
    if arg in ('bin', 'env'):
      return 0

    if arg == 'lib':  # OPTIONAL lib
      arg_r.Next()

    # Cosmetic: separator for 'use bin __ grep sed'.  Allowed for 'lib' to be
    # consistent.
    arg = arg_r.Peek()
    if arg == '__':  # OPTIONAL __
      arg_r.Next()

    # Now import everything.
    rest = arg_r.Rest()
    for path in rest:
      log('path %s', path)

    return 0


class Env(object):
  """env {} blocks are preferred over 'export'."""
  pass


class Fork(object):
  """Replaces &.  Takes a block.

  Similar to Wait, which is in osh/builtin_process.py.
  """
  pass
