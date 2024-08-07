from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import loc, loc_t
from _devbuild.gen.value_asdl import value, LeftName
from builtin import read_osh
from core import error
from core.error import e_usage
from core import pyos
from core import state
from core import vm
from data_lang import j8
from frontend import flag_util
from frontend import args
from frontend import typed_args
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import log

import posix_ as posix

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from display import ui

_ = log

_JSON_ACTION_ERROR = "builtin expects 'read' or 'write'"


class Json(vm._Builtin):
    """JSON read and write.

    --pretty=0 writes it on a single line
    --indent=2 controls multiline indentation
    """

    def __init__(self, mem, errfmt, is_j8):
        # type: (state.Mem, ui.ErrorFormatter, bool) -> None
        self.mem = mem
        self.errfmt = errfmt

        self.is_j8 = is_j8
        self.name = 'json8' if is_j8 else 'json'  # for error messages

        self.stdout_ = mylib.Stdout()

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
            attrs = flag_util.Parse('json_write', arg_r)

            arg_jw = arg_types.json_write(attrs.attrs)

            if not arg_r.AtEnd():
                e_usage('write got too many args', arg_r.Location())

            rd = typed_args.ReaderForProc(cmd_val)
            val = rd.PosValue()
            # default is 2, rather than 0 for toJson()
            space = mops.BigTruncate(rd.NamedInt('space', 2))
            rd.Done()

            # Convert from external JS-like API to internal API.
            if space <= 0:
                indent = -1
            else:
                indent = space

            buf = mylib.BufWriter()
            try:
                if self.is_j8:
                    j8.PrintMessage(val, buf, indent)
                else:
                    j8.PrintJsonMessage(val, buf, indent)
            except error.Encode as e:
                self.errfmt.PrintMessage(
                    '%s write: %s' % (self.name, e.Message()), action_loc)
                return 1

            self.stdout_.write(buf.getvalue())
            self.stdout_.write('\n')

        elif action == 'read':
            attrs = flag_util.Parse('json_read', arg_r)
            #arg_jr = arg_types.json_read(attrs.attrs)

            if cmd_val.proc_args:  # json read (&x)
                rd = typed_args.ReaderForProc(cmd_val)
                place = rd.PosPlace()
                rd.Done()

                blame_loc = cmd_val.proc_args.typed_args.left  # type: loc_t

            else:  # json read
                var_name = '_reply'

                #log('VAR %s', var_name)
                blame_loc = cmd_val.arg_locs[0]
                place = value.Place(LeftName(var_name, blame_loc),
                                    self.mem.TopNamespace())

            if not arg_r.AtEnd():
                e_usage('read got too many args', arg_r.Location())

            try:
                contents = read_osh.ReadAll()
            except pyos.ReadError as e:  # different paths for read -d, etc.
                # don't quote code since YSH errexit will likely quote
                self.errfmt.PrintMessage("read error: %s" %
                                         posix.strerror(e.err_num))
                return 1

            p = j8.Parser(contents, self.is_j8)
            try:
                val = p.ParseValue()
            except error.Decode as err:
                # TODO: Need to show position info
                self.errfmt.Print_('%s read: %s' % (self.name, err.Message()),
                                   blame_loc=action_loc)
                return 1

            self.mem.SetPlace(place, val, blame_loc)

        else:
            raise error.Usage(_JSON_ACTION_ERROR, action_loc)

        return 0
