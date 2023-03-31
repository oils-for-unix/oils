from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import (
    value, scope_e, cmd_value__Argv
)
from _devbuild.gen.syntax_asdl import loc
from core import error
from core.pyerror import e_usage
from core import state
from core import vm
from frontend import flag_spec
from frontend import args
from frontend import location
from frontend import match
from frontend import typed_args

import sys
import yajl
import posix_ as posix

from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from core.ui import ErrorFormatter
  from oil_lang import expr_eval

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
    # type: (state.Mem, expr_eval.OilEvaluator, ErrorFormatter) -> None
    self.mem = mem
    self.expr_ev = expr_ev
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'json'

    action, action_spid = arg_r.Peek2()
    if action is None:
      raise error.Usage(_JSON_ACTION_ERROR)
    arg_r.Next()

    if action == 'write':
      attrs = flag_spec.Parse('json_write', arg_r)
      arg_jw = arg_types.json_write(attrs.attrs)


      if not arg_r.AtEnd():
        e_usage('write got too many args', span_id=arg_r.SpanId())

      expr = typed_args.RequiredExpr(cmd_val.typed_args)
      obj = self.expr_ev.EvalExpr(expr)

      if arg_jw.pretty:
        indent = arg_jw.indent
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
      attrs = flag_spec.Parse('json_read', arg_r)
      arg_jr = arg_types.json_read(attrs.attrs)
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
        self.errfmt.Print_('json read: %s' % e, blame_loc=loc.Span(action_spid))
        return 1

      # TODO: use token directly
      self.mem.SetValue(
          location.LName(var_name), value.Obj(obj), scope_e.LocalOnly)

    else:
      raise error.Usage(_JSON_ACTION_ERROR, span_id=action_spid)

    return 0
