from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import scope_e, cmd_value
from _devbuild.gen.syntax_asdl import loc
from core import error
from core.error import e_usage
from core import pyos
from core import state
from core import vm
from data_lang import j8
from frontend import flag_spec
from frontend import args
from frontend import location
from frontend import match
from frontend import typed_args
from mycpp import mylib
from osh import builtin_misc
from ysh import cpython

import sys
import yajl
import posix_ as posix

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.ui import ErrorFormatter
    from ysh import expr_eval

_JSON_ACTION_ERROR = "builtin expects 'read' or 'write'"


class Json(vm._Builtin):
    """JSON read and write.

    --pretty=0 writes it on a single line
    --indent=2 controls multiline indentation
    """

    def __init__(self, mem, expr_ev, errfmt, is_j8):
        # type: (state.Mem, expr_eval.ExprEvaluator, ErrorFormatter, bool) -> None
        self.mem = mem
        self.expr_ev = expr_ev
        self.errfmt = errfmt
        if is_j8:
            self.printer = j8.Printer(0)
        else:
            # TODO: restrict to JSON with some flags
            self.printer = j8.Printer(0)

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
        arg_r.Next()  # skip 'json'

        action, action_loc = arg_r.Peek2()
        if action is None:
            raise error.Usage(_JSON_ACTION_ERROR, loc.Missing)
        arg_r.Next()

        if action == 'write':
            # NOTE slightly different flags
            # json write --surrogate-ok $'\udc00'
            # not valid for j8 write
            attrs = flag_spec.Parse('json_write', arg_r)

            arg_jw = arg_types.json_write(attrs.attrs)

            if not arg_r.AtEnd():
                e_usage('write got too many args', arg_r.Location())

            expr = typed_args.RequiredExpr(cmd_val.typed_args)
            val = self.expr_ev.EvalExpr(expr, loc.Missing)

            if arg_jw.pretty:
                indent = arg_jw.indent
                extra_newline = False
            else:
                # How yajl works: if indent is -1, then everything is on one line.
                indent = -1
                extra_newline = True

            if 0:
                buf = mylib.BufWriter()
                self.printer.Print(val, buf, indent=indent)
                sys.stdout.write(buf.getvalue())
                sys.stdout.write('\n')
            else:

                obj = cpython._ValueToPyObj(val)

                j = yajl.dumps(obj, indent=indent)
                sys.stdout.write(j)
                if extra_newline:
                    sys.stdout.write('\n')

        elif action == 'read':
            attrs = flag_spec.Parse('json_read', arg_r)
            arg_jr = arg_types.json_read(attrs.attrs)
            # TODO:
            # Respect -validate=F

            var_name, name_loc = arg_r.ReadRequired2("expected variable name")
            if var_name.startswith(':'):
                var_name = var_name[1:]

            if not arg_r.AtEnd():
                e_usage('read got too many args', arg_r.Location())

            if not match.IsValidVarName(var_name):
                raise error.Usage('got invalid variable name %r' % var_name,
                                  name_loc)

            try:
                contents = builtin_misc.ReadAll()
            except pyos.ReadError as e:  # different paths for read -d, etc.
                # don't quote code since YSH errexit will likely quote
                self.errfmt.PrintMessage("read error: %s" %
                                         posix.strerror(e.err_num))
                return 1

            if mylib.PYTHON:
                try:
                    obj = yajl.loads(contents)
                except ValueError as e:
                    self.errfmt.Print_('json read: %s' % e, blame_loc=action_loc)
                    return 1

                # TODO: use token directly
                val = cpython._PyObjToValue(obj)
                self.mem.SetValue(location.LName(var_name), val, scope_e.LocalOnly)

        else:
            raise error.Usage(_JSON_ACTION_ERROR, action_loc)

        return 0
