#!/usr/bin/env python2
"""Builtin_assign.py."""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.option_asdl import builtin_i
from _devbuild.gen.runtime_asdl import (
    value,
    value_e,
    value_t,
    scope_e,
    cmd_value,
    AssignArg,
)
from _devbuild.gen.syntax_asdl import loc, loc_t, word_t

from core import error
from core.error import e_usage
from core import state
from core import vm
from frontend import flag_spec
from frontend import location
from frontend import args
from mycpp import mylib
from mycpp.mylib import log
from osh import cmd_eval
from osh import sh_expr_eval
from data_lang import qsn

from typing import cast, Optional, Dict, List, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import Proc
    from core.state import Mem
    from core.ui import ErrorFormatter
    from frontend.args import _Attributes

_ = log

_OTHER = 0
_READONLY = 1
_EXPORT = 2


def _PrintVariables(mem, cmd_val, attrs, print_flags, builtin=_OTHER):
    # type: (Mem, cmd_value.Assign, _Attributes, bool, int) -> int
    """
  Args:
    print_flags: whether to print flags
    builtin: is it the readonly or export builtin?
  """
    flag = attrs.attrs

    # Turn dynamic vars to static.
    tmp_g = flag.get('g')
    tmp_a = flag.get('a')
    tmp_A = flag.get('A')

    flag_g = cast(value.Bool,
                  tmp_g).b if tmp_g and tmp_g.tag() == value_e.Bool else False
    flag_a = cast(value.Bool,
                  tmp_a).b if tmp_a and tmp_a.tag() == value_e.Bool else False
    flag_A = cast(value.Bool,
                  tmp_A).b if tmp_A and tmp_A.tag() == value_e.Bool else False

    tmp_n = flag.get('n')
    tmp_r = flag.get('r')
    tmp_x = flag.get('x')

    #log('FLAG %r', flag)

    # SUBTLE: export -n vs. declare -n.  flag vs. OPTION.
    # flags are value.Bool, while options are Undef or Str.
    # '+', '-', or None
    flag_n = cast(
        value.Str, tmp_n
    ).s if tmp_n and tmp_n.tag() == value_e.Str else None  # type: Optional[str]
    flag_r = cast(
        value.Str, tmp_r
    ).s if tmp_r and tmp_r.tag() == value_e.Str else None  # type: Optional[str]
    flag_x = cast(
        value.Str, tmp_x
    ).s if tmp_x and tmp_x.tag() == value_e.Str else None  # type: Optional[str]

    if cmd_val.builtin_id == builtin_i.local:
        if flag_g and not mem.IsGlobalScope():
            return 1
        which_scopes = scope_e.LocalOnly
    elif flag_g:
        which_scopes = scope_e.GlobalOnly
    else:
        which_scopes = mem.ScopesForReading()  # reading

    if len(cmd_val.pairs) == 0:
        print_all = True
        cells = mem.GetAllCells(which_scopes)
        names = sorted(cells)  # type: List[str]
    else:
        print_all = False
        names = []
        cells = {}
        for pair in cmd_val.pairs:
            name = pair.var_name
            if pair.rval and pair.rval.tag() == value_e.Str:
                # Invalid: declare -p foo=bar
                # Add a sentinel so we skip it, but know to exit with status 1.
                s = cast(value.Str, pair.rval).s
                invalid = "%s=%s" % (name, s)
                names.append(invalid)
                cells[invalid] = None
            else:
                names.append(name)
                cells[name] = mem.GetCell(name, which_scopes)

    count = 0
    for name in names:
        cell = cells[name]
        if cell is None:
            continue  # Invalid
        val = cell.val
        #log('name %r %s', name, val)

        if val.tag() == value_e.Undef:
            continue
        if builtin == _READONLY and not cell.readonly:
            continue
        if builtin == _EXPORT and not cell.exported:
            continue

        if flag_n == '-' and not cell.nameref:
            continue
        if flag_n == '+' and cell.nameref:
            continue
        if flag_r == '-' and not cell.readonly:
            continue
        if flag_r == '+' and cell.readonly:
            continue
        if flag_x == '-' and not cell.exported:
            continue
        if flag_x == '+' and cell.exported:
            continue

        if flag_a and val.tag() != value_e.BashArray:
            continue
        if flag_A and val.tag() != value_e.BashAssoc:
            continue

        decl = []  # type: List[str]
        if print_flags:
            flags = []  # type: List[str]
            if cell.nameref:
                flags.append('n')
            if cell.readonly:
                flags.append('r')
            if cell.exported:
                flags.append('x')
            if val.tag() == value_e.BashArray:
                flags.append('a')
            elif val.tag() == value_e.BashAssoc:
                flags.append('A')
            if len(flags) == 0:
                flags.append('-')

            decl.extend(["declare -", ''.join(flags), " ", name])
        else:
            decl.append(name)

        if val.tag() == value_e.Str:
            str_val = cast(value.Str, val)
            decl.extend(["=", qsn.maybe_shell_encode(str_val.s)])

        elif val.tag() == value_e.BashArray:
            array_val = cast(value.BashArray, val)

            # mycpp rewrite: None in array_val.strs
            has_holes = False
            for s in array_val.strs:
                if s is None:
                    has_holes = True
                    break

            if has_holes:
                # Note: Arrays with unset elements are printed in the form:
                #   declare -p arr=(); arr[3]='' arr[4]='foo' ...
                decl.append("=()")
                first = True
                for i, element in enumerate(array_val.strs):
                    if element is not None:
                        if first:
                            decl.append(";")
                            first = False
                        decl.extend([
                            " ", name, "[",
                            str(i), "]=",
                            qsn.maybe_shell_encode(element)
                        ])
            else:
                body = []  # type: List[str]
                for element in array_val.strs:
                    if len(body) > 0:
                        body.append(" ")
                    body.append(qsn.maybe_shell_encode(element))
                decl.extend(["=(", ''.join(body), ")"])

        elif val.tag() == value_e.BashAssoc:
            assoc_val = cast(value.BashAssoc, val)
            body = []
            for key in sorted(assoc_val.d):
                if len(body) > 0:
                    body.append(" ")
                key_quoted = qsn.maybe_shell_encode(key, flags=qsn.MUST_QUOTE)
                value_quoted = qsn.maybe_shell_encode(assoc_val.d[key])
                body.extend(["[", key_quoted, "]=", value_quoted])
            if len(body) > 0:
                decl.extend(["=(", ''.join(body), ")"])

        else:
            pass  # note: other types silently ignored

        print(''.join(decl))
        count += 1

    if print_all or count == len(names):
        return 0
    else:
        return 1


