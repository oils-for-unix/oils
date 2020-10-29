#!/usr/bin/env python2
"""
builtin_oil.py - Oil builtins.

See rfc/0024-oil-builtins.md for notes.

env: Should be in builtin_compat.py?

It's sort of like xargs too.
"""
from __future__ import print_function

import sys

from _devbuild.gen.runtime_asdl import value, value_e, scope_e
from _devbuild.gen.syntax_asdl import (
    sh_lhs_expr, command_e, command__ShFunction
)
from core import error
from core.pyerror import log, e_usage
from core import vm
from frontend import flag_spec
from frontend import args
from frontend import match
from mycpp.mylib import tagswitch
from qsn_ import qsn

import yajl
import posix_ as posix

from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
  from core.alloc import Arena
  from core.ui import ErrorFormatter
  from core.state import Mem
  from osh.cmd_eval import CommandEvaluator


class _Builtin(vm._Builtin):
  def __init__(self, mem, errfmt):
    # type: (Mem, ErrorFormatter) -> None
    self.mem = mem
    self.errfmt = errfmt


class Pp(_Builtin):
  """Given a list of variable names, print their values.

  'repr a' is a lot easier to type than 'argv.py "${a[@]}"'.
  """
  def __init__(self, mem, errfmt, procs, arena):
    # type: (Mem, ErrorFormatter, Dict[str, command__ShFunction], Arena) -> None
    self.mem = mem
    self.errfmt = errfmt
    self.procs = procs
    self.arena = arena

  def Run(self, cmd_val):
    arg, arg_r = flag_spec.ParseOilCmdVal('repr', cmd_val)

    action, action_spid = arg_r.ReadRequired2(
        'expected an action (proc, .cell, etc.)')

    # Actions that print unstable formats start with '.'
    if action == '.cell':
      argv, spids = arg_r.Rest2()

      status = 0
      for i, name in enumerate(argv):
        if name.startswith(':'):
          name = name[1:]

        if not match.IsValidVarName(name):
          raise error.Usage('got invalid variable name %r' % name,
                            span_id=spids[i])

        cell = self.mem.GetCell(name)
        if cell is None:
          self.errfmt.Print("Couldn't find a variable named %r" % name,
                            span_id=spids[i])
          status = 1
        else:
          sys.stdout.write('%s = ' % name)
          cell.PrettyPrint()  # may be color
          sys.stdout.write('\n')

    elif action == 'proc':
      names, spids = arg_r.Rest2()
      if len(names):
        for i, name in enumerate(names):
          node = self.procs.get(name)
          if node is None:
            self.errfmt.Print_('Invalid proc %r' % name, span_id=spids[i])
            return 1
      else:
        names = sorted(self.procs)

      # QTSV header
      print('proc_name\tdoc_comment')
      for name in names:
        node = self.procs[name]  # must exist
        body = node.body

        # TODO: not just command__ShFunction, but command__Proc!
        doc = ''
        if body.tag_() == command_e.BraceGroup:
          if body.doc_token:
            span_id = body.doc_token.span_id
            span = self.arena.GetLineSpan(span_id)
            line = self.arena.GetLine(span.line_id)
            # 1 to remove leading space
            doc = line[span.col+1 : span.col + span.length]

        # No limits on proc names
        print('%s\t%s' % (qsn.maybe_encode(name), qsn.maybe_encode(doc)))

      status = 0

    else:
      e_usage('got invalid action %r' % action, span_id=action_spid)

    return status


class Push(_Builtin):
  """Push args onto an array.

  Note: this could also be in builtins_pure.py?
  """
  def Run(self, cmd_val):
    arg, arg_r = flag_spec.ParseOilCmdVal('push', cmd_val)

    var_name, var_spid = arg_r.ReadRequired2(
        'requires a variable name')

    if var_name.startswith(':'):  # optional : sigil
      var_name = var_name[1:]

    if not match.IsValidVarName(var_name):
      raise error.Usage('got invalid variable name %r' % var_name,
                            span_id=var_spid)

    val = self.mem.GetVar(var_name)
    # TODO: value.Obj too
    if val.tag != value_e.MaybeStrArray:
      self.errfmt.Print("%r isn't an array", var_name, span_id=var_spid)
      return 1

    val.strs.extend(arg_r.Rest())
    return 0


