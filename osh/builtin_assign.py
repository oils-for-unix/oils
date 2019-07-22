#!/usr/bin/env python2
"""
builtin_assign.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import (
    value_e, lvalue, scope_e, var_flags_e, builtin_e
)
#from core.util import log
from frontend import args
from frontend import match
from osh.builtin import _Register


EXPORT_SPEC = _Register('export')
EXPORT_SPEC.ShortFlag('-n')


class Export(object):
  def __init__(self, mem, errfmt):
    self.mem = mem
    self.errfmt = errfmt

  def __call__(self, cmd_val):
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()
    arg, arg_index = EXPORT_SPEC.Parse(arg_r)

    positional = cmd_val.argv[arg_index:]
    if arg.n:
      for pair in cmd_val.pairs:
        if pair.rval is not None:
          raise args.UsageError("doesn't accept RHS with -n", span_id=pair.spid)

        # NOTE: bash doesn't care if it wasn't found.
        self.mem.ClearFlag(pair.lval.name, var_flags_e.Exported, scope_e.Dynamic)
    else:
      for pair in cmd_val.pairs:
        # NOTE: when rval is None, only flags are changed
        self.mem.SetVar(
            pair.lval, pair.rval, (var_flags_e.Exported,), scope_e.Dynamic)

    return 0


READONLY_SPEC = _Register('readonly')

# TODO: Check the consistency of -a and -A against values, here and below.
READONLY_SPEC.ShortFlag('-a')
READONLY_SPEC.ShortFlag('-A')


class Readonly(object):
  def __init__(self, mem):
    self.mem = mem

  def __call__(self, cmd_val):
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()
    arg, arg_index = READONLY_SPEC.Parse(arg_r)

    for pair in cmd_val.pairs:
      flags = (var_flags_e.ReadOnly,)
      # NOTE: when rval is None, only flags are changed
      self.mem.SetVar(pair.lval, pair.rval, flags, scope_e.GlobalOnly)

    return 0


NEW_VAR_SPEC = _Register('declare')

# print stuff
NEW_VAR_SPEC.ShortFlag('-f')
NEW_VAR_SPEC.ShortFlag('-F')
NEW_VAR_SPEC.ShortFlag('-p')

NEW_VAR_SPEC.ShortFlag('-x')  # export
NEW_VAR_SPEC.ShortFlag('-r')  # readonly
NEW_VAR_SPEC.ShortFlag('-g')  # global

# Common between readonly/declare
NEW_VAR_SPEC.ShortFlag('-a')
NEW_VAR_SPEC.ShortFlag('-A')


class NewVar(object):
  """declare/typeset/local."""

  def __init__(self, mem, funcs):
    self.mem = mem
    self.funcs = funcs

  def __call__(self, cmd_val):
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()
    arg, arg_index = NEW_VAR_SPEC.Parse(arg_r)

    status = 0

    # NOTE: in bash, -f shows the function body, while -F shows the name.  In
    # osh, they're identical and behave like -F.
    if arg.f or arg.F:  # Lookup and print functions.
      names = [pair.lval.name for pair in cmd_val.pairs]
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
      return status

    if arg.p:  # Lookup and print variables.
      names = [pair.lval.name for pair in cmd_val.pairs]
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
      return status

    #
    # Set variables
    #

    #raise args.UsageError("doesn't understand %s" % cmd_val.argv[1:])
    if cmd_val.builtin_id == builtin_e.LOCAL:
      lookup_mode = scope_e.LocalOnly
    else:  # declare/typeset
      if arg.g:  
        lookup_mode = scope_e.GlobalOnly
      else:
        lookup_mode = scope_e.LocalOnly

    flags = []
    if arg.x:
      flags.append(var_flags_e.Exported)
    if arg.r:
      flags.append(var_flags_e.ReadOnly)
    if arg.A:
      flags.append(var_flags_e.AssocArray)
    if arg.g:  # e.g. 'declare -Ag'
      flags.append(var_flags_e.Global)

    for pair in cmd_val.pairs:
      self.mem.SetVar(pair.lval, pair.rval, tuple(flags), lookup_mode)

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
