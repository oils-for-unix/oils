"""expr_parse.py."""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (loc, Token, DoubleQuoted, SingleQuoted,
                                       CommandSub, ShArrayLiteral,
                                       CompoundWord, word_part_t, word_e)
from _devbuild.gen.id_kind_asdl import Id, Kind, Id_str
from _devbuild.gen.types_asdl import lex_mode_e

from display import ui
from core.error import p_die
from frontend import consts
from frontend import lexer
from frontend import reader
from mycpp import mylib
from mycpp.mylib import log, tagswitch
from osh import braces
from osh import word_
from osh import word_compile
from pgen2 import parse
from pgen2.pnode import PNodeAllocator

_ = log

from typing import TYPE_CHECKING, Any, Dict, Tuple, List, cast, Optional
if TYPE_CHECKING:
    from frontend.lexer import Lexer
    from frontend.parse_lib import ParseContext
    from pgen2.grammar import Grammar
    from pgen2.pnode import PNode

if mylib.PYTHON:

    class ParseTreePrinter(object):
        """Prints a tree of PNode instances."""

        def __init__(self, names):
            # type: (Dict[int, str]) -> None
            self.names = names
            self.f = mylib.Stdout()

        def _Print(self, pnode, indent, i):
            # type: (PNode, int, int) -> None

            ind = '  ' * indent
            # NOTE:
            # - why isn't 'tok' None for PRODUCTIONS?  There is some redundancy to get
            #   rid of.
            if pnode.tok:
                if isinstance(pnode.tok, Token):
                    v = lexer.TokenVal(pnode.tok)
                else:
                    # e.g. CommandSub for x = $(echo hi)
                    v = repr(pnode.tok)
            else:
                v = '-'
            self.f.write('%s%d %s %s\n' % (ind, i, self.names[pnode.typ], v))
            if pnode.children is not None:
                for i, child in enumerate(pnode.children):
                    self._Print(child, indent + 1, i)

        def Print(self, pnode):
            # type: (PNode) -> None
            self._Print(pnode, 0, 0)


def _Classify(gr, tok):
    # type: (Grammar, Token) -> int

    # We have to match up what ParserGenerator.make_grammar() did when
    # calling make_label() and make_first().  See classify() in
    # opy/pgen2/driver.py.

    id_ = tok.id  # mycpp fix: we need C++ to do uint16_t -> int conversion

    # TODO: use something more efficient than a Dict
    if id_ in gr.tokens:
        return gr.tokens[id_]

    if id_ == Id.Unknown_DEqual:
        p_die('Use === to be exact, or ~== to convert types', tok)

    if id_ == Id.Unknown_DAmp:
        p_die("Use 'and' in expression mode (OILS-ERR-15)", tok)
    if id_ == Id.Unknown_DPipe:
        p_die("Use 'or' in expression mode (OILS-ERR-15)", tok)
    # Not possible to check '!' as it conflicts with Id.Expr_Bang

    if id_ == Id.Unknown_DDot:
        p_die('Use ..< for half-open range, or ..= for closed range (OILS-ERR-16)', tok)

    if id_ == Id.Unknown_Tok:
        type_str = ''
    else:
        type_str = ' (%s)' % ui.PrettyId(tok.id)
    p_die('Unexpected token in expression mode%s' % type_str, tok)


# Newlines are ignored between these pairs.
# yapf: disable
_OTHER_BALANCE = {

    # Parenthesized expressions (tuples) and func/proc parameter lists
    Id.Op_LParen: 1,
    Id.Op_RParen: -1,
    Id.Op_LBracket: 1,
    Id.Op_RBracket: -1,

    # Dicts are {}, and the grammar respects Op_Newline.
}
# yapf: enable


