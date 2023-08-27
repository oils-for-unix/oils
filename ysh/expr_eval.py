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
    word_part,
    SingleQuoted,
    DoubleQuoted,
    BracedVarSub,
    SimpleVarSub,
    ShArrayLiteral,
    CommandSub,
    expr,
    expr_e,
    expr_t,
    place_expr,
    place_expr_e,
    place_expr_t,
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
)
from _devbuild.gen.runtime_asdl import (
    coerced_e,
    coerced_t,
    scope_e,
    scope_t,
    part_value,
    part_value_t,
    lvalue,
    lvalue_e,
    lvalue_t,
    value,
    value_e,
    value_t,
    IntBox,
)
from core import error
from core.error import e_die, e_die_status
from core import state
from core import ui
from core import vm
from frontend import consts
from frontend import match
from frontend import location
from osh import braces
from osh import word_compile
from mycpp import mylib
from mycpp.mylib import log, NewDict, switch, tagswitch
from ysh import cpython
from ysh import val_ops

import libc

from typing import cast, Any, Optional, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import ArgList
    from core import ui
    from core.state import Mem
    from osh.word_eval import AbstractWordEvaluator
    from osh import split

_ = log


def LookupVar(mem, var_name, which_scopes, var_loc):
    # type: (Mem, str, scope_t, loc_t) -> value_t

    # Lookup WITHOUT dynamic scope.
    val = mem.GetValue(var_name, which_scopes=which_scopes)
    if val.tag() == value_e.Undef:
        # TODO: Location info
        e_die('Undefined variable %r' % var_name, var_loc)

    return val