def _ExportReadonly(mem, pair, flags):
    # type: (Mem, AssignArg, int) -> None
    """For 'export' and 'readonly' to respect += and flags.

    Like 'setvar' (scope_e.LocalOnly), unless dynamic scope is on.  That is, it
    respects shopt --unset dynamic_scope.

    Used for assignment builtins, (( a = b )), {fd}>out, ${x=}, etc.
    """
    which_scopes = mem.ScopesForWriting()

    lval = location.LName(pair.var_name)
    if pair.plus_eq:
        old_val = sh_expr_eval.OldValue(lval, mem, None)  # ignore set -u
        # When 'export e+=', then rval is value.Str('')
        # When 'export foo', the pair.plus_eq flag is false.
        assert pair.rval is not None
        val = cmd_eval.PlusEquals(old_val, pair.rval)
    else:
        # NOTE: when rval is None, only flags are changed
        val = pair.rval

    mem.SetValue(lval, val, which_scopes, flags=flags)


class Export(vm._AssignBuiltin):
    def __init__(self, mem, errfmt):
        # type: (Mem, ErrorFormatter) -> None
        self.mem = mem
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Assign) -> int
        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
        arg_r.Next()
        attrs = flag_spec.Parse('export_', arg_r)
        arg = arg_types.export_(attrs.attrs)
        #arg = attrs

        if arg.f:
            e_usage(
                "doesn't accept -f because it's dangerous.  "
                "(The code can usually be restructured with 'source')",
                loc.Missing)

        if arg.p or len(cmd_val.pairs) == 0:
            return _PrintVariables(self.mem,
                                   cmd_val,
                                   attrs,
                                   True,
                                   builtin=_EXPORT)

        if arg.n:
            for pair in cmd_val.pairs:
                if pair.rval is not None:
                    e_usage("doesn't accept RHS with -n",
                            loc.Word(pair.blame_word))

                # NOTE: we don't care if it wasn't found, like bash.
                self.mem.ClearFlag(pair.var_name, state.ClearExport)
        else:
            for pair in cmd_val.pairs:
                _ExportReadonly(self.mem, pair, state.SetExport)

        return 0


