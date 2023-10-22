"""expr_to_ast.py."""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str
from _devbuild.gen.syntax_asdl import (
    Token,
    loc,
    loc_t,
    DoubleQuoted,
    SingleQuoted,
    SimpleVarSub,
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
    lhs_expr,
    lhs_expr_t,
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
)
from _devbuild.gen import grammar_nt
from core.error import p_die
from frontend import lexer
from mycpp import mylib
from mycpp.mylib import log, tagswitch
from ysh import expr_parse

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

# Copied from pgen2/token.py to avoid dependency.
NT_OFFSET = 256

if mylib.PYTHON:

    def MakeGrammarNames(ysh_grammar):
        # type: (Grammar) -> Dict[int, str]

        # TODO: Break this dependency
        from frontend import lexer_def

        names = {}

        #from _devbuild.gen.id_kind_asdl import _Id_str
        # This is a dictionary

        # _Id_str()

        for id_name, k in lexer_def.ID_SPEC.id_str2int.items():
            # Hm some are out of range
            #assert k < 256, (k, id_name)

            # HACK: Cut it off at 256 now!  Expr/Arith/Op doesn't go higher than
            # that.  TODO: Change NT_OFFSET?  That might affect C code though.
            # Best to keep everything fed to pgen under 256.  This only affects
            # pretty printing.
            if k < 256:
                names[k] = id_name

        for k, v in ysh_grammar.number2symbol.items():
            # eval_input == 256.  Remove?
            assert k >= 256, (k, v)
            names[k] = v

        return names


