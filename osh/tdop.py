"""
tdop.py - Library for expression parsing.
"""

from _devbuild.gen.id_kind_asdl import Id, Id_t
from _devbuild.gen.syntax_asdl import (loc, arith_expr, arith_expr_e,
                                       arith_expr_t, word_e, word_t,
                                       CompoundWord, Token)
from core.error import p_die
from display import ui
from mycpp import mylib
from mycpp.mylib import tagswitch
from osh import word_

from typing import (Callable, List, Dict, Tuple, Any, cast, TYPE_CHECKING)

if TYPE_CHECKING:  # break circular dep
    from osh.word_parse import WordParser
    from core import optview
    LeftFunc = Callable[['TdopParser', word_t, arith_expr_t, int],
                        arith_expr_t]
    NullFunc = Callable[['TdopParser', word_t, int], arith_expr_t]


def IsIndexable(node):
    # type: (arith_expr_t) -> bool
    """In POSIX shell arith, a[1] is allowed but a[1][1] isn't.

    We also allow $a[i] and foo$x[i] (formerly parse_dynamic_arith)
    """
    with tagswitch(node) as case:
        if case(arith_expr_e.VarSub, arith_expr_e.Word):
            return True
    return False


def CheckLhsExpr(node, blame_word):
    # type: (arith_expr_t, word_t) -> None
    """Determine if a node is a valid L-value by whitelisting tags.

    Valid:
      x = y
      a[1] = y
    Invalid:
      a[0][0] = y
    """
    UP_node = node
    if node.tag() == arith_expr_e.Binary:
        node = cast(arith_expr.Binary, UP_node)
        if node.op.id == Id.Arith_LBracket and IsIndexable(node.left):
            return
        # But a[0][0] = 1 is NOT valid.

    if IsIndexable(node):
        return

    p_die("Left-hand side of this assignment is invalid", loc.Word(blame_word))


#
# Null Denotation
#


def NullError(p, t, bp):
    # type: (TdopParser, word_t, int) -> arith_expr_t
    # TODO: I need position information
    p_die("Token can't be used in prefix position", loc.Word(t))
    return None  # never reached


def NullConstant(p, w, bp):
    # type: (TdopParser, word_t, int) -> arith_expr_t
    name_tok = word_.LooksLikeArithVar(w)
    if name_tok:
        return name_tok

    # Id.Word_Compound in the spec ensures this cast is valid
    return cast(CompoundWord, w)


def NullParen(p, t, bp):
    # type: (TdopParser, word_t, int) -> arith_expr_t
    """Arithmetic grouping."""
    r = p.ParseUntil(bp)
    p.Eat(Id.Arith_RParen)
    return r


def NullPrefixOp(p, w, bp):
    # type: (TdopParser, word_t, int) -> arith_expr_t
    """Prefix operator.

    Low precedence:  return, raise, etc.
      return x+y is return (x+y), not (return x) + y

    High precedence: logical negation, bitwise complement, etc.
      !x && y is (!x) && y, not !(x && y)
    """
    right = p.ParseUntil(bp)
    return arith_expr.Unary(word_.ArithId(w), right)


#
# Left Denotation
#


def LeftError(p, t, left, rbp):
    # type: (TdopParser, word_t, arith_expr_t, int) -> arith_expr_t
    # Hm is this not called because of binding power?
    p_die("Token can't be used in infix position", loc.Word(t))
    return None  # never reached


def LeftBinaryOp(p, w, left, rbp):
    # type: (TdopParser, word_t, arith_expr_t, int) -> arith_expr_t
    """Normal binary operator like 1+2 or 2*3, etc."""

    assert w.tag() == word_e.Operator, w
    tok = cast(Token, w)

    return arith_expr.Binary(tok, left, p.ParseUntil(rbp))


def LeftAssign(p, w, left, rbp):
    # type: (TdopParser, word_t, arith_expr_t, int) -> arith_expr_t
    """Normal binary operator like 1+2 or 2*3, etc."""
    # x += 1, or a[i] += 1

    CheckLhsExpr(left, w)
    return arith_expr.BinaryAssign(word_.ArithId(w), left, p.ParseUntil(rbp))


#
# Parser definition
# TODO: To be consistent, move this to osh/tdop_def.py.
#

