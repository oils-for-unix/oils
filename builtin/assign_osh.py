#!/usr/bin/env python2
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.option_asdl import builtin_i
from _devbuild.gen.runtime_asdl import (
    scope_e,
    scope_t,
    cmd_value,
    AssignArg,
)
from _devbuild.gen.value_asdl import (value, value_e, value_t, LeftName)
from _devbuild.gen.syntax_asdl import loc, loc_t

from core import bash_impl
from core import error
from core.error import e_usage, e_die
from core import state
from core import vm
from data_lang import j8_lite
from display import ui
from frontend import flag_util
from frontend import args
from mycpp.mylib import log, tagswitch
from osh import cmd_eval
from osh import sh_expr_eval

from typing import cast, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from core import optview
    from frontend.args import _Attributes

_ = log

_OTHER = 0
_READONLY = 1
_EXPORT = 2


def _PrintVariables(
        mem,  # type: state.Mem
        errfmt,  # type: ui.ErrorFormatter
        cmd_val,  # type: cmd_value.Assign
        attrs,  # type: _Attributes
        print_flags,  # type: bool
        builtin=_OTHER,  # type: int
):
    # type: (...) -> int
    """
    Args:
      attrs: flag attributes
      print_flags: whether to print flags
      builtin: is it the readonly or export builtin?
    """
    flag = attrs.attrs

    # Turn dynamic vars to static.
    tmp_g = flag.get('g')
    tmp_a = flag.get('a')
    tmp_A = flag.get('A')

    flag_g = (cast(value.Bool, tmp_g).b
              if tmp_g and tmp_g.tag() == value_e.Bool else False)
    flag_a = (cast(value.Bool, tmp_a).b
              if tmp_a and tmp_a.tag() == value_e.Bool else False)
    flag_A = (cast(value.Bool, tmp_A).b
              if tmp_A and tmp_A.tag() == value_e.Bool else False)

    tmp_n = flag.get('n')
    tmp_r = flag.get('r')
    tmp_x = flag.get('x')

    #log('FLAG %r', flag)

    # SUBTLE: export -n vs. declare -n.  flag vs. OPTION.
    # flags are value.Bool, while options are Undef or Str.
    # '+', '-', or None
    flag_n = (cast(value.Str, tmp_n).s if tmp_n and tmp_n.tag() == value_e.Str
              else None)  # type: Optional[str]
    flag_r = (cast(value.Str, tmp_r).s if tmp_r and tmp_r.tag() == value_e.Str
              else None)  # type: Optional[str]
    flag_x = (cast(value.Str, tmp_x).s if tmp_x and tmp_x.tag() == value_e.Str
              else None)  # type: Optional[str]

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
            # declare/typeset/local -p var1 var2 print an error
            # There is no readonly/export -p var1 var2
            errfmt.PrintMessage(
                'osh: %s: %r is not defined' % (cmd_val.argv[0], name),
                cmd_val.arg_locs[0])
            continue  # not defined

        val = cell.val
        # Mem.var_stack does not store value.Undef
        assert val.tag() != value_e.Undef, val

        #log('name %r %s', name, val)

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

        if flag_a and val.tag() not in (value_e.InternalStringArray,
                                        value_e.BashArray):
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
            if val.tag() in (value_e.InternalStringArray, value_e.BashArray):
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
            decl.extend(["=", j8_lite.MaybeShellEncode(str_val.s)])

        elif val.tag() == value_e.InternalStringArray:
            array_val = cast(value.InternalStringArray, val)
            decl.extend([
                "=",
                bash_impl.InternalStringArray_ToStrForShellPrint(
                    array_val, name)
            ])

        elif val.tag() == value_e.BashAssoc:
            assoc_val = cast(value.BashAssoc, val)
            decl.extend(
                ["=", bash_impl.BashAssoc_ToStrForShellPrint(assoc_val)])

        elif val.tag() == value_e.BashArray:
            sparse_val = cast(value.BashArray, val)
            decl.extend(
                ["=", bash_impl.BashArray_ToStrForShellPrint(sparse_val)])

        else:
            pass  # note: other types silently ignored

        print(''.join(decl))
        count += 1

    if print_all or count == len(names):
        return 0
    else:
        return 1