class ExprEvaluator(object):
    """Shared between arith and bool evaluators.

    They both:

    1. Convert strings to integers, respecting shopt -s strict_arith.
    2. Look up variables and evaluate words.
    """

    def __init__(
            self,
            mem,  # type: Mem
            mutable_opts,  # type: state.MutableOpts
            methods,  # type: Dict[int, Dict[str, vm._Callable]]
            splitter,  # type: split.SplitContext
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.shell_ex = None  # type: vm._Executor
        self.word_ev = None  # type: AbstractWordEvaluator

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

    def EvalPlusEquals(self, lval, rhs_val, op):
        # type: (lvalue_t, value_t, Token) -> value_t
        """Called by CommandEvaluator."""

        # TODO: Handle other augmented assignment
        #
        # It might be nice to do auto d[x] += 1 too

        UP_lval = lval
        with tagswitch(lval) as case:
            if case(lvalue_e.Named):
                lval = cast(lvalue.Named, UP_lval)
                lhs_val = self._LookupVar(lval.name, lval.blame_loc)
                return self._ArithNumeric(lhs_val, rhs_val, op)
            else:
                # TODO: Handle other lvalue, like sh_expr_eval.OldValue() But
                # this is for YSH values, not value.BashArray etc.
                raise AssertionError()

    def EvalLHS(self, node):
        # type: (expr_t) -> lvalue_t
        if 0:
            print('EvalLHS()')
            node.PrettyPrint()
            print('')

        UP_node = node
        with tagswitch(node) as case:
            if case(expr_e.Var):
                node = cast(expr.Var, UP_node)
                return location.LName(node.name.tval)
            else:
                # TODO:
                # subscripts, tuple unpacking, starred expressions, etc.
                raise NotImplementedError(node.__class__.__name__)

    def _EvalPlaceExpr(self, place):
        # type: (place_expr_t) -> lvalue_t

        UP_place = place
        with tagswitch(place) as case:
            if case(place_expr_e.Var):
                place = cast(place_expr.Var, UP_place)

                return location.LName(place.name.tval)

            elif case(place_expr_e.Subscript):
                place = cast(Subscript, UP_place)
                # setvar mylist[0] = 42
                # setvar mydict['key'] = 42

                lval = self._EvalExpr(place.obj)
                index = self._EvalExpr(place.index)
                #log('index %s', index)
                return lvalue.ObjIndex(lval, index)

            elif case(place_expr_e.Attribute):
                place = cast(Attribute, UP_place)
                # setvar mydict.key = 42

                lval = self._EvalExpr(place.obj)
                if place.op.id == Id.Expr_Dot:
                    attr = value.Str(place.attr.tval)
                    return lvalue.ObjIndex(lval, attr)
                else:
                    raise AssertionError()

            else:
                raise NotImplementedError(place)

        raise AssertionError()  # silence C++ compiler

    def EvalPlaceExpr(self, place):
        # type: (place_expr_t) -> lvalue_t
        """Public API for _EvalPlaceExpr to ensure command_sub_errexit"""
        if mylib.PYTHON:

            blame_loc = loc.Missing
            try:
                with state.ctx_OilExpr(self.mutable_opts):
                    lval = self._EvalPlaceExpr(place)
                return lval

            # Catch PYTHON exceptions.  Remove after function calls are statically typed
            except TypeError as e:
                raise error.Expr('Type error in place expression: %s' % str(e),
                                 blame_loc)
            except (AttributeError, ValueError) as e:
                raise error.Expr('Place expression eval error: %s' % str(e),
                                 blame_loc)
        else:
            # Pure C++ won't need to catch exceptions
            with state.ctx_OilExpr(self.mutable_opts):
                lval = self._EvalPlaceExpr(place)
            return lval

    def EvalExprSub(self, part):
        # type: (word_part.ExprSub) -> part_value_t

        val = self.EvalExpr(part.child, part.left)

        if part.left.id == Id.Left_DollarBracket:  # $[join(x)]
            s = val_ops.Stringify(val, loc.WordPart(part))
            return part_value.String(s, False, False)

        elif part.left.id == Id.Lit_AtLBracket:  # @[split(x)]
            strs = val_ops.ToShellArray(val,
                                        loc.WordPart(part),
                                        prefix='Expr splice ')
            return part_value.Array(strs)

        else:
            raise AssertionError(part.left)

    def SpliceValue(self, val, part):
        # type: (value_t, word_part.Splice) -> List[str]
        """ write -- @myvar """
        return val_ops.ToShellArray(val, loc.WordPart(part), prefix='Splice ')

    def EvalExpr(self, node, blame_loc):
        # type: (expr_t, loc_t) -> value_t
        """Public API for _EvalExpr to ensure command_sub_errexit is on."""
        self.mem.SetLocationForExpr(blame_loc)
        if mylib.PYTHON:
            try:
                with state.ctx_OilExpr(self.mutable_opts):
                    val = self._EvalExpr(node)
                return val

            # Catch PYTHON exceptions.  Remove after function calls are statically typed
            except TypeError as e:
                raise error.Expr('Type error in expression: %s' % str(e),
                                 blame_loc)
            except (AttributeError, ValueError) as e:
                raise error.Expr('Expression eval error: %s' % str(e),
                                 blame_loc)

        else:
            # Pure C++ won't need to catch exceptions
            with state.ctx_OilExpr(self.mutable_opts):
                val = self._EvalExpr(node)
            return val

        # Note: IndexError and KeyError are handled in more specific places

    def _ConvertToInt(self, val):
        # type: (value_t) -> int
        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return val.i

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                if match.LooksLikeInteger(val.s):
                    return int(val.s)
                else:
                    raise ValueError("%r doesn't look like an integer" % val.s)

        raise error.TypeErr(val, 'Expected Int', loc.Missing)

    def _ConvertToNumber(self, val):
        # type: (value_t) -> Tuple[coerced_t, int, float]
        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return coerced_e.Int, val.i, -1.0

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                return coerced_e.Float, -1, val.f

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                if match.LooksLikeInteger(val.s):
                    return coerced_e.Int, int(val.s), -1.0

                if match.LooksLikeFloat(val.s):
                    return coerced_e.Float, -1, float(val.s)

        return coerced_e.Neither, -1, -1.0

    def _ConvertForBinaryOp(self, left, right):
        # type: (value_t, value_t) -> Tuple[coerced_t, int, int, float, float]
        """
        Returns one of
          value_e.Int or value_e.Float
          2 ints or 2 floats

        To indicate which values the operation should be done on
        """
        c1, i1, f1 = self._ConvertToNumber(left)
        c2, i2, f2 = self._ConvertToNumber(right)

        if c1 == coerced_e.Int and c2 == coerced_e.Int:
            return coerced_e.Int, i1, i2, -1.0, -1.0

        elif c1 == coerced_e.Int and c2 == coerced_e.Float:
            return coerced_e.Float, -1, -1, float(i1), f2

        elif c1 == coerced_e.Float and c2 == coerced_e.Int:
            return coerced_e.Float, -1, -1, f1, float(i2)

        elif c1 == coerced_e.Float and c2 == coerced_e.Float:
            return coerced_e.Float, -1, -1, f1, f2

        else:
            # No operation is valid
            return coerced_e.Neither, -1, -1, -1.0, -1.0

    def _EvalConst(self, node):
        # type: (expr.Const) -> value_t

        # Remove underscores from 1_000_000.  The lexer is responsible for
        # validation.  TODO: Do this at PARSE TIME / COMPILE TIME.

        c = node.c.tval.replace('_', '')

        id_ = node.c.id
        if id_ == Id.Expr_DecInt:
            return value.Int(int(c))
        if id_ == Id.Expr_BinInt:
            return value.Int(int(c, 2))
        if id_ == Id.Expr_OctInt:
            return value.Int(int(c, 8))
        if id_ == Id.Expr_HexInt:
            return value.Int(int(c, 16))

        if id_ == Id.Expr_Float:
            return value.Float(float(c))

        if id_ == Id.Expr_Null:
            return value.Null
        if id_ == Id.Expr_True:
            return value.Bool(True)
        if id_ == Id.Expr_False:
            return value.Bool(False)

        if id_ == Id.Expr_Name:
            # for {name: 'bob'}
            # Maybe also :Symbol?
            return value.Str(node.c.tval)

        # These calculations could also be done at COMPILE TIME
        if id_ == Id.Char_OneChar:
            # TODO: look up integer directly?
            return value.Int(ord(consts.LookupCharC(node.c.tval[1])))
        if id_ == Id.Char_UBraced:
            s = node.c.tval[3:-1]  # \u{123}
            return value.Int(int(s, 16))
        if id_ == Id.Char_Pound:
            # TODO: accept UTF-8 code point instead of single byte
            byte = node.c.tval[2]  # the a in #'a'
            return value.Int(ord(byte))  # It's an integer

        # NOTE: We could allow Ellipsis for a[:, ...] here, but we're not using it
        # yet.
        raise AssertionError(id_)

    def _EvalUnary(self, node):
        # type: (expr.Unary) -> value_t
        val = self._EvalExpr(node.child)
        if node.op.id == Id.Arith_Minus:
            c1, i1, f1 = self._ConvertToNumber(val)
            if c1 == coerced_e.Int:
                return value.Int(-i1)
            if c1 == coerced_e.Float:
                return value.Float(-f1)
            raise error.TypeErr(val, 'Negation expected Int or Float', node.op)

        if node.op.id == Id.Arith_Tilde:
            i = self._ConvertToInt(val)
            return value.Int(~i)

        if node.op.id == Id.Expr_Not:
            b = val_ops.ToBool(val)
            return value.Bool(False if b else True)

        raise NotImplementedError(node.op.id)

    def _ArithNumeric(self, left, right, op):
        # type: (value_t, value_t, Token) -> value_t
        """
        Note: may be replaced with arithmetic on tagged integers, e.g. 60 bit
        with overflow detection
        """
        c, i1, i2, f1, f2 = self._ConvertForBinaryOp(left, right)

        op_id = op.id

        if c == coerced_e.Int:
            with switch(op_id) as case:
                if case(Id.Arith_Plus, Id.Arith_PlusEqual):
                    return value.Int(i1 + i2)
                elif case(Id.Arith_Minus, Id.Arith_MinusEqual):
                    return value.Int(i1 - i2)
                elif case(Id.Arith_Star, Id.Arith_StarEqual):
                    return value.Int(i1 * i2)
                elif case(Id.Arith_Slash, Id.Arith_SlashEqual):
                    if i2 == 0:
                        raise ZeroDivisionError()
                    return value.Float(float(i1) / float(i2))
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
                        raise ZeroDivisionError()
                    return value.Float(f1 / f2)
                else:
                    raise AssertionError()

        else:
            raise error.TypeErrVerbose(
                'Binary operator expected numbers, got %s and %s' %
                (ui.ValType(left), ui.ValType(right)), loc.Missing)

    def _Concat(self, left, right):
        # type: (value_t, value_t) -> value_t
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
                (ui.ValType(left), ui.ValType(right)), loc.Missing)

    def _EvalBinary(self, node):
        # type: (expr.Binary) -> value_t

        left = self._EvalExpr(node.left)
        right = self._EvalExpr(node.right)

        op_id = node.op.id

        # Logical
        if op_id == Id.Expr_And:
            if val_ops.ToBool(left):  # no errors
                return right
            else:
                return left

        if op_id == Id.Expr_Or:
            if val_ops.ToBool(left):
                return left
            else:
                return right

        # Str or List
        if op_id == Id.Arith_DPlus:  # a ++ b to concat
            return self._Concat(left, right)

        # Int or Float
        if op_id in \
          (Id.Arith_Plus, Id.Arith_Minus, Id.Arith_Star, Id.Arith_Slash):
            try:
                return self._ArithNumeric(left, right, node.op)
            except ZeroDivisionError:
                raise error.Expr('Divide by zero', node.op)

        # Everything below has 2 integer operands
        i1 = self._ConvertToInt(left)
        i2 = self._ConvertToInt(right)

        if op_id == Id.Expr_DSlash:  # a // b
            if i2 == 0:
                raise error.Expr('Divide by zero', node.op)
            return value.Int(i1 // i2)

        if op_id == Id.Arith_Percent:  # a % b
            if i2 == 0:
                raise error.Expr('Divide by zero', node.op)
            return value.Int(i1 % i2)

        if op_id == Id.Arith_DStar:  # a ** b
            # Same as sh_expr_eval.py
            if i2 < 0:
                raise error.Expr("Exponent can't be a negative number",
                                 node.op)
            ret = 1
            for i in xrange(i2):
                ret *= i1
            return value.Int(ret)

        # Bitwise
        if op_id == Id.Arith_Amp:
            return value.Int(i1 & i2)

        if op_id == Id.Arith_Pipe:
            return value.Int(i1 | i2)

        if op_id == Id.Arith_Caret:
            return value.Int(i1 ^ i2)

        if op_id == Id.Arith_DGreat:
            return value.Int(i1 >> i2)

        if op_id == Id.Arith_DLess:
            return value.Int(i1 << i2)

        raise NotImplementedError(op_id)

    def _EvalSlice(self, node):
        # type: (expr.Slice) -> value_t

        lower = None  # type: Optional[IntBox]
        upper = None  # type: Optional[IntBox]

        if node.lower:
            msg = 'Slice begin should be Int'
            i = val_ops.ToInt(self._EvalExpr(node.lower), msg, loc.Missing)
            lower = IntBox(i)

        if node.upper:
            msg = 'Slice end should be Int'
            i = val_ops.ToInt(self._EvalExpr(node.upper), msg, loc.Missing)
            upper = IntBox(i)

        return value.Slice(lower, upper)

    def _EvalRange(self, node):
        # type: (expr.Range) -> value_t
        assert node.lower is not None
        assert node.upper is not None

        msg = 'Range begin should be Int'
        i = val_ops.ToInt(self._EvalExpr(node.lower), msg, loc.Missing)

        msg = 'Range end should be Int'
        j = val_ops.ToInt(self._EvalExpr(node.upper), msg, loc.Missing)

        return value.Range(i, j)

    def _CompareNumeric(self, left, right, op):
        # type: (value_t, value_t, Token) -> bool
        c, i1, i2, f1, f2 = self._ConvertForBinaryOp(left, right)

        op_id = op.id
        if c == coerced_e.Int:
            with switch(op_id) as case:
                if case(Id.Arith_Less):
                    return i1 < i2
                elif case(Id.Arith_Great):
                    return i1 > i2
                elif case(Id.Arith_LessEqual):
                    return i1 <= i2
                elif case(Id.Arith_GreatEqual):
                    return i1 >= i2
                else:
                    raise AssertionError()

        elif c == coerced_e.Float:
            with switch(op_id) as case:
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

            if op.id in \
              (Id.Arith_Less, Id.Arith_Great, Id.Arith_LessEqual, Id.Arith_GreatEqual):
                result = self._CompareNumeric(left, right, op)

            elif op.id == Id.Expr_TEqual:
                if left.tag() != right.tag():
                    result = False
                else:
                    result = val_ops.ExactlyEqual(left, right)
            elif op.id == Id.Expr_NotDEqual:
                if left.tag() != right.tag():
                    result = True
                else:
                    result = not val_ops.ExactlyEqual(left, right)

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

                        log('left %r left2 %r', left, left2)
                        return value.Bool(lb == right.b)

                    elif case(value_e.Int):
                        right = cast(value.Int, UP_right)
                        if not left2.isdigit():
                            return value.Bool(False)

                        return value.Bool(int(left2) == right.i)

                e_die('~== expects Str, Int, or Bool on the right', op)

            else:
                try:
                    if op.id == Id.Arith_Tilde:
                        result = val_ops.RegexMatch(left, right, self.mem)

                    elif op.id == Id.Expr_NotTilde:
                        # don't pass self.mem to not set a match
                        result = not val_ops.RegexMatch(left, right, None)

                    else:
                        raise AssertionError(op)
                except RuntimeError as e:
                    # Status 2 indicates a regex parse error.  This is fatal in OSH but
                    # not in bash, which treats [[ like a command with an exit code.
                    e_die_status(2, 'Invalid regex %r' % right, op)

            if not result:
                return value.Bool(result)

            left = right

        return value.Bool(result)

    def _EvalDict(self, node):
        # type: (expr.Dict) -> value_t

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

    def EvalArgList(self, args):
        # type: (ArgList) -> Tuple[List[Any], Dict[str, Any]]
        """For procs and funcs - UNTYPED"""
        pos_args = []  # type: List[Any]
        for arg in args.positional:
            UP_arg = arg

            if arg.tag() == expr_e.Spread:
                arg = cast(expr.Spread, UP_arg)
                # assume it returns a list
                #pos_args.extend(self._EvalExpr(arg.child))
            else:
                pos_args.append(self._EvalExpr(arg))

        kwargs = {}  # type: Dict[str, Any]

        # NOTE: Keyword args aren't tested
        if 0:
            for named in args.named:
                if named.name:
                    kwargs[named.name.tval] = self._EvalExpr(named.value)
                else:
                    # ...named
                    kwargs.update(self._EvalExpr(named.value))

        return pos_args, kwargs

    def EvalArgList2(self, args, me=None):
        # type: (ArgList, Optional[value_t]) -> Tuple[List[value_t], Dict[str, value_t]]
        """For procs and args - TYPED """
        pos_args = []  # type: List[value_t]

        if me:  # self/this argument
            pos_args.append(me)

        for arg in args.positional:
            UP_arg = arg

            if arg.tag() == expr_e.Spread:
                arg = cast(expr.Spread, UP_arg)
                # assume it returns a list
                #pos_args.extend(self._EvalExpr(arg.child))
                pass
            else:
                pos_args.append(self._EvalExpr(arg))

        kwargs = {}  # type: Dict[str, value_t]

        # NOTE: Keyword args aren't tested
        if 0:
            for named in args.named:
                if named.name:
                    kwargs[named.name.tval] = self._EvalExpr(named.value)
                else:
                    # ...named
                    kwargs.update(self._EvalExpr(named.value))

        return pos_args, kwargs

    def _EvalFuncCall(self, node):
        # type: (expr.FuncCall) -> value_t

        func = self._EvalExpr(node.func)
        UP_func = func

        with tagswitch(func) as case:
            if case(value_e.Func):
                func = cast(value.Func, UP_func)
                if mylib.PYTHON:
                    f = func.callable
                    if isinstance(f, vm._Callable):  # typed
                        pos_args, named_args = self.EvalArgList2(node.args)
                        #log('pos_args %s', pos_args)

                        ret = f.Call(pos_args, named_args)

                        #log('ret %s', ret)
                        return ret
                    else:
                        u_pos_args, u_named_args = self.EvalArgList(node.args)
                        #log('ARGS %s', u_pos_args)
                        #ret = f(*u_pos_args, **u_named_args)

                        pos_args = [
                            cpython._ValueToPyObj(a) for a in u_pos_args
                        ]
                        ret = f(*pos_args)

                        return cpython._PyObjToValue(ret)
                else:
                    # C++ cast to work around ASDL 'any'
                    f = cast(vm._Callable, func.callable)
                    pos_args, named_args = self.EvalArgList2(node.args)
                    #log('pos_args %s', pos_args)

                    ret = f.Call(pos_args, named_args)

                    #log('ret %s', ret)
                    return ret

            elif case(value_e.BoundFunc):
                func = cast(value.BoundFunc, UP_func)

                #assert isinstance(func.callable, vm._Callable), "Bound funcs must be typed"
                # Cast to work around ASDL limitation for now
                f = cast(vm._Callable, func.callable)

                pos_args, named_args = self.EvalArgList2(node.args, me=func.me)

                ret = f.Call(pos_args, named_args)

                return ret

            else:
                raise error.TypeErr(func, 'Expected a function or method',
                                    node.args.left)

        raise AssertionError()

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
                        try:
                            return value.Str(obj.s[index.i])
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
                        try:
                            return obj.items[index.i]
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
                    raise error.Expr('dict entry not found', loc.Missing)

        raise error.TypeErr(obj, 'Subscript expected Str, List, or Dict',
                            loc.Missing)

    def _EvalAttribute(self, node):
        # type: (Attribute) -> value_t

        o = self._EvalExpr(node.obj)
        UP_o = o

        id_ = node.op.id
        if id_ == Id.Expr_RArrow:
            name = node.attr.tval
            ty = o.tag()

            recv = self.methods.get(ty)
            method = recv.get(name) if recv is not None else None
            if not method:
                raise error.TypeErrVerbose(
                    'Method %r does not exist on type %s' %
                    (name, ui.ValType(o)), node.attr)

            return value.BoundFunc(o, method)

        if id_ == Id.Expr_Dot:  # d.key is like d['key']
            name = node.attr.tval
            with tagswitch(o) as case:
                if case(value_e.Dict):
                    o = cast(value.Dict, UP_o)
                    try:
                        result = o.d[name]
                    except KeyError:
                        raise error.Expr('dict entry not found', node.op)

                else:
                    raise error.TypeErr(o, 'Dot operator expected Dict',
                                        node.op)

            return result

        if id_ == Id.Expr_DColon:  # StaticName::member
            raise NotImplementedError(id_)

            # TODO: We should prevent virtual lookup here?  This is a pure static
            # namespace lookup?
            # But Python doesn't any hook for this.
            # Maybe we can just check that it's a module?  And modules don't lookup
            # in a supertype or __class__, etc.

        raise AssertionError(id_)

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
                return self._LookupVar(node.name.tval, node.name)

            elif case(expr_e.CommandSub):
                node = cast(CommandSub, UP_node)

                id_ = node.left_token.id
                if id_ == Id.Left_CaretParen:
                    # ^(echo block literal)
                    return value.Str('TODO: value.Block')
                else:
                    stdout_str = self.shell_ex.RunCommandSub(node)
                    if id_ == Id.Left_AtParen:  # @(seq 3)
                        # TODO: Should use QSN8 lines
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
                node = cast(SimpleVarSub, UP_node)
                return value.Str(self.word_ev.EvalSimpleVarSubToString(node))

            elif case(expr_e.Unary):
                node = cast(expr.Unary, UP_node)
                return self._EvalUnary(node)

            elif case(expr_e.Binary):
                node = cast(expr.Binary, UP_node)
                return self._EvalBinary(node)

            elif case(expr_e.Slice):  # a[:0]
                node = cast(expr.Slice, UP_node)
                return self._EvalSlice(node)

            elif case(expr_e.Range):
                node = cast(expr.Range, UP_node)
                return self._EvalRange(node)

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
                return self._EvalDict(node)

            elif case(expr_e.ListComp):
                e_die_status(
                    2, 'List comprehension reserved but not implemented')

            elif case(expr_e.GeneratorExp):
                e_die_status(
                    2, 'Generator expression reserved but not implemented')

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

            elif case(expr_e.RegexLiteral):
                node = cast(expr.RegexLiteral, UP_node)
                return value.Eggex(self.EvalRegex(node.regex), None)

            else:
                raise NotImplementedError(node.__class__.__name__)

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
                s = val_ops.ToStr(val,
                                      'Eggex char class splice expected Str',
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

    def _EvalRegex(self, node):
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
                new_children = [
                    self._EvalRegex(child) for child in node.children
                ]
                return re.Seq(new_children)

            elif case(re_e.Alt):
                node = cast(re.Alt, UP_node)
                new_children = [
                    self._EvalRegex(child) for child in node.children
                ]
                return re.Alt(new_children)

            elif case(re_e.Repeat):
                node = cast(re.Repeat, UP_node)
                return re.Repeat(self._EvalRegex(node.child), node.op)

            elif case(re_e.Group):
                node = cast(re.Group, UP_node)
                return re.Group(self._EvalRegex(node.child))

            elif case(re_e.Capture):  # Identical to Group
                node = cast(re.Capture, UP_node)
                return re.Capture(self._EvalRegex(node.child), node.var_name)

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
                tval = node.tval

                if id_ == Id.Expr_Dot:
                    return re.Primitive(Id.Re_Dot)

                if id_ == Id.Arith_Caret:  # ^
                    return re.Primitive(Id.Re_Start)

                if id_ == Id.Expr_Dollar:  # $
                    return re.Primitive(Id.Re_End)

                if id_ == Id.Expr_Name:
                    if tval == 'dot':
                        return re.Primitive(Id.Re_Dot)
                    raise NotImplementedError(tval)

                if id_ == Id.Expr_Symbol:
                    if tval == '%start':
                        return re.Primitive(Id.Re_Start)
                    if tval == '%end':
                        return re.Primitive(Id.Re_End)
                    raise NotImplementedError(tval)

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
                        # Note: we only splice the regex, and ignore flags.
                        # Should we warn about this?
                        to_splice = val.expr

                    else:
                        raise error.TypeErr(
                            val, 'Eggex splice expected Str or Eggex',
                            node.name)
                return to_splice

            else:
                # These are evaluated at translation time

                # case(re_e.PosixClass)
                # case(re_e.PerlClass)
                return node

    def EvalRegex(self, node):
        # type: (re_t) -> re_t
        """Trivial wrapper."""
        new_node = self._EvalRegex(node)

        # View it after evaluation
        if 0:
            log('After evaluation:')
            new_node.PrettyPrint()
            print()
        return new_node


# vim: sw=4
