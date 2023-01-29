#!/usr/bin/env python2
"""
builtin_oil.py - Oil builtins.

See rfc/0024-oil-builtins.md for notes.

env: Should be in builtin_compat.py?

It's sort of like xargs too.
"""
from __future__ import print_function

import sys

from _devbuild.gen.runtime_asdl import (
    value, value_e, scope_e, Proc, cmd_value__Assign
)
from _devbuild.gen.syntax_asdl import (
    sh_lhs_expr, command_e, BraceGroup, 
)
from core import error
from core.pyerror import log, e_usage
from core import state
from core import vm
from frontend import flag_spec
from frontend import args
from frontend import match
from frontend import typed_args
from mycpp.mylib import tagswitch
from qsn_ import qsn

import yajl
import posix_ as posix

from typing import Dict, TYPE_CHECKING, cast
if TYPE_CHECKING:
  from core.alloc import Arena
  from core.ui import ErrorFormatter
  from oil_lang import expr_eval

_ = log


class _Builtin(vm._Builtin):
  def __init__(self, mem, errfmt):
    # type: (state.Mem, ErrorFormatter) -> None
    self.mem = mem
    self.errfmt = errfmt


class Pp(_Builtin):
  """Given a list of variable names, print their values.

  'pp cell a' is a lot easier to type than 'argv.py "${a[@]}"'.
  """
  def __init__(self, mem, errfmt, procs, arena):
    # type: (state.Mem, ErrorFormatter, Dict[str, Proc], Arena) -> None
    self.mem = mem
    self.errfmt = errfmt
    self.procs = procs
    self.arena = arena

  def Run(self, cmd_val):
    # type: (cmd_value__Assign) -> int
    arg, arg_r = flag_spec.ParseCmdVal('pp', cmd_val)

    action, action_spid = arg_r.ReadRequired2(
        'expected an action (proc, cell, etc.)')

    # Actions that print unstable formats start with '.'
    if action == 'cell':
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
          self.errfmt.Print_("Couldn't find a variable named %r" % name,
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
        proc = self.procs[name]  # must exist
        #log('Proc %s', proc)
        body = proc.body

        # TODO: not just command__ShFunction, but command__Proc!
        doc = ''
        if body.tag_() == command_e.BraceGroup:
          bgroup = cast(BraceGroup, body)
          if bgroup.doc_token:
            span_id = bgroup.doc_token.span_id
            span = self.arena.GetToken(span_id)
            line = self.arena.GetLine(span.line_id)
            # 1 to remove leading space
            doc = line[span.col+1 : span.col + span.length]

        # No limits on proc names
        print('%s\t%s' % (qsn.maybe_encode(name), qsn.maybe_encode(doc)))

      status = 0

    else:
      e_usage('got invalid action %r' % action, span_id=action_spid)

    return status


class Append(_Builtin):
  """Push args onto an array.

  Note: this could also be in builtins_pure.py?
  """
  def Run(self, cmd_val):
    # type: (cmd_value__Assign) -> int
    arg, arg_r = flag_spec.ParseCmdVal('append', cmd_val)

    var_name, var_spid = arg_r.ReadRequired2(
        'requires a variable name')

    if var_name.startswith(':'):  # optional : sigil
      var_name = var_name[1:]

    if not match.IsValidVarName(var_name):
      raise error.Usage('got invalid variable name %r' % var_name,
                            span_id=var_spid)

    val = self.mem.GetValue(var_name)

    # TODO: Get rid of the value.MaybeStrArray and value.Obj distinction!
    ok = False
    with tagswitch(val) as case:
      if case(value_e.MaybeStrArray):
        val.strs.extend(arg_r.Rest())
        ok = True
      if case(value_e.Obj):
        if isinstance(val.obj, list):
          val.obj.extend(arg_r.Rest())
          ok = True
    if not ok:
      self.errfmt.Print_("%r isn't an array" % var_name, span_id=var_spid)
      return 1

    return 0


class ArgParse(_Builtin):
  """getopts replacement.

  argparse :grep_opts {
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
    # type: (cmd_value__Assign) -> int
    return 0


class Describe(_Builtin):
  """Builtin test frameowrk.

  TODO: Can this be user code?

  It would test out Oil blocks well.
  """
  def Run(self, cmd_val):
    # type: (cmd_value__Assign) -> int
    return 0


JSON_WRITE_SPEC = flag_spec.FlagSpec('json-write')
JSON_WRITE_SPEC.LongFlag(
    '--pretty', args.Bool, default=True,
    help='Whitespace in output (default true)')
JSON_WRITE_SPEC.LongFlag(
    '--indent', args.Int, default=2,
    help='Indent JSON by this amount')

JSON_READ_SPEC = flag_spec.FlagSpec('json-read')
# yajl has this option
JSON_READ_SPEC.LongFlag(
    '--validate', args.Bool, default=True,
    help='Validate UTF-8')

_JSON_ACTION_ERROR = "builtin expects 'read' or 'write'"

# global file object that can be passed to yajl.load(), and that also can be
# used with redirects.  See comment below.
_STDIN = posix.fdopen(0)


class Json(vm._Builtin):
  """JSON read and write

    --pretty=0 writes it on a single line
    --indent=2 controls multiline indentation
  """
  def __init__(self, mem, expr_ev, errfmt):
    # type: (state.Mem, expr_eval.ExprEvaluator, ErrorFormatter) -> None
    self.mem = mem
    self.expr_ev = expr_ev
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Assign) -> int
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'json'

    action, action_spid = arg_r.Peek2()
    if action is None:
      raise error.Usage(_JSON_ACTION_ERROR)
    arg_r.Next()

    if action == 'write':
      arg = args.Parse(JSON_WRITE_SPEC, arg_r)

      if not arg_r.AtEnd():
        e_usage('write got too many args', span_id=arg_r.SpanId())

      expr = typed_args.RequiredExpr(cmd_val.typed_args)
      obj = self.expr_ev.EvalExpr(expr)

      if arg.pretty:
        indent = arg.indent 
        extra_newline = False
      else:
        # How yajl works: if indent is -1, then everything is on one line.
        indent = -1
        extra_newline = True

      j = yajl.dumps(obj, indent=indent)
      sys.stdout.write(j)
      if extra_newline:
        sys.stdout.write('\n')

    elif action == 'read':
      arg = args.Parse(JSON_READ_SPEC, arg_r)
      # TODO:
      # Respect -validate=F

      var_name, name_spid = arg_r.ReadRequired2("expected variable name")
      if var_name.startswith(':'):
        var_name = var_name[1:]

      if not arg_r.AtEnd():
        e_usage('read got too many args', span_id=arg_r.SpanId())

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
        self.errfmt.Print_('json read: %s' % e, span_id=action_spid)
        return 1

      # TODO: use token directly
      left = self.errfmt.arena.GetToken(name_spid)
      self.mem.SetValue(
          sh_lhs_expr.Name(left, var_name), value.Obj(obj), scope_e.LocalOnly)

    else:
      raise error.Usage(_JSON_ACTION_ERROR, span_id=action_spid)

    return 0


class Write(_Builtin):
  """
  write -- @strs
  write --sep ' ' --end '' -- @strs
  write -n -- @
  write --qsn -- @strs   # argv serialization
  write --qsn --sep $'\t' -- @strs   # this is like QTSV
  """
  def Run(self, cmd_val):
    # type: (cmd_value__Assign) -> int
    arg, arg_r = flag_spec.ParseCmdVal('write', cmd_val)
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


class Qtt(_Builtin):
  """QTT I/O.

  cat foo.qtt | qtt read-rows {
    # first reads schema line, and the processes
    # process _row
  }
  qtt write-row (mydict)

  # Cut down a file and read it into memory as a dict
  cat foo.qtt | select %(name age) | qtt read :filtered

  # Literal by column
  # I guess it has to detect the types
  qtt write ({name: %(foo bar), age: [10, 20]})

  # Literal by row.  Will throw a syntax error.
  # Good for unit tests and so forth.
  qtt tabify :x <<< '''
  name  age:Int
  bob   20 
  carol 30
  '''


  """
  pass
