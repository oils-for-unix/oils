#!/usr/bin/env python2
"""
builtin_assign.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import (
    value, value_e, lvalue, scope_e, var_flags_e
)
from frontend import args
from frontend import match
from osh.builtin import _Register


EXPORT_SPEC = _Register('export')
EXPORT_SPEC.ShortFlag('-n')


class Export(object):
  def __init__(self, mem):
    self.mem = mem

  def __call__(self, arg_vec):
    arg, arg_index = EXPORT_SPEC.ParseVec(arg_vec)
    positional = arg_vec.strs[arg_index:]
    if arg.n:
      for name in positional:
        if not match.IsValidVarName(name):
          # TODO: span_id=
          raise args.UsageError('export: Invalid variable name %r' % name)

        # NOTE: bash doesn't care if it wasn't found.
        self.mem.ClearFlag(name, var_flags_e.Exported, scope_e.Dynamic)
    else:
      for arg in positional:
        parts = arg.split('=', 1)
        if len(parts) == 1:
          name = parts[0]
          val = None  # Creates an empty variable
        else:
          name, s = parts
          val = value.Str(s)

        if not match.IsValidVarName(name):
          # TODO: span_id=
          raise args.UsageError('export: Invalid variable name %r' % name)

        #log('%s %s', name, val)
        self.mem.SetVar(
            lvalue.Named(name), val, (var_flags_e.Exported,), scope_e.Dynamic)

    return 0


DECLARE_SPEC = _Register('declare')
DECLARE_SPEC.ShortFlag('-f')
DECLARE_SPEC.ShortFlag('-F')
DECLARE_SPEC.ShortFlag('-p')


class DeclareTypeset(object):
  def __init__(self, mem, funcs):
    self.mem = mem
    self.funcs = funcs

  def __call__(self, arg_vec):
    arg, arg_index = DECLARE_SPEC.ParseVec(arg_vec)
    names = arg_vec.strs[arg_index:]

    status = 0

    # NOTE: in bash, -f shows the function body, while -F shows the name.  In
    # osh, they're identical and behave like -F.

    if arg.f or arg.F:  # Lookup and print functions.
      if names:
        for name in names:
          if name in self.funcs:
            print(name)
            # TODO: Could print LST, or render LST.  Bash does this.  'trap' too.
            #print(funcs[name])
          else:
            status = 1
      elif arg.F:
        for func_name in sorted(self.funcs):
          print('declare -f %s' % (func_name))
      else:
        raise args.UsageError('declare/typeset -f without args')

    elif arg.p:  # Lookup and print variables.
      if names:
        for name in names:
          val = self.mem.GetVar(name)
          if val.tag != value_e.Undef:
            # TODO: Print flags.

            print(name)
          else:
            status = 1
      else:
        raise args.UsageError('declare/typeset -p without args')

    else:
      raise args.UsageError("doesn't understand %s" % arg_vec.strs[1:])

    return status


UNSET_SPEC = _Register('unset')
UNSET_SPEC.ShortFlag('-v')
UNSET_SPEC.ShortFlag('-f')


# TODO:
# - Parse lvalue expression: unset 'a[ i - 1 ]'.  Static or dynamic parsing?
# - It would make more sense to treat no args as an error (bash doesn't.)
#   - Should we have strict builtins?  Or just make it stricter?

class Unset(object):
  def __init__(self, mem, funcs, errfmt):
    self.mem = mem
    self.funcs = funcs
    self.errfmt = errfmt

  def _UnsetVar(self, name, spid):
    if not match.IsValidVarName(name):
      raise args.UsageError(
          'got invalid variable name %r' % name, span_id=spid)

    ok, found = self.mem.Unset(lvalue.Named(name), scope_e.Dynamic)
    if not ok:
      self.errfmt.Print("Can't unset readonly variable %r", name,
                        span_id=spid)
    return ok, found

  def __call__(self, arg_vec):
    arg, offset = UNSET_SPEC.ParseVec(arg_vec)
    n = len(arg_vec.strs)

    for i in xrange(offset, n):
      name = arg_vec.strs[i]
      spid = arg_vec.spids[i]

      if arg.f:
        if name in self.funcs:
          del self.funcs[name]
      elif arg.v:
        ok, _ = self._UnsetVar(name, spid)
        if not ok:
          return 1
      else:
        # Try to delete var first, then func.
        ok, found = self._UnsetVar(name, spid)
        if not ok:
          return 1

        #log('%s: %s', name, found)
        if not found:
          if name in self.funcs:
            del self.funcs[name]

    return 0


class Shift(object):
  def __init__(self, mem):
    self.mem = mem

  def __call__(self, arg_vec):
    num_args = len(arg_vec.strs) - 1
    if num_args == 0:
      n = 1
    elif num_args == 1:
      arg = arg_vec.strs[1]
      try:
        n = int(arg)
      except ValueError:
        raise args.UsageError("Invalid shift argument %r" % arg)
    else:
      raise args.UsageError('got too many arguments')

    return self.mem.Shift(n)
