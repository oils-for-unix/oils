"""expr_to_ast.py."""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str, Kind
from _devbuild.gen.syntax_asdl import (
    Token,
    SimpleVarSub,
    loc,
    loc_t,
    DoubleQuoted,
    SingleQuoted,
    BracedVarSub,
    CommandSub,
    ShArrayLiteral,
    command,
    expr,
    expr_e,
    expr_t,
    expr_context_e,
    re,
    re_t,
    re_repeat,
    re_repeat_t,
    class_literal_term,
    class_literal_term_t,
    PosixClass,
    PerlClass,
    NameType,
    y_lhs_t,
    Comprehension,
    Subscript,
    Attribute,
    proc_sig,
    proc_sig_t,
    Param,
    RestParam,
    ParamGroup,
    NamedArg,
    ArgList,
    pat,
    pat_t,
    TypeExpr,
    Func,
    Eggex,
    EggexFlag,
    CharCode,
    CharRange,
)
from _devbuild.gen.value_asdl import value, value_t
from _devbuild.gen import grammar_nt
from core.error import p_die
from data_lang import j8
from frontend import consts
from frontend import lexer
from frontend import location
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import log, tagswitch
from osh import word_compile
from ysh import expr_parse
from ysh import regex_translate

from typing import TYPE_CHECKING, Dict, List, Tuple, Optional, cast
if TYPE_CHECKING:
    from pgen2.grammar import Grammar
    from pgen2.pnode import PNode

_ = log

PERL_CLASSES = {
    'd': 'd',
    'w': 'w',
    'word': 'w',
    's': 's',
}
# https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html
POSIX_CLASSES = [
    'alnum',
    'cntrl',
    'lower',
    'space',
    'alpha',
    'digit',
    'print',
    'upper',
    'blank',
    'graph',
    'punct',
    'xdigit',
]
# NOTE: There are also things like \p{Greek} that we could put in the
# "non-sigil" namespace.

RANGE_POINT_TOO_LONG = "Range start/end shouldn't have more than one character"

POS_ARG_MISPLACED = "Positional arg can't appear in group of named args"

# Copied from pgen2/token.py to avoid dependency.
NT_OFFSET = 256

if mylib.PYTHON:

    def MakeGrammarNames(ysh_grammar):
        # type: (Grammar) -> Dict[int, str]

        # TODO: Break this dependency
        from frontend import lexer_def

        names = {}

        for id_name, k in lexer_def.ID_SPEC.id_str2int.items():
            # Hm some are out of range
            #assert k < 256, (k, id_name)

            # TODO: Some tokens have values greater than NT_OFFSET
            if k < NT_OFFSET:
                names[k] = id_name

        for k, v in ysh_grammar.number2symbol.items():
            assert k >= NT_OFFSET, (k, v)
            names[k] = v

        return names


