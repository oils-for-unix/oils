#!/usr/bin/env python2
"""expr_eval.py."""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.syntax_asdl import (
    loc,
    loc_t,
    re,
    re_e,
    re_t,
    Token,
    NameTok,
    word_part,
    SingleQuoted,
    DoubleQuoted,
    BracedVarSub,
    ShArrayLiteral,
    CommandSub,
    expr,
    expr_e,
    expr_t,
    y_lhs_e,
    y_lhs_t,
    Attribute,
    Subscript,
    class_literal_term,
    class_literal_term_e,
    class_literal_term_t,
    char_class_term,
    char_class_term_t,
    PosixClass,
    PerlClass,
    CharCode,
    ArgList,
    Eggex,
)
from _devbuild.gen.runtime_asdl import (
    coerced_e,
    coerced_t,
    scope_e,
    scope_t,
    part_value,
    part_value_t,
)
from _devbuild.gen.value_asdl import (value, value_e, value_t, y_lvalue,
                                      y_lvalue_e, y_lvalue_t, IntBox, LeftName)
from core import error
from core.error import e_die, e_die_status
from core import num
from core import pyutil
from core import state
from core import ui
from core import vm
from frontend import consts
from frontend import lexer
from frontend import match
from frontend import typed_args
from osh import braces
from osh import word_compile
from mycpp import mops
from mycpp.mylib import log, NewDict, switch, tagswitch, print_stderr
from ysh import func_proc
from ysh import val_ops

import libc

from typing import cast, Optional, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from osh import cmd_eval
    from osh import word_eval
    from osh import split

_ = log


def LookupVar(mem, var_name, which_scopes, var_loc):
    # type: (state.Mem, str, scope_t, loc_t) -> value_t

    # Lookup WITHOUT dynamic scope.
    val = mem.GetValue(var_name, which_scopes=which_scopes)
    if val.tag() == value_e.Undef:
        e_die('Undefined variable %r' % var_name, var_loc)

    return val


def _ConvertToInt(val, msg, blame_loc):
    # type: (value_t, str, loc_t) -> mops.BigInt
    UP_val = val
    with tagswitch(val) as case:
        if case(value_e.Int):
            val = cast(value.Int, UP_val)
            return val.i

        elif case(value_e.Str):
            val = cast(value.Str, UP_val)
            if match.LooksLikeInteger(val.s):
                # TODO: Handle ValueError
                return mops.FromStr(val.s)

    raise error.TypeErr(val, msg, blame_loc)


def _ConvertToNumber(val):
    # type: (value_t) -> Tuple[coerced_t, mops.BigInt, float]
    UP_val = val
    with tagswitch(val) as case:
        if case(value_e.Int):
            val = cast(value.Int, UP_val)
            return coerced_e.Int, val.i, -1.0

        elif case(value_e.Float):
            val = cast(value.Float, UP_val)
            return coerced_e.Float, mops.MINUS_ONE, val.f

        elif case(value_e.Str):
            val = cast(value.Str, UP_val)
            if match.LooksLikeInteger(val.s):
                # TODO: Handle ValueError
                return coerced_e.Int, mops.FromStr(val.s), -1.0

            if match.LooksLikeFloat(val.s):
                return coerced_e.Float, mops.MINUS_ONE, float(val.s)

    return coerced_e.Neither, mops.MINUS_ONE, -1.0


def _ConvertForBinaryOp(left, right):
    # type: (value_t, value_t) -> Tuple[coerced_t, mops.BigInt, mops.BigInt, float, float]
    """
    Returns one of
      value_e.Int or value_e.Float
      2 ints or 2 floats

    To indicate which values the operation should be done on
    """
    c1, i1, f1 = _ConvertToNumber(left)
    c2, i2, f2 = _ConvertToNumber(right)

    nope = mops.MINUS_ONE

    if c1 == coerced_e.Int and c2 == coerced_e.Int:
        return coerced_e.Int, i1, i2, -1.0, -1.0

    elif c1 == coerced_e.Int and c2 == coerced_e.Float:
        return coerced_e.Float, nope, nope, mops.ToFloat(i1), f2

    elif c1 == coerced_e.Float and c2 == coerced_e.Int:
        return coerced_e.Float, nope, nope, f1, mops.ToFloat(i2)

    elif c1 == coerced_e.Float and c2 == coerced_e.Float:
        return coerced_e.Float, nope, nope, f1, f2

    else:
        # No operation is valid
        return coerced_e.Neither, nope, nope, -1.0, -1.0