def _ReconcileTypes(rval, flag_a, flag_A, blame_word):
    # type: (Optional[value_t], bool, bool, word_t) -> value_t
    """Check that -a and -A flags are consistent with RHS.

    Special case: () is allowed to mean empty indexed array or empty assoc array
    if the context is clear.

    Shared between NewVar and Readonly.
    """
    if flag_a and rval is not None and rval.tag() != value_e.BashArray:
        e_usage("Got -a but RHS isn't an array", loc.Word(blame_word))

    if flag_A and rval:
        # Special case: declare -A A=() is OK.  The () is changed to mean an empty
        # associative array.
        if rval.tag() == value_e.BashArray:
            array_val = cast(value.BashArray, rval)
            if len(array_val.strs) == 0:
                return value.BashAssoc({})
                #return value.BashArray([])

        if rval.tag() != value_e.BashAssoc:
            e_usage("Got -A but RHS isn't an associative array",
                    loc.Word(blame_word))

    return rval


class Readonly(vm._AssignBuiltin):
    def __init__(self, mem, errfmt):
        # type: (Mem, ErrorFormatter) -> None
        self.mem = mem
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Assign) -> int
        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
        arg_r.Next()
        attrs = flag_spec.Parse('readonly', arg_r)
        arg = arg_types.readonly(attrs.attrs)

        if arg.p or len(cmd_val.pairs) == 0:
            return _PrintVariables(self.mem,
                                   cmd_val,
                                   attrs,
                                   True,
                                   builtin=_READONLY)

        for pair in cmd_val.pairs:
            if pair.rval is None:
                if arg.a:
                    rval = value.BashArray([])  # type: value_t
                elif arg.A:
                    rval = value.BashAssoc({})
                else:
                    rval = None
            else:
                rval = pair.rval

            rval = _ReconcileTypes(rval, arg.a, arg.A, pair.blame_word)

            # NOTE:
            # - when rval is None, only flags are changed
            # - dynamic scope because flags on locals can be changed, etc.
            _ExportReadonly(self.mem, pair, state.SetReadOnly)

        return 0


