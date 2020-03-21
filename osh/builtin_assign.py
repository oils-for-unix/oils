#!/usr/bin/env python2
"""
builtin_assign.py
"""
from __future__ import print_function

from _devbuild.gen.option_asdl import builtin_i
from _devbuild.gen.runtime_asdl import (
    value, value_e, value_t, value__Str, value__MaybeStrArray, value__AssocArray,
    lvalue, scope_e,
    cmd_value__Argv, cmd_value__Assign,
)
#from core.util import log
from frontend import args
from frontend import match
from core import state
from mycpp import mylib
from osh import string_ops

from typing import cast, Dict, Tuple, Any, TYPE_CHECKING
if TYPE_CHECKING:
  from core.state import Mem
  from core.ui import ErrorFormatter

if mylib.PYTHON:
  from frontend import arg_def


def _PrintVariables(mem, cmd_val, arg, print_flags, readonly=False, exported=False):
  # type: (Mem, value_t, Any, bool, bool, bool) -> int
  flag_g = getattr(arg, 'g', None)
  flag_n = getattr(arg, 'n', None)
  flag_r = getattr(arg, 'r', None)
  flag_x = getattr(arg, 'x', None)
  flag_a = getattr(arg, 'a', None)
  flag_A = getattr(arg, 'A', None)

  lookup_mode = scope_e.Dynamic
  if cmd_val.builtin_id == builtin_i.local:
    if flag_g and not mem.IsGlobalScope():
      return 1
    lookup_mode = scope_e.LocalOnly
  elif flag_g:
    lookup_mode = scope_e.GlobalOnly

  if len(cmd_val.pairs) == 0:
    print_all = True
    cells = mem.GetAllCells(lookup_mode)
    names = sorted(cells)
  else:
    print_all = False
    names = []
    cells = {}
    for pair in cmd_val.pairs:
      name = pair.lval.name
      if pair.rval and pair.rval.tag_() == value_e.Str:
        name += "=" + cast(value__Str, pair.rval).s
        names.append(name)
        cells[name] = None
      else:
        names.append(name)
        cells[name] = mem.GetCell(name, lookup_mode)

  count = 0
  for name in names:
    cell = cells[name]
    if cell is None: continue
    val = cell.val

    if val.tag_() == value_e.Undef: continue
    if readonly and not cell.readonly: continue
    if exported and not cell.exported: continue
    if flag_n == '-' and not cell.nameref: continue
    if flag_n == '+' and cell.nameref: continue
    if flag_r == '-' and not cell.readonly: continue
    if flag_r == '+' and cell.readonly: continue
    if flag_x == '-' and not cell.exported: continue
    if flag_x == '+' and cell.exported: continue
    if flag_a and val.tag_() != value_e.MaybeStrArray: continue
    if flag_A and val.tag_() != value_e.AssocArray: continue

    if print_flags:
      flags = '-'
      if cell.nameref: flags += 'n'
      if cell.readonly: flags += 'r'
      if cell.exported: flags += 'x'
      if val.tag_() == value_e.MaybeStrArray:
        flags += 'a'
      elif val.tag_() == value_e.AssocArray:
        flags += 'A'
      if flags == '-': flags += '-'

      decl = 'declare ' + flags + ' ' + name
    else:
      decl = name

    if val.tag_() == value_e.Str:
      str_val = cast(value__Str, val)
      decl += "=" + string_ops.ShellQuote(str_val.s)
    elif val.tag_() == value_e.MaybeStrArray:
      array_val = cast(value__MaybeStrArray, val)
      if None in array_val.strs:
        # Note: Arrays with unset elements are printed in the form:
        #   declare -p arr=(); arr[3]='' arr[4]='foo' ...
        decl += "=()"
        first = True
        for i, element in enumerate(array_val.strs):
          if element is not None:
            if first:
              decl += ";"
              first = False
            decl += " " + name + "[" + str(i) + "]=" + string_ops.ShellQuote(element)
      else:
        body = ''
        for element in array_val.strs:
          if body: body += ' '
          body += string_ops.ShellQuote(element or '')
        decl += "=(" + body + ")"
    elif val.tag_() == value_e.AssocArray:
      assoc_val = cast(value__AssocArray, val)
      body = ''
      for key in sorted(assoc_val.d):
        if body: body += ' '
        key_quoted = string_ops.ShellQuote(key)
        value_quoted = string_ops.ShellQuote(assoc_val.d[key] or '')
        body += "[" + key_quoted + "]=" + value_quoted
      if body:
        decl += "=(" + body + ")"

    print(decl)
    count += 1

  if print_all or count == len(names):
    return 0
  else:
    return 1