class ExprEvaluator(object):
    """Shared between arith and bool evaluators.

    They both:

    1. Convert strings to integers, respecting shopt -s strict_arith.
    2. Look up variables and evaluate words.
    """

    def __init__(
            self,
            mem,  # type: state.Mem
            mutable_opts,  # type: state.MutableOpts
            methods,  # type: Dict[int, Dict[str, vm._Callable]]
            splitter,  # type: split.SplitContext
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.shell_ex = None  # type: vm._Executor
        self.cmd_ev = None  # type: cmd_eval.CommandEvaluator
        self.word_ev = None  # type: word_eval.AbstractWordEvaluator

        self.mem = mem
        self.mutable_opts = mutable_opts
        self.methods = methods
        self.splitter = splitter
        self.errfmt = errfmt

    def CheckCircularDeps(self):
        # type: () -> None
        assert self.shell_ex is not None
        assert self.word_ev is not None

    def _LookupVar(self, name, var_loc):
        # type: (str, loc_t) -> value_t
        return LookupVar(self.mem, name, scope_e.LocalOrGlobal, var_loc)

    def EvalAugmented(self, lval, rhs_val, op, which_scopes):
        # type: (y_lvalue_t, value_t, Token, scope_t) -> None
        """ setvar x +=1, setvar L[0] -= 1 

        Called by CommandEvaluator
        """
        # TODO: It might be nice to do auto d[x] += 1 too

        UP_lval = lval
        with tagswitch(lval) as case:
            if case(y_lvalue_e.Local):  # setvar x += 1
                lval = cast(LeftName, UP_lval)
                lhs_val = self._LookupVar(lval.name, lval.blame_loc)
                if op.id in (Id.Arith_PlusEqual, Id.Arith_MinusEqual,
                             Id.Arith_StarEqual, Id.Arith_SlashEqual):
                    new_val = self._ArithIntFloat(lhs_val, rhs_val, op)
                else:
                    new_val = self._ArithIntOnly(lhs_val, rhs_val, op)

                self.mem.SetNamed(lval, new_val, which_scopes)

            elif case(y_lvalue_e.Container):  # setvar d.key += 1
                lval = cast(y_lvalue.Container, UP_lval)

                obj = lval.obj
                UP_obj = obj

                lhs_val_ = None  # type: value_t
                # Similar to command_e.Mutation
                with tagswitch(obj) as case:
                    if case(value_e.List):
                        obj = cast(value.List, UP_obj)
                        index = val_ops.ToInt(lval.index,
                                              'List index should be Int',
                                              loc.Missing)
                        lhs_val_ = obj.items[index]

                    elif case(value_e.Dict):
                        obj = cast(value.Dict, UP_obj)
                        index = -1  # silence C++ warning
                        key = val_ops.ToStr(lval.index,
                                            'Dict index should be Str',
                                            loc.Missing)
                        lhs_val_ = obj.d[key]

                    else:
                        raise error.TypeErr(
                            obj, "obj[index] expected List or Dict",
                            loc.Missing)

                if op.id in (Id.Arith_PlusEqual, Id.Arith_MinusEqual,
                             Id.Arith_StarEqual, Id.Arith_SlashEqual):
                    new_val_ = self._ArithIntFloat(lhs_val_, rhs_val, op)
                else:
                    new_val_ = self._ArithIntOnly(lhs_val_, rhs_val, op)

                with tagswitch(obj) as case:
                    if case(value_e.List):
                        obj = cast(value.List, UP_obj)
                        assert index != -1, 'Should have been initialized'
                        obj.items[index] = new_val_

                    elif case(value_e.Dict):
                        obj = cast(value.Dict, UP_obj)
                        obj.d[key] = new_val_

            else:
                raise AssertionError()

    def _EvalLhsExpr(self, lhs):
        # type: (y_lhs_t) -> y_lvalue_t

        UP_lhs = lhs
        with tagswitch(lhs) as case:
            if case(y_lhs_e.Var):
                lhs = cast(NameTok, UP_lhs)
                return LeftName(lhs.var_name, lhs.left)

            elif case(y_lhs_e.Subscript):
                lhs = cast(Subscript, UP_lhs)
                # setvar mylist[0] = 42
                # setvar mydict['key'] = 42

                lval = self._EvalExpr(lhs.obj)
                index = self._EvalExpr(lhs.index)
                #log('index %s', index)
                return y_lvalue.Container(lval, index)

            elif case(y_lhs_e.Attribute):
                lhs = cast(Attribute, UP_lhs)
                assert lhs.op.id == Id.Expr_Dot

                # setvar mydict.key = 42
                lval = self._EvalExpr(lhs.obj)

                attr = value.Str(lhs.attr_name)
                return y_lvalue.Container(lval, attr)

            else:
                raise AssertionError()

    def EvalExpr(self, node, blame_loc):
        # type: (expr_t, loc_t) -> value_t
        """Public API for _EvalExpr to ensure command_sub_errexit"""
        self.mem.SetLocationForExpr(blame_loc)
        # Pure C++ won't need to catch exceptions
        with state.ctx_YshExpr(self.mutable_opts):
            val = self._EvalExpr(node)
        return val

    def EvalLhsExpr(self, lhs):
        # type: (y_lhs_t) -> y_lvalue_t
        """Public API for _EvalLhsExpr to ensure command_sub_errexit"""
        with state.ctx_YshExpr(self.mutable_opts):
            lval = self._EvalLhsExpr(lhs)
        return lval

    def EvalExprSub(self, part):
        # type: (word_part.ExprSub) -> part_value_t

        val = self.EvalExpr(part.child, part.left)

        with switch(part.left.id) as case:
            if case(Id.Left_DollarBracket):  # $[join(x)]
                s = val_ops.Stringify(val, loc.WordPart(part))
                return part_value.String(s, False, False)

            elif case(Id.Lit_AtLBracket):  # @[split(x)]
                strs = val_ops.ToShellArray(val,
                                            loc.WordPart(part),
                                            prefix='Expr splice ')
                return part_value.Array(strs)

            else:
                raise AssertionError(part.left)

    def PluginCall(self, func_val, pos_args):
        # type: (value.Func, List[value_t]) -> value_t
        """For renderPrompt()

        Similar to
        - WordEvaluator.EvalForPlugin(), which evaluates $PS1 outside main loop
        - ReadlineCallback.__call__, which executes shell outside main loop
        """
        with state.ctx_YshExpr(self.mutable_opts):
            with state.ctx_Registers(self.mem):  # to sandbox globals
                named_args = {}  # type: Dict[str, value_t]
                arg_list = ArgList.CreateNull()  # There's no call site
                rd = typed_args.Reader(pos_args, named_args, arg_list)

                try:
                    val = func_proc.CallUserFunc(func_val, rd, self.mem,
                                                 self.cmd_ev)
                except error.FatalRuntime as e:
                    val = value.Str('<Runtime error: %s>' %
                                    e.UserErrorString())

                except (IOError, OSError) as e:
                    val = value.Str('<I/O error: %s>' % pyutil.strerror(e))

                except KeyboardInterrupt:
                    val = value.Str('<Ctrl-C>')

        return val

    def CallConvertFunc(self, func_val, arg, convert_tok, call_loc):
        # type: (value_t, value_t, Token, loc_t) -> value_t
        """ For Eggex captures """
        with state.ctx_YshExpr(self.mutable_opts):
            pos_args = [arg]
            named_args = {}  # type: Dict[str, value_t]
            arg_list = ArgList.CreateNull()  # There's no call site
            rd = typed_args.Reader(pos_args, named_args, arg_list)
            rd.SetFallbackLocation(convert_tok)
            try:
                val = self._CallFunc(func_val, rd)
            except error.FatalRuntime as e:
                func_name = lexer.TokenVal(convert_tok)
                self.errfmt.Print_(
                    'Fatal error calling Eggex conversion func %r from this Match accessor'
                    % func_name, call_loc)
                print_stderr('')
                raise

        return val

    def SpliceValue(self, val, part):
        # type: (value_t, word_part.Splice) -> List[str]
        """ write -- @myvar """
        return val_ops.ToShellArray(val, loc.WordPart(part), prefix='Splice ')

    def _EvalConst(self, node):
        # type: (expr.Const) -> value_t
        return node.val

    def _EvalUnary(self, node):
        # type: (expr.Unary) -> value_t

        val = self._EvalExpr(node.child)

        with switch(node.op.id) as case:
            if case(Id.Arith_Minus):
                c1, i1, f1 = _ConvertToNumber(val)
                if c1 == coerced_e.Int:
                    return value.Int(mops.Negate(i1))
                if c1 == coerced_e.Float:
                    return value.Float(-f1)
                raise error.TypeErr(val, 'Negation expected Int or Float',
                                    node.op)

            elif case(Id.Arith_Tilde):
                i = _ConvertToInt(val, '~ expected Int', node.op)
                return value.Int(mops.BitNot(i))

            elif case(Id.Expr_Not):
                b = val_ops.ToBool(val)
                return value.Bool(False if b else True)

            # &s  &a[0]  &d.key  &d.nested.other
            elif case(Id.Arith_Amp):
                # Only 3 possibilities:
                # - expr.Var
                # - expr.Attribute with `.` operator (d.key)
                # - expr.SubScript
                #
                # See _EvalLhsExpr, which gives you y_lvalue

                # TODO: &x, &a[0], &d.key, creates a value.Place?
                # If it's Attribute or SubScript, you don't evaluate them.
                # y_lvalue_t -> place_t

                raise NotImplementedError(node.op)

            else:
                raise AssertionError(node.op)

        raise AssertionError('for C++ compiler')

    def _ArithIntFloat(self, left, right, op):
        # type: (value_t, value_t, Token) -> value_t
        """
        Note: may be replaced with arithmetic on tagged integers, e.g. 60 bit
        with overflow detection
        """
        c, i1, i2, f1, f2 = _ConvertForBinaryOp(left, right)

        op_id = op.id

        if c == coerced_e.Int:
            with switch(op_id) as case:
                if case(Id.Arith_Plus, Id.Arith_PlusEqual):
                    return value.Int(mops.Add(i1, i2))
                elif case(Id.Arith_Minus, Id.Arith_MinusEqual):
                    return value.Int(mops.Sub(i1, i2))
                elif case(Id.Arith_Star, Id.Arith_StarEqual):
                    return value.Int(mops.Mul(i1, i2))
                elif case(Id.Arith_Slash, Id.Arith_SlashEqual):
                    if mops.Equal(i2, mops.ZERO):
                        raise error.Expr('Divide by zero', op)
                    return value.Float(mops.ToFloat(i1) / mops.ToFloat(i2))
                else:
                    raise AssertionError()

        elif c == coerced_e.Float:
            with switch(op_id) as case:
                if case(Id.Arith_Plus, Id.Arith_PlusEqual):
                    return value.Float(f1 + f2)
                elif case(Id.Arith_Minus, Id.Arith_MinusEqual):
                    return value.Float(f1 - f2)
                elif case(Id.Arith_Star, Id.Arith_StarEqual):
                    return value.Float(f1 * f2)
                elif case(Id.Arith_Slash, Id.Arith_SlashEqual):
                    if f2 == 0.0:
                        raise error.Expr('Divide by zero', op)
                    return value.Float(f1 / f2)
                else:
                    raise AssertionError()

        else:
            raise error.TypeErrVerbose(
                'Binary operator expected numbers, got %s and %s' %
                (ui.ValType(left), ui.ValType(right)), op)

    def _ArithIntOnly(self, left, right, op):
        # type: (value_t, value_t, Token) -> value_t

        i1 = _ConvertToInt(left, 'Left operand should be Int', op)
        i2 = _ConvertToInt(right, 'Right operand should be Int', op)

        with switch(op.id) as case:

            # a % b   setvar a %= b
            if case(Id.Arith_Percent, Id.Arith_PercentEqual):
                if mops.Equal(i2, mops.ZERO):
                    raise error.Expr('Divide by zero', op)
                if mops.Greater(mops.ZERO, i2):
                    # Disallow this to remove confusion between modulus and remainder
                    raise error.Expr("Divisor can't be negative", op)

                return value.Int(num.IntRemainder(i1, i2))

            # a // b   setvar a //= b
            elif case(Id.Expr_DSlash, Id.Expr_DSlashEqual):
                if mops.Equal(i2, mops.ZERO):
                    raise error.Expr('Divide by zero', op)
                return value.Int(num.IntDivide(i1, i2))

            # a ** b   setvar a **= b (ysh only)
            elif case(Id.Arith_DStar, Id.Expr_DStarEqual):
                # Same as sh_expr_eval.py
                if mops.Greater(mops.ZERO, i2):
                    raise error.Expr("Exponent can't be a negative number", op)
                return value.Int(num.Exponent(i1, i2))

            # Bitwise
            elif case(Id.Arith_Amp, Id.Arith_AmpEqual):  # &
                return value.Int(mops.BitAnd(i1, i2))

            elif case(Id.Arith_Pipe, Id.Arith_PipeEqual):  # |
                return value.Int(mops.BitOr(i1, i2))

            elif case(Id.Arith_Caret, Id.Arith_CaretEqual):  # ^
                return value.Int(mops.BitXor(i1, i2))

            elif case(Id.Arith_DGreat, Id.Arith_DGreatEqual):  # >>
                return value.Int(mops.RShift(i1, i2))

            elif case(Id.Arith_DLess, Id.Arith_DLessEqual):  # <<
                return value.Int(mops.LShift(i1, i2))

            else:
                raise AssertionError(op.id)

    def _Concat(self, left, right, op):
        # type: (value_t, value_t, Token) -> value_t
        UP_left = left
        UP_right = right

        if left.tag() == value_e.Str and right.tag() == value_e.Str:
            left = cast(value.Str, UP_left)
            right = cast(value.Str, UP_right)

            return value.Str(left.s + right.s)

        elif left.tag() == value_e.List and right.tag() == value_e.List:
            left = cast(value.List, UP_left)
            right = cast(value.List, UP_right)

            c = list(left.items)  # mycpp rewrite of L1 + L2
            c.extend(right.items)
            return value.List(c)

        else:
            raise error.TypeErrVerbose(
                'Expected Str ++ Str or List ++ List, got %s ++ %s' %
                (ui.ValType(left), ui.ValType(right)), op)

    def _EvalBinary(self, node):
        # type: (expr.Binary) -> value_t

        left = self._EvalExpr(node.left)

        # Logical and/or lazily evaluate
        with switch(node.op.id) as case:
            if case(Id.Expr_And):
                if val_ops.ToBool(left):  # no errors
                    return self._EvalExpr(node.right)
                else:
                    return left

            elif case(Id.Expr_Or):
                if val_ops.ToBool(left):
                    return left
                else:
                    return self._EvalExpr(node.right)

        # These operators all eagerly evaluate
        right = self._EvalExpr(node.right)

        with switch(node.op.id) as case:
            if case(Id.Arith_DPlus):  # a ++ b to concat Str or List
                return self._Concat(left, right, node.op)

            elif case(Id.Arith_Plus, Id.Arith_Minus, Id.Arith_Star,
                      Id.Arith_Slash):
                return self._ArithIntFloat(left, right, node.op)

            else:
                return self._ArithIntOnly(left, right, node.op)

    def _CompareNumeric(self, left, right, op):
        # type: (value_t, value_t, Token) -> bool
        c, i1, i2, f1, f2 = _ConvertForBinaryOp(left, right)

        if c == coerced_e.Int:
            with switch(op.id) as case:
                if case(Id.Arith_Less):
                    return mops.Greater(i2, i1)
                elif case(Id.Arith_Great):
                    return mops.Greater(i1, i2)
                elif case(Id.Arith_LessEqual):
                    return mops.Greater(i2, i1) or mops.Equal(i1, i2)
                elif case(Id.Arith_GreatEqual):
                    return mops.Greater(i1, i2) or mops.Equal(i1, i2)
                else:
                    raise AssertionError()

        elif c == coerced_e.Float:
            with switch(op.id) as case:
                if case(Id.Arith_Less):
                    return f1 < f2
                elif case(Id.Arith_Great):
                    return f1 > f2
                elif case(Id.Arith_LessEqual):
                    return f1 <= f2
                elif case(Id.Arith_GreatEqual):
                    return f1 >= f2
                else:
                    raise AssertionError()

        else:
            raise error.TypeErrVerbose(
                'Comparison operator expected numbers, got %s and %s' %
                (ui.ValType(left), ui.ValType(right)), op)

    def _EvalCompare(self, node):
        # type: (expr.Compare) -> value_t

        left = self._EvalExpr(node.left)
        result = True  # Implicit and
        for i, op in enumerate(node.ops):
            right_expr = node.comparators[i]

            right = self._EvalExpr(right_expr)

            if op.id in (Id.Arith_Less, Id.Arith_Great, Id.Arith_LessEqual,
                         Id.Arith_GreatEqual):
                result = self._CompareNumeric(left, right, op)

            elif op.id == Id.Expr_TEqual:
                if left.tag() != right.tag():
                    result = False
                else:
                    result = val_ops.ExactlyEqual(left, right, op)
            elif op.id == Id.Expr_NotDEqual:
                if left.tag() != right.tag():
                    result = True
                else:
                    result = not val_ops.ExactlyEqual(left, right, op)

            elif op.id == Id.Expr_In:
                result = val_ops.Contains(left, right)
            elif op.id == Id.Node_NotIn:
                result = not val_ops.Contains(left, right)

            elif op.id == Id.Expr_Is:
                if left.tag() != right.tag():
                    raise error.TypeErrVerbose('Mismatched types', op)
                result = left is right

            elif op.id == Id.Node_IsNot:
                if left.tag() != right.tag():
                    raise error.TypeErrVerbose('Mismatched types', op)
                result = left is not right

            elif op.id == Id.Expr_DTilde:
                # no extglob in Oil language; use eggex
                if left.tag() != value_e.Str:
                    raise error.TypeErrVerbose('LHS must be Str', op)

                if right.tag() != value_e.Str:
                    raise error.TypeErrVerbose('RHS must be Str', op)

                UP_left = left
                UP_right = right
                left = cast(value.Str, UP_left)
                right = cast(value.Str, UP_right)
                return value.Bool(libc.fnmatch(right.s, left.s))

            elif op.id == Id.Expr_NotDTilde:
                if left.tag() != value_e.Str:
                    raise error.TypeErrVerbose('LHS must be Str', op)

                if right.tag() != value_e.Str:
                    raise error.TypeErrVerbose('RHS must be Str', op)

                UP_left = left
                UP_right = right
                left = cast(value.Str, UP_left)
                right = cast(value.Str, UP_right)
                return value.Bool(not libc.fnmatch(right.s, left.s))

            elif op.id == Id.Expr_TildeDEqual:
                # Approximate equality
                UP_left = left
                if left.tag() != value_e.Str:
                    e_die('~== expects a string on the left', op)

                left = cast(value.Str, UP_left)
                left2 = left.s.strip()

                UP_right = right
                with tagswitch(right) as case:
                    if case(value_e.Str):
                        right = cast(value.Str, UP_right)
                        return value.Bool(left2 == right.s)

                    elif case(value_e.Bool):
                        right = cast(value.Bool, UP_right)
                        left2 = left2.lower()
                        lb = False
                        if left2 == 'true':
                            lb = True
                        elif left2 == 'false':
                            lb = False
                        else:
                            return value.Bool(False)

                        #log('left %r left2 %r', left, left2)
                        return value.Bool(lb == right.b)

                    elif case(value_e.Int):
                        right = cast(value.Int, UP_right)
                        if not left2.isdigit():
                            return value.Bool(False)

                        eq = mops.Equal(mops.FromStr(left2), right.i)
                        return value.Bool(eq)

                e_die('~== expects Str, Int, or Bool on the right', op)

            else:
                try:
                    if op.id == Id.Arith_Tilde:
                        result = val_ops.MatchRegex(left, right, self.mem)

                    elif op.id == Id.Expr_NotTilde:
                        # don't pass self.mem to not set a match
                        result = not val_ops.MatchRegex(left, right, None)

                    else:
                        raise AssertionError(op)
                except ValueError as e:
                    # Status 2 indicates a regex parse error, as with [[ in OSH
                    e_die_status(2, e.message, op)

            if not result:
                return value.Bool(result)

            left = right

        return value.Bool(result)

    def _CallFunc(self, to_call, rd):
        # type: (value_t, typed_args.Reader) -> value_t

        # Now apply args to either builtin or user-defined function
        UP_to_call = to_call
        with tagswitch(to_call) as case:
            if case(value_e.Func):
                to_call = cast(value.Func, UP_to_call)

                return func_proc.CallUserFunc(to_call, rd, self.mem,
                                              self.cmd_ev)

            elif case(value_e.BuiltinFunc):
                to_call = cast(value.BuiltinFunc, UP_to_call)

                # C++ cast to work around ASDL 'any'
                f = cast(vm._Callable, to_call.callable)
                return f.Call(rd)
            else:
                raise AssertionError("Shouldn't have been bound")

    def _EvalFuncCall(self, node):
        # type: (expr.FuncCall) -> value_t

        func = self._EvalExpr(node.func)
        UP_func = func

        # The () operator has a 2x2 matrix of
        #   (free, bound) x (builtin, user-defined)

        # Eval args first
        with tagswitch(func) as case:
            if case(value_e.Func, value_e.BuiltinFunc):
                to_call = func
                pos_args, named_args = func_proc._EvalArgList(self, node.args)
                rd = typed_args.Reader(pos_args, named_args, node.args)

            elif case(value_e.BoundFunc):
                func = cast(value.BoundFunc, UP_func)

                to_call = func.func
                pos_args, named_args = func_proc._EvalArgList(self,
                                                              node.args,
                                                              me=func.me)
                rd = typed_args.Reader(pos_args,
                                       named_args,
                                       node.args,
                                       is_bound=True)
            else:
                raise error.TypeErr(func, 'Expected a function or method',
                                    node.args.left)

        return self._CallFunc(to_call, rd)

    def _EvalSubscript(self, node):
        # type: (Subscript) -> value_t

        obj = self._EvalExpr(node.obj)
        index = self._EvalExpr(node.index)

        UP_obj = obj
        UP_index = index

        with tagswitch(obj) as case:
            if case(value_e.Str):
                # Note: s[i] and s[i:j] are like Go, on bytes.  We may provide
                # s->numBytes(), s->countRunes(), and iteration over runes.
                obj = cast(value.Str, UP_obj)
                with tagswitch(index) as case2:
                    if case2(value_e.Slice):
                        index = cast(value.Slice, UP_index)

                        lower = index.lower.i if index.lower else 0
                        upper = index.upper.i if index.upper else len(obj.s)
                        return value.Str(obj.s[lower:upper])

                    elif case2(value_e.Int):
                        index = cast(value.Int, UP_index)
                        i = mops.BigTruncate(index.i)
                        try:
                            return value.Str(obj.s[i])
                        except IndexError:
                            # TODO: expr.Subscript has no error location
                            raise error.Expr('index out of range', loc.Missing)

                    else:
                        raise error.TypeErr(index,
                                            'Str index expected Int or Slice',
                                            loc.Missing)

            elif case(value_e.List):
                obj = cast(value.List, UP_obj)
                with tagswitch(index) as case2:
                    if case2(value_e.Slice):
                        index = cast(value.Slice, UP_index)

                        lower = index.lower.i if index.lower else 0
                        upper = index.upper.i if index.upper else len(
                            obj.items)
                        return value.List(obj.items[lower:upper])

                    elif case2(value_e.Int):
                        index = cast(value.Int, UP_index)
                        i = mops.BigTruncate(index.i)
                        try:
                            return obj.items[i]
                        except IndexError:
                            # TODO: expr.Subscript has no error location
                            raise error.Expr('index out of range', loc.Missing)

                    else:
                        raise error.TypeErr(
                            index, 'List index expected Int or Slice',
                            loc.Missing)

            elif case(value_e.Dict):
                obj = cast(value.Dict, UP_obj)
                if index.tag() != value_e.Str:
                    raise error.TypeErr(index, 'Dict index expected Str',
                                        loc.Missing)

                index = cast(value.Str, UP_index)
                try:
                    return obj.d[index.s]
                except KeyError:
                    # TODO: expr.Subscript has no error location
                    raise error.Expr('Dict entry %r not found' % index.s,
                                     loc.Missing)

        raise error.TypeErr(obj, 'Subscript expected Str, List, or Dict',
                            loc.Missing)

    def _EvalAttribute(self, node):
        # type: (Attribute) -> value_t

        o = self._EvalExpr(node.obj)
        UP_o = o

        with switch(node.op.id) as case:
            # Right now => is a synonym for ->
            # Later we may enforce that => is pure, and -> is for mutation and
            # I/O.
            if case(Id.Expr_RArrow, Id.Expr_RDArrow):
                name = node.attr_name
                # Look up builtin methods
                type_methods = self.methods.get(o.tag())
                vm_callable = (type_methods.get(name)
                               if type_methods is not None else None)
                if vm_callable:
                    func_val = value.BuiltinFunc(vm_callable)
                    return value.BoundFunc(o, func_val)

                # If the operator is ->, fail because we don't have any
                # user-defined methods
                if node.op.id == Id.Expr_RArrow:
                    raise error.TypeErrVerbose(
                        'Method %r does not exist on type %s' %
                        (name, ui.ValType(o)), node.attr)

                # Operator is =>, so try function chaining.

                # Instead of str(f()) => upper()
                #         or str(f()).upper() as in Pythohn
                #
                # It's more natural to write
                #     f() => str() => upper()

                # Could improve error message: may give "Undefined variable"
                val = self._LookupVar(name, node.attr)

                with tagswitch(val) as case2:
                    if case2(value_e.Func, value_e.BuiltinFunc):
                        return value.BoundFunc(o, val)
                    else:
                        raise error.TypeErr(
                            val, 'Fat arrow => expects method or function',
                            node.attr)

            elif case(Id.Expr_Dot):  # d.key is like d['key']
                name = node.attr_name
                with tagswitch(o) as case2:
                    if case2(value_e.Dict):
                        o = cast(value.Dict, UP_o)
                        try:
                            result = o.d[name]
                        except KeyError:
                            raise error.Expr('Dict entry %r not found' % name,
                                             node.op)

                    else:
                        raise error.TypeErr(o, 'Dot operator expected Dict',
                                            node.op)

                return result

            else:
                raise AssertionError(node.op)

    def _EvalExpr(self, node):
        # type: (expr_t) -> value_t
        """Turn an expression into a value."""
        if 0:
            print('_EvalExpr()')
            node.PrettyPrint()
            print('')

        UP_node = node
        with tagswitch(node) as case:
            if case(expr_e.Const):
                node = cast(expr.Const, UP_node)
                return self._EvalConst(node)

            elif case(expr_e.Var):
                node = cast(expr.Var, UP_node)
                return self._LookupVar(node.name, node.left)

            elif case(expr_e.Place):
                node = cast(expr.Place, UP_node)
                frame = self.mem.TopNamespace()
                return value.Place(LeftName(node.var_name, node.blame_tok),
                                   frame)

            elif case(expr_e.CommandSub):
                node = cast(CommandSub, UP_node)

                id_ = node.left_token.id
                if id_ == Id.Left_CaretParen:  # ^(echo block literal)
                    # TODO: Propgate location info?
                    return value.Command(node.child)
                else:
                    stdout_str = self.shell_ex.RunCommandSub(node)
                    if id_ == Id.Left_AtParen:  # @(seq 3)
                        # TODO: Should use J8 lines
                        strs = self.splitter.SplitForWordEval(stdout_str)
                        items = [value.Str(s)
                                 for s in strs]  # type: List[value_t]
                        return value.List(items)
                    else:
                        return value.Str(stdout_str)

            elif case(expr_e.ShArrayLiteral):  # var x = :| foo *.py |
                node = cast(ShArrayLiteral, UP_node)
                words = braces.BraceExpandWords(node.words)
                strs = self.word_ev.EvalWordSequence(words)
                #log('ARRAY LITERAL EVALUATED TO -> %s', strs)
                #return value.BashArray(strs)

                # It's equivalent to ['foo', 'bar']
                items = [value.Str(s) for s in strs]
                return value.List(items)

            elif case(expr_e.DoubleQuoted):
                node = cast(DoubleQuoted, UP_node)
                # In an ideal world, YSH would *statically* disallow:
                #
                # - "$@" and "${array[@]}"
                # - backticks like `echo hi`
                # - $(( 1+2 )) and $[] -- although useful for refactoring
                #   - not sure: ${x%%} -- could disallow this
                #     - these enters the ArgDQ state: "${a:-foo bar}" ?
                #
                # But that would complicate the parser/evaluator.  So just rely
                # on runtime strict_array to disallow the bad parts.
                return value.Str(self.word_ev.EvalDoubleQuotedToString(node))

            elif case(expr_e.SingleQuoted):
                node = cast(SingleQuoted, UP_node)
                return value.Str(word_compile.EvalSingleQuoted(node))

            elif case(expr_e.BracedVarSub):
                node = cast(BracedVarSub, UP_node)
                return value.Str(self.word_ev.EvalBracedVarSubToString(node))

            elif case(expr_e.SimpleVarSub):
                node = cast(NameTok, UP_node)
                return value.Str(self.word_ev.EvalSimpleVarSubToString(node))

            elif case(expr_e.Unary):
                node = cast(expr.Unary, UP_node)
                return self._EvalUnary(node)

            elif case(expr_e.Binary):
                node = cast(expr.Binary, UP_node)
                return self._EvalBinary(node)

            elif case(expr_e.Slice):  # a[:0]
                node = cast(expr.Slice, UP_node)

                lower = None  # type: Optional[IntBox]
                upper = None  # type: Optional[IntBox]

                if node.lower:
                    msg = 'Slice begin should be Int'
                    i = val_ops.ToInt(self._EvalExpr(node.lower), msg,
                                      loc.Missing)
                    lower = IntBox(i)

                if node.upper:
                    msg = 'Slice end should be Int'
                    i = val_ops.ToInt(self._EvalExpr(node.upper), msg,
                                      loc.Missing)
                    upper = IntBox(i)

                return value.Slice(lower, upper)

            elif case(expr_e.Range):
                node = cast(expr.Range, UP_node)

                assert node.lower is not None
                assert node.upper is not None

                msg = 'Range begin should be Int'
                i = val_ops.ToInt(self._EvalExpr(node.lower), msg, loc.Missing)

                msg = 'Range end should be Int'
                j = val_ops.ToInt(self._EvalExpr(node.upper), msg, loc.Missing)

                return value.Range(i, j)

            elif case(expr_e.Compare):
                node = cast(expr.Compare, UP_node)
                return self._EvalCompare(node)

            elif case(expr_e.IfExp):
                node = cast(expr.IfExp, UP_node)
                b = val_ops.ToBool(self._EvalExpr(node.test))
                if b:
                    return self._EvalExpr(node.body)
                else:
                    return self._EvalExpr(node.orelse)

            elif case(expr_e.List):
                node = cast(expr.List, UP_node)
                items = [self._EvalExpr(e) for e in node.elts]
                return value.List(items)

            elif case(expr_e.Tuple):
                node = cast(expr.Tuple, UP_node)
                # YSH language: Tuple syntax evaluates to LIST !
                items = [self._EvalExpr(e) for e in node.elts]
                return value.List(items)

            elif case(expr_e.Dict):
                node = cast(expr.Dict, UP_node)

                kvals = [self._EvalExpr(e) for e in node.keys]
                values = []  # type: List[value_t]

                for i, value_expr in enumerate(node.values):
                    if value_expr.tag() == expr_e.Implicit:  # {key}
                        # Enforced by parser.  Key is expr.Const
                        assert kvals[i].tag() == value_e.Str, kvals[i]
                        key = cast(value.Str, kvals[i])
                        v = self._LookupVar(key.s, loc.Missing)
                    else:
                        v = self._EvalExpr(value_expr)

                    values.append(v)

                d = NewDict()  # type: Dict[str, value_t]
                for i, kval in enumerate(kvals):
                    k = val_ops.ToStr(kval, 'Dict keys must be strings',
                                      loc.Missing)
                    d[k] = values[i]

                return value.Dict(d)

            elif case(expr_e.ListComp):
                e_die_status(
                    2, 'List comprehension reserved but not implemented')

            elif case(expr_e.GeneratorExp):
                e_die_status(
                    2, 'Generator expression reserved but not implemented')

            elif case(expr_e.Literal):  # ^[1 + 2]
                node = cast(expr.Literal, UP_node)
                return value.Expr(node.inner)

            elif case(expr_e.Lambda):  # |x| x+1 syntax is reserved
                # TODO: Location information for |, or func
                # Note: anonymous functions also evaluate to a Lambda, but they shouldn't
                e_die_status(2, 'Lambda reserved but not implemented')

            elif case(expr_e.FuncCall):
                node = cast(expr.FuncCall, UP_node)
                return self._EvalFuncCall(node)

            elif case(expr_e.Subscript):
                node = cast(Subscript, UP_node)
                return self._EvalSubscript(node)

            elif case(expr_e.Attribute):  # obj->method or mydict.key
                node = cast(Attribute, UP_node)
                return self._EvalAttribute(node)

            elif case(expr_e.Eggex):
                node = cast(Eggex, UP_node)
                return self.EvalEggex(node)

            else:
                raise NotImplementedError(node.__class__.__name__)

    def EvalEggex(self, node):
        # type: (Eggex) -> value.Eggex

        # Splice, check flags consistency, and accumulate convert_funcs indexed
        # by capture group
        ev = EggexEvaluator(self.mem, node.canonical_flags)
        spliced = ev.EvalE(node.regex)

        # as_ere and capture_names filled by ~ operator or Str method
        return value.Eggex(spliced, node.canonical_flags, ev.convert_funcs,
                           ev.convert_toks, None, [])


class EggexEvaluator(object):

    def __init__(self, mem, canonical_flags):
        # type: (state.Mem, str) -> None
        self.mem = mem
        self.canonical_flags = canonical_flags
        self.convert_funcs = []  # type: List[Optional[value_t]]
        self.convert_toks = []  # type: List[Optional[Token]]

    def _LookupVar(self, name, var_loc):
        # type: (str, loc_t) -> value_t
        """
        Duplicated from ExprEvaluator
        """
        return LookupVar(self.mem, name, scope_e.LocalOrGlobal, var_loc)

    def _EvalClassLiteralTerm(self, term, out):
        # type: (class_literal_term_t, List[char_class_term_t]) -> None
        UP_term = term

        # These 2 vars will be initialized if we don't return early
        s = None  # type: str
        char_code_tok = None  # type: Token

        with tagswitch(term) as case:

            if case(class_literal_term_e.CharLiteral):
                term = cast(class_literal_term.CharLiteral, UP_term)

                # What about \0?
                # At runtime, ERE should disallow it.  But we can also disallow it here.
                out.append(word_compile.EvalCharLiteralForRegex(term.tok))
                return

            elif case(class_literal_term_e.Range):
                term = cast(class_literal_term.Range, UP_term)

                cp_start = word_compile.EvalCharLiteralForRegex(term.start)
                cp_end = word_compile.EvalCharLiteralForRegex(term.end)
                out.append(char_class_term.Range(cp_start, cp_end))
                return

            elif case(class_literal_term_e.PosixClass):
                term = cast(PosixClass, UP_term)
                out.append(term)
                return

            elif case(class_literal_term_e.PerlClass):
                term = cast(PerlClass, UP_term)
                out.append(term)
                return

            elif case(class_literal_term_e.SingleQuoted):
                term = cast(SingleQuoted, UP_term)

                s = word_compile.EvalSingleQuoted(term)
                char_code_tok = term.left

            elif case(class_literal_term_e.Splice):
                term = cast(class_literal_term.Splice, UP_term)

                val = self._LookupVar(term.var_name, term.name)
                s = val_ops.ToStr(val, 'Eggex char class splice expected Str',
                                  term.name)
                char_code_tok = term.name

        assert s is not None, term
        for ch in s:
            char_int = ord(ch)
            if char_int >= 128:
                # / [ '\x7f\xff' ] / is better written as / [ \x7f \xff ] /
                e_die(
                    "Use unquoted char literal for byte %d, which is >= 128"
                    " (avoid confusing a set of bytes with a sequence)" %
                    char_int, char_code_tok)
            out.append(CharCode(char_int, False, char_code_tok))

    def EvalE(self, node):
        # type: (re_t) -> re_t
        """Resolve references and eval constants in an Eggex

        Rules:
          Splice => re_t   # like Hex and @const in  / Hex '.' @const /
          Speck/Token (syntax) => Primitive (logical)
          Chars and Strings => LiteralChars
        """
        UP_node = node

        with tagswitch(node) as case:
            if case(re_e.Seq):
                node = cast(re.Seq, UP_node)
                new_children = [self.EvalE(child) for child in node.children]
                return re.Seq(new_children)

            elif case(re_e.Alt):
                node = cast(re.Alt, UP_node)
                new_children = [self.EvalE(child) for child in node.children]
                return re.Alt(new_children)

            elif case(re_e.Repeat):
                node = cast(re.Repeat, UP_node)
                return re.Repeat(self.EvalE(node.child), node.op)

            elif case(re_e.Group):
                node = cast(re.Group, UP_node)

                # placeholder for non-capturing group
                self.convert_funcs.append(None)
                self.convert_toks.append(None)
                return re.Group(self.EvalE(node.child))

            elif case(re_e.Capture):  # Identical to Group
                node = cast(re.Capture, UP_node)
                convert_func = None  # type: Optional[value_t]
                convert_tok = None  # type: Optional[Token]
                if node.func_name:
                    func_name = lexer.TokenVal(node.func_name)
                    func_val = self.mem.GetValue(func_name)
                    with tagswitch(func_val) as case:
                        if case(value_e.Func, value_e.BuiltinFunc):
                            convert_func = func_val
                            convert_tok = node.func_name
                        else:
                            raise error.TypeErr(
                                func_val,
                                "Expected %r to be a func" % func_name,
                                node.func_name)

                self.convert_funcs.append(convert_func)
                self.convert_toks.append(convert_tok)
                return re.Capture(self.EvalE(node.child), node.name,
                                  node.func_name)

            elif case(re_e.CharClassLiteral):
                node = cast(re.CharClassLiteral, UP_node)

                new_terms = []  # type: List[char_class_term_t]
                for t in node.terms:
                    # can get multiple char_class_term.CharCode for a
                    # class_literal_term_t
                    self._EvalClassLiteralTerm(t, new_terms)
                return re.CharClass(node.negated, new_terms)

            elif case(re_e.Token):
                node = cast(Token, UP_node)

                id_ = node.id

                # Must be Id.Char_{OneChar,Hex,Unicode4,Unicode8}
                kind = consts.GetKind(id_)
                assert kind == Kind.Char, id_
                s = word_compile.EvalCStringToken(node)
                return re.LiteralChars(s, node)

            elif case(re_e.SingleQuoted):
                node = cast(SingleQuoted, UP_node)

                s = word_compile.EvalSingleQuoted(node)
                return re.LiteralChars(s, node.left)

            elif case(re_e.Splice):
                node = cast(re.Splice, UP_node)

                val = self._LookupVar(node.var_name, node.name)
                UP_val = val
                with tagswitch(val) as case:
                    if case(value_e.Str):
                        val = cast(value.Str, UP_val)
                        to_splice = re.LiteralChars(val.s,
                                                    node.name)  # type: re_t

                    elif case(value_e.Eggex):
                        val = cast(value.Eggex, UP_val)

                        # Splicing means we get the conversion funcs too.
                        self.convert_funcs.extend(val.convert_funcs)
                        self.convert_toks.extend(val.convert_toks)

                        # Splicing requires flags to match.  This check is
                        # transitive.
                        to_splice = val.spliced

                        if val.canonical_flags != self.canonical_flags:
                            e_die(
                                "Expected eggex flags %r, but got %r" %
                                (self.canonical_flags, val.canonical_flags),
                                node.name)

                    else:
                        raise error.TypeErr(
                            val, 'Eggex splice expected Str or Eggex',
                            node.name)
                return to_splice

            else:
                # These are evaluated at translation time

                # case(re_e.Primitive)
                # case(re_e.PosixClass)
                # case(re_e.PerlClass)
                return node


# vim: sw=4