class NewVar(vm._AssignBuiltin):
    """declare/typeset/local."""

    def __init__(self, mem, procs, errfmt):
        # type: (Mem, Dict[str, Proc], ErrorFormatter) -> None
        self.mem = mem
        self.procs = procs
        self.errfmt = errfmt

    def _PrintFuncs(self, names):
        # type: (List[str]) -> int
        status = 0
        for name in names:
            if name in self.procs:
                print(name)
                # TODO: Could print LST for -f, or render LST.  Bash does this.  'trap'
                # could use that too.
            else:
                status = 1
        return status

    def Run(self, cmd_val):
        # type: (cmd_value.Assign) -> int
        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
        arg_r.Next()
        attrs = flag_spec.Parse('new_var', arg_r)
        arg = arg_types.new_var(attrs.attrs)

        status = 0

        if arg.f:
            names = arg_r.Rest()
            if len(names):
                # This is only used for a STATUS QUERY now.  We only show the name,
                # not the body.
                status = self._PrintFuncs(names)
            else:
                # Disallow this since it would be incompatible.
                e_usage('with -f expects function names', loc.Missing)
            return status

        if arg.F:
            names = arg_r.Rest()
            if len(names):
                status = self._PrintFuncs(names)
            else:
                # bash quirk: with no names, they're printed in a different format!
                for func_name in sorted(self.procs):
                    print('declare -f %s' % (func_name))
            return status

        if arg.p:  # Lookup and print variables.
            return _PrintVariables(self.mem, cmd_val, attrs, True)
        elif len(cmd_val.pairs) == 0:
            return _PrintVariables(self.mem, cmd_val, attrs, False)

        #
        # Set variables
        #

        #raise error.Usage("doesn't understand %s" % cmd_val.argv[1:])
        if cmd_val.builtin_id == builtin_i.local:
            which_scopes = scope_e.LocalOnly
        else:  # declare/typeset
            if arg.g:
                which_scopes = scope_e.GlobalOnly
            else:
                which_scopes = scope_e.LocalOnly

        flags = 0
        if arg.x == '-':
            flags |= state.SetExport
        if arg.r == '-':
            flags |= state.SetReadOnly
        if arg.n == '-':
            flags |= state.SetNameref

        if arg.x == '+':
            flags |= state.ClearExport
        if arg.r == '+':
            flags |= state.ClearReadOnly
        if arg.n == '+':
            flags |= state.ClearNameref

        for pair in cmd_val.pairs:
            rval = pair.rval
            # declare -a foo=(a b); declare -a foo;  should not reset to empty array
            if rval is None and (arg.a or arg.A):
                old_val = self.mem.GetValue(pair.var_name)
                if arg.a:
                    if old_val.tag() != value_e.BashArray:
                        rval = value.BashArray([])
                elif arg.A:
                    if old_val.tag() != value_e.BashAssoc:
                        rval = value.BashAssoc({})

            lval = location.LName(pair.var_name)
            if pair.plus_eq:
                old_val = sh_expr_eval.OldValue(lval, self.mem,
                                                None)  # ignore set -u
                # When 'typeset e+=', then rval is value.Str('')
                # When 'typeset foo', the pair.plus_eq flag is false.
                assert pair.rval is not None
                rval = cmd_eval.PlusEquals(old_val, pair.rval)
            else:
                rval = _ReconcileTypes(rval, arg.a, arg.A, pair.blame_word)

            self.mem.SetValue(lval, rval, which_scopes, flags=flags)

        return status


# TODO:
# - It would make more sense to treat no args as an error (bash doesn't.)
#   - Should we have strict builtins?  Or just make it stricter?
# - Typed args: unset (mylist[0]) is like Python's del
#   - It has the same word as 'setvar', which makes sense


class Unset(vm._Builtin):
    def __init__(self, mem, procs, unsafe_arith, errfmt):
        # type: (Mem, Dict[str, Proc], sh_expr_eval.UnsafeArith, ErrorFormatter) -> None
        self.mem = mem
        self.procs = procs
        self.unsafe_arith = unsafe_arith
        self.errfmt = errfmt

    def _UnsetVar(self, arg, location, proc_fallback):
        # type: (str, loc_t, bool) -> bool
        """
    Returns:
      bool: whether the 'unset' builtin should succeed with code 0.
    """
        lval = self.unsafe_arith.ParseLValue(arg, location)

        #log('lval %s', lval)
        found = False
        try:
            found = self.mem.Unset(lval, scope_e.Shopt)
        except error.Runtime as e:
            # note: in bash, myreadonly=X fails, but declare myreadonly=X doesn't
            # fail because it's a builtin.  So I guess the same is true of 'unset'.
            msg = e.UserErrorString()
            self.errfmt.Print_(msg, blame_loc=location)
            return False

        if proc_fallback and not found:
            mylib.dict_erase(self.procs, arg)

        return True

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_spec.ParseCmdVal('unset', cmd_val)
        arg = arg_types.unset(attrs.attrs)

        argv, arg_locs = arg_r.Rest2()
        for i, name in enumerate(argv):
            location = arg_locs[i]

            if arg.f:
                mylib.dict_erase(self.procs, name)

            elif arg.v:
                if not self._UnsetVar(name, location, False):
                    return 1

            else:
                # proc_fallback: Try to delete var first, then func.
                if not self._UnsetVar(name, location, True):
                    return 1

        return 0


class Shift(vm._Builtin):
    def __init__(self, mem):
        # type: (Mem) -> None
        self.mem = mem

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        num_args = len(cmd_val.argv) - 1
        if num_args == 0:
            n = 1
        elif num_args == 1:
            arg = cmd_val.argv[1]
            try:
                n = int(arg)
            except ValueError:
                e_usage("Invalid shift argument %r" % arg, loc.Missing)
        else:
            e_usage('got too many arguments', loc.Missing)

        return self.mem.Shift(n)