def ISNONTERMINAL(x):
    # type: (int) -> bool
    assert isinstance(x, int), x
    return x >= NT_OFFSET


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
        Trailer: ( '(' [arglist] ')' | '[' subscriptlist ']'
                 | '.' NAME | '->' NAME | '::' NAME
                 )
        """
        op_tok = p_trailer.GetChild(0).tok

        if op_tok.id == Id.Op_LParen:
            lparen = op_tok
            rparen = p_trailer.GetChild(-1).tok
            arglist = ArgList(lparen, [], None, [], rparen)
            if p_trailer.NumChildren() == 2:  # ()
                return expr.FuncCall(base, arglist)

            p = p_trailer.GetChild(1)  # the X in ( X )
            assert p.typ == grammar_nt.arglist  # f(x, y)
            self._ArgList(p, arglist)
            return expr.FuncCall(base, arglist)

        if op_tok.id == Id.Op_LBracket:
            p_args = p_trailer.GetChild(1)
            assert p_args.typ == grammar_nt.subscriptlist
            n = p_args.NumChildren()
            if n > 1:
                p_die("Only 1 subscript is accepted", p_args.GetChild(1).tok)

            a = p_args.GetChild(0)
            return Subscript(op_tok, base, self._Subscript(a))

        if op_tok.id in (Id.Expr_Dot, Id.Expr_RArrow, Id.Arith_Colon):
            attr = p_trailer.GetChild(1).tok  # will be Id.Expr_Name
            return Attribute(base, op_tok, attr, expr_context_e.Store)

        raise AssertionError(Id_str(op_tok.id))

    def _DictPair(self, p_node):
        # type: (PNode) -> Tuple[expr_t, expr_t]
        """dict_pair: ( Expr_Name [':' test] |

        '[' testlist ']' ':' test )
        """
        assert p_node.typ == grammar_nt.dict_pair

        typ = p_node.GetChild(0).typ

        if ISNONTERMINAL(typ):  # for sq_string
            # Note: Could inline these cases instead of going through self.Expr.
            if typ == grammar_nt.sq_string:
                key = self.Expr(p_node.GetChild(0))  # type: expr_t
            elif typ == grammar_nt.dq_string:
                key = self.Expr(p_node.GetChild(0))

            value = self.Expr(p_node.GetChild(2))
            return key, value

        tok0 = p_node.GetChild(0).tok
        id_ = tok0.id

        if id_ == Id.Expr_Name:
            key = expr.Const(tok0)
            if p_node.NumChildren() >= 3:
                value = self.Expr(p_node.GetChild(2))
            else:
                value = expr.Implicit

        if id_ == Id.Op_LBracket:  # {[x+y]: 'val'}
            key = self.Expr(p_node.GetChild(1))
            value = self.Expr(p_node.GetChild(4))
            return key, value

        return key, value

    def _Dict(self, parent, p_node):
        # type: (PNode, PNode) -> expr.Dict
        """Parse tree to LST
        
        dict: dict_pair (',' dict_pair)* [',']
        dict2: dict_pair (comma_newline dict_pair)* [comma_newline]
        """
        if not ISNONTERMINAL(p_node.typ):
            assert p_node.tok.id == Id.Op_RBrace
            return expr.Dict(parent.tok, [], [])

        #assert p_node.typ == grammar_nt.dict

        keys = []  # type: List[expr_t]
        values = []  # type: List[expr_t]

        n = p_node.NumChildren()
        for i in xrange(0, n, 2):
            key, value = self._DictPair(p_node.GetChild(i))
            keys.append(key)
            values.append(value)

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
        """Parse tree to LST
        
        testlist_comp:
          (test|star_expr) ( comp_for | (',' (test|star_expr))* [','] )
        """
        assert p_node.typ == grammar_nt.testlist_comp
        n = p_node.NumChildren()
        if n > 1 and p_node.GetChild(1).typ == grammar_nt.comp_for:
            elt = self.Expr(p_node.GetChild(0))
            comp = self._CompFor(p_node.GetChild(1))
            if id0 == Id.Op_LParen:
                return expr.GeneratorExp(elt, [comp])
            if id0 == Id.Op_LBracket:
                return expr.ListComp(parent.tok, elt, [comp])
            raise AssertionError()

        if id0 == Id.Op_LParen:
            if n == 1:  # parenthesized expression like (x+1) or (x)
                return self.Expr(p_node.GetChild(0))

            # (1,)  (1, 2)  etc.
            if p_node.GetChild(1).tok.id == Id.Arith_Comma:
                return self._Tuple(p_node)

            raise NotImplementedError('testlist_comp')

        if id0 == Id.Op_LBracket:
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
                assert parent.GetChild(
                    1).tok.id == Id.Op_RParen, parent.GetChild(1)
                return expr.Tuple(tok, [], expr_context_e.Store)

            return self._TestlistComp(parent, parent.GetChild(1), id_)

        if id_ == Id.Op_LBracket:
            # atom: ... | '[' [testlist_comp] ']' | ...

            if n == 2:  # []
                assert parent.GetChild(
                    1).tok.id == Id.Op_RBracket, parent.GetChild(1)
                return expr.List(tok, [],
                                 expr_context_e.Store)  # unused expr_context_e

            return self._TestlistComp(parent, parent.GetChild(1), id_)

        if id_ == Id.Op_LBrace:
            # atom: ... | '{' [Op_Newline] [dict] '}'
            i = 1
            if parent.GetChild(i).tok.id == Id.Op_Newline:
                i += 1
            return self._Dict(parent, parent.GetChild(i))

        if id_ == Id.Arith_Slash:
            r = self._Regex(parent.GetChild(1))
            flags = []  # type: List[Token]
            # TODO: Parse translation preference.
            trans_pref = None  # type: Token
            return expr.RegexLiteral(
                parent.GetChild(0).tok, r, flags, trans_pref)

        if id_ == Id.Expr_Func:
            # STUB.  This should really be a Func, not Lambda.
            return expr.Lambda([], expr.Implicit)

        raise NotImplementedError(Id_str(id_))

    def _NameTypeList(self, p_node):
        # type: (PNode) -> List[NameType]
        """name_type_list: name_type (',' name_type)*"""
        assert p_node.typ == grammar_nt.name_type_list
        results = []  # type: List[NameType]

        n = p_node.NumChildren()
        for i in xrange(0, n, 2):  # was children[::2]
            p = p_node.GetChild(i)

            if p.NumChildren() == 2:
                typ = self._TypeExpr(p.GetChild(1))
            else:
                typ = None

            node = NameType(p.GetChild(0).tok, typ)
            results.append(node)
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

        if ISNONTERMINAL(typ0):
            if n == 3:  # a[1:2]
                lower = self.Expr(parent.GetChild(0))
                upper = self.Expr(parent.GetChild(2))
            elif n == 2:  # a[1:]
                lower = self.Expr(parent.GetChild(0))
                upper = None
            else:  # a[1]
                return self.Expr(parent.GetChild(0))
        else:
            assert parent.GetChild(0).tok.id == Id.Arith_Colon
            lower = None
            if n == 1:  # a[:]
                upper = None
            else:  # a[:3]
                upper = self.Expr(parent.GetChild(1))
        return expr.Slice(lower, parent.GetChild(0).tok, upper)

    def Expr(self, pnode):
        # type: (PNode) -> expr_t
        """Transform expressions (as opposed to statements)."""
        typ = pnode.typ
        tok = pnode.tok

        if ISNONTERMINAL(typ):

            #
            # Oil Entry Points / Additions
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
                while i < n and ISNONTERMINAL(pnode.GetChild(i).typ):
                    node = self._Trailer(node, pnode.GetChild(i))
                    i += 1

                if i != n:  # ['**' factor]
                    op_tok = pnode.GetChild(i).tok
                    assert op_tok.id == Id.Arith_DStar, op_tok
                    factor = self.Expr(pnode.GetChild(i + 1))
                    node = expr.Binary(op_tok, node, factor)

                return node

            elif typ == grammar_nt.literal_expr:
                inner = self.Expr(pnode.GetChild(1))
                return expr.Literal(inner)

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
                return cast(DoubleQuoted, pnode.GetChild(1).tok)

            elif typ == grammar_nt.sq_string:
                return cast(SingleQuoted, pnode.GetChild(1).tok)

            elif typ == grammar_nt.simple_var_sub:
                tok = pnode.GetChild(0).tok

                if tok.id == Id.VSub_DollarName:  # $foo is disallowed
                    bare = tok.tval[1:]
                    p_die(
                        'In expressions, remove $ and use `%s`, or sometimes "$%s"'
                        % (bare, bare), tok)

                # $? is allowed
                return SimpleVarSub(tok, lexer.TokenSliceLeft(tok, 1))

            else:
                nt_name = self.number2symbol[typ]
                raise AssertionError("PNode type %d (%s) wasn't handled" %
                                     (typ, nt_name))

        else:  # Terminals should have a token
            id_ = tok.id

            if id_ == Id.Expr_Name:
                return expr.Var(tok)

            if id_ in (Id.Expr_DecInt, Id.Expr_BinInt, Id.Expr_OctInt,
                       Id.Expr_HexInt, Id.Expr_Float):
                return expr.Const(tok)

            if id_ in (Id.Expr_Null, Id.Expr_True, Id.Expr_False,
                       Id.Char_OneChar, Id.Char_UBraced, Id.Char_Pound):
                return expr.Const(tok)

            raise NotImplementedError(Id_str(id_))

    def _ArrayItem(self, p_node):
        # type: (PNode) -> expr_t
        assert p_node.typ == grammar_nt.array_item

        child0 = p_node.GetChild(0)
        typ0 = child0.typ
        if ISNONTERMINAL(typ0):
            return self.Expr(child0)
        else:
            if child0.tok.id == Id.Op_LParen:  # (x+1)
                return self.Expr(p_node.GetChild(1))
            return self.Expr(child0)  # $1 ${x} etc.

    def _LhsExprList(self, p_node):
        # type: (PNode) -> List[lhs_expr_t]
        """place_list: expr (',' expr)*"""
        assert p_node.typ == grammar_nt.place_list

        places = []  # type: List[lhs_expr_t]
        n = p_node.NumChildren()
        for i in xrange(0, n, 2):  # was children[::2]
            p = p_node.GetChild(i)

            e = self.Expr(p)
            UP_e = e
            with tagswitch(e) as case:
                if case(expr_e.Var):
                    e = cast(expr.Var, UP_e)
                    places.append(lhs_expr.Var(e.name))

                elif case(expr_e.Subscript):
                    e = cast(Subscript, UP_e)
                    places.append(e)

                elif case(expr_e.Attribute):
                    e = cast(Attribute, UP_e)
                    if e.op.id != Id.Expr_Dot:
                        # e.g. setvar obj->method is not valid
                        p_die("Can't assign to this attribute expr", e.op)
                    places.append(e)

                else:
                    pass  # work around mycpp bug

                    # TODO: could blame arbitary expr_t, bu this works most of
                    # the time
                    if p.tok:
                        blame = p.tok  # type: loc_t
                    else:
                        blame = loc.Missing
                    p_die("Can't assign to this expression", blame)

        return places

    def MakeVarDecl(self, p_node):
        # type: (PNode) -> command.VarDecl
        """ysh_var_decl: name_type_list '=' testlist end_stmt."""
        typ = p_node.typ
        assert typ == grammar_nt.ysh_var_decl

        #log('len(children) = %d', len(children))
        lhs = self._NameTypeList(p_node.GetChild(0))  # could be a tuple
        # This syntax is confusing, and different than JavaScript
        #   var x, y = 1, 2
        # But this is useful:
        #   var flag, i = parseArgs(spec, argv)

        rhs = self.Expr(p_node.GetChild(2))

        # The caller should fill in the keyword token.
        return command.VarDecl(None, lhs, rhs)

    def MakeMutation(self, p_node):
        # type: (PNode) -> command.Mutation
        """Parse tree to LST
        
        ysh_place_mutation: place_list (augassign | '=') testlist end_stmt
        """
        typ = p_node.typ
        assert typ == grammar_nt.ysh_place_mutation

        place_list = self._LhsExprList(p_node.GetChild(0))  # could be a tuple
        op_tok = p_node.GetChild(1).tok
        if len(place_list) > 1 and op_tok.id != Id.Arith_Equal:
            p_die('Multiple assignment must use =', op_tok)
        rhs = self.Expr(p_node.GetChild(2))
        return command.Mutation(None, place_list, op_tok, rhs)

    def OilForExpr(self, pnode):
        # type: (PNode) -> Tuple[List[NameType], expr_t]
        typ = pnode.typ

        if typ == grammar_nt.ysh_for:
            # ysh_for: '(' lvalue_list 'in' testlist ')'
            lhs = self._NameTypeList(pnode.GetChild(1))  # could be a tuple
            iterable = self.Expr(pnode.GetChild(3))
            return lhs, iterable

        nt_name = self.number2symbol[typ]
        raise AssertionError("PNode type %d (%s) wasn't handled" %
                             (typ, nt_name))

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
            elif typ == grammar_nt.pat_exprs:
                exprs = []  # type: List[expr_t]
                for i in xrange(pattern.NumChildren()):
                    child = pattern.GetChild(i)
                    if child.typ == grammar_nt.expr:
                        expr = self.Expr(child)
                        exprs.append(expr)
                return pat.YshExprs(exprs)

        elif typ == grammar_nt.pat_eggex:
            # pat_eggex
            re = self._Regex(pattern.GetChild(1))
            return pat.Eggex(re)

        raise NotImplementedError()

    def _Argument(self, p_node, after_semi, arglist):
        # type: (PNode, bool, ArgList) -> None
        """Parse tree to LST

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
                p_die('Positional args must come before the semi-colon',
                      child.tok)
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

            if p_node.GetChild(1).typ == grammar_nt.comp_for:
                child = p_node.GetChild(0)
                if after_semi:
                    p_die('Positional args must come before the semi-colon',
                          child.tok)

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
            if ISNONTERMINAL(p_child.typ):
                self._Argument(p_child, after_semi, arglist)

    def _ArgList(self, p_node, arglist):
        # type: (PNode, ArgList) -> None
        """For both funcs and procs

        arglist: [arg_group] [';' arg_group]
        """
        n = p_node.NumChildren()
        if n == 0:
            return

        p0 = p_node.GetChild(0)
        i = 0
        if ISNONTERMINAL(p0.typ):
            self._ArgGroup(p0, False, arglist)
            i += 1

        if n >= 2:
            arglist.semi_tok = p_node.GetChild(i).tok
            self._ArgGroup(p_node.GetChild(i + 1), True, arglist)

    def ToArgList(self, pnode, arglist):
        # type: (PNode, ArgList) -> None
        """
        ysh_eager_arglist: '(' [arglist] ')'
        ysh_lazy_arglist: '[' [arglist] ']'
        """
        if pnode.NumChildren() == 2:  # f()
            return

        assert pnode.NumChildren() == 3
        p = pnode.GetChild(1)  # the X in '( X )'

        assert p.typ == grammar_nt.arglist
        self._ArgList(p, arglist)

    def _TypeExpr(self, pnode):
        # type: (PNode) -> TypeExpr
        """
        type_expr: Expr_Name [ '[' type_expr (',' type_expr)* ']' ]
        """
        assert pnode.typ == grammar_nt.type_expr, pnode.typ

        #self.p_printer.Print(pnode)

        ty = TypeExpr.CreateNull()  # don't allocate children

        ty.tok = pnode.GetChild(0).tok
        ty.name = ty.tok.tval  # TODO: TokenVal()

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

        #self.p_printer.Print(pnode)

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

        #self.p_printer.Print(p_node)

        params = []  # type: List[Param]
        rest_of = None  # type: Optional[RestParam]

        n = p_node.NumChildren()
        i = 0
        while i < n:
            child = p_node.GetChild(i)
            if child.typ == grammar_nt.param:
                params.append(self._Param(child))
            elif child.tok.id == Id.Expr_Ellipsis:
                tok = p_node.GetChild(i + 1).tok
                rest_of = RestParam(tok, lexer.TokenVal(tok))
            i += 2
            #log('i %d n %d', i, n)

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

        #self.p_printer.Print(p_node)

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
        """Parse tree to LST

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
    # Regex Language
    #

    def _RangeChar(self, p_node):
        # type: (PNode) -> Token
        """An endpoint of a range (single char)

        range_char: Expr_Name | Expr_DecInt | sq_string | char_literal
                    a-z         0-9           'a'-'z'     \x00-\xff
        """
        assert p_node.typ == grammar_nt.range_char, p_node
        typ = p_node.GetChild(0).typ
        if ISNONTERMINAL(typ):
            # 'a' in 'a'-'b'
            if typ == grammar_nt.sq_string:
                sq_part = cast(SingleQuoted,
                               p_node.GetChild(0).GetChild(1).tok)
                tokens = sq_part.tokens
                # Can happen with multiline single-quoted strings
                if len(tokens) > 1:
                    p_die(RANGE_POINT_TOO_LONG, loc.WordPart(sq_part))
                if len(tokens[0].tval) > 1:
                    p_die(RANGE_POINT_TOO_LONG, loc.WordPart(sq_part))
                return tokens[0]

            if typ == grammar_nt.char_literal:
                tok = p_node.GetChild(0).GetChild(0).tok
                return tok

            raise NotImplementedError()
        else:
            # Expr_Name or Expr_DecInt
            tok = p_node.tok
            if tok.id in (Id.Expr_Name, Id.Expr_DecInt):
                # For the a in a-z, 0 in 0-9
                if len(tok.tval) != 1:
                    p_die(RANGE_POINT_TOO_LONG, tok)
                return tok

            raise NotImplementedError()

    def _NonRangeChars(self, p_node):
        # type: (PNode) -> class_literal_term_t
        """\" \u1234 '#'."""
        assert p_node.typ == grammar_nt.range_char, p_node
        typ = p_node.GetChild(0).typ
        if ISNONTERMINAL(typ):
            p_child = p_node.GetChild(0)
            if typ == grammar_nt.sq_string:
                return cast(SingleQuoted, p_child.GetChild(1).tok)

            if typ == grammar_nt.char_literal:
                return class_literal_term.CharLiteral(p_node.GetChild(0).tok)

            raise NotImplementedError()
        else:
            # Look up PerlClass and PosixClass
            return self._NameInClass(None, p_node.GetChild(0).tok)

    def _ClassLiteralTerm(self, p_node):
        # type: (PNode) -> class_literal_term_t
        """Parse tree to LST

        class_literal_term:
          range_char ['-' range_char ] 
        | '@' Expr_Name  # splice
        | '!' Expr_Name  # negate char class
          ...
        """
        assert p_node.typ == grammar_nt.class_literal_term, p_node

        first = p_node.GetChild(0)
        typ = first.typ

        if ISNONTERMINAL(typ):
            n = p_node.NumChildren()

            if n == 1 and typ == grammar_nt.range_char:
                return self._NonRangeChars(p_node.GetChild(0))

            # 'a'-'z' etc.
            if n == 3 and p_node.GetChild(1).tok.id == Id.Arith_Minus:
                start = self._RangeChar(p_node.GetChild(0))
                end = self._RangeChar(p_node.GetChild(2))
                return class_literal_term.Range(start, end)

        else:
            if first.tok.id == Id.Expr_At:
                tok1 = p_node.GetChild(1).tok
                return class_literal_term.Splice(tok1, lexer.TokenVal(tok1))

            if first.tok.id == Id.Expr_Bang:
                return self._NameInClass(
                    p_node.GetChild(0).tok,
                    p_node.GetChild(1).tok)

            raise AssertionError(p_node.GetChild(0).tok.id)

        nt_name = self.number2symbol[typ]
        raise NotImplementedError(nt_name)

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
        tok_str = tok.tval
        if tok_str == 'dot':
            if negated_tok:
                p_die("Can't negate this symbol", tok)
            return tok

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
        """Like the above, but 'dot' doesn't mean anything.

        And `d` is a literal 'd', not `digit`.
        """
        tok_str = tok.tval

        # A bare, unquoted character literal.  In the grammar, this is expressed as
        # range_char without an ending.

        # d is NOT 'digit', it's a literal 'd'!
        if len(tok_str) == 1:
            # Expr_Name matches VAR_NAME_RE, which starts with [a-zA-Z_]
            assert tok.id in (Id.Expr_Name, Id.Expr_DecInt)

            if negated_tok:  # [~d] is not allowed, only [~digit]
                p_die("Can't negate this symbol", tok)
            return class_literal_term.CharLiteral(tok)

        # digit, word, but not d, w, etc.
        if tok_str in POSIX_CLASSES:
            return PosixClass(negated_tok, tok_str)

        perl = PERL_CLASSES.get(tok_str)
        if perl is not None:
            return PerlClass(negated_tok, perl)
        p_die("%r isn't a character class" % tok_str, tok)

    def _ReAtom(self, p_atom):
        # type: (PNode) -> re_t
        """re_atom: ( char_literal."""
        assert p_atom.typ == grammar_nt.re_atom, p_atom.typ

        typ = p_atom.GetChild(0).typ

        if ISNONTERMINAL(typ):
            p_child = p_atom.GetChild(0)
            if typ == grammar_nt.class_literal:
                return re.CharClassLiteral(False, self._ClassLiteral(p_child))

            if typ == grammar_nt.sq_string:
                return cast(SingleQuoted, p_child.GetChild(1).tok)

            if typ == grammar_nt.char_literal:
                return p_atom.GetChild(0).tok

            raise NotImplementedError(typ)

        else:
            tok = p_atom.GetChild(0).tok

            # Special punctuation
            if tok.id in (Id.Expr_Dot, Id.Arith_Caret, Id.Expr_Dollar):
                return tok

            # TODO: d digit can turn into PosixClass and PerlClass right here!
            # It's parsing.
            if tok.id == Id.Expr_Name:
                return self._NameInRegex(None, tok)

            if tok.id == Id.Expr_Symbol:
                # Validate symbols here, like we validate PerlClass, etc.
                if tok.tval in ('%start', '%end', 'dot'):
                    return tok
                p_die("Unexpected token %r in regex" % tok.tval, tok)

            if tok.id == Id.Expr_At:
                # | '@' Expr_Name
                tok = p_atom.GetChild(1).tok
                return re.Splice(tok, lexer.TokenVal(tok))

            if tok.id == Id.Expr_Bang:
                # | '!' (Expr_Name | class_literal)
                # | '!' '!' Expr_Name (Expr_Name | Expr_DecInt | '(' regex ')')
                n = p_atom.NumChildren()
                if n == 2:
                    typ = p_atom.GetChild(1).typ
                    if ISNONTERMINAL(typ):
                        return re.CharClassLiteral(
                            True, self._ClassLiteral(p_atom.GetChild(1)))
                    else:
                        return self._NameInRegex(tok, p_atom.GetChild(1).tok)
                else:
                    # Note: !! conflicts with shell history
                    p_die(
                        "Backtracking with !! isn't implemented (requires Python/PCRE)",
                        p_atom.GetChild(1).tok)

            if tok.id == Id.Op_LParen:
                # | '(' regex ')'

                # Note: in ERE (d+) is the same as <d+>.  That is, Group becomes
                # Capture.
                return re.Group(self._Regex(p_atom.GetChild(1)))

            if tok.id == Id.Arith_Less:
                # | '<' regex [':' name_type] '>'

                regex = self._Regex(p_atom.GetChild(1))

                n = p_atom.NumChildren()
                if n == 5:
                    # TODO: Add type expression
                    # YES
                    #   < d+ '.' d+ : ratio Float >
                    #   < d+ : month Int >
                    # INVALID
                    #   < d+ : month List[int] >
                    name_tok = p_atom.GetChild(3).GetChild(0).tok

                    # TODO: is it possible to output the capture name <-> index mapping
                    # here for POSIX ERE?

                else:
                    name_tok = None

                return re.Capture(regex, name_tok)

            if tok.id == Id.Arith_Colon:
                # | ':' '(' regex ')'
                raise NotImplementedError(Id_str(tok.id))

            raise NotImplementedError(Id_str(tok.id))

    def _RepeatOp(self, p_repeat):
        # type: (PNode) -> re_repeat_t
        assert p_repeat.typ == grammar_nt.repeat_op, p_repeat

        tok = p_repeat.GetChild(0).tok
        id_ = tok.id
        # a+
        if id_ in (Id.Arith_Plus, Id.Arith_Star, Id.Arith_QMark):
            return re_repeat.Op(tok)

        if id_ == Id.Op_LBrace:
            p_range = p_repeat.GetChild(1)
            assert p_range.typ == grammar_nt.repeat_range, p_range

            # repeat_range: (
            #     Expr_DecInt [',']
            #   | ',' Expr_DecInt
            #   | Expr_DecInt ',' Expr_DecInt
            # )

            n = p_range.NumChildren()
            if n == 1:  # {3}
                return re_repeat.Num(p_range.GetChild(0).tok)

            if n == 2:
                if p_range.GetChild(0).tok.id == Id.Expr_DecInt:  # {,3}
                    return re_repeat.Range(p_range.GetChild(0).tok, None)
                else:  # {1,}
                    return re_repeat.Range(None, p_range.GetChild(1).tok)

            if n == 3:  # {1,3}
                return re_repeat.Range(
                    p_range.GetChild(0).tok,
                    p_range.GetChild(2).tok)

            raise AssertionError(n)

        raise AssertionError(id_)

    def _Regex(self, p_node):
        # type: (PNode) -> re_t
        typ = p_node.typ

        if typ == grammar_nt.regex:
            # regex: [re_alt] (('|'|'or') re_alt)*

            if p_node.NumChildren() == 1:
                return self._Regex(p_node.GetChild(0))

            # NOTE: We're losing the | and or operators
            alts = []  # type: List[re_t]
            n = p_node.NumChildren()
            for i in xrange(0, n, 2):  # was children[::2]
                c = p_node.GetChild(i)
                alts.append(self._Regex(c))
            return re.Alt(alts)

        if typ == grammar_nt.re_alt:
            # re_alt: (re_atom [repeat_op])+
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

        nt_name = self.number2symbol[typ]
        raise NotImplementedError(nt_name)


# vim: sw=4