class Use(_Builtin):
  """use lib, bin, env.  Respects namespaces.

  use lib foo.sh {  # "punning" on block syntax.  1 or 3 words.
    func1
    func2 as myalias
  }
  """
  def Run(self, cmd_val):
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
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


class Env(_Builtin):
  """env {} blocks are preferred over 'export'.

  Should be compatible with POSIX, but also take a block.
  """
  pass


class Opts(_Builtin):
  """getopts replacement.

  opts :grep_opts {
    flag -v --invert Bool "Invert"
    flag -A --after Int "Lines after"
    flag -t --timeout Float "Seconds to wait" { default = 1.0 }

    # / pattern file* /
    arg 1 pattern "Regular expression"
    arg 2- file "Regular expression"
  }
  var opt = grep_opts.Parse(ARGV)
  opt.invert
  opt.after
  opt.pattern
  opt.file
  """
  def Run(self, cmd_val):
    raise NotImplementedError()


JSON_WRITE_SPEC = flag_spec.OilFlags('json-write', typed=True)
JSON_WRITE_SPEC.Flag('-pretty', args.Bool, default=True,
                     help='Whitespace in output (default true)')
JSON_WRITE_SPEC.Flag('-indent', args.Int, default=2,
                     help='Indent JSON by this amount')

JSON_READ_SPEC = flag_spec.OilFlags('json-read', typed=True)
# yajl has this option
JSON_READ_SPEC.Flag('-validate', args.Bool, default=True,
                     help='Validate UTF-8')

_JSON_ACTION_ERROR = "builtin expects 'read' or 'write'"

# global file object that can be passed to yajl.load(), and that also can be
# used with redirects.  See comment below.
_STDIN = posix.fdopen(0)


class Json(vm._Builtin):
  """Json I/O.

  -indent pretty prints it.  Is the default indent 2?  -pretty=0 can turn it
  off.

  json echo :myobj

  json echo -indent 2 :myobj :other_obj {
    x = 1
    d = {name: 'andy'}
  }

  json read :x < foo.tsv2

  How about:
      json echo &myobj 
  Well that will get confused with a redirect.
  """
  def __init__(self, mem, cmd_ev, errfmt):
    # type: (Mem, CommandEvaluator, ErrorFormatter) -> None
    self.mem = mem
    self.cmd_ev = cmd_ev
    self.errfmt = errfmt

  def Run(self, cmd_val):
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'json'

    action, action_spid = arg_r.Peek2()
    if action is None:
      raise error.Usage(_JSON_ACTION_ERROR)
    arg_r.Next()

    if action == 'write':
      arg = JSON_WRITE_SPEC.Parse(arg_r)

      # GetVar() of each name and print it.

      for var_name in arg_r.Rest():
        if var_name.startswith(':'):
          var_name = var_name[1:]

        val = self.mem.GetVar(var_name)
        with tagswitch(val) as case:
          if case(value_e.Undef):
            # TODO: blame the right span_id
            self.errfmt.Print("no variable named %r is defined", var_name)
            return 1
          elif case(value_e.Str):
            obj = val.s
          elif case(value_e.MaybeStrArray):
            obj = val.strs
          elif case(value_e.AssocArray):
            obj = val.d
          elif case(value_e.Obj):
            obj = val.obj
          else:
            raise AssertionError(val)

        if arg.pretty:
          indent = arg.indent 
          extra_newline = False
        else:
          # How yajl works: if indent is -1, then everything is on one line.
          indent = -1
          extra_newline = True

        j = yajl.dump(obj, sys.stdout, indent=indent)
        if extra_newline:
          sys.stdout.write('\n')

      # TODO: Accept a block.  They aren't hooked up yet.
      if cmd_val.block:
        # TODO: flatten value.{Str,Obj} into a flat dict?
        namespace = self.cmd_ev.EvalBlock(cmd_val.block)

        print(yajl.dump(namespace))

    elif action == 'read':
      arg = JSON_READ_SPEC.Parse(arg_r)
      # TODO:
      # Respect -validate=F

      var_name, name_spid = arg_r.ReadRequired2("expected variable name")
      if var_name.startswith(':'):
        var_name = var_name[1:]

      if not match.IsValidVarName(var_name):
        raise error.Usage('got invalid variable name %r' % var_name,
                              span_id=name_spid)

      try:
        # Use a global _STDIN, because we get EBADF on a redirect if we use a
        # local.  A Py_DECREF closes the file, which we don't want, because the
        # redirect is responsible for freeing it.
        #
        # https://github.com/oilshell/oil/issues/675
        #
        # TODO: write a better binding like yajl.readfd()
        #
        # It should use streaming like here:
        # https://lloyd.github.io/yajl/

        obj = yajl.load(_STDIN)
      except ValueError as e:
        self.errfmt.Print('json read: %s', e, span_id=action_spid)
        return 1

      self.mem.SetVar(
          sh_lhs_expr.Name(var_name), value.Obj(obj), scope_e.LocalOnly)

    else:
      raise error.Usage(_JSON_ACTION_ERROR, span_id=action_spid)

    return 0