def _AssignVarForBuiltin(
        mem,  # type: state.Mem
        rval,  # type: value_t
        pair,  # type: AssignArg
        which_scopes,  # type: scope_t
        flags,  # type: int
        arith_ev,  # type: sh_expr_eval.ArithEvaluator
        flag_a,  # type: bool
        flag_A,  # type: bool
):
    # type: (...) -> None
    """For 'export', 'readonly', and NewVar to respect += and flags.

    Like 'setvar' (scope_e.LocalOnly), unless dynamic scope is on.  That is, it
    respects shopt --unset dynamic_scope.

    Used for assignment builtins, (( a = b )), {fd}>out, ${x=}, etc.
    """
    lval = LeftName(pair.var_name, pair.blame_word)

    initializer = None  # type: value.InitializerList
    if rval is None:
        # When 'export e+=', then rval is value.Str('')
        # When 'export foo', the pair.plus_eq flag is false.
        # Thus, when rval is None, plus_eq cannot be True.
        assert not pair.plus_eq, pair.plus_eq
        # NOTE: when rval is None, only flags are changed
        val = None  # type: value_t
    elif rval.tag() == value_e.InitializerList:
        old_val = sh_expr_eval.OldValue(
            lval,
            mem,
            None,  # ignore set -u
            pair.blame_word)
        initializer = cast(value.InitializerList, rval)

        val = old_val
        if flag_a:
            if old_val.tag() in (value_e.Undef, value_e.Str,
                                 value_e.BashArray):
                # We do not need adjustemnts for -a.  These types are
                # consistently handled within ListInitialize
                pass
            else:
                # Note: BashAssoc cannot be converted to a BashArray
                e_die(
                    "Can't convert type %s into BashArray" %
                    ui.ValType(old_val), pair.blame_word)
        elif flag_A:
            with tagswitch(old_val) as case:
                if case(value_e.Undef):
                    # Note: We explicitly initialize BashAssoc for Undef.
                    val = bash_impl.BashAssoc_New()
                elif case(value_e.Str):
                    # Note: We explicitly initialize BashAssoc for Str.  When
                    #   applying +=() to Str, we associate an old value to the
                    #   key '0'.  OSH disables this when strict_array is turned
                    #   on.
                    assoc_val = bash_impl.BashAssoc_New()
                    if pair.plus_eq:
                        if mem.exec_opts.strict_array():
                            e_die(
                                "Can't convert Str to BashAssoc (strict_array)",
                                pair.blame_word)
                        bash_impl.BashAssoc_SetElement(
                            assoc_val, '0',
                            cast(value.Str, old_val).s)
                    val = assoc_val
                elif case(value_e.BashAssoc):
                    # We do not need adjustments for -A.
                    pass
                else:
                    # Note: BashArray cannot be converted to a BashAssoc
                    e_die(
                        "Can't convert type %s into BashAssoc" %
                        ui.ValType(old_val), pair.blame_word)

        val = cmd_eval.ListInitializeTarget(val, pair.plus_eq, mem.exec_opts,
                                            pair.blame_word)
    elif pair.plus_eq:
        old_val = sh_expr_eval.OldValue(
            lval,
            mem,
            None,  # ignore set -u
            pair.blame_word)
        val = cmd_eval.PlusEquals(old_val, rval)
    else:
        val = rval

    mem.SetNamed(lval, val, which_scopes, flags=flags)
    if initializer is not None:
        cmd_eval.ListInitialize(val, initializer, pair.plus_eq, mem.exec_opts,
                                pair.blame_word, arith_ev)


class Export(vm._AssignBuiltin):

    def __init__(self, mem, arith_ev, errfmt):
        # type: (state.Mem, sh_expr_eval.ArithEvaluator, ui.ErrorFormatter) -> None
        self.mem = mem
        self.arith_ev = arith_ev
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Assign) -> int
        if self.mem.exec_opts.no_exported():
            self.errfmt.Print_(
                "YSH doesn't have 'export'.  Hint: setglobal ENV.FOO = 'bar'",
                cmd_val.arg_locs[0])
            return 1

        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
        arg_r.Next()
        attrs = flag_util.Parse('export_', arg_r)
        arg = arg_types.export_(attrs.attrs)
        #arg = attrs

        if arg.f:
            e_usage(
                "doesn't accept -f because it's dangerous.  "
                "(The code can usually be restructured with 'source')",
                loc.Missing)

        if arg.p or len(cmd_val.pairs) == 0:
            return _PrintVariables(self.mem,
                                   self.errfmt,
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
            which_scopes = self.mem.ScopesForWriting()
            for pair in cmd_val.pairs:
                _AssignVarForBuiltin(self.mem, pair.rval, pair, which_scopes,
                                     state.SetExport, self.arith_ev, False,
                                     False)

        return 0


def _ReconcileTypes(rval, flag_a, flag_A, pair, mem):
    # type: (Optional[value_t], bool, bool, AssignArg, state.Mem) -> value_t
    """Check that -a and -A flags are consistent with RHS.

    If RHS is empty and the current value of LHS has a different type from the
    one expected by the -a and -A flags, we create an empty array.

    Special case: () is allowed to mean empty indexed array or empty assoc array
    if the context is clear.

    Shared between NewVar and Readonly.

    """

    if rval is None:
        # declare -a foo=(a b); declare -a foo; should not reset to empty array
        if flag_a:
            old_val = mem.GetValue(pair.var_name)
            if old_val.tag() not in (value_e.InternalStringArray,
                                     value_e.BashArray):
                rval = bash_impl.BashArray_New()
        elif flag_A:
            old_val = mem.GetValue(pair.var_name)
            if old_val.tag() != value_e.BashAssoc:
                rval = bash_impl.BashAssoc_New()
    else:
        if flag_a:
            if rval.tag() != value_e.InitializerList:
                e_usage("Got -a but RHS isn't an initializer list",
                        loc.Word(pair.blame_word))
        elif flag_A:
            if rval.tag() != value_e.InitializerList:
                e_usage("Got -A but RHS isn't an initializer list",
                        loc.Word(pair.blame_word))

    return rval


class Readonly(vm._AssignBuiltin):

    def __init__(self, mem, arith_ev, errfmt):
        # type: (state.Mem, sh_expr_eval.ArithEvaluator, ui.ErrorFormatter) -> None
        self.mem = mem
        self.arith_ev = arith_ev
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Assign) -> int
        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
        arg_r.Next()
        attrs = flag_util.Parse('readonly', arg_r)
        arg = arg_types.readonly(attrs.attrs)

        if arg.p or len(cmd_val.pairs) == 0:
            return _PrintVariables(self.mem,
                                   self.errfmt,
                                   cmd_val,
                                   attrs,
                                   True,
                                   builtin=_READONLY)

        which_scopes = self.mem.ScopesForWriting()
        for pair in cmd_val.pairs:
            rval = _ReconcileTypes(pair.rval, arg.a, arg.A, pair, self.mem)

            # NOTE:
            # - when rval is None, only flags are changed
            # - dynamic scope because flags on locals can be changed, etc.
            _AssignVarForBuiltin(self.mem, rval, pair, which_scopes,
                                 state.SetReadOnly, self.arith_ev, arg.a,
                                 arg.A)

        return 0