def _PushYshTokens(parse_ctx, gr, p, lex):
    # type: (ParseContext, Grammar, parse.Parser, Lexer) -> Token
    """Push tokens onto pgen2's parser.

    Returns the last token so it can be reused/seen by the CommandParser.
    """
    #log('keywords = %s', gr.keywords)
    #log('tokens = %s', gr.tokens)

    last_token = None  # type: Optional[Token]
    prev_was_newline = False

    balance = 0  # to ignore newlines

    while True:
        if last_token:  # e.g. left over from WordParser
            tok = last_token
            #log('last_token = %s', last_token)
            last_token = None
        else:
            tok = lex.Read(lex_mode_e.Expr)
            #log('tok = %s', tok)

        # Comments and whitespace.  Newlines aren't ignored.
        if consts.GetKind(tok.id) == Kind.Ignored:
            continue

        # For multiline lists, maps, etc.
        if tok.id == Id.Op_Newline:
            if balance > 0:
                #log('*** SKIPPING NEWLINE')
                continue
            # Eliminate duplicate newline tokens.  It makes the grammar simpler, and
            # it's consistent with CPython's lexer and our own WordParser.
            if prev_was_newline:
                continue
            prev_was_newline = True
        else:
            prev_was_newline = False

        balance += _OTHER_BALANCE.get(tok.id, 0)
        #log('BALANCE after seeing %s = %d', tok.id, balance)

        if tok.id == Id.Op_LParen:
            # For nesting inside $()
            lex.PushHint(Id.Op_RParen, Id.Op_RParen)

        #if tok.id == Id.Expr_Name and tok.val in KEYWORDS:
        #  tok.id = KEYWORDS[tok.val]
        #  log('Replaced with %s', tok.id)

        assert tok.id < 256, Id_str(tok.id)

        ilabel = _Classify(gr, tok)
        #log('tok = %s, ilabel = %d', tok, ilabel)

        if p.addtoken(tok.id, tok, ilabel):
            return tok

        #
        # Mututally recursive calls into the command/word parsers.
        #

        if tok.id in (Id.Left_ColonPipe,
                      Id.Left_PercentParen):  # :|  %(  LEGACY!
            left_tok = tok
            if tok.id == Id.Left_PercentParen:
                lex.PushHint(Id.Op_RParen, Id.Right_ShArrayLiteral)

            # Blame the opening token
            line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
            w_parser = parse_ctx.MakeWordParser(lex, line_reader)
            words = []  # type: List[CompoundWord]
            close_tok = None  # type: Optional[Token]
            done = False
            while not done:
                w = w_parser.ReadWord(lex_mode_e.ShCommand)
                with tagswitch(w) as case:
                    if case(word_e.Operator):
                        tok = cast(Token, w)
                        if tok.id == Id.Right_ShArrayLiteral:
                            if left_tok.id != Id.Left_PercentParen:
                                p_die('Expected ) to close', left_tok)
                            close_tok = tok
                            done = True  # can't use break here
                        elif tok.id == Id.Op_Pipe:
                            if left_tok.id != Id.Left_ColonPipe:
                                p_die('Expected ) to close', left_tok)
                            close_tok = tok
                            done = True  # can't use break here
                        elif tok.id == Id.Op_Newline:  # internal newlines allowed
                            continue
                        else:
                            p_die('Unexpected token in array literal',
                                  loc.Word(w))

                    elif case(word_e.Compound):
                        words.append(cast(CompoundWord, w))

                    else:
                        raise AssertionError()

            words2 = braces.BraceDetectAll(words)
            words3 = word_.TildeDetectAll(words2)

            typ = Id.Expr_CastedDummy

            lit_part = ShArrayLiteral(left_tok, words3, close_tok)
            opaque = cast(Token, lit_part)  # HACK for expr_to_ast
            done = p.addtoken(typ, opaque, gr.tokens[typ])
            assert not done  # can't end the expression

            # Now push the closing )
            ilabel = _Classify(gr, close_tok)
            done = p.addtoken(tok.id, close_tok, ilabel)
            assert not done  # can't end the expression

            continue

        # $(  @(  ^(
        if tok.id in (Id.Left_DollarParen, Id.Left_AtParen,
                      Id.Left_CaretParen):

            left_token = tok

            lex.PushHint(Id.Op_RParen, Id.Eof_RParen)
            line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
            c_parser = parse_ctx.MakeParserForCommandSub(
                line_reader, lex, Id.Eof_RParen)
            node = c_parser.ParseCommandSub()
            # A little gross: Copied from osh/word_parse.py
            right_token = c_parser.w_parser.cur_token

            cs_part = CommandSub(left_token, node, right_token)

            typ = Id.Expr_CastedDummy
            opaque = cast(Token, cs_part)  # HACK for expr_to_ast
            done = p.addtoken(typ, opaque, gr.tokens[typ])
            assert not done  # can't end the expression

            # Now push the closing )
            ilabel = _Classify(gr, right_token)
            done = p.addtoken(right_token.id, right_token, ilabel)
            assert not done  # can't end the expression

            continue

        # "   $"   """   $"""   ^"
        if tok.id in (Id.Left_DoubleQuote, Id.Left_DollarDoubleQuote,
                      Id.Left_TDoubleQuote, Id.Left_DollarTDoubleQuote,
                      Id.Left_CaretDoubleQuote):

            left_token = tok
            line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
            w_parser = parse_ctx.MakeWordParser(lex, line_reader)

            parts = []  # type: List[word_part_t]
            last_token = w_parser.ReadDoubleQuoted(left_token, parts)
            expr_dq_part = DoubleQuoted(left_token, parts, last_token)

            typ = Id.Expr_CastedDummy
            opaque = cast(Token, expr_dq_part)  # HACK for expr_to_ast
            done = p.addtoken(typ, opaque, gr.tokens[typ])
            assert not done  # can't end the expression

            continue

        # ${
        if tok.id == Id.Left_DollarBrace:
            left_token = tok
            line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
            w_parser = parse_ctx.MakeWordParser(lex, line_reader)

            part, last_token = w_parser.ReadBracedVarSub(left_token)

            # It's casted word_part.BracedVarSub -> dummy -> expr.BracedVarSub!
            typ = Id.Expr_CastedDummy
            opaque = cast(Token, part)  # HACK for expr_to_ast
            done = p.addtoken(typ, opaque, gr.tokens[typ])
            assert not done  # can't end the expression

            continue

        # 'x'  '''x'''
        # r'x'  r'''x'''
        # u'x'  u'''x'''
        # b'x'  b'''x'''
        # $'x'
        if tok.id in (Id.Left_SingleQuote, Id.Left_TSingleQuote,
                      Id.Left_RSingleQuote, Id.Left_RTSingleQuote,
                      Id.Left_USingleQuote, Id.Left_UTSingleQuote,
                      Id.Left_BSingleQuote, Id.Left_BTSingleQuote,
                      Id.Left_DollarSingleQuote):
            if tok.id == Id.Left_DollarSingleQuote:
                sq_mode = lex_mode_e.SQ_C
            elif tok.id in (Id.Left_USingleQuote, Id.Left_UTSingleQuote,
                            Id.Left_BSingleQuote, Id.Left_BTSingleQuote):
                sq_mode = lex_mode_e.J8_Str
            else:
                sq_mode = lex_mode_e.SQ_Raw

            left_token = tok
            line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
            w_parser = parse_ctx.MakeWordParser(lex, line_reader)

            tokens = []  # type: List[Token]
            last_token = w_parser.ReadSingleQuoted(sq_mode, left_token, tokens,
                                                   True)

            sval = word_compile.EvalSingleQuoted(left_token.id, tokens)
            sq_part = SingleQuoted(left_token, sval, last_token)

            typ = Id.Expr_CastedDummy
            opaque = cast(Token, sq_part)  # HACK for expr_to_ast
            done = p.addtoken(typ, opaque, gr.tokens[typ])
            assert not done  # can't end the expression
            continue

    else:
        # We never broke out -- EOF is too soon (how can this happen???)
        raise parse.ParseError("incomplete input", tok.id, tok)