if mylib.PYTHON:

    def _ModuleAndFuncName(f):
        # type: (Any) -> Tuple[str, str]
        namespace = f.__module__.split('.')[-1]
        return namespace, f.__name__

    def _CppFuncName(f):
        # type: (Any) -> str
        return '%s::%s' % _ModuleAndFuncName(f)

    class LeftInfo(object):
        """Row for operator.

        In C++ this should be a big array.
        """

        def __init__(self, led=None, lbp=0, rbp=0):
            # type: (LeftFunc, int, int) -> None
            self.led = led or LeftError
            self.lbp = lbp
            self.rbp = rbp

        def __str__(self):
            # type: () -> str
            """Used by C++ code generation."""
            return '{ %s, %d, %d },' % (_CppFuncName(
                self.led), self.lbp, self.rbp)

        def ModuleAndFuncName(self):
            # type: () -> Tuple[str, str]
            """Used by C++ code generation."""
            return _ModuleAndFuncName(self.led)

    class NullInfo(object):
        """Row for operator.

        In C++ this should be a big array.
        """

        def __init__(self, nud=None, bp=0):
            # type: (NullFunc, int) -> None
            self.nud = nud or LeftError
            self.bp = bp

        def __str__(self):
            # type: () -> str
            """Used by C++ code generation."""
            return '{ %s, %d },' % (_CppFuncName(self.nud), self.bp)

        def ModuleAndFuncName(self):
            # type: () -> Tuple[str, str]
            """Used by C++ code generation."""
            return _ModuleAndFuncName(self.nud)

    class ParserSpec(object):
        """Specification for a TDOP parser.

        This can be compiled to a table in C++.
        """

        def __init__(self):
            # type: () -> None
            self.nud_lookup = {}  # type: Dict[Id_t, NullInfo]
            self.led_lookup = {}  # type: Dict[Id_t, LeftInfo]

        def Null(self, bp, nud, tokens):
            # type: (int, NullFunc, List[Id_t]) -> None
            """Register a token that doesn't take anything on the left.

            Examples: constant, prefix operator, error.
            """
            for token in tokens:
                self.nud_lookup[token] = NullInfo(nud=nud, bp=bp)
                if token not in self.led_lookup:
                    self.led_lookup[token] = LeftInfo()  # error

        def _RegisterLed(self, lbp, rbp, led, tokens):
            # type: (int, int, LeftFunc, List[Id_t]) -> None
            for token in tokens:
                if token not in self.nud_lookup:
                    self.nud_lookup[token] = NullInfo(NullError)
                self.led_lookup[token] = LeftInfo(lbp=lbp, rbp=rbp, led=led)

        def Left(self, bp, led, tokens):
            # type: (int, LeftFunc, List[Id_t]) -> None
            """Register a token that takes an expression on the left."""
            self._RegisterLed(bp, bp, led, tokens)

        def LeftRightAssoc(self, bp, led, tokens):
            # type: (int, LeftFunc, List[Id_t]) -> None
            """Register a right associative operator."""
            self._RegisterLed(bp, bp - 1, led, tokens)

        def LookupNud(self, token):
            # type: (Id_t) -> NullInfo

            # As long as the table is complete, this shouldn't fail
            return self.nud_lookup[token]

        def LookupLed(self, token):
            # type: (Id_t) -> LeftInfo
            """Get a left_info for the token."""

            # As long as the table is complete, this shouldn't fail
            return self.led_lookup[token]


class TdopParser(object):

    def __init__(self, spec, w_parser, parse_opts):
        # type: (ParserSpec, WordParser, optview.Parse) -> None
        self.spec = spec
        self.w_parser = w_parser
        self.parse_opts = parse_opts

        # NOTE: Next() overwrites this state, so we don't need a Reset() method in
        # between reuses of this TdopParser instance.
        self.cur_word = None  # type: word_t  # current token
        self.op_id = Id.Undefined_Tok

    def CurrentId(self):
        # type: () -> Id_t
        """Glue used by the WordParser to check for extra tokens."""
        return word_.ArithId(self.cur_word)

    def AtToken(self, token_type):
        # type: (Id_t) -> bool
        return self.op_id == token_type

    def Eat(self, token_type):
        # type: (Id_t) -> None
        """Assert that we're at the current token and advance."""
        if not self.AtToken(token_type):
            p_die(
                'Parser expected %s, got %s' %
                (ui.PrettyId(token_type), ui.PrettyId(self.op_id)),
                loc.Word(self.cur_word))
        self.Next()

    def Next(self):
        # type: () -> bool
        self.cur_word = self.w_parser.ReadArithWord()
        self.op_id = word_.ArithId(self.cur_word)
        return True

    def ParseUntil(self, rbp):
        # type: (int) -> arith_expr_t
        """Parse to the right, eating tokens until we encounter a token with
        binding power LESS THAN OR EQUAL TO rbp."""
        # TODO: use Kind.Eof
        if self.op_id in (Id.Eof_Real, Id.Eof_RParen, Id.Eof_Backtick):
            p_die('Unexpected end of input', loc.Word(self.cur_word))

        t = self.cur_word
        null_info = self.spec.LookupNud(self.op_id)

        self.Next()  # skip over the token, e.g. ! ~ + -
        node = null_info.nud(self, t, null_info.bp)

        while True:
            t = self.cur_word
            left_info = self.spec.LookupLed(self.op_id)

            # Examples:
            # If we see 1*2+  , rbp = 27 and lbp = 25, so stop.
            # If we see 1+2+  , rbp = 25 and lbp = 25, so stop.
            # If we see 1**2**, rbp = 26 and lbp = 27, so keep going.
            if rbp >= left_info.lbp:
                break
            self.Next()  # skip over the token, e.g. / *

            node = left_info.led(self, t, node, left_info.rbp)

        return node

    def Parse(self):
        # type: () -> arith_expr_t

        self.Next()  # may raise ParseError

        if not self.parse_opts.parse_sh_arith():
            # Affects:
            #    echo $(( x ))
            #    ${a[i]} which should be $[a[i]] -- could have better error
            #
            # Note: sh_expr_eval.UnsafeArith has a dynamic e_die() check
            #
            # Doesn't affect:
            #    printf -v x         # unsafe_arith.ParseLValue
            #    unset x             # unsafe_arith.ParseLValue
            #    ${!ref}             # unsafe_arith.ParseVarRef
            #    declare -n          # not fully implemented yet
            #
            #    a[i+1]=             # parse_sh_assign
            #
            #    (( a = 1 ))         # parse_dparen
            #    for (( i = 0; ...   # parse_dparen

            p_die("POSIX shell arithmetic isn't allowed (parse_sh_arith)",
                  loc.Word(self.cur_word))

        return self.ParseUntil(0)