if mylib.PYTHON:
  EXPORT_SPEC = arg_def.Register('export')
  EXPORT_SPEC.ShortFlag('-n')
  EXPORT_SPEC.ShortFlag('-f')  # stubbed
  EXPORT_SPEC.ShortFlag('-p')
  # Instead of Reader?  Or just make everything take a reader/
  # They should check for extra args?
  #spec.AcceptsCmdVal()

  # Later, use it like:
  #
  # from _devbuild.gen import arg_parse
  #
  # arg = arg_parse.export_cmdval(cmd_val)?
  # arg = arg_parse.echo(arg_r)
  # arg = arg_parse.bin_oil(arg_r)?
  #
  # So from arg_def you generate arg_parse.


class Export(object):
  def __init__(self, mem, errfmt):
    # type: (Mem, ErrorFormatter) -> None
    self.mem = mem
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Assign) -> int
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()
    arg, arg_index = EXPORT_SPEC.Parse(arg_r)

    if arg.f:
      raise args.UsageError(
          "doesn't accept -f because it's dangerous.  (The code can usually be restructured with 'source')")

    if arg.p or len(cmd_val.pairs) == 0:
      return _PrintVariables(self.mem, cmd_val, arg, True, exported=True)

    positional = cmd_val.argv[arg_index:]
    if arg.n:
      for pair in cmd_val.pairs:
        if pair.rval is not None:
          raise args.UsageError("doesn't accept RHS with -n", span_id=pair.spid)

        # NOTE: we don't care if it wasn't found, like bash.
        self.mem.ClearFlag(pair.lval.name, state.ClearExport, scope_e.Dynamic)
    else:
      for pair in cmd_val.pairs:
        # NOTE: when rval is None, only flags are changed
        self.mem.SetVar(pair.lval, pair.rval, scope_e.Dynamic,
                        flags=state.SetExport)

    return 0


def _ReconcileTypes(rval, arg, span_id):
  # type: (value_t, Any, int) -> value_t
  """Check that -a and -A flags are consistent with RHS.

  Special case: () is allowed to mean empty indexed array or empty assoc array
  if the context is clear.

  Shared between NewVar and Readonly.
  """
  if arg.a and rval and rval.tag_() != value_e.MaybeStrArray:
    raise args.UsageError(
        "Got -a but RHS isn't an array", span_id=span_id)

  if arg.A and rval:
    # Special case: declare -A A=() is OK.  The () is changed to mean an empty
    # associative array.
    if rval.tag_() == value_e.MaybeStrArray:
      array_val = cast(value__MaybeStrArray, rval)
      if len(array_val.strs) == 0:
        return value.AssocArray({})
        #return value.MaybeStrArray([])

    if rval.tag_() != value_e.AssocArray:
      raise args.UsageError(
          "Got -A but RHS isn't an associative array", span_id=span_id)

  return rval


if mylib.PYTHON:
  READONLY_SPEC = arg_def.Register('readonly')

# TODO: Check the consistency of -a and -A against values, here and below.
  READONLY_SPEC.ShortFlag('-a')
  READONLY_SPEC.ShortFlag('-A')
  READONLY_SPEC.ShortFlag('-p')


class Readonly(object):
  def __init__(self, mem, errfmt):
    # type: (Mem, ErrorFormatter) -> None
    self.mem = mem
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Assign) -> int
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()
    arg, arg_index = READONLY_SPEC.Parse(arg_r)

    if arg.p or len(cmd_val.pairs) == 0:
      return _PrintVariables(self.mem, cmd_val, arg, True, readonly=True)

    for pair in cmd_val.pairs:
      if pair.rval is None:
        if arg.a:
          rval = value.MaybeStrArray([])  # type: value_t
        elif arg.A:
          rval = value.AssocArray({})
        else:
          rval = None
      else:
        rval = pair.rval

      rval = _ReconcileTypes(rval, arg, pair.spid)

      # NOTE:
      # - when rval is None, only flags are changed
      # - dynamic scope because flags on locals can be changed, etc.
      self.mem.SetVar(pair.lval, rval, scope_e.Dynamic,
                      flags=state.SetReadOnly)

    return 0