class ExprParser(object):
    """A wrapper around a pgen2 parser."""

    def __init__(self, parse_ctx, gr):
        # type: (ParseContext, Grammar) -> None
        self.parse_ctx = parse_ctx
        self.gr = gr
        # Reused multiple times.
        self.push_parser = parse.Parser(gr)
        self.pnode_alloc = None  # type: Optional[PNodeAllocator]

    def Parse(self, lexer, start_symbol):
        # type: (Lexer, int) -> Tuple[PNode, Token]

        # Reuse the parser
        self.push_parser.setup(start_symbol, self.pnode_alloc)
        try:
            last_token = _PushYshTokens(self.parse_ctx, self.gr,
                                        self.push_parser, lexer)
        except parse.ParseError as e:
            #log('ERROR %s', e)
            # TODO:
            # - Describe what lexer mode we're in (Invalid syntax in regex)
            #   - Maybe say where the mode started
            # - Id.Unknown_Tok could say "This character is invalid"

            # ParseError has a "too much input" case but I haven't been able to
            # tickle it.  Maybe it's because of the Eof tokens?

            p_die(
                'Syntax error in expression (near %s)' % ui.PrettyId(e.tok.id),
                e.tok)

        return self.push_parser.rootnode, last_token


class ctx_PNodeAllocator(object):

    def __init__(self, ep):
        # type: (ExprParser) -> None
        self.expr_parser = ep
        self.expr_parser.pnode_alloc = PNodeAllocator()

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.expr_parser.pnode_alloc.Clear()
        self.expr_parser.pnode_alloc = None