class NewVar(vm._AssignBuiltin):
    """declare/typeset/local."""

    def __init__(
            self,
            mem,  # type: state.Mem
            procs,  # type: state.Procs
            exec_opts,  # type: optview.Exec
            arith_ev,  # type: sh_expr_eval.ArithEvaluator
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.mem = mem
        self.procs = procs
        self.exec_opts = exec_opts
        self.arith_ev = arith_ev
        self.errfmt = errfmt

    def _PrintFuncs(self, names):
        # type: (List[str]) -> int
        status = 0
        for name in names:
            proc_val = self.procs.GetShellFunc(name)
            if proc_val:
                if self.exec_opts.extdebug():
                    tok = proc_val.name_tok
                    assert tok is not None, tok
                    assert tok.line is not None, tok.line
                    filename_str = ui.GetFilenameString(tok.line)
                    # Note: the filename could have a newline, and this won't
                    # be a single line.  But meh, this is a bash feature.
                    line = '%s %d %s' % (name, tok.line.line_num, filename_str)
                    print(line)
                else:
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
        attrs = flag_util.Parse('new_var', arg_r)
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
                for func_name in self.procs.ShellFuncNames():
                    print('declare -f %s' % (func_name))
            return status

        if arg.p:  # Lookup and print variables.
            return _PrintVariables(self.mem, self.errfmt, cmd_val, attrs, True)
        elif len(cmd_val.pairs) == 0:
            return _PrintVariables(self.mem, self.errfmt, cmd_val, attrs,
                                   False)

        if not self.exec_opts.ignore_flags_not_impl():
            if arg.i:
                e_usage(
                    "doesn't implement flag -i (shopt --set ignore_flags_not_impl)",
                    loc.Missing)

            if arg.l or arg.u:
                # Just print a warning!  The program may still run.
                self.errfmt.Print_(
                    "Warning: OSH doesn't implement flags -l or -u (shopt --set ignore_flags_not_impl)",
                    loc.Missing)

        #
        # Set variables
        #

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
            rval = _ReconcileTypes(pair.rval, arg.a, arg.A, pair, self.mem)

            _AssignVarForBuiltin(self.mem, rval, pair, which_scopes, flags,
                                 self.arith_ev, arg.a, arg.A)

        return status


# TODO:
# - It would make more sense to treat no args as an error (bash doesn't.)
#   - Should we have strict builtins?  Or just make it stricter?
# - Typed args: unset (mylist[0]) is like Python's del
#   - It has the same word as 'setvar', which makes sense


class Unset(vm._Builtin):

    def __init__(
            self,
            mem,  # type: state.Mem
            procs,  # type: state.Procs
            unsafe_arith,  # type: sh_expr_eval.UnsafeArith
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
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

        #log('unsafe lval %s', lval)
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
            self.procs.EraseShellFunc(arg)

        return True

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('unset', cmd_val)
        arg = arg_types.unset(attrs.attrs)

        argv, arg_locs = arg_r.Rest2()
        for i, name in enumerate(argv):
            location = arg_locs[i]

            if arg.f:
                self.procs.EraseShellFunc(name)

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
        # type: (state.Mem) -> None
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