# TODO: Put this in flag_def.py
WRITE_SPEC = flag_spec.OilFlags('write')
WRITE_SPEC.Flag('-sep', args.String, default='\n',
                help='Characters to separate each argument')
WRITE_SPEC.Flag('-end', args.String, default='\n',
                help='Characters to terminate the whole invocation')
WRITE_SPEC.Flag('-n', args.Bool, default=False,
                help="Omit newline (synonym for -end '')")
WRITE_SPEC.Flag('-qsn', args.Bool, default=False,
                help='Write elements in QSN format')

# x means I want \x00
# u means I want \u{1234}
# raw is utf-8
# might also want: maybe?
WRITE_SPEC.Flag('-unicode', ['raw', 'u', 'x',], default='raw',
                help='Encode QSN with these options.  '
                     'x assumes an opaque byte string, while raw and u try to '
                     'decode UTF-8.')


class Write(_Builtin):
  """
  write -- @strs
  write --sep ' ' --end '' -- @strs
  write -n -- @
  write --qsn -- @strs   # argv serialization
  write --qsn --sep $'\t' -- @strs   # this is like QTSV
  """
  def Run(self, cmd_val):
    arg, arg_r = flag_spec.ParseOilCmdVal('write', cmd_val)
    #print(arg)

    if arg.unicode == 'raw':
      bit8_display = qsn.BIT8_UTF8
    elif arg.unicode == 'u':
      bit8_display = qsn.BIT8_U_ESCAPE
    elif arg.unicode == 'x':
      bit8_display = qsn.BIT8_X_ESCAPE
    else:
      raise AssertionError()

    i = 0
    while not arg_r.AtEnd():
      if i != 0:
        sys.stdout.write(arg.sep)
      s = arg_r.Peek()

      if arg.qsn:
        s = qsn.maybe_encode(s, bit8_display)

      sys.stdout.write(s)

      arg_r.Next()
      i += 1

    if arg.n:
      pass
    elif arg.end:
      sys.stdout.write(arg.end)

    return 0


class Qtsv(_Builtin):
  """QTSV I/O.

  # Takes a block.
  tsv2 echo :var1 :var2 {
    # Does this make sense?
    x = %(a b c)
    age = [1, 2, 3]
  }

  tsv2 read :x < foo.tsv2
  """
  pass