if mylib.PYTHON:
  NEW_VAR_SPEC = arg_def.Register('declare')

  # print stuff
  NEW_VAR_SPEC.ShortFlag('-f')
  NEW_VAR_SPEC.ShortFlag('-F')
  NEW_VAR_SPEC.ShortFlag('-p')

  NEW_VAR_SPEC.ShortFlag('-g')  # Look up in global scope

  # Options +r +x +n
  NEW_VAR_SPEC.ShortOption('x')  # export
  NEW_VAR_SPEC.ShortOption('r')  # readonly
  NEW_VAR_SPEC.ShortOption('n')  # named ref

  # Common between readonly/declare
  NEW_VAR_SPEC.ShortFlag('-a')
  NEW_VAR_SPEC.ShortFlag('-A')



class NewVar(object):
  """declare/typeset/local."""

  def __init__(self, mem, funcs, errfmt):
    # type: (Mem, Dict[str, Any], ErrorFormatter) -> None
    self.mem = mem
    self.funcs = funcs
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Assign) -> int
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
      return _PrintVariables(self.mem, cmd_val, arg, True)
    elif len(cmd_val.pairs) == 0:
      return _PrintVariables(self.mem, cmd_val, arg, False)

    #
    # Set variables
    #

    #raise args.UsageError("doesn't understand %s" % cmd_val.argv[1:])
    if cmd_val.builtin_id == builtin_i.local:
      lookup_mode = scope_e.LocalOnly
    else:  # declare/typeset
      if arg.g:  
        lookup_mode = scope_e.GlobalOnly
      else:
        lookup_mode = scope_e.LocalOnly

    flags = 0
    if arg.x == '-': 
      flags |= state.SetExport
    if arg.r == '-':
      flags |= state.SetReadOnly
    if arg.n == '-':
      flags |= state.SetNameref

    flags_to_clear = 0
    if arg.x == '+': 
      flags |= state.ClearExport
    if arg.r == '+':
      flags |= state.ClearReadOnly
    if arg.n == '+':
      flags |= state.ClearNameref

    for pair in cmd_val.pairs:
      if pair.rval is None:
        if arg.a:
          rval = value.MaybeStrArray([])  # type: value_t
        elif arg.A:
          rval = value.AssocArray({})
        else:
          rval = None
      else:
        rval = pair.rval

      rval = _ReconcileTypes(rval, arg, pair.spid)
      self.mem.SetVar(pair.lval, rval, lookup_mode, flags=flags)

    return status


if mylib.PYTHON:
  UNSET_SPEC = arg_def.Register('unset')
  UNSET_SPEC.ShortFlag('-v')
  UNSET_SPEC.ShortFlag('-f')


# TODO:
# - Parse lvalue expression: unset 'a[ i - 1 ]'.  Static or dynamic parsing?
# - It would make more sense to treat no args as an error (bash doesn't.)
#   - Should we have strict builtins?  Or just make it stricter?

class Unset(object):
  def __init__(self, mem, funcs, errfmt):
    # type: (Mem, Dict[str, Any], ErrorFormatter) -> None
    self.mem = mem
    self.funcs = funcs
    self.errfmt = errfmt

  def _UnsetVar(self, name, spid):
    # type: (str, int) -> Tuple[bool, bool]
    if not match.IsValidVarName(name):
      raise args.UsageError(
          'got invalid variable name %r' % name, span_id=spid)

    ok, found = self.mem.Unset(lvalue.Named(name), scope_e.Dynamic)
    if not ok:
      self.errfmt.Print("Can't unset readonly variable %r", name,
                        span_id=spid)
    return ok, found

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    arg, offset = UNSET_SPEC.ParseCmdVal(cmd_val)
    n = len(cmd_val.argv)

    for i in xrange(offset, n):
      name = cmd_val.argv[i]
      spid = cmd_val.arg_spids[i]

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
    # type: (Mem) -> None
    self.mem = mem

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    num_args = len(cmd_val.argv) - 1
    if num_args == 0:
      n = 1
    elif num_args == 1:
      arg = cmd_val.argv[1]
      try:
        n = int(arg)
      except ValueError:
        raise args.UsageError("Invalid shift argument %r" % arg)
    else:
      raise args.UsageError('got too many arguments')

    return self.mem.Shift(n)