class Transformer(object):
    """Homogeneous parse tree -> heterogeneous AST ("lossless syntax tree")

    pgen2 (Python's LL parser generator) doesn't have semantic actions like yacc,
    so this "transformer" is the equivalent.

    Files to refer to when modifying this function:

      ysh/grammar.pgen2 (generates _devbuild/gen/grammar_nt.py)
      frontend/syntax.asdl   (generates _devbuild/gen/syntax_asdl.py)

    Related examples:

      opy/compiler2/transformer.py (Python's parse tree -> AST, ~1500 lines)
      Python-2.7.13/Python/ast.c   (the "real" CPython version, ~3600 lines)

    Other:
      frontend/parse_lib.py  (turn on print_parse_tree)

    Public methods:
      Expr, VarDecl
      atom, trailer, etc. are private, named after productions in grammar.pgen2.
    """

    def __init__(self, gr):
        # type: (Grammar) -> None
        self.number2symbol = gr.number2symbol
        if mylib.PYTHON:
            names = MakeGrammarNames(gr)
            # print raw nodes
            self.p_printer = expr_parse.ParseTreePrinter(names)

    def _LeftAssoc(self, p_node):
        # type: (PNode) -> expr_t
        """For an associative binary operation.

        Examples:
          xor_expr: and_expr ('xor' and_expr)*
          term: factor (('*'|'/'|'%'|'div') factor)*

        3 - 1 - 2 must be grouped as ((3 - 1) - 2).
        """
        # Note: Compare the iteractive com_binary() method in
        # opy/compiler2/transformer.py.

        # Examples:
        # - The PNode for '3 - 1' will have 3 children
        # - The PNode for '3 - 1 - 2' will have 5 children

        #self.p_printer.Print(p_node)

        i = 1  # index of the operator
        n = p_node.NumChildren()

        left = self.Expr(p_node.GetChild(0))
        while i < n:
            op = p_node.GetChild(i)
            right = self.Expr(p_node.GetChild(i + 1))

            # create a new left node
            left = expr.Binary(op.tok, left, right)
            i += 2

        return left

    def _Trailer(self, base, p_trailer):
        # type: (expr_t, PNode) -> expr_t
        """
        trailer: ( '(' [arglist] ')' | '[' subscriptlist ']'
                 | '.' NAME | '->' NAME | '::' NAME
                 )
        """
        tok0 = p_trailer.GetChild(0).tok
        typ0 = p_trailer.GetChild(0).typ

        if typ0 == Id.Op_LParen:
            lparen = tok0
            rparen = p_trailer.GetChild(-1).tok
            arglist = ArgList(lparen, [], None, [], None, None, rparen)
            if p_trailer.NumChildren() == 2:  # ()
                return expr.FuncCall(base, arglist)

            p = p_trailer.GetChild(1)  # the X in ( X )
            assert p.typ == grammar_nt.arglist  # f(x, y)
            self._ArgList(p, arglist)
            return expr.FuncCall(base, arglist)

        if typ0 == Id.Op_LBracket:
            p_args = p_trailer.GetChild(1)
            assert p_args.typ == grammar_nt.subscriptlist
            n = p_args.NumChildren()
            if n > 1:
                p_die("Only 1 subscript is accepted", p_args.GetChild(1).tok)

            a = p_args.GetChild(0)
            return Subscript(tok0, base, self._Subscript(a))

        if typ0 in (Id.Expr_Dot, Id.Expr_RArrow, Id.Expr_RDArrow):
            attr = p_trailer.GetChild(1).tok  # will be Id.Expr_Name
            return Attribute(base, tok0, attr, lexer.TokenVal(attr),
                             expr_context_e.Store)

        raise AssertionError(typ0)

    def _DictPair(self, p_node):
        # type: (PNode) -> Tuple[expr_t, expr_t]
        """
        dict_pair: ( Expr_Name [':' test]
                   | '[' testlist ']' ':' test )
                   | sq_string ':' test 
                   | dq_string ':' test )
        """
        assert p_node.typ == grammar_nt.dict_pair

        typ = p_node.GetChild(0).typ

        if typ in (grammar_nt.sq_string, grammar_nt.dq_string):
            key = self.Expr(p_node.GetChild(0))  # type: expr_t
            val = self.Expr(p_node.GetChild(2))
            return key, val

        tok0 = p_node.GetChild(0).tok
        id_ = tok0.id

        if id_ == Id.Expr_Name:
            key_str = value.Str(lexer.TokenVal(tok0))
            key = expr.Const(tok0, key_str)
            if p_node.NumChildren() >= 3:
                val = self.Expr(p_node.GetChild(2))
            else:
                val = expr.Implicit

        if id_ == Id.Op_LBracket:  # {[x+y]: 'val'}
            key = self.Expr(p_node.GetChild(1))
            val = self.Expr(p_node.GetChild(4))
            return key, val

        return key, val

    def _Dict(self, parent, p_node):
        # type: (PNode, PNode) -> expr.Dict
        """
        dict: dict_pair (comma_newline dict_pair)* [comma_newline]
        """
        if p_node.typ == Id.Op_RBrace:  # {}
            return expr.Dict(parent.tok, [], [])

        assert p_node.typ == grammar_nt.dict

        keys = []  # type: List[expr_t]
        values = []  # type: List[expr_t]

        n = p_node.NumChildren()
        for i in xrange(0, n, 2):
            key, val = self._DictPair(p_node.GetChild(i))
            keys.append(key)
            values.append(val)

        return expr.Dict(parent.tok, keys, values)

    def _Tuple(self, parent):
        # type: (PNode) -> expr_t

        n = parent.NumChildren()

        # (x) -- not a tuple
        if n == 1:
            return self.Expr(parent.GetChild(0))

        # x, and (x,) aren't allowed
        if n == 2:
            p_die('Invalid trailing comma', parent.GetChild(1).tok)

        elts = []  # type: List[expr_t]
        for i in xrange(0, n, 2):  # skip commas
            p_node = parent.GetChild(i)
            elts.append(self.Expr(p_node))

        return expr.Tuple(parent.tok, elts,
                          expr_context_e.Store)  # unused expr_context_e

    def _TestlistComp(self, parent, p_node, id0):
        # type: (PNode, PNode, Id_t) -> expr_t
        """
        testlist_comp:
          (test|star_expr) ( comp_for | (',' (test|star_expr))* [','] )
        """
        assert p_node.typ == grammar_nt.testlist_comp

        n = p_node.NumChildren()
        if n > 1 and p_node.GetChild(1).typ == grammar_nt.comp_for:
            elt = self.Expr(p_node.GetChild(0))
            comp = self._CompFor(p_node.GetChild(1))
            if id0 == Id.Op_LParen:  # (x+1 for x in y)
                return expr.GeneratorExp(elt, [comp])
            if id0 == Id.Op_LBracket:  # [x+1 for x in y]
                return expr.ListComp(parent.tok, elt, [comp])
            raise AssertionError()

        if id0 == Id.Op_LParen:
            # Parenthesized expression like (x+1) or (x)
            if n == 1:
                return self.Expr(p_node.GetChild(0))

            # Tuples (1,)  (1, 2)  etc. - TODO: should be a list literal?
            if p_node.GetChild(1).typ == Id.Arith_Comma:
                return self._Tuple(p_node)

            raise AssertionError()

        if id0 == Id.Op_LBracket:  # List [1,2,3]
            elts = []  # type: List[expr_t]
            for i in xrange(0, n, 2):  # skip commas
                elts.append(self.Expr(p_node.GetChild(i)))

            return expr.List(parent.tok, elts,
                             expr_context_e.Store)  # unused expr_context_e

        raise AssertionError(Id_str(id0))

    def _Atom(self, parent):
        # type: (PNode) -> expr_t
        """Handle alternatives of 'atom' where there's more than one child."""

        tok = parent.GetChild(0).tok
        id_ = tok.id
        n = parent.NumChildren()

        if id_ == Id.Op_LParen:
            # atom: '(' [yield_expr|testlist_comp] ')' | ...
            if n == 2:  # () is a tuple
                assert (
                    parent.GetChild(1).typ == Id.Op_RParen), parent.GetChild(1)
                return expr.Tuple(tok, [], expr_context_e.Store)

            return self._TestlistComp(parent, parent.GetChild(1), id_)

        if id_ == Id.Op_LBracket:
            # atom: ... | '[' [testlist_comp] ']' | ...

            if n == 2:  # []
                assert (parent.GetChild(1).typ == Id.Op_RBracket
                        ), parent.GetChild(1)
                return expr.List(tok, [],
                                 expr_context_e.Store)  # unused expr_context_e

            return self._TestlistComp(parent, parent.GetChild(1), id_)

        if id_ == Id.Left_CaretBracket:  # ^[42 + x]
            child = self.Expr(parent.GetChild(1))
            return expr.Literal(child)

        if id_ == Id.Op_LBrace:
            # atom: ... | '{' [Op_Newline] [dict] '}'
            i = 1
            if parent.GetChild(i).typ == Id.Op_Newline:
                i += 1
            return self._Dict(parent, parent.GetChild(i))

        if id_ == Id.Arith_Amp:
            n = parent.NumChildren()
            if n >= 3:
                p_die("Places in containers not implemented yet",
                      parent.GetChild(2).tok)

            name_tok = parent.GetChild(1).tok
            return expr.Place(name_tok, lexer.TokenVal(name_tok), [])

        if id_ == Id.Expr_Func:
            # STUB.  This should really be a Func, not Lambda.
            return expr.Lambda([], expr.Implicit)

        # 100 M
        # Ignoring the suffix for now
        if id_ == Id.Expr_DecInt:
            assert n > 1
            p_die("Units suffix not implemented", parent.GetChild(1).tok)
            #return self.Expr(parent.GetChild(0))

        # 100.5 M
        # Ignoring the suffix for now
        if id_ == Id.Expr_Float:
            assert n > 1
            p_die("unix suffix implemented", parent.GetChild(1).tok)
            #return self.Expr(parent.GetChild(0))

        raise AssertionError(Id_str(id_))

    def _NameType(self, p_node):
        # type: (PNode) -> NameType
        """ name_type: Expr_Name [':'] [type_expr] """
        name_tok = p_node.GetChild(0).tok
        typ = None  # type: Optional[TypeExpr]

        n = p_node.NumChildren()
        if n == 2:
            typ = self._TypeExpr(p_node.GetChild(1))
        if n == 3:
            typ = self._TypeExpr(p_node.GetChild(2))

        return NameType(name_tok, lexer.TokenVal(name_tok), typ)

    def _NameTypeList(self, p_node):
        # type: (PNode) -> List[NameType]
        """ name_type_list: name_type (',' name_type)* """
        assert p_node.typ == grammar_nt.name_type_list
        results = []  # type: List[NameType]

        n = p_node.NumChildren()
        for i in xrange(0, n, 2):  # was children[::2]
            results.append(self._NameType(p_node.GetChild(i)))
        return results

    def _CompFor(self, p_node):
        # type: (PNode) -> Comprehension
        """comp_for: 'for' exprlist 'in' or_test ['if' or_test]"""
        lhs = self._NameTypeList(p_node.GetChild(1))
        iterable = self.Expr(p_node.GetChild(3))

        if p_node.NumChildren() >= 6:
            cond = self.Expr(p_node.GetChild(5))
        else:
            cond = None

        return Comprehension(lhs, iterable, cond)

    def _CompareChain(self, parent):
        # type: (PNode) -> expr_t
        """comparison: expr (comp_op expr)*"""
        cmp_ops = []  # type: List[Token]
        comparators = []  # type: List[expr_t]
        left = self.Expr(parent.GetChild(0))

        i = 1
        n = parent.NumChildren()
        while i < n:
            p = parent.GetChild(i)
            op = p.GetChild(0).tok
            if p.NumChildren() == 2:
                # Blame the first token, and change its type
                if op.id == Id.Expr_Not:  # not in
                    op.id = Id.Node_NotIn
                elif op.id == Id.Expr_Is:  # is not
                    op.id = Id.Node_IsNot
                else:
                    raise AssertionError()
            else:
                # is, <, ==, etc.
                pass

            cmp_ops.append(op)
            i += 1
            comparators.append(self.Expr(parent.GetChild(i)))
            i += 1
        return expr.Compare(left, cmp_ops, comparators)

    def _Subscript(self, parent):
        # type: (PNode) -> expr_t
        """subscript: expr | [expr] ':' [expr]"""
        typ0 = parent.GetChild(0).typ

        n = parent.NumChildren()

        if typ0 == grammar_nt.expr:
            if n == 3:  # a[1:2]
                lower = self.Expr(parent.GetChild(0))
                upper = self.Expr(parent.GetChild(2))
            elif n == 2:  # a[1:]
                lower = self.Expr(parent.GetChild(0))
                upper = None
            else:  # a[1]
                return self.Expr(parent.GetChild(0))
        else:
            assert typ0 == Id.Arith_Colon
            lower = None
            if n == 1:  # a[:]
                upper = None
            else:  # a[:3]
                upper = self.Expr(parent.GetChild(1))

        return expr.Slice(lower, parent.GetChild(0).tok, upper)

    def Expr(self, pnode):
        # type: (PNode) -> expr_t
        """Transform expressions (as opposed to statements)"""
        typ = pnode.typ

        #
        # YSH Entry Points / Additions
        #

        if typ == grammar_nt.ysh_expr:  # for if/while
            # ysh_expr: '(' testlist ')'
            return self.Expr(pnode.GetChild(1))

        if typ == grammar_nt.command_expr:
            # return_expr: testlist end_stmt
            return self.Expr(pnode.GetChild(0))

        #
        # Python-like Expressions / Operators
        #

        if typ == grammar_nt.atom:
            if pnode.NumChildren() == 1:
                return self.Expr(pnode.GetChild(0))
            return self._Atom(pnode)

        if typ == grammar_nt.testlist:
            # testlist: test (',' test)* [',']
            return self._Tuple(pnode)

        if typ == grammar_nt.test:
            # test: or_test ['if' or_test 'else' test] | lambdef
            if pnode.NumChildren() == 1:
                return self.Expr(pnode.GetChild(0))

            # TODO: Handle lambdef

            test = self.Expr(pnode.GetChild(2))
            body = self.Expr(pnode.GetChild(0))
            orelse = self.Expr(pnode.GetChild(4))
            return expr.IfExp(test, body, orelse)

        if typ == grammar_nt.lambdef:
            # lambdef: '|' [name_type_list] '|' test

            n = pnode.NumChildren()
            if n == 4:
                params = self._NameTypeList(pnode.GetChild(1))
            else:
                params = []

            body = self.Expr(pnode.GetChild(n - 1))
            return expr.Lambda(params, body)

        #
        # Operators with Precedence
        #

        if typ == grammar_nt.or_test:
            # or_test: and_test ('or' and_test)*
            return self._LeftAssoc(pnode)

        if typ == grammar_nt.and_test:
            # and_test: not_test ('and' not_test)*
            return self._LeftAssoc(pnode)

        if typ == grammar_nt.not_test:
            # not_test: 'not' not_test | comparison
            if pnode.NumChildren() == 1:
                return self.Expr(pnode.GetChild(0))

            op_tok = pnode.GetChild(0).tok  # not
            return expr.Unary(op_tok, self.Expr(pnode.GetChild(1)))

        elif typ == grammar_nt.comparison:
            if pnode.NumChildren() == 1:
                return self.Expr(pnode.GetChild(0))

            return self._CompareChain(pnode)

        elif typ == grammar_nt.range_expr:
            n = pnode.NumChildren()
            if n == 1:
                return self.Expr(pnode.GetChild(0))

            if n == 3:
                return expr.Range(self.Expr(pnode.GetChild(0)),
                                  pnode.GetChild(1).tok,
                                  self.Expr(pnode.GetChild(2)))

            raise AssertionError(n)

        elif typ == grammar_nt.expr:
            # expr: xor_expr ('|' xor_expr)*
            return self._LeftAssoc(pnode)

        if typ == grammar_nt.xor_expr:
            # xor_expr: and_expr ('xor' and_expr)*
            return self._LeftAssoc(pnode)

        if typ == grammar_nt.and_expr:  # a & b
            # and_expr: shift_expr ('&' shift_expr)*
            return self._LeftAssoc(pnode)

        elif typ == grammar_nt.shift_expr:
            # shift_expr: arith_expr (('<<'|'>>') arith_expr)*
            return self._LeftAssoc(pnode)

        elif typ == grammar_nt.arith_expr:
            # arith_expr: term (('+'|'-') term)*
            return self._LeftAssoc(pnode)

        elif typ == grammar_nt.term:
            # term: factor (('*'|'/'|'div'|'mod') factor)*
            return self._LeftAssoc(pnode)

        elif typ == grammar_nt.factor:
            # factor: ('+'|'-'|'~') factor | power
            # the power would have already been reduced
            if pnode.NumChildren() == 1:
                return self.Expr(pnode.GetChild(0))

            assert pnode.NumChildren() == 2
            op = pnode.GetChild(0)
            e = pnode.GetChild(1)

            assert isinstance(op.tok, Token)
            return expr.Unary(op.tok, self.Expr(e))

        elif typ == grammar_nt.power:
            # power: atom trailer* ['**' factor]

            node = self.Expr(pnode.GetChild(0))
            if pnode.NumChildren() == 1:  # No trailers
                return node

            # Support a->startswith(b) and mydict.key
            n = pnode.NumChildren()
            i = 1
            while i < n and pnode.GetChild(i).typ == grammar_nt.trailer:
                node = self._Trailer(node, pnode.GetChild(i))
                i += 1

            if i != n:  # ['**' factor]
                op_tok = pnode.GetChild(i).tok
                assert op_tok.id == Id.Arith_DStar, op_tok
                factor = self.Expr(pnode.GetChild(i + 1))
                node = expr.Binary(op_tok, node, factor)

            return node

        elif typ == grammar_nt.eggex:
            return self._Eggex(pnode)

        elif typ == grammar_nt.ysh_expr_sub:
            return self.Expr(pnode.GetChild(0))

        #
        # YSH Lexer Modes
        #

        elif typ == grammar_nt.sh_array_literal:
            return cast(ShArrayLiteral, pnode.GetChild(1).tok)

        elif typ == grammar_nt.old_sh_array_literal:
            return cast(ShArrayLiteral, pnode.GetChild(1).tok)

        elif typ == grammar_nt.sh_command_sub:
            return cast(CommandSub, pnode.GetChild(1).tok)

        elif typ == grammar_nt.braced_var_sub:
            return cast(BracedVarSub, pnode.GetChild(1).tok)

        elif typ == grammar_nt.dq_string:
            dq = cast(DoubleQuoted, pnode.GetChild(1).tok)
            # sugar: ^"..." is short for ^["..."]
            if pnode.GetChild(0).typ == Id.Left_CaretDoubleQuote:
                return expr.Literal(dq)
            return dq

        elif typ == grammar_nt.sq_string:
            return cast(SingleQuoted, pnode.GetChild(1).tok)

        elif typ == grammar_nt.simple_var_sub:
            tok = pnode.GetChild(0).tok

            if tok.id == Id.VSub_DollarName:  # $foo is disallowed
                bare = lexer.TokenSliceLeft(tok, 1)
                p_die(
                    'In expressions, remove $ and use `%s`, or sometimes "$%s"'
                    % (bare, bare), tok)

            # $? is allowed
            return SimpleVarSub(tok)

        #
        # Terminals
        #

        tok = pnode.tok
        if typ == Id.Expr_Name:
            return expr.Var(tok, lexer.TokenVal(tok))

        # Everything else is an expr.Const
        tok_str = lexer.TokenVal(tok)
        # Remove underscores from 1_000_000.  The lexer is responsible for
        # validation.
        c_under = tok_str.replace('_', '')

        if typ == Id.Expr_DecInt:
            try:
                cval = value.Int(mops.FromStr(c_under))  # type: value_t
            except ValueError:
                p_die('Decimal int constant is too large', tok)

        elif typ == Id.Expr_BinInt:
            assert c_under[:2] in ('0b', '0B'), c_under
            try:
                cval = value.Int(mops.FromStr(c_under[2:], 2))
            except ValueError:
                p_die('Binary int constant is too large', tok)

        elif typ == Id.Expr_OctInt:
            assert c_under[:2] in ('0o', '0O'), c_under
            try:
                cval = value.Int(mops.FromStr(c_under[2:], 8))
            except ValueError:
                p_die('Octal int constant is too large', tok)

        elif typ == Id.Expr_HexInt:
            assert c_under[:2] in ('0x', '0X'), c_under
            try:
                cval = value.Int(mops.FromStr(c_under[2:], 16))
            except ValueError:
                p_die('Hex int constant is too large', tok)

        elif typ == Id.Expr_Float:
            # Note: float() in mycpp/gc_builtins.cc currently uses strtod
            # I think this never raises ValueError, because the lexer
            # should only accept strings that strtod() does?
            cval = value.Float(float(c_under))

        elif typ == Id.Expr_Null:
            cval = value.Null

        elif typ == Id.Expr_True:
            cval = value.Bool(True)

        elif typ == Id.Expr_False:
            cval = value.Bool(False)

        elif typ == Id.Char_OneChar:  # \n
            assert len(tok_str) == 2, tok_str
            s = consts.LookupCharC(lexer.TokenSliceLeft(tok, 1))
            cval = value.Str(s)

        elif typ == Id.Char_YHex:  # \yff
            assert len(tok_str) == 4, tok_str
            hex_str = lexer.TokenSliceLeft(tok, 2)
            s = chr(int(hex_str, 16))
            cval = value.Str(s)

        elif typ == Id.Char_UBraced:  # \u{123}
            hex_str = lexer.TokenSlice(tok, 3, -1)
            code_point = int(hex_str, 16)
            s = j8.Utf8Encode(code_point)
            cval = value.Str(s)

        else:
            raise AssertionError(typ)

        return expr.Const(tok, cval)

    def _CheckLhs(self, lhs):
        # type: (expr_t) -> None

        UP_lhs = lhs
        with tagswitch(lhs) as case:
            if case(expr_e.Var):
                # OK - e.g. setvar a.b.c[i] = 42
                pass

            elif case(expr_e.Subscript):
                lhs = cast(Subscript, UP_lhs)
                self._CheckLhs(lhs.obj)  # recurse on LHS

            elif case(expr_e.Attribute):
                lhs = cast(Attribute, UP_lhs)
                self._CheckLhs(lhs.obj)  # recurse on LHS

            else:
                # Illegal - e.g. setglobal {}["key"] = 42
                p_die("Subscript/Attribute not allowed on this LHS expression",
                      location.TokenForExpr(lhs))

    def _LhsExprList(self, p_node):
        # type: (PNode) -> List[y_lhs_t]
        """lhs_list: expr (',' expr)*"""
        assert p_node.typ == grammar_nt.lhs_list

        lhs_list = []  # type: List[y_lhs_t]
        n = p_node.NumChildren()
        for i in xrange(0, n, 2):
            p = p_node.GetChild(i)
            #self.p_printer.Print(p)

            e = self.Expr(p)
            UP_e = e
            with tagswitch(e) as case:
                if case(expr_e.Var):
                    e = cast(expr.Var, UP_e)
                    lhs_list.append(e.left)

                elif case(expr_e.Subscript):
                    e = cast(Subscript, UP_e)
                    self._CheckLhs(e)
                    lhs_list.append(e)

                elif case(expr_e.Attribute):
                    e = cast(Attribute, UP_e)
                    self._CheckLhs(e)
                    if e.op.id != Id.Expr_Dot:
                        # e.g. setvar obj->method is not valid
                        p_die("Can't assign to this attribute expr", e.op)
                    lhs_list.append(e)

                else:
                    pass  # work around mycpp bug

                    # TODO: could blame arbitary expr_t, bu this works most of
                    # the time
                    if p.tok:
                        blame = p.tok  # type: loc_t
                    else:
                        blame = loc.Missing
                    p_die("Can't assign to this expression", blame)

        return lhs_list

    def MakeVarDecl(self, p_node):
        # type: (PNode) -> command.VarDecl
        """
        ysh_var_decl: name_type_list ['=' testlist] end_stmt
        """
        assert p_node.typ == grammar_nt.ysh_var_decl

        lhs = self._NameTypeList(p_node.GetChild(0))  # could be a tuple

        # This syntax is confusing, and different than JavaScript
        #   var x, y = 1, 2
        # But this is useful:
        #   var flag, i = parseArgs(spec, argv)

        n = p_node.NumChildren()
        if n >= 3:
            rhs = self.Expr(p_node.GetChild(2))
        else:
            rhs = None

        # The caller should fill in the keyword token.
        return command.VarDecl(None, lhs, rhs)

    def MakeMutation(self, p_node):
        # type: (PNode) -> command.Mutation
        """
        ysh_mutation: lhs_list (augassign | '=') testlist end_stmt
        """
        typ = p_node.typ
        assert typ == grammar_nt.ysh_mutation

        lhs_list = self._LhsExprList(p_node.GetChild(0))  # could be a tuple
        op_tok = p_node.GetChild(1).tok
        if len(lhs_list) > 1 and op_tok.id != Id.Arith_Equal:
            p_die('Multiple assignment must use =', op_tok)
        rhs = self.Expr(p_node.GetChild(2))
        return command.Mutation(None, lhs_list, op_tok, rhs)

    def _EggexFlag(self, p_node):
        # type: (PNode) -> EggexFlag
        n = p_node.NumChildren()
        if n == 1:
            return EggexFlag(False, p_node.GetChild(0).tok)
        elif n == 2:
            return EggexFlag(True, p_node.GetChild(1).tok)
        else:
            raise AssertionError()

    def _Eggex(self, p_node):
        # type: (PNode) -> Eggex
        """
        eggex: '/' regex [';' re_flag* [';' Expr_Name] ] '/'
        """
        left = p_node.GetChild(0).tok
        regex = self._Regex(p_node.GetChild(1))

        flags = []  # type: List[EggexFlag]
        trans_pref = None  # type: Optional[Token]

        i = 2
        current = p_node.GetChild(i)
        if current.typ == Id.Op_Semi:
            i += 1
            while True:
                current = p_node.GetChild(i)
                if current.typ != grammar_nt.re_flag:
                    break
                flags.append(self._EggexFlag(current))
                i += 1

            if current.typ == Id.Op_Semi:
                i += 1
                trans_pref = p_node.GetChild(i).tok

        # Canonicalize and validate flags for ERE only.  Default is ERE.
        if trans_pref is None or lexer.TokenVal(trans_pref) == 'ERE':
            canonical_flags = regex_translate.CanonicalFlags(flags)
        else:
            canonical_flags = None

        return Eggex(left, regex, flags, trans_pref, canonical_flags)

    def YshCasePattern(self, pnode):
        # type: (PNode) -> pat_t
        assert pnode.typ == grammar_nt.ysh_case_pat, pnode

        pattern = pnode.GetChild(0)
        typ = pattern.typ
        if typ == Id.Op_LParen:
            # pat_expr or pat_else
            pattern = pnode.GetChild(1)
            typ = pattern.typ

            if typ == grammar_nt.pat_else:
                return pat.Else

            if typ == grammar_nt.pat_exprs:
                exprs = []  # type: List[expr_t]
                for i in xrange(pattern.NumChildren()):
                    child = pattern.GetChild(i)
                    if child.typ == grammar_nt.expr:
                        expr = self.Expr(child)
                        exprs.append(expr)
                return pat.YshExprs(exprs)

        if typ == grammar_nt.eggex:
            return self._Eggex(pattern)

        raise AssertionError()

    def _BlockArg(self, p_node):
        # type: (PNode) -> expr_t

        n = p_node.NumChildren()
        if n == 1:
            child = p_node.GetChild(0)
            return self.Expr(child)

        # It can only be an expression, not a=42, or ...expr
        p_die('Invalid block expression argument', p_node.tok)

    def _Argument(self, p_node, after_semi, arglist):
        # type: (PNode, bool, ArgList) -> None
        """
        argument: (
          test [comp_for]
        | test '=' test  # named arg
        | '...' test  # var args
        )
        """
        pos_args = arglist.pos_args
        named_args = arglist.named_args

        assert p_node.typ == grammar_nt.argument, p_node
        n = p_node.NumChildren()
        if n == 1:
            child = p_node.GetChild(0)
            if after_semi:
                p_die(POS_ARG_MISPLACED, child.tok)
            arg = self.Expr(child)
            pos_args.append(arg)
            return

        if n == 2:
            # Note: We allow multiple spreads, just like Julia.  They are
            # concatenated as in lists and dicts.
            tok0 = p_node.GetChild(0).tok
            if tok0.id == Id.Expr_Ellipsis:
                spread_expr = expr.Spread(tok0, self.Expr(p_node.GetChild(1)))
                if after_semi:  # f(; ... named)
                    named_args.append(NamedArg(None, spread_expr))
                else:  # f(...named)
                    pos_args.append(spread_expr)
                return

            # Note: generator expression not implemented
            if p_node.GetChild(1).typ == grammar_nt.comp_for:
                child = p_node.GetChild(0)
                if after_semi:
                    p_die(POS_ARG_MISPLACED, child.tok)

                elt = self.Expr(child)
                comp = self._CompFor(p_node.GetChild(1))
                arg = expr.GeneratorExp(elt, [comp])
                pos_args.append(arg)
                return

            raise AssertionError()

        if n == 3:  # named args can come before or after the semicolon
            n1 = NamedArg(
                p_node.GetChild(0).tok, self.Expr(p_node.GetChild(2)))
            named_args.append(n1)
            return

        raise AssertionError()

    def _ArgGroup(self, p_node, after_semi, arglist):
        # type: (PNode, bool, ArgList) -> None
        """
        arg_group: argument (',' argument)* [',']
        """
        for i in xrange(p_node.NumChildren()):
            p_child = p_node.GetChild(i)
            if p_child.typ == grammar_nt.argument:
                self._Argument(p_child, after_semi, arglist)

    def _ArgList(self, p_node, arglist):
        # type: (PNode, ArgList) -> None
        """For both funcs and procs

        arglist: (
               [arg_group]
          [';' [arg_group]]
        )

        arglist3: ...
        """
        n = p_node.NumChildren()
        if n == 0:
            return

        i = 0

        if i >= n:
            return
        child = p_node.GetChild(i)
        if child.typ == grammar_nt.arg_group:
            self._ArgGroup(child, False, arglist)
            i += 1

        if i >= n:
            return
        child = p_node.GetChild(i)
        if child.typ == Id.Op_Semi:
            arglist.semi_tok = child.tok
            i += 1

        # Named args after first semi-colon
        if i >= n:
            return
        child = p_node.GetChild(i)
        if child.typ == grammar_nt.arg_group:
            self._ArgGroup(child, True, arglist)
            i += 1

        #
        # Special third group may have block expression - only for arglist3,
        # used for procs!
        #

        if i >= n:
            return
        assert p_node.typ == grammar_nt.arglist3, p_node

        child = p_node.GetChild(i)
        if child.typ == Id.Op_Semi:
            arglist.semi_tok2 = child.tok
            i += 1

        if i >= n:
            return
        child = p_node.GetChild(i)
        if child.typ == grammar_nt.argument:
            arglist.block_expr = self._BlockArg(child)
            i += 1

    def ProcCallArgs(self, pnode, arglist):
        # type: (PNode, ArgList) -> None
        """
        ysh_eager_arglist: '(' [arglist3] ')'
        ysh_lazy_arglist: '[' [arglist] ']'
        """
        n = pnode.NumChildren()
        if n == 2:  # f()
            return

        if n == 3:
            child1 = pnode.GetChild(1)  # the X in '( X )'

            self._ArgList(child1, arglist)
            return

        raise AssertionError()

    def _TypeExpr(self, pnode):
        # type: (PNode) -> TypeExpr
        """
        type_expr: Expr_Name [ '[' type_expr (',' type_expr)* ']' ]
        """
        assert pnode.typ == grammar_nt.type_expr, pnode.typ

        ty = TypeExpr.CreateNull()  # don't allocate children

        ty.tok = pnode.GetChild(0).tok
        ty.name = lexer.TokenVal(ty.tok)

        n = pnode.NumChildren()
        if n == 1:
            return ty

        ty.params = []
        i = 2
        while i < n:
            p = self._TypeExpr(pnode.GetChild(i))
            ty.params.append(p)
            i += 2  # skip comma

        return ty

    def _Param(self, pnode):
        # type: (PNode) -> Param
        """
        param: Expr_Name [type_expr] ['=' expr]
        """
        assert pnode.typ == grammar_nt.param

        name_tok = pnode.GetChild(0).tok
        n = pnode.NumChildren()

        assert name_tok.id == Id.Expr_Name, name_tok

        default_val = None  # type: expr_t
        type_ = None  # type: TypeExpr

        if n == 1:
            # proc p(a)
            pass

        elif n == 2:
            # proc p(a Int)
            type_ = self._TypeExpr(pnode.GetChild(1))

        elif n == 3:
            # proc p(a = 3)
            default_val = self.Expr(pnode.GetChild(2))

        elif n == 4:
            # proc p(a Int = 3)
            type_ = self._TypeExpr(pnode.GetChild(1))
            default_val = self.Expr(pnode.GetChild(3))

        return Param(name_tok, lexer.TokenVal(name_tok), type_, default_val)

    def _ParamGroup(self, p_node):
        # type: (PNode) -> ParamGroup
        """
        param_group:
          (param ',')*
          [ (param | '...' Expr_Name) [,] ]
        """
        assert p_node.typ == grammar_nt.param_group, p_node

        params = []  # type: List[Param]
        rest_of = None  # type: Optional[RestParam]

        n = p_node.NumChildren()
        i = 0
        while i < n:
            child = p_node.GetChild(i)
            if child.typ == grammar_nt.param:
                params.append(self._Param(child))

            elif child.typ == Id.Expr_Ellipsis:
                tok = p_node.GetChild(i + 1).tok
                rest_of = RestParam(tok, lexer.TokenVal(tok))

            i += 2

        return ParamGroup(params, rest_of)

    def Proc(self, p_node):
        # type: (PNode) -> proc_sig_t
        """
        ysh_proc: (
          [ '(' 
                  [ param_group ]         # word params, with defaults
            [ ';' [ param_group ] ]       # positional typed params, with defaults
            [ ';' [ param_group ] ]       # named params, with defaults
            [ ';' Expr_Name ]             # optional block param, with no type or default
            ')'  
          ]
          '{'  # opening { for pgen2
        )
        """
        typ = p_node.typ
        assert typ == grammar_nt.ysh_proc

        n = p_node.NumChildren()
        if n == 1:  # proc f {
            return proc_sig.Open

        if n == 3:  # proc f () {
            sig = proc_sig.Closed.CreateNull(alloc_lists=True)  # no params

        # proc f( three param groups, and block group )
        sig = proc_sig.Closed.CreateNull(alloc_lists=True)  # no params

        # Word args
        i = 1
        child = p_node.GetChild(i)
        if child.typ == grammar_nt.param_group:
            sig.word = self._ParamGroup(p_node.GetChild(i))

            # Validate word args
            for word in sig.word.params:
                if word.type:
                    if word.type.name not in ('Str', 'Ref'):
                        p_die('Word params may only have type Str or Ref',
                              word.type.tok)
                    if word.type.params is not None:
                        p_die('Unexpected type parameters', word.type.tok)

            i += 2
        else:
            i += 1

        #log('i %d n %d', i, n)
        if i >= n:
            return sig

        # Positional args
        child = p_node.GetChild(i)
        if child.typ == grammar_nt.param_group:
            sig.positional = self._ParamGroup(p_node.GetChild(i))
            i += 2
        else:
            i += 1

        #log('i %d n %d', i, n)
        if i >= n:
            return sig

        # Keyword args
        child = p_node.GetChild(i)
        if child.typ == grammar_nt.param_group:
            sig.named = self._ParamGroup(p_node.GetChild(i))
            i += 2
        else:
            i += 1

        #log('i %d n %d', i, n)
        if i >= n:
            return sig

        child = p_node.GetChild(i)
        if child.typ == grammar_nt.param_group:
            group = self._ParamGroup(p_node.GetChild(i))
            params = group.params
            if len(params) > 1:
                p_die('Only 1 block param is allowed', params[1].blame_tok)
            if group.rest_of:
                p_die("Rest param isn't allowed for blocks",
                      group.rest_of.blame_tok)

            if len(params) == 1:
                if params[0].type:
                    if params[0].type.name != 'Command':
                        p_die('Block param must have type Command',
                              params[0].type.tok)
                    if params[0].type.params is not None:
                        p_die('Unexpected type parameters', params[0].type.tok)

                sig.block_param = params[0]

        return sig

    def YshFunc(self, p_node, out):
        # type: (PNode, Func) -> None
        """
        ysh_func: Expr_Name '(' [param_group] [';' param_group] ')'
        """
        assert p_node.typ == grammar_nt.ysh_func

        #self.p_printer.Print(p_node)

        out.name = p_node.GetChild(0).tok

        n = p_node.NumChildren()
        i = 2  # after (

        child = p_node.GetChild(i)
        if child.typ == grammar_nt.param_group:
            out.positional = self._ParamGroup(child)
            i += 2  # skip past ;
        else:
            i += 1

        if i >= n:
            return

        child = p_node.GetChild(i)
        if child.typ == grammar_nt.param_group:
            out.named = self._ParamGroup(child)

    #
    # Eggex Language
    #

    def _RangeCharSingleQuoted(self, p_node):
        # type: (PNode) -> Optional[CharCode]

        assert p_node.typ == grammar_nt.range_char, p_node

        # 'a' in 'a'-'b'

        child0 = p_node.GetChild(0)
        if child0.typ == grammar_nt.sq_string:
            sq_part = cast(SingleQuoted, child0.GetChild(1).tok)
            n = len(sq_part.sval)
            if n == 0:
                p_die("Quoted range char can't be empty",
                      loc.WordPart(sq_part))
            elif n == 1:
                return CharCode(sq_part.left, ord(sq_part.sval[0]), False)
            else:
                p_die(RANGE_POINT_TOO_LONG, loc.WordPart(sq_part))
        return None

    def _OtherRangeToken(self, p_node):
        # type: (PNode) -> Token
        """An endpoint of a range (single char)

        range_char: Expr_Name | Expr_DecInt | sq_string | char_literal
                    a-z         0-9           'a'-'z'     \x00-\xff
        """
        assert p_node.typ == grammar_nt.range_char, p_node

        child0 = p_node.GetChild(0)
        if child0.typ == grammar_nt.char_literal:
            # \x00 in /[\x00 - \x20]/
            tok = child0.GetChild(0).tok
            return tok

        tok = p_node.tok
        # a in a-z is Expr_Name
        # 0 in 0-9 is Expr_DecInt
        assert tok.id in (Id.Expr_Name, Id.Expr_DecInt), tok

        if tok.length != 1:
            p_die(RANGE_POINT_TOO_LONG, tok)
        return tok

    def _NonRangeChars(self, p_node):
        # type: (PNode) -> class_literal_term_t
        """
        \" \u1234 '#'
        """
        assert p_node.typ == grammar_nt.range_char, p_node

        child0 = p_node.GetChild(0)
        typ0 = p_node.GetChild(0).typ

        if typ0 == grammar_nt.sq_string:
            return cast(SingleQuoted, child0.GetChild(1).tok)

        if typ0 == grammar_nt.char_literal:
            return word_compile.EvalCharLiteralForRegex(child0.tok)

        if typ0 == Id.Expr_Name:
            # Look up PerlClass and PosixClass
            return self._NameInClass(None, child0.tok)

        raise AssertionError()

    def _ClassLiteralTerm(self, p_node):
        # type: (PNode) -> class_literal_term_t
        """
        class_literal_term:
          range_char ['-' range_char ] 
        | '@' Expr_Name  # splice
        | '!' Expr_Name  # negate char class
          ...
        """
        assert p_node.typ == grammar_nt.class_literal_term, p_node

        typ0 = p_node.GetChild(0).typ

        if typ0 == grammar_nt.range_char:
            n = p_node.NumChildren()

            if n == 1:
                return self._NonRangeChars(p_node.GetChild(0))

            # 'a'-'z' etc.
            if n == 3:
                assert p_node.GetChild(1).typ == Id.Arith_Minus, p_node

                left = p_node.GetChild(0)
                right = p_node.GetChild(2)

                code1 = self._RangeCharSingleQuoted(left)
                if code1 is None:
                    tok1 = self._OtherRangeToken(left)
                    code1 = word_compile.EvalCharLiteralForRegex(tok1)

                code2 = self._RangeCharSingleQuoted(right)
                if code2 is None:
                    tok2 = self._OtherRangeToken(right)
                    code2 = word_compile.EvalCharLiteralForRegex(tok2)
                return CharRange(code1, code2)

            raise AssertionError()

        if typ0 == Id.Expr_At:
            tok1 = p_node.GetChild(1).tok
            return class_literal_term.Splice(tok1, lexer.TokenVal(tok1))

        if typ0 == Id.Expr_Bang:
            return self._NameInClass(
                p_node.GetChild(0).tok,
                p_node.GetChild(1).tok)

        p_die("This kind of class literal term isn't implemented",
              p_node.GetChild(0).tok)

    def _ClassLiteral(self, p_node):
        # type: (PNode) -> List[class_literal_term_t]
        """class_literal: '[' class_literal_term+ ']'."""
        assert p_node.typ == grammar_nt.class_literal
        # skip [ and ]
        terms = []  # type: List[class_literal_term_t]
        for i in xrange(1, p_node.NumChildren() - 1):
            terms.append(self._ClassLiteralTerm(p_node.GetChild(i)))

        return terms

    def _NameInRegex(self, negated_tok, tok):
        # type: (Token, Token) -> re_t
        tok_str = lexer.TokenVal(tok)
        if tok_str == 'dot':
            if negated_tok:
                p_die("Can't negate this symbol", tok)
            return re.Primitive(tok, Id.Eggex_Dot)

        if tok_str in POSIX_CLASSES:
            return PosixClass(negated_tok, tok_str)

        perl = PERL_CLASSES.get(tok_str)
        if perl is not None:
            return PerlClass(negated_tok, perl)

        if tok_str[0].isupper():  # e.g. HexDigit
            return re.Splice(tok, lexer.TokenVal(tok))

        p_die("%r isn't a character class" % tok_str, tok)

    def _NameInClass(self, negated_tok, tok):
        # type: (Token, Token) -> class_literal_term_t
        """Like the above, but 'dot' and 'd' don't mean anything within []"""
        tok_str = lexer.TokenVal(tok)

        # A bare, unquoted character literal.  In the grammar, this is expressed as
        # range_char without an ending.

        # d is NOT 'digit', it's a literal 'd'!
        if len(tok_str) == 1:
            # Expr_Name matches VAR_NAME_RE, which starts with [a-zA-Z_]
            assert tok.id in (Id.Expr_Name, Id.Expr_DecInt)

            if negated_tok:  # [~d] is not allowed, only [~digit]
                p_die("Can't negate this symbol", tok)
            return word_compile.EvalCharLiteralForRegex(tok)

        # digit, word, but not d, w, etc.
        if tok_str in POSIX_CLASSES:
            return PosixClass(negated_tok, tok_str)

        perl = PERL_CLASSES.get(tok_str)
        if perl is not None:
            return PerlClass(negated_tok, perl)
        p_die("%r isn't a character class" % tok_str, tok)

    def _ReAtom(self, p_atom):
        # type: (PNode) -> re_t
        """
        re_atom: ( char_literal | ...
        """
        assert p_atom.typ == grammar_nt.re_atom, p_atom.typ

        child0 = p_atom.GetChild(0)

        typ0 = p_atom.GetChild(0).typ
        tok0 = p_atom.GetChild(0).tok

        # Non-terminals

        if typ0 == grammar_nt.class_literal:
            return re.CharClassLiteral(False, self._ClassLiteral(child0))

        if typ0 == grammar_nt.sq_string:
            return cast(SingleQuoted, child0.GetChild(1).tok)

        if typ0 == grammar_nt.char_literal:
            # Note: ERE doesn't seem to support escapes like Python
            #    https://docs.python.org/3/library/re.html
            # We might want to do a translation like this;
            #
            # \u{03bc} -> \u03bc
            # \x00 -> \x00
            # \n -> \n

            # Must be Id.Char_{OneChar,Hex,UBraced}
            assert consts.GetKind(tok0.id) == Kind.Char
            s = word_compile.EvalCStringToken(tok0.id, lexer.TokenVal(tok0))
            return re.LiteralChars(tok0, s)

        # Special punctuation
        if typ0 == Id.Expr_Dot:  # .
            return re.Primitive(tok0, Id.Eggex_Dot)

        if typ0 == Id.Arith_Caret:  # ^
            return re.Primitive(tok0, Id.Eggex_Start)

        if typ0 == Id.Expr_Dollar:  # $
            return re.Primitive(tok0, Id.Eggex_End)

        if typ0 == Id.Expr_Name:
            # d digit -> PosixClass PerlClass etc.
            return self._NameInRegex(None, tok0)

        if typ0 == Id.Expr_Symbol:
            # Validate symbols here, like we validate PerlClass, etc.
            tok_str = lexer.TokenVal(tok0)
            if tok_str == '%start':
                return re.Primitive(tok0, Id.Eggex_Start)
            if tok_str == '%end':
                return re.Primitive(tok0, Id.Eggex_End)
            p_die("Unexpected token %r in regex" % tok_str, tok0)

        if typ0 == Id.Expr_At:
            # | '@' Expr_Name
            tok1 = p_atom.GetChild(1).tok
            return re.Splice(tok0, lexer.TokenVal(tok1))

        if typ0 == Id.Expr_Bang:
            # | '!' (Expr_Name | class_literal)
            # | '!' '!' Expr_Name (Expr_Name | Expr_DecInt | '(' regex ')')
            n = p_atom.NumChildren()
            if n == 2:
                child1 = p_atom.GetChild(1)
                if child1.typ == grammar_nt.class_literal:
                    return re.CharClassLiteral(True,
                                               self._ClassLiteral(child1))
                else:
                    return self._NameInRegex(tok0, p_atom.GetChild(1).tok)
            else:
                # Note: !! conflicts with shell history
                p_die(
                    "Backtracking with !! isn't implemented (requires Python/PCRE)",
                    p_atom.GetChild(1).tok)

        if typ0 == Id.Op_LParen:
            # | '(' regex ')'

            # Note: in ERE (d+) is the same as <d+>.  That is, Group becomes
            # Capture.
            return re.Group(self._Regex(p_atom.GetChild(1)))

        if typ0 == Id.Arith_Less:
            # | '<' 'capture' regex ['as' Expr_Name] [':' Expr_Name] '>'

            n = p_atom.NumChildren()
            assert n == 4 or n == 6 or n == 8, n

            # < capture d+ >
            regex = self._Regex(p_atom.GetChild(2))

            as_name = None  # type: Optional[Token]
            func_name = None  # type: Optional[Token]

            i = 3  # points at any of   >   as   :

            typ = p_atom.GetChild(i).typ
            if typ == Id.Expr_As:
                as_name = p_atom.GetChild(i + 1).tok
                i += 2

            typ = p_atom.GetChild(i).typ
            if typ == Id.Arith_Colon:
                func_name = p_atom.GetChild(i + 1).tok

            return re.Capture(regex, as_name, func_name)

        raise AssertionError(typ0)

    def _RepeatOp(self, p_repeat):
        # type: (PNode) -> re_repeat_t
        """
        repeat_op: '+' | '*' | '?' 
                 | '{' [Expr_Name] ('+' | '*' | '?' | repeat_range) '}'
        """
        assert p_repeat.typ == grammar_nt.repeat_op, p_repeat

        tok = p_repeat.GetChild(0).tok
        id_ = tok.id

        if id_ in (Id.Arith_Plus, Id.Arith_Star, Id.Arith_QMark):
            return tok  # a+  a*  a?

        if id_ == Id.Op_LBrace:
            child1 = p_repeat.GetChild(1)
            if child1.typ != grammar_nt.repeat_range:
                # e.g. dot{N *} is .*?
                p_die("Perl-style repetition isn't implemented with libc",
                      child1.tok)

            # repeat_range: (
            #     Expr_DecInt [',']
            #   | ',' Expr_DecInt
            #   | Expr_DecInt ',' Expr_DecInt
            # )

            n = child1.NumChildren()
            if n == 1:  # {3}
                tok = child1.GetChild(0).tok
                return tok  # different operator than + * ?

            if n == 2:
                if child1.GetChild(0).typ == Id.Expr_DecInt:  # {,3}
                    left = child1.GetChild(0).tok
                    return re_repeat.Range(left, lexer.TokenVal(left), '',
                                           None)
                else:  # {1,}
                    right = child1.GetChild(1).tok
                    return re_repeat.Range(None, '', lexer.TokenVal(right),
                                           right)

            if n == 3:  # {1,3}
                left = child1.GetChild(0).tok
                right = child1.GetChild(2).tok
                return re_repeat.Range(left, lexer.TokenVal(left),
                                       lexer.TokenVal(right), right)

            raise AssertionError(n)

        raise AssertionError(id_)

    def _ReAlt(self, p_node):
        # type: (PNode) -> re_t
        """
        re_alt: (re_atom [repeat_op])+
        """
        assert p_node.typ == grammar_nt.re_alt

        i = 0
        n = p_node.NumChildren()
        seq = []  # type: List[re_t]
        while i < n:
            r = self._ReAtom(p_node.GetChild(i))
            i += 1
            if i < n and p_node.GetChild(i).typ == grammar_nt.repeat_op:
                repeat_op = self._RepeatOp(p_node.GetChild(i))
                r = re.Repeat(r, repeat_op)
                i += 1
            seq.append(r)

        if len(seq) == 1:
            return seq[0]
        else:
            return re.Seq(seq)

    def _Regex(self, p_node):
        # type: (PNode) -> re_t
        """
        regex: [re_alt] (('|'|'or') re_alt)*
        """
        assert p_node.typ == grammar_nt.regex

        n = p_node.NumChildren()
        alts = []  # type: List[re_t]
        for i in xrange(0, n, 2):  # was children[::2]
            c = p_node.GetChild(i)
            alts.append(self._ReAlt(c))

        if len(alts) == 1:
            return alts[0]
        else:
            return re.Alt(alts)


# vim: sw=4
