#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
sh_expr_eval.py -- Shell boolean and arithmetic expressions.
"""

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import (
    scope_t,
    lvalue,
    lvalue_e,
    lvalue_t,
    value,
    value_e,
    value_t,
)
from _devbuild.gen.syntax_asdl import (
    word_t,
    CompoundWord,
    Token,
    loc,
    loc_t,
    source,
    arith_expr,
    arith_expr_e,
    arith_expr_t,
    bool_expr,
    bool_expr_e,
    bool_expr_t,
    sh_lhs_expr,
    sh_lhs_expr_e,
    sh_lhs_expr_t,
    BracedVarSub,
    SimpleVarSub,
)
from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.types_asdl import bool_arg_type_e
from core import alloc
from core import error
from core.error import e_die, e_die_status, e_strict, e_usage
from core import state
from core import ui
from frontend import consts
from frontend import match
from frontend import parse_lib
from frontend import reader
from mycpp import mylib
from mycpp.mylib import log, tagswitch, switch, str_cmp
from osh import bool_stat
from osh import word_eval

import libc  # for fnmatch

from typing import Tuple, Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from core.ui import ErrorFormatter
    from core import optview

_ = log

#
# Arith and Command/Word variants of assignment
#
# Calls EvalShellLhs()
#   a[$key]=$val             # osh/cmd_eval.py:814  (command_e.ShAssignment)
# Calls EvalArithLhs()
#   (( a[key] = val ))       # osh/sh_expr_eval.py:326 (_EvalLhsArith)
#
# Calls OldValue()
#   a[$key]+=$val            # osh/cmd_eval.py:795     (assign_op_e.PlusEqual)
#   (( a[key] += val ))      # osh/sh_expr_eval.py:308 (_EvalLhsAndLookupArith)
#
# RHS Indexing
#   val=${a[$key]}           # osh/word_eval.py:639 (bracket_op_e.ArrayIndex)
#   (( val = a[key] ))       # osh/sh_expr_eval.py:509 (Id.Arith_LBracket)
#


def OldValue(lval, mem, exec_opts):
    # type: (lvalue_t, state.Mem, Optional[optview.Exec]) -> value_t
    """Look up for augmented assignment.

    For s+=val and (( i += 1 ))

    Args:
      lval: value we need to
      exec_opts: can be None if we don't want to check set -u!
        Because s+=val doesn't check it.

    TODO: A stricter and less ambiguous version for YSH.
    - Problem: why does lvalue have Indexed and Keyed, while sh_lhs_expr only has
      IndexedName?
      - should I have location.LName and lvalue.Indexed only?
      - and Indexed uses the index_t type?
        - well that might be Str or Int
    """
    assert isinstance(lval, lvalue_t), lval

    # TODO: refactor lvalue_t to make this simpler
    UP_lval = lval
    with tagswitch(lval) as case:
        if case(lvalue_e.Named):  # (( i++ ))
            lval = cast(lvalue.Named, UP_lval)
            var_name = lval.name
        elif case(lvalue_e.Indexed):  # (( a[i]++ ))
            lval = cast(lvalue.Indexed, UP_lval)
            var_name = lval.name
        elif case(lvalue_e.Keyed):  # (( A['K']++ )) ?  I think this works
            lval = cast(lvalue.Keyed, UP_lval)
            var_name = lval.name
        else:
            raise AssertionError()

    val = mem.GetValue(var_name)
    if exec_opts and exec_opts.nounset() and val.tag() == value_e.Undef:
        e_die('Undefined variable %r' % var_name)  # TODO: location info

    UP_val = val
    with tagswitch(lval) as case:
        if case(lvalue_e.Named):
            return val

        elif case(lvalue_e.Indexed):
            lval = cast(lvalue.Indexed, UP_lval)

            array_val = None  # type: value.BashArray
            with tagswitch(val) as case2:
                if case2(value_e.Undef):
                    array_val = value.BashArray([])
                elif case2(value_e.BashArray):
                    tmp = cast(value.BashArray, UP_val)
                    # mycpp rewrite: add tmp.  cast() creates a new var in inner scope
                    array_val = tmp
                else:
                    e_die("Can't use [] on value of type %s" % ui.ValType(val))

            s = word_eval.GetArrayItem(array_val.strs, lval.index)

            if s is None:
                val = value.Str('')  # NOTE: Other logic is value.Undef?  0?
            else:
                assert isinstance(s, str), s
                val = value.Str(s)

        elif case(lvalue_e.Keyed):
            lval = cast(lvalue.Keyed, UP_lval)

            assoc_val = None  # type: value.BashAssoc
            with tagswitch(val) as case2:
                if case2(value_e.Undef):
                    # This never happens, because undef[x]+= is assumed to
                    raise AssertionError()
                elif case2(value_e.BashAssoc):
                    tmp2 = cast(value.BashAssoc, UP_val)
                    # mycpp rewrite: add tmp.  cast() creates a new var in inner scope
                    assoc_val = tmp2
                else:
                    e_die("Can't use [] on value of type %s" % ui.ValType(val))

            s = assoc_val.d.get(lval.key)
            if s is None:
                val = value.Str('')
            else:
                val = value.Str(s)

        else:
            raise AssertionError()

    return val


# TODO: Should refactor for int/char-based processing
if mylib.PYTHON:

    def IsLower(ch):
        # type: (str) -> bool
        return 'a' <= ch and ch <= 'z'

    def IsUpper(ch):
        # type: (str) -> bool
        return 'A' <= ch and ch <= 'Z'


class UnsafeArith(object):
    """For parsing a[i] at RUNTIME."""

    def __init__(self, mem, exec_opts, mutable_opts, parse_ctx, arith_ev,
                 errfmt):
        # type: (state.Mem, optview.Exec, state.MutableOpts, parse_lib.ParseContext, ArithEvaluator, ui.ErrorFormatter) -> None
        self.mem = mem
        self.exec_opts = exec_opts
        self.mutable_opts = mutable_opts
        self.parse_ctx = parse_ctx
        self.arith_ev = arith_ev
        self.errfmt = errfmt

        self.arena = self.parse_ctx.arena

    def ParseLValue(self, s, location):
        # type: (str, loc_t) -> lvalue_t
        """Parse lvalue/place for 'unset' and 'printf -v'.

        It uses the arith parser, so it behaves like the LHS of (( a[i] = x ))
        """
        if not self.parse_ctx.parse_opts.parse_sh_arith():
            # Do something simpler for YSH
            if not match.IsValidVarName(s):
                e_die('Invalid variable name %r (parse_sh_arith is off)' % s,
                      location)
            return lvalue.Named(s, location)

        a_parser = self.parse_ctx.MakeArithParser(s)

        with alloc.ctx_Location(self.arena,
                                source.ArgvWord('dynamic place', location)):
            try:
                anode = a_parser.Parse()
            except error.Parse as e:
                self.errfmt.PrettyPrintError(e)
                # Exception for builtins 'unset' and 'printf'
                e_usage('got invalid place expression', location)

        # Note: we parse '1+2', and then it becomes a runtime error because it's
        # not a valid place.  Could be a parse error.

        if self.exec_opts.eval_unsafe_arith():
            lval = self.arith_ev.EvalArithLhs(anode)
        else:
            # Prevent attacks like these by default:
            #
            # unset -v 'A["$(echo K; rm *)"]'
            with state.ctx_Option(self.mutable_opts,
                                  [option_i._allow_command_sub], False):
                lval = self.arith_ev.EvalArithLhs(anode)

        return lval

    def ParseVarRef(self, ref_str, blame_tok):
        # type: (str, Token) -> BracedVarSub
        """Parse and evaluate value for ${!ref}

        This supports:
        - 0 to 9 for $0 to $9
        - @ for "$@" etc.

        See grammar in osh/word_parse.py, which is related to grammar in
        osh/word_parse.py _ReadBracedVarSub

        Note: declare -n allows 'varname' and 'varname[i]' and 'varname[@]', but it
        does NOT allow 0 to 9, @, *

        NamerefExpr = NAME Subscript?   # this allows @ and * too

        _ResolveNameOrRef currently gives you a 'cell'.  So it might not support
        lvalue.Indexed?
        """
        line_reader = reader.StringLineReader(ref_str, self.arena)
        lexer = self.parse_ctx.MakeLexer(line_reader)
        w_parser = self.parse_ctx.MakeWordParser(lexer, line_reader)

        src = source.VarRef(blame_tok)
        with alloc.ctx_Location(self.arena, src):
            try:
                bvs_part = w_parser.ParseVarRef()
            except error.Parse as e:
                # This prints the inner location
                self.errfmt.PrettyPrintError(e)

                # this affects builtins 'unset' and 'printf'
                e_die("Invalid var ref expression", blame_tok)

        return bvs_part


class ArithEvaluator(object):
    """Shared between arith and bool evaluators.

    They both:

    1. Convert strings to integers, respecting shopt -s strict_arith.
    2. Look up variables and evaluate words.
    """

    def __init__(self, mem, exec_opts, mutable_opts, parse_ctx, errfmt):
        # type: (state.Mem, optview.Exec, state.MutableOpts, Optional[parse_lib.ParseContext], ErrorFormatter) -> None
        self.word_ev = None  # type: word_eval.StringWordEvaluator
        self.mem = mem
        self.exec_opts = exec_opts
        self.mutable_opts = mutable_opts
        self.parse_ctx = parse_ctx
        self.errfmt = errfmt

    def CheckCircularDeps(self):
        # type: () -> None
        assert self.word_ev is not None

    def _StringToInteger(self, s, blame_loc):
        # type: (str, loc_t) -> int
        """Use bash-like rules to coerce a string to an integer.

        Runtime parsing enables silly stuff like $(( $(echo 1)$(echo 2) + 1 )) => 13

        0xAB -- hex constant
        042  -- octal constant
        42   -- decimal constant
        64#z -- arbitrary base constant

        bare word: variable
        quoted word: string (not done?)
        """
        if s.startswith('0x'):
            try:
                integer = int(s, 16)
            except ValueError:
                e_strict('Invalid hex constant %r' % s, blame_loc)
            return integer

        if s.startswith('0'):
            try:
                integer = int(s, 8)
            except ValueError:
                e_strict('Invalid octal constant %r' % s, blame_loc)
            return integer

        if '#' in s:
            b, digits = mylib.split_once(s, '#')
            try:
                base = int(b)
            except ValueError:
                e_strict('Invalid base for numeric constant %r' % b, blame_loc)

            integer = 0
            for ch in digits:
                if IsLower(ch):
                    digit = ord(ch) - ord('a') + 10
                elif IsUpper(ch):
                    digit = ord(ch) - ord('A') + 36
                elif ch == '@':  # horrible syntax
                    digit = 62
                elif ch == '_':
                    digit = 63
                elif ch.isdigit():
                    digit = int(ch)
                else:
                    e_strict('Invalid digits for numeric constant %r' % digits,
                             blame_loc)

                if digit >= base:
                    e_strict(
                        'Digits %r out of range for base %d' % (digits, base),
                        blame_loc)

                integer = integer * base + digit
            return integer

        try:
            # Normal base 10 integer.  This includes negative numbers like '-42'.
            integer = int(s)
        except ValueError:
            # doesn't look like an integer

            # note: 'test' and '[' never evaluate recursively
            if self.parse_ctx:
                arena = self.parse_ctx.arena

                # Special case so we don't get EOF error
                if len(s.strip()) == 0:
                    return 0

                # For compatibility: Try to parse it as an expression and evaluate it.
                a_parser = self.parse_ctx.MakeArithParser(s)

                # TODO: Fill in the variable name
                with alloc.ctx_Location(arena, source.Variable(None,
                                                               blame_loc)):
                    try:
                        node2 = a_parser.Parse()  # may raise error.Parse
                    except error.Parse as e:
                        self.errfmt.PrettyPrintError(e)
                        e_die('Parse error in recursive arithmetic', e.location)

                # Prevent infinite recursion of $(( 1x )) -- it's a word that evaluates
                # to itself, and you don't want to reparse it as a word.
                if node2.tag() == arith_expr_e.Word:
                    e_die("Invalid integer constant %r" % s, blame_loc)

                if self.exec_opts.eval_unsafe_arith():
                    integer = self.EvalToInt(node2)
                else:
                    # BoolEvaluator doesn't have parse_ctx or mutable_opts
                    assert self.mutable_opts is not None

                    # We don't need to flip _allow_process_sub, because they can't be
                    # parsed.  See spec/bugs.test.sh.
                    with state.ctx_Option(self.mutable_opts,
                                          [option_i._allow_command_sub], False):
                        integer = self.EvalToInt(node2)

            else:
                if len(s.strip()) == 0 or match.IsValidVarName(s):
                    # x42 could evaluate to 0
                    e_strict("Invalid integer constant %r" % s, blame_loc)
                else:
                    # 42x is always fatal!
                    e_die("Invalid integer constant %r" % s, blame_loc)

        return integer

    def _ValToIntOrError(self, val, blame):
        # type: (value_t, arith_expr_t) -> int
        try:
            UP_val = val
            with tagswitch(val) as case:
                if case(value_e.Undef
                       ):  # 'nounset' already handled before got here
                    # Happens upon a[undefined]=42, which unfortunately turns into a[0]=42.
                    e_strict('Undefined value in arithmetic context',
                             loc.Arith(blame))

                elif case(value_e.Int):
                    val = cast(value.Int, UP_val)
                    return val.i

                elif case(value_e.Str):
                    val = cast(value.Str, UP_val)
                    return self._StringToInteger(
                        val.s, loc.Arith(blame))  # calls e_strict

        except error.Strict as e:
            if self.exec_opts.strict_arith():
                raise
            else:
                return 0

        # Arrays and associative arrays always fail -- not controlled by
        # strict_arith.
        # In bash, (( a )) is like (( a[0] )), but I don't want that.
        # And returning '0' gives different results.
        e_die(
            "Expected a value convertible to integer, got %s" % ui.ValType(val),
            loc.Arith(blame))

    def _EvalLhsAndLookupArith(self, node):
        # type: (arith_expr_t) -> Tuple[int, lvalue_t]
        """ For x = y  and   x += y  and  ++x """

        lval = self.EvalArithLhs(node)
        val = OldValue(lval, self.mem, self.exec_opts)

        # BASH_LINENO, arr (array name without strict_array), etc.
        if val.tag() in (value_e.BashArray,
                         value_e.BashAssoc) and lval.tag() == lvalue_e.Named:
            named_lval = cast(lvalue.Named, lval)
            if word_eval.ShouldArrayDecay(named_lval.name, self.exec_opts):
                if val.tag() == value_e.BashArray:
                    lval = lvalue.Indexed(named_lval.name, 0, loc.Missing)
                elif val.tag() == value_e.BashAssoc:
                    lval = lvalue.Keyed(named_lval.name, '0', loc.Missing)
                val = word_eval.DecayArray(val)

        # This error message could be better, but we already have one
        #if val.tag() == value_e.BashArray:
        #  e_die("Can't use assignment like ++ or += on arrays")

        i = self._ValToIntOrError(val, node)
        return i, lval

    def _Store(self, lval, new_int):
        # type: (lvalue_t, int) -> None
        val = value.Str(str(new_int))
        state.OshLanguageSetValue(self.mem, lval, val)

    def EvalToInt(self, node):
        # type: (arith_expr_t) -> int
        """Used externally by ${a[i+1]} and ${a:start:len}.

        Also used internally.
        """
        val = self.Eval(node)

        # BASH_LINENO, arr (array name without strict_array), etc.
        if val.tag() in (value_e.BashArray, value_e.BashAssoc
                        ) and node.tag() == arith_expr_e.VarSub:
            vsub = cast(SimpleVarSub, node)
            if word_eval.ShouldArrayDecay(vsub.var_name, self.exec_opts):
                val = word_eval.DecayArray(val)

        i = self._ValToIntOrError(val, node)
        return i

    def Eval(self, node):
        # type: (arith_expr_t) -> value_t
        """
    Args:
      node: arith_expr_t

    Returns:
      None for Undef  (e.g. empty cell)  TODO: Don't return 0!
      int for Str
      List[int] for BashArray
      Dict[str, str] for BashAssoc (TODO: Should we support this?)

    NOTE: (( A['x'] = 'x' )) and (( x = A['x'] )) are syntactically valid in
    bash, but don't do what you'd think.  'x' sometimes a variable name and
    sometimes a key.
    """
        # OSH semantics: Variable NAMES cannot be formed dynamically; but INTEGERS
        # can.  ${foo:-3}4 is OK.  $? will be a compound word too, so we don't have
        # to handle that as a special case.

        UP_node = node
        with tagswitch(node) as case:
            if case(arith_expr_e.VarSub):  # $(( x ))  (can be array)
                vsub = cast(SimpleVarSub, UP_node)
                val = self.mem.GetValue(vsub.var_name)
                if val.tag() == value_e.Undef and self.exec_opts.nounset():
                    e_die('Undefined variable %r' % vsub.var_name, vsub.left)
                return val

            elif case(arith_expr_e.Word):  # $(( $x )) $(( ${x}${y} )), etc.
                w = cast(CompoundWord, UP_node)
                return self.word_ev.EvalWordToString(w)

            elif case(arith_expr_e.UnaryAssign):  # a++
                node = cast(arith_expr.UnaryAssign, UP_node)

                op_id = node.op_id
                old_int, lval = self._EvalLhsAndLookupArith(node.child)

                if op_id == Id.Node_PostDPlus:  # post-increment
                    new_int = old_int + 1
                    ret = old_int

                elif op_id == Id.Node_PostDMinus:  # post-decrement
                    new_int = old_int - 1
                    ret = old_int

                elif op_id == Id.Arith_DPlus:  # pre-increment
                    new_int = old_int + 1
                    ret = new_int

                elif op_id == Id.Arith_DMinus:  # pre-decrement
                    new_int = old_int - 1
                    ret = new_int

                else:
                    raise AssertionError(op_id)

                #log('old %d new %d ret %d', old_int, new_int, ret)
                self._Store(lval, new_int)
                return value.Int(ret)

            elif case(arith_expr_e.BinaryAssign):  # a=1, a+=5, a[1]+=5
                node = cast(arith_expr.BinaryAssign, UP_node)
                op_id = node.op_id

                if op_id == Id.Arith_Equal:
                    # Don't really need a span ID here, because tdop.CheckLhsExpr should
                    # have done all the validation.
                    lval = self.EvalArithLhs(node.left)
                    rhs_int = self.EvalToInt(node.right)

                    self._Store(lval, rhs_int)
                    return value.Int(rhs_int)

                old_int, lval = self._EvalLhsAndLookupArith(node.left)
                rhs = self.EvalToInt(node.right)

                if op_id == Id.Arith_PlusEqual:
                    new_int = old_int + rhs
                elif op_id == Id.Arith_MinusEqual:
                    new_int = old_int - rhs
                elif op_id == Id.Arith_StarEqual:
                    new_int = old_int * rhs

                elif op_id == Id.Arith_SlashEqual:
                    if rhs == 0:
                        e_die('Divide by zero')  # TODO: location
                    new_int = old_int / rhs

                elif op_id == Id.Arith_PercentEqual:
                    if rhs == 0:
                        e_die('Divide by zero')  # TODO: location
                    new_int = old_int % rhs

                elif op_id == Id.Arith_DGreatEqual:
                    new_int = old_int >> rhs
                elif op_id == Id.Arith_DLessEqual:
                    new_int = old_int << rhs
                elif op_id == Id.Arith_AmpEqual:
                    new_int = old_int & rhs
                elif op_id == Id.Arith_PipeEqual:
                    new_int = old_int | rhs
                elif op_id == Id.Arith_CaretEqual:
                    new_int = old_int ^ rhs
                else:
                    raise AssertionError(op_id)  # shouldn't get here

                self._Store(lval, new_int)
                return value.Int(new_int)

            elif case(arith_expr_e.Unary):
                node = cast(arith_expr.Unary, UP_node)
                op_id = node.op_id

                i = self.EvalToInt(node.child)

                if op_id == Id.Node_UnaryPlus:
                    ret = i
                elif op_id == Id.Node_UnaryMinus:
                    ret = -i

                elif op_id == Id.Arith_Bang:  # logical negation
                    ret = 1 if i == 0 else 0
                elif op_id == Id.Arith_Tilde:  # bitwise complement
                    ret = ~i
                else:
                    raise AssertionError(op_id)  # shouldn't get here

                return value.Int(ret)

            elif case(arith_expr_e.Binary):
                node = cast(arith_expr.Binary, UP_node)
                op_id = node.op_id

                # Short-circuit evaluation for || and &&.
                if op_id == Id.Arith_DPipe:
                    lhs = self.EvalToInt(node.left)
                    if lhs == 0:
                        rhs = self.EvalToInt(node.right)
                        ret = int(rhs != 0)
                    else:
                        ret = 1  # true
                    return value.Int(ret)

                if op_id == Id.Arith_DAmp:
                    lhs = self.EvalToInt(node.left)
                    if lhs == 0:
                        ret = 0  # false
                    else:
                        rhs = self.EvalToInt(node.right)
                        ret = int(rhs != 0)
                    return value.Int(ret)

                if op_id == Id.Arith_LBracket:
                    # NOTE: Similar to bracket_op_e.ArrayIndex in osh/word_eval.py

                    left = self.Eval(node.left)
                    UP_left = left
                    with tagswitch(left) as case:
                        if case(value_e.BashArray):
                            array_val = cast(value.BashArray, UP_left)
                            index = self.EvalToInt(node.right)
                            s = word_eval.GetArrayItem(array_val.strs, index)

                        elif case(value_e.BashAssoc):
                            left = cast(value.BashAssoc, UP_left)
                            key = self.EvalWordToString(node.right)
                            s = left.d.get(key)

                        else:
                            # TODO: Add error context
                            e_die(
                                'Expected array or assoc in index expression, got %s'
                                % ui.ValType(left))

                    if s is None:
                        val = value.Undef
                    else:
                        val = value.Str(s)

                    return val

                if op_id == Id.Arith_Comma:
                    self.EvalToInt(node.left)  # throw away result
                    ret = self.EvalToInt(node.right)
                    return value.Int(ret)

                # Rest are integers
                lhs = self.EvalToInt(node.left)
                rhs = self.EvalToInt(node.right)

                if op_id == Id.Arith_Plus:
                    ret = lhs + rhs
                elif op_id == Id.Arith_Minus:
                    ret = lhs - rhs
                elif op_id == Id.Arith_Star:
                    ret = lhs * rhs
                elif op_id == Id.Arith_Slash:
                    if rhs == 0:
                        # TODO: blame / operator
                        e_die('Divide by zero', loc.Arith(node.right))

                    ret = lhs / rhs

                elif op_id == Id.Arith_Percent:
                    if rhs == 0:
                        # TODO: blame / operator
                        e_die('Divide by zero', loc.Arith(node.right))

                    ret = lhs % rhs

                elif op_id == Id.Arith_DStar:
                    if rhs < 0:
                         # TODO: error location
                        e_die("Exponent can't be less than zero", loc.Missing)
                    ret = 1
                    for i in xrange(rhs):
                        ret *= lhs

                elif op_id == Id.Arith_DEqual:
                    ret = int(lhs == rhs)
                elif op_id == Id.Arith_NEqual:
                    ret = int(lhs != rhs)
                elif op_id == Id.Arith_Great:
                    ret = int(lhs > rhs)
                elif op_id == Id.Arith_GreatEqual:
                    ret = int(lhs >= rhs)
                elif op_id == Id.Arith_Less:
                    ret = int(lhs < rhs)
                elif op_id == Id.Arith_LessEqual:
                    ret = int(lhs <= rhs)

                elif op_id == Id.Arith_Pipe:
                    ret = lhs | rhs
                elif op_id == Id.Arith_Amp:
                    ret = lhs & rhs
                elif op_id == Id.Arith_Caret:
                    ret = lhs ^ rhs

                # Note: how to define shift of negative numbers?
                elif op_id == Id.Arith_DLess:
                    ret = lhs << rhs
                elif op_id == Id.Arith_DGreat:
                    ret = lhs >> rhs
                else:
                    raise AssertionError(op_id)

                return value.Int(ret)

            elif case(arith_expr_e.TernaryOp):
                node = cast(arith_expr.TernaryOp, UP_node)

                cond = self.EvalToInt(node.cond)
                if cond:  # nonzero
                    return self.Eval(node.true_expr)
                else:
                    return self.Eval(node.false_expr)

            else:
                raise AssertionError(node.tag())

        raise AssertionError('for -Wreturn-type in C++')

    def EvalWordToString(self, node):
        # type: (arith_expr_t) -> str
        """
    Args:
      node: arith_expr_t

    Returns:
      str

    Raises:
      error.FatalRuntime if the expression isn't a string
      Or if it contains a bare variable like a[x]

    These are allowed because they're unambiguous, unlike a[x]

    a[$x] a["$x"] a["x"] a['x']
    """
        UP_node = node
        if node.tag() == arith_expr_e.Word:  # $(( $x )) $(( ${x}${y} )), etc.
            w = cast(CompoundWord, UP_node)
            val = self.word_ev.EvalWordToString(w)
            return val.s
        else:
            # TODO: location info for original
            e_die("Associative array keys must be strings: $x 'x' \"$x\" etc.")

    def EvalShellLhs(self, node, which_scopes):
        # type: (sh_lhs_expr_t, scope_t) -> lvalue_t
        """Evaluate a shell LHS expression, i.e. place expression.

        For  a=b  and  a[x]=b  etc.
        """
        assert isinstance(node, sh_lhs_expr_t), node

        UP_node = node
        lval = None  # type: lvalue_t
        with tagswitch(node) as case:
            if case(sh_lhs_expr_e.Name):  # a=x
                node = cast(sh_lhs_expr.Name, UP_node)
                assert node.name is not None

                lval1 = lvalue.Named(node.name, node.left)
                lval = lval1

            elif case(sh_lhs_expr_e.IndexedName):  # a[1+2]=x
                node = cast(sh_lhs_expr.IndexedName, UP_node)
                assert node.name is not None

                if self.mem.IsBashAssoc(node.name):
                    key = self.EvalWordToString(node.index)
                    lval2 = lvalue.Keyed(node.name, key, node.left)
                    lval = lval2
                else:
                    index = self.EvalToInt(node.index)
                    lval3 = lvalue.Indexed(node.name, index, node.left)
                    lval = lval3

            else:
                raise AssertionError(node.tag())

        return lval

    def _VarNameOrWord(self, anode):
        # type: (arith_expr_t) -> Tuple[Optional[str], loc_t]
        """Returns a variable name if the arith node can be interpreted that
        way."""
        UP_anode = anode
        with tagswitch(anode) as case:
            if case(arith_expr_e.VarSub):
                tok = cast(SimpleVarSub, UP_anode)
                return (tok.var_name, tok.left)

            elif case(arith_expr_e.Word):
                w = cast(CompoundWord, UP_anode)
                var_name = self.EvalWordToString(w)
                return (var_name, w)

        no_str = None  # type: str
        return (no_str, loc.Missing)

    def EvalArithLhs(self, anode):
        # type: (arith_expr_t) -> lvalue_t
        """
    For (( a[x] = 1 )) etc.
    """
        UP_anode = anode
        if anode.tag() == arith_expr_e.Binary:
            anode = cast(arith_expr.Binary, UP_anode)
            if anode.op_id == Id.Arith_LBracket:
                var_name, location = self._VarNameOrWord(anode.left)

                # (( 1[2] = 3 )) isn't valid
                if not match.IsValidVarName(var_name):
                    e_die('Invalid variable name %r' % var_name, location)

                if var_name is not None:
                    if self.mem.IsBashAssoc(var_name):
                        key = self.EvalWordToString(anode.right)
                        return lvalue.Keyed(var_name, key, location)
                    else:
                        index = self.EvalToInt(anode.right)
                        return lvalue.Indexed(var_name, index, location)

        var_name, location = self._VarNameOrWord(anode)
        if var_name is not None:
            return lvalue.Named(var_name, location)

        # e.g. unset 'x-y'.  status 2 for runtime parse error
        e_die_status(2, 'Invalid place to modify', location)


class BoolEvaluator(ArithEvaluator):
    """This is also an ArithEvaluator because it has to understand.

    [[ x -eq 3 ]]

    where x='1+2'
    """

    def __init__(self,
                 mem,
                 exec_opts,
                 mutable_opts,
                 parse_ctx,
                 errfmt,
                 always_strict=False):
        # type: (state.Mem, optview.Exec, Optional[state.MutableOpts], Optional[parse_lib.ParseContext], ErrorFormatter, bool) -> None
        ArithEvaluator.__init__(self, mem, exec_opts, mutable_opts, parse_ctx,
                                errfmt)
        self.always_strict = always_strict

    def _StringToIntegerOrError(self, s, blame_word=None):
        # type: (str, Optional[word_t]) -> int
        """Used by both [[ $x -gt 3 ]] and (( $x ))."""
        if blame_word:
            location = loc.Word(blame_word)  # type: loc_t
        else:
            location = loc.Missing

        try:
            i = self._StringToInteger(s, location)
        except error.Strict as e:
            if self.always_strict or self.exec_opts.strict_arith():
                raise
            else:
                i = 0
        return i

    def _EvalCompoundWord(self, word, eval_flags=0):
        # type: (word_t, int) -> str
        val = self.word_ev.EvalWordToString(word, eval_flags)
        return val.s

    def EvalB(self, node):
        # type: (bool_expr_t) -> bool

        UP_node = node
        with tagswitch(node) as case:
            if case(bool_expr_e.WordTest):
                node = cast(bool_expr.WordTest, UP_node)
                s = self._EvalCompoundWord(node.w)
                return bool(s)

            elif case(bool_expr_e.LogicalNot):
                node = cast(bool_expr.LogicalNot, UP_node)
                b = self.EvalB(node.child)
                return not b

            elif case(bool_expr_e.LogicalAnd):
                node = cast(bool_expr.LogicalAnd, UP_node)
                # Short-circuit evaluation
                if self.EvalB(node.left):
                    return self.EvalB(node.right)
                else:
                    return False

            elif case(bool_expr_e.LogicalOr):
                node = cast(bool_expr.LogicalOr, UP_node)
                if self.EvalB(node.left):
                    return True
                else:
                    return self.EvalB(node.right)

            elif case(bool_expr_e.Unary):
                node = cast(bool_expr.Unary, UP_node)
                op_id = node.op_id
                s = self._EvalCompoundWord(node.child)

                # Now dispatch on arg type
                arg_type = consts.BoolArgType(
                    op_id)  # could be static in the LST?

                if arg_type == bool_arg_type_e.Path:
                    return bool_stat.DoUnaryOp(op_id, s)

                if arg_type == bool_arg_type_e.Str:
                    if op_id == Id.BoolUnary_z:
                        return not bool(s)
                    if op_id == Id.BoolUnary_n:
                        return bool(s)

                    raise AssertionError(op_id)  # should never happen

                if arg_type == bool_arg_type_e.Other:
                    if op_id == Id.BoolUnary_t:
                        return bool_stat.isatty(s, node.child)

                    # See whether 'set -o' options have been set
                    if op_id == Id.BoolUnary_o:
                        index = consts.OptionNum(s)
                        if index == 0:
                            return False
                        else:
                            return self.exec_opts.opt0_array[index]

                    if op_id == Id.BoolUnary_v:
                        val = self.mem.GetValue(s)
                        return val.tag() != value_e.Undef

                    e_die("%s isn't implemented" %
                          ui.PrettyId(op_id))  # implicit location

                raise AssertionError(arg_type)

            elif case(bool_expr_e.Binary):
                node = cast(bool_expr.Binary, UP_node)

                op_id = node.op_id
                # Whether to glob escape
                eval_flags = 0
                with switch(op_id) as case2:
                    if case2(Id.BoolBinary_GlobEqual, Id.BoolBinary_GlobDEqual,
                             Id.BoolBinary_GlobNEqual):
                        eval_flags |= word_eval.QUOTE_FNMATCH
                    elif case2(Id.BoolBinary_EqualTilde):
                        eval_flags |= word_eval.QUOTE_ERE

                s1 = self._EvalCompoundWord(node.left)
                s2 = self._EvalCompoundWord(node.right, eval_flags)

                # Now dispatch on arg type
                arg_type = consts.BoolArgType(op_id)

                if arg_type == bool_arg_type_e.Path:
                    return bool_stat.DoBinaryOp(op_id, s1, s2)

                if arg_type == bool_arg_type_e.Int:
                    # NOTE: We assume they are constants like [[ 3 -eq 3 ]].
                    # Bash also allows [[ 1+2 -eq 3 ]].
                    i1 = self._StringToIntegerOrError(s1, blame_word=node.left)
                    i2 = self._StringToIntegerOrError(s2, blame_word=node.right)

                    if op_id == Id.BoolBinary_eq:
                        return i1 == i2
                    if op_id == Id.BoolBinary_ne:
                        return i1 != i2
                    if op_id == Id.BoolBinary_gt:
                        return i1 > i2
                    if op_id == Id.BoolBinary_ge:
                        return i1 >= i2
                    if op_id == Id.BoolBinary_lt:
                        return i1 < i2
                    if op_id == Id.BoolBinary_le:
                        return i1 <= i2

                    raise AssertionError(op_id)  # should never happen

                if arg_type == bool_arg_type_e.Str:

                    if op_id in (Id.BoolBinary_GlobEqual,
                                 Id.BoolBinary_GlobDEqual):
                        #log('Matching %s against pattern %s', s1, s2)
                        return libc.fnmatch(s2, s1)

                    if op_id == Id.BoolBinary_GlobNEqual:
                        return not libc.fnmatch(s2, s1)

                    if op_id in (Id.BoolBinary_Equal, Id.BoolBinary_DEqual):
                        return s1 == s2

                    if op_id == Id.BoolBinary_NEqual:
                        return s1 != s2

                    if op_id == Id.BoolBinary_EqualTilde:
                        # TODO: This should go to --debug-file
                        #log('Matching %r against regex %r', s1, s2)
                        try:
                            matches = libc.regex_match(s2, s1)
                        except RuntimeError as e:
                            # Status 2 indicates a regex parse error.  This is fatal in OSH but
                            # not in bash, which treats [[ like a command with an exit code.
                            msg = e.message  # type: str
                            e_die_status(2, 'Invalid regex %r: %s' % (s2, msg),
                                         loc.Word(node.right))

                        if matches is not None:
                            self.mem.SetMatches(matches)
                            return True
                        else:
                            self.mem.ClearMatches()
                            return False

                    if op_id == Id.Op_Less:
                        return str_cmp(s1, s2) < 0

                    if op_id == Id.Op_Great:
                        return str_cmp(s1, s2) > 0

                    raise AssertionError(op_id)  # should never happen

        raise AssertionError(node.tag())
