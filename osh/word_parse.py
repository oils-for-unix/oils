# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
word_parse.py - Parse the shell word language.

Hairy example:

hi$((1 + 2))"$(echo hi)"${var:-__"$(echo default)"__}

Substitutions can be nested, but which inner subs are allowed depends on the
outer sub.

lex_mode_e.ShCommand (_ReadUnquotedLeftParts)
  All subs and quotes are allowed:
  $v ${v}   $() ``   $(())   '' ""   $'' $""  <()  >()

lex_mode_e.DQ  (_ReadDoubleQuotedLeftParts)
  Var, Command, Arith, but no quotes.
  $v ${v}   $() ``   $(())
  No process substitution.

lex_mode_e.Arith
  Similar to DQ: Var, Command, and Arith sub, but no process sub.  bash doesn't
  allow quotes, but OSH does.  We allow ALL FOUR kinds of quotes, because we
  need those for associative array indexing.

lex_mode_e.VSub_ArgUnquoted
  Like UNQUOTED, everything is allowed (even process substitutions), but we
  stop at }, and space is SIGNIFICANT.
  
  Example: ${a:-  b   }

  ${X:-$v}   ${X:-${v}}  ${X:-$(echo hi)}  ${X:-`echo hi`}  ${X:-$((1+2))}
  ${X:-'single'}  ${X:-"double"}  ${X:-$'\n'}  ${X:-<(echo hi)}

lex_mode_e.VSub_ArgDQ
  In contrast to DQ, VS_ARG_DQ accepts nested "" and $'' and $"", e.g.
  "${x:-"default"}".

  In contrast, VS_ARG_UNQ respects single quotes and process substitution.

  It's weird that double quotes are allowed.  Space is also significant here,
  e.g. "${x:-a  "b"}".
"""

from _devbuild.gen import grammar_nt
from _devbuild.gen.id_kind_asdl import Id, Id_t, Kind
from _devbuild.gen.types_asdl import lex_mode_t, lex_mode_e
from _devbuild.gen.syntax_asdl import (
    BoolParamBox,
    Token,
    loc,
    source,
    DoubleQuoted,
    SingleQuoted,
    SimpleVarSub,
    BracedVarSub,
    CommandSub,
    ShArrayLiteral,
    AssocPair,
    bracket_op,
    bracket_op_t,
    suffix_op,
    suffix_op_t,
    rhs_word,
    rhs_word_e,
    rhs_word_t,
    word_e,
    word_t,
    CompoundWord,
    word_part,
    word_part_t,
    place_expr,
    place_expr_e,
    arith_expr_t,
    command,
    expr_t,
    ArgList,
    pat_t,
)
from core import alloc
from core.error import p_die
from mycpp.mylib import log
from core import pyutil
from core import ui
from frontend import consts
from frontend import lexer
from frontend import reader
from osh import tdop
from osh import arith_parse
from osh import braces
from osh import word_
from osh import word_compile
from mycpp.mylib import tagswitch

from typing import List, Optional, Tuple, cast
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from frontend.lexer import Lexer
    from frontend.parse_lib import ParseContext
    from frontend.reader import _Reader
    from osh.cmd_parse import VarChecker

_ = log

KINDS_THAT_END_WORDS = [Kind.Eof, Kind.WS, Kind.Op, Kind.Right]


class WordEmitter(object):
    """Common interface for [ and [["""

    def __init__(self):
        # type: () -> None
        """Empty constructor for mycpp."""
        pass

    def ReadWord(self, lex_mode):
        # type: (lex_mode_t) -> word_t
        raise NotImplementedError()


class WordParser(WordEmitter):
    def __init__(self, parse_ctx, lexer, line_reader):
        # type: (ParseContext, Lexer, _Reader) -> None
        self.parse_ctx = parse_ctx
        self.lexer = lexer
        self.line_reader = line_reader
        self.arena = line_reader.arena

        self.parse_opts = parse_ctx.parse_opts
        self.a_parser = tdop.TdopParser(arith_parse.Spec(), self,
                                        self.parse_opts)
        self.Reset()

    def Init(self, lex_mode):
        # type: (lex_mode_t) -> None
        """Used to parse arithmetic, see ParseContext."""
        self.next_lex_mode = lex_mode

    def Reset(self):
        # type: () -> None
        """Called by interactive loop."""
        # For _GetToken()
        self.cur_token = None  # type: Token
        self.token_kind = Kind.Undefined
        self.token_type = Id.Undefined_Tok

        self.next_lex_mode = lex_mode_e.ShCommand

        # Boolean mutated by CommandParser via word_.ctx_EmitDocToken.  For ### doc
        # comments
        self.emit_doc_token = False
        # Boolean mutated by CommandParser via word_.ctx_Multiline.  '...' starts
        # multiline mode.
        self.multiline = False

        # For detecting invalid \n\n in multiline mode.  Counts what we got
        # directly from the lexer.
        self.newline_state = 0
        # For consolidating \n\n -> \n for the CALLER.  This simplifies the parsers
        # that consume words.
        self.returned_newline = False

        # For integration with pgen2
        self.buffered_word = None  # type: word_t

    def _GetToken(self):
        # type: () -> None
        """Call this when you need to make a decision based on any of:

        self.token_type self.token_kind self.cur_token  # contents
        """
        if self.next_lex_mode != lex_mode_e.Undefined:
            self.cur_token = self.lexer.Read(self.next_lex_mode)
            self.token_type = self.cur_token.id
            self.token_kind = consts.GetKind(self.token_type)

            # number of consecutive newlines, ignoring whitespace
            if self.token_type == Id.Op_Newline:
                self.newline_state += 1
            elif self.token_kind != Kind.WS:
                self.newline_state = 0

            self.parse_ctx.trail.AppendToken(self.cur_token)  # For completion
            self.next_lex_mode = lex_mode_e.Undefined

    def _SetNext(self, lex_mode):
        # type: (lex_mode_t) -> None
        """Set the next lex state, but don't actually read a token.

        We need this for proper interactive parsing.
        """
        self.next_lex_mode = lex_mode

    def _ReadVarOpArg(self, arg_lex_mode):
        # type: (lex_mode_t) -> rhs_word_t

        # NOTE: Operators like | and < are not treated as special, so ${a:- | >} is
        # valid, even when unquoted.
        self._SetNext(arg_lex_mode)
        self._GetToken()

        w = self._ReadVarOpArg2(arg_lex_mode, Id.Undefined_Tok,
                                True)  # empty_ok

        # If the Compound has no parts, and we're in a double-quoted VarSub
        # arg, and empty_ok, then return Empty.  This is so it can evaluate to
        # the empty string and not get elided.
        #
        # Examples:
        # - "${s:-}", "${s/%pat/}"
        # It's similar to LooksLikeShAssignment where we turn x= into x=''.  And it
        # has the same potential problem of not having Token location info.
        #
        # NOTE: empty_ok is False only for the PatSub pattern, which means we'll
        # return a Compound with no parts, which is explicitly checked with a
        # custom error message.
        if len(w.parts) == 0 and arg_lex_mode == lex_mode_e.VSub_ArgDQ:
            return rhs_word.Empty

        return w

    def _ReadVarOpArg2(self, arg_lex_mode, eof_type, empty_ok):
        # type: (lex_mode_t, Id_t, bool) -> CompoundWord
        """Return a CompoundWord.

        Helper function for _ReadVarOpArg and used directly by
        _ReadPatSubVarOp.
        """
        w = self._ReadCompoundWord3(arg_lex_mode, eof_type, empty_ok)
        #log('w %s', w)
        tilde = word_.TildeDetect(w)
        if tilde:
            w = tilde
        return w

    def _ReadSliceVarOp(self):
        # type: () -> suffix_op.Slice
        """VarOf ':' ArithExpr (':' ArithExpr )?"""
        self._SetNext(lex_mode_e.Arith)
        self._GetToken()
        cur_id = self.token_type  # e.g. Id.Arith_Colon

        if self.token_type == Id.Arith_Colon:  # A pun for Id.VOp2_Colon
            # no beginning specified
            begin = None  # type: Optional[arith_expr_t]
        else:
            begin = self.a_parser.Parse()
            cur_id = self.a_parser.CurrentId()

        if cur_id == Id.Arith_RBrace:
            no_length = None  # type: Optional[arith_expr_t]  # No length specified
            return suffix_op.Slice(begin, no_length)

        # Id.Arith_Colon is a pun for Id.VOp2_Colon
        if cur_id == Id.Arith_Colon:
            self._SetNext(lex_mode_e.Arith)
            length = self._ReadArithExpr(Id.Arith_RBrace)
            return suffix_op.Slice(begin, length)

        p_die("Expected : or } in slice", self.cur_token)
        raise AssertionError()  # for MyPy

    def _ReadPatSubVarOp(self):
        # type: () -> suffix_op.PatSub
        """Looking at the first '/' after VarOf:

        VarSub    = ...
                  | VarOf '/' Match ( '/' WORD? )?
        Match     = '/' WORD   # can't be empty
                  | '#' WORD?  # may be empty
                  | '%' WORD?
        """
        slash_tok = self.cur_token  # location info
        replace_mode = Id.Undefined_Tok  # bizarre syntax / # %

        self._SetNext(lex_mode_e.VSub_ArgUnquoted)  # advance past /

        self._GetToken()
        if self.token_type == Id.Right_DollarBrace:
            pat = CompoundWord([])
            return suffix_op.PatSub(pat, rhs_word.Empty, replace_mode,
                                    slash_tok)

        if self.token_type in (Id.Lit_Slash, Id.Lit_Pound, Id.Lit_Percent):
            replace_mode = self.token_type
            self._SetNext(lex_mode_e.VSub_ArgUnquoted)

        # Bash quirk:
        # echo ${x/#/replace} has an empty pattern
        # echo ${x////replace} is non-empty; it means echo ${x//'/'/replace}
        empty_ok = replace_mode != Id.Lit_Slash
        pat = self._ReadVarOpArg2(lex_mode_e.VSub_ArgUnquoted, Id.Lit_Slash,
                                  empty_ok)
        #log('pat 1 %r', pat)

        if self.token_type == Id.Lit_Slash:
            # read until }
            replace = self._ReadVarOpArg(
                lex_mode_e.VSub_ArgUnquoted)  # type: rhs_word_t
        else:
            # e.g. ${v/a} is the same as ${v/a/}  -- empty replacement string
            replace = rhs_word.Empty

        self._GetToken()
        if self.token_type != Id.Right_DollarBrace:
            # This happens on invalid code
            p_die(
                "Expected } after replacement string, got %s" %
                ui.PrettyId(self.token_type), self.cur_token)

        return suffix_op.PatSub(pat, replace, replace_mode, slash_tok)

    def _ReadSubscript(self):
        # type: () -> bracket_op_t
        """ Subscript = '[' ('@' | '*' | ArithExpr) ']' """
        # Lookahead to see if we get @ or *.  Otherwise read a full arithmetic
        # expression.
        next_id = self.lexer.LookPastSpace(lex_mode_e.Arith)
        if next_id in (Id.Lit_At, Id.Arith_Star):
            op = bracket_op.WholeArray(next_id)  # type: bracket_op_t

            self._SetNext(lex_mode_e.Arith)  # skip past [
            self._GetToken()
            self._SetNext(lex_mode_e.Arith)  # skip past @
            self._GetToken()
        else:
            self._SetNext(lex_mode_e.Arith)  # skip past [
            anode = self._ReadArithExpr(Id.Arith_RBracket)
            op = bracket_op.ArrayIndex(anode)

        if self.token_type != Id.Arith_RBracket:  # Should be looking at ]
            p_die('Expected ] to close subscript', self.cur_token)

        self._SetNext(lex_mode_e.VSub_2)  # skip past ]
        self._GetToken()  # Needed to be in the same spot as no subscript

        return op

    def _ParseVarOf(self):
        # type: () -> BracedVarSub
        """
        VarOf     = NAME Subscript?
                  | NUMBER      # no subscript allowed, none of these are arrays
                                # ${@[1]} doesn't work, even though slicing does
                  | VarSymbol
        """
        self._GetToken()
        name_token = self.cur_token
        self._SetNext(lex_mode_e.VSub_2)

        self._GetToken()  # Check for []
        if self.token_type == Id.VOp2_LBracket:
            bracket_op = self._ReadSubscript()
        else:
            bracket_op = None

        part = BracedVarSub.CreateNull()
        part.token = name_token
        part.var_name = lexer.TokenVal(name_token)
        part.bracket_op = bracket_op
        return part

    def _ParseVarExpr(self, arg_lex_mode, allow_query=False):
        # type: (lex_mode_t, bool) -> BracedVarSub
        """Start parsing at the op -- we already skipped past the name."""
        part = self._ParseVarOf()

        self._GetToken()
        if self.token_type == Id.Right_DollarBrace:
            return part  # no ops

        op_kind = self.token_kind

        if op_kind == Kind.VTest:
            tok = self.cur_token
            arg_word = self._ReadVarOpArg(arg_lex_mode)
            if self.token_type != Id.Right_DollarBrace:
                p_die('Expected } to close ${', self.cur_token)

            part.suffix_op = suffix_op.Unary(tok, arg_word)

        elif op_kind == Kind.VOpOil:
            tok = self.cur_token
            arg_word = self._ReadVarOpArg(arg_lex_mode)
            if self.token_type != Id.Right_DollarBrace:
                p_die('Expected } to close ${', self.cur_token)

            UP_arg_word = arg_word
            with tagswitch(arg_word) as case:
                if case(rhs_word_e.Empty):
                    pass
                elif case(rhs_word_e.Compound):
                    arg_word = cast(CompoundWord, UP_arg_word)
                    # This handles ${x|html} and ${x %.3f} now
                    # However I think ${x %.3f} should be statically parsed?  It can enter
                    # the printf lexer modes.
                    ok, arg, quoted = word_.StaticEval(arg_word)
                    if not ok or quoted:
                        p_die('Expected a constant argument',
                              loc.Word(arg_word))

            part.suffix_op = suffix_op.Static(tok, arg)

        elif op_kind == Kind.VOp0:
            part.suffix_op = self.cur_token  # Nullary
            self._SetNext(lex_mode_e.VSub_2)  # Expecting }
            self._GetToken()

        elif op_kind == Kind.VOp1:  # % %% # ## etc.
            tok = self.cur_token
            # Weird exception that all shells have: these operators take a glob
            # pattern, so they're lexed as VSub_ArgUnquoted, not VSub_ArgDQ
            arg_word = self._ReadVarOpArg(lex_mode_e.VSub_ArgUnquoted)
            if self.token_type != Id.Right_DollarBrace:
                p_die('Expected } to close ${', self.cur_token)

            part.suffix_op = suffix_op.Unary(tok, arg_word)

        elif op_kind == Kind.VOp2:  # / : [ ]
            if self.token_type == Id.VOp2_Slash:
                patsub_op = self._ReadPatSubVarOp()

                # awkwardness for mycpp; could fix
                temp = cast(suffix_op_t, patsub_op)
                part.suffix_op = temp

                # Checked by the method above
                assert self.token_type == Id.Right_DollarBrace, self.cur_token

            elif self.token_type == Id.VOp2_Colon:
                part.suffix_op = self._ReadSliceVarOp()
                # NOTE: } in arithmetic mode.
                if self.token_type != Id.Arith_RBrace:
                    # Token seems off; doesn't point to X in # ${a:1:2 X
                    p_die('Expected } to close ${', self.cur_token)

            else:
                # TODO: Does this ever happen?
                p_die('Unexpected token in ${} (%s)' % 'VOp2', self.cur_token)

        elif op_kind == Kind.VOp3:  # ${prefix@} etc.
            if allow_query:
                part.suffix_op = self.cur_token  # Nullary
                self._SetNext(lex_mode_e.VSub_2)  # Expecting }
                self._GetToken()
            else:
                p_die("Unexpected token in ${} (%s)" % 'VOp3', self.cur_token)

        # NOTE: Arith_RBrace is for slicing, because it reads } in arithmetic
        # mode.  It's redundantly checked above.
        if self.token_type not in (Id.Right_DollarBrace, Id.Arith_RBrace):
            # ${a.} or ${!a.}
            p_die('Expected } to close ${', self.cur_token)

        # Now look for ops
        return part

    def ReadBracedVarSub(self, left_token):
        # type: (Token) -> Tuple[BracedVarSub, Token]
        """   For YSH expressions like var x = ${x:-"default"}.  """
        part = self._ReadBracedVarSub(left_token, d_quoted=False)
        last_token = self.cur_token
        return part, last_token

    def _ReadBracedVarSub(self, left_token, d_quoted):
        # type: (Token, bool) -> BracedVarSub
        """For the ${} expression language.

        NAME        = [a-zA-Z_][a-zA-Z0-9_]*
        NUMBER      = [0-9]+                    # ${10}, ${11}, ...

        Subscript   = '[' ('@' | '*' | ArithExpr) ']'
        VarSymbol   = '!' | '@' | '#' | ...
        VarOf       = NAME Subscript?
                    | NUMBER      # no subscript allowed, none of these are arrays
                                  # ${@[1]} doesn't work, even though slicing does
                    | VarSymbol

        NULLARY_OP  = '@Q' | '@E' | '@P' | '@A' | '@a'  # VOp0

        TEST_OP     = '-' | ':-' | '=' | ':=' | '+' | ':+' | '?' | ':?'
        STRIP_OP    = '#' | '##' | '%' | '%%'
        CASE_OP     = ',' | ',,' | '^' | '^^'
        UnaryOp     = TEST_OP | STRIP_OP | CASE_OP

        YSH_UNARY   = '|' | ' '                 # ${x|html} and ${x %.3f}.
                                                # SPACE is operator not %
        Match       = ('/' | '#' | '%') WORD    # match all / prefix / suffix
        VarExpr     = VarOf
                    | VarOf NULLARY_OP
                    | VarOf UnaryOp WORD
                    | VarOf YSH_UNARY STATIC_WORD
                    | VarOf ':' ArithExpr (':' ArithExpr )?
                    | VarOf '/' Match '/' WORD

        LengthExpr  = '#' VarOf    # can't apply operators after length

        RefOrKeys   = '!' VarExpr  # CAN apply operators after a named ref
                                   # ${!ref[0]} vs ${!keys[@]} resolved later

        PrefixQuery = '!' NAME ('*' | '@')  # list variable names with a prefix

        BuiltinSub  = '.' WORD+    # ${.myproc 'builtin' $sub}

        VarSub      = LengthExpr
                    | RefOrKeys
                    | PrefixQuery
                    | VarExpr
                    | BuiltinSub

        NOTES:
        - Arithmetic expressions are used twice, inside subscripts ${a[x+1]} and
          slicing ${a:x+1:y+2}
        - ${#} and ${!} need LL(2) lookahead (considering how my tokenizer works)
        - @ and * are technically arithmetic expressions in this implementation
        - We don't account for bash 4.4: ${param@operator} -- Q E P A a.  Note that
          it's also vectorized.

        Strictness over bash:
        - echo ${a[0][0]} doesn't do anything useful, so we disallow it from the
          grammar
        - ! and # prefixes can't be composed, even though named refs can be
          composed with other operators
        - '#' means 4 different things: length prefix, VarSymbol, UnaryOp to strip
          a prefix, and it can also be a literal part of WORD.

        From the parser's point of view, the prefix # can't be combined with
        UnaryOp/slicing/matching, and the ! can.  However

        - ${a[@]:1:2} is not allowed
        - ${#a[@]:1:2} is allowed, but gives the wrong answer
        """
        if d_quoted:
            arg_lex_mode = lex_mode_e.VSub_ArgDQ
        else:
            arg_lex_mode = lex_mode_e.VSub_ArgUnquoted

        self._SetNext(lex_mode_e.VSub_1)
        self._GetToken()

        ty = self.token_type
        first_tok = self.cur_token

        if ty == Id.VSub_Pound:
            # Disambiguate
            next_id = self.lexer.LookPastSpace(lex_mode_e.VSub_1)
            if next_id not in (Id.Unknown_Tok, Id.Right_DollarBrace):
                # e.g. a name, '#' is the prefix
                self._SetNext(lex_mode_e.VSub_1)
                part = self._ParseVarOf()

                self._GetToken()
                if self.token_type != Id.Right_DollarBrace:
                    p_die('Expected } after length expression', self.cur_token)

                part.prefix_op = first_tok

            else:  # not a prefix, '#' is the variable
                part = self._ParseVarExpr(arg_lex_mode)

        elif ty == Id.VSub_Bang:
            next_id = self.lexer.LookPastSpace(lex_mode_e.VSub_1)
            if next_id not in (Id.Unknown_Tok, Id.Right_DollarBrace):
                # e.g. a name, '!' is the prefix
                # ${!a} -- this is a ref
                # ${!3} -- this is ref
                # ${!a[1]} -- this is a ref
                # ${!a[@]} -- this is a keys
                # No lookahead -- do it in a second step, or at runtime
                self._SetNext(lex_mode_e.VSub_1)
                part = self._ParseVarExpr(arg_lex_mode, allow_query=True)

                part.prefix_op = first_tok

            else:  # not a prefix, '!' is the variable
                part = self._ParseVarExpr(arg_lex_mode)

        elif ty == Id.VSub_Dot:
            # Note: this will become a new builtin_sub type, so this method must
            # return word_part_t rather than BracedVarSub.  I don't think that
            # should cause problems.
            p_die('TODO: ${.myproc builtin sub}', self.cur_token)

        # VS_NAME, VS_NUMBER, symbol that isn't # or !
        elif self.token_kind == Kind.VSub:
            part = self._ParseVarExpr(arg_lex_mode)

        else:
            # e.g. ${^}
            p_die('Unexpected token in ${}', self.cur_token)

        part.left = left_token  # attach the argument
        part.right = self.cur_token
        return part

    def _ReadSingleQuoted(self, left_token, lex_mode):
        # type: (Token, lex_mode_t) -> SingleQuoted
        """Internal method to read a word_part."""
        tokens = []  # type: List[Token]
        # In command mode, we never disallow backslashes like '\'
        self.ReadSingleQuoted(lex_mode, left_token, tokens, False)
        right_quote = self.cur_token
        node = SingleQuoted(left_token, tokens, right_quote)
        return node

    def ReadSingleQuoted(self, lex_mode, left_token, tokens, is_oil_expr):
        # type: (lex_mode_t, Token, List[Token], bool) -> Token
        """Used by expr_parse.py."""

        # YSH could also disallow Unicode{4,8} and Octal{3,4}?  And certain OneChar
        # like \v if we want to be pedantic.  Well that would make porting harder
        # for no real reason.  It's probably better in a lint tool.
        #
        # The backslash issue is a correctness thing.  It allows the language to be
        # expanded later.

        # echo '\' is allowed, but x = '\' is invalid, in favor of x = r'\'
        no_backslashes = is_oil_expr and left_token.id == Id.Left_SingleQuote

        expected_end_tokens = 3 if left_token.id in (
            Id.Left_TSingleQuote, Id.Left_RTSingleQuote,
            Id.Left_DollarTSingleQuote) else 1
        num_end_tokens = 0

        while num_end_tokens < expected_end_tokens:
            self._SetNext(lex_mode)
            self._GetToken()

            # Kind.Char emitted in DOLLAR_SQ state
            if self.token_kind in (Kind.Lit, Kind.Char):
                tok = self.cur_token
                # Happens in lex_mode_e.SQ: 'one\two' is ambiguous, should be
                # r'one\two' or c'one\\two'
                if no_backslashes and '\\' in tok.tval:
                    p_die(
                        r"Strings with backslashes should look like r'\n' or $'\n'",
                        tok)

                if is_oil_expr:
                    if self.token_type == Id.Char_Octal3:
                        p_die(
                            r"Use \xhh or \u{...} instead of octal escapes in YSH strings",
                            tok)

                    if self.token_type == Id.Char_Hex and self.cur_token.length != 4:
                        # disallow \xH
                        p_die(
                            r'Invalid hex escape in YSH string (must be \xHH)',
                            tok)

                tokens.append(tok)

            elif self.token_kind == Kind.Unknown:
                tok = self.cur_token
                # x = $'\z' is disallowed; ditto for echo $'\z' if shopt -u parse_backslash
                if is_oil_expr or not self.parse_opts.parse_backslash():
                    p_die("Invalid char escape in C-style string literal", tok)

                tokens.append(tok)

            elif self.token_kind == Kind.Eof:
                p_die('Unexpected EOF in single-quoted string that began here',
                      left_token)

            elif self.token_kind == Kind.Right:
                # assume Id.Right_SingleQuote
                num_end_tokens += 1
                tokens.append(self.cur_token)

            else:
                raise AssertionError(self.cur_token)

            if self.token_kind != Kind.Right:
                num_end_tokens = 0  # we need three in a ROW

        if expected_end_tokens == 1:
            tokens.pop()
        elif expected_end_tokens == 3:  # Get rid of spurious end tokens
            tokens.pop()
            tokens.pop()
            tokens.pop()

        # Remove space from '''  r'''  $''' in both expression mode and command mode
        if left_token.id in (Id.Left_TSingleQuote, Id.Left_RTSingleQuote,
                             Id.Left_DollarTSingleQuote):
            word_compile.RemoveLeadingSpaceSQ(tokens)

        return self.cur_token

    def _ReadDoubleQuotedLeftParts(self):
        # type: () -> word_part_t
        """Read substitution parts in a double quoted context."""
        if self.token_type in (Id.Left_DollarParen, Id.Left_Backtick):
            return self._ReadCommandSub(self.token_type, d_quoted=True)

        if self.token_type == Id.Left_DollarBrace:
            return self._ReadBracedVarSub(self.cur_token, d_quoted=True)

        if self.token_type == Id.Left_DollarDParen:
            return self._ReadArithSub()

        if self.token_type == Id.Left_DollarBracket:
            return self._ReadExprSub(lex_mode_e.DQ)

        raise AssertionError(self.cur_token)

    def _ReadUnquotedLeftParts(self, triple_out):
        # type: (Optional[BoolParamBox]) -> word_part_t
        """Read substitutions and quoted strings (for lex_mode_e.ShCommand).

        If triple_out is set, then we try parsing triple quoted strings,
        and set its value to True if we got one.
        """
        if self.token_type in (Id.Left_DoubleQuote, Id.Left_DollarDoubleQuote):
            # NOTE: $"" is a synonym for "" for now.
            # It would make sense if it added \n \0 \x00 \u{123} etc.  But that's not
            # what bash does!
            dq_part = self._ReadDoubleQuoted(self.cur_token)
            if triple_out and len(dq_part.parts) == 0:  # read empty word ""
                if self.lexer.ByteLookAhead() == '"':
                    self._SetNext(lex_mode_e.ShCommand)
                    self._GetToken()
                    # HACK: magically transform the third " in """ to
                    # Id.Left_TDoubleQuote, so that """ is the terminator
                    left_dq_token = self.cur_token
                    left_dq_token.id = Id.Left_TDoubleQuote
                    triple_out.b = True  # let caller know we got it
                    return self._ReadDoubleQuoted(left_dq_token)

            return dq_part

        if self.token_type in (Id.Left_SingleQuote, Id.Left_RSingleQuote,
                               Id.Left_DollarSingleQuote):
            if self.token_type == Id.Left_DollarSingleQuote:
                lexer_mode = lex_mode_e.SQ_C
                new_id = Id.Left_DollarTSingleQuote
            else:
                lexer_mode = lex_mode_e.SQ_Raw
                # Note we should also use Id.Left_RTSingleQuote
                new_id = Id.Left_TSingleQuote

            sq_part = self._ReadSingleQuoted(self.cur_token, lexer_mode)
            if triple_out and len(
                    sq_part.tokens) == 0:  # read empty '' or r'' or $''
                if self.lexer.ByteLookAhead() == "'":
                    self._SetNext(lex_mode_e.ShCommand)
                    self._GetToken()

                    # HACK: magically transform the third ' in r''' to
                    # Id.Left_TSingleQuote, so that ''' is the terminator
                    left_sq_token = self.cur_token
                    left_sq_token.id = new_id
                    triple_out.b = True  # let caller know we got it
                    return self._ReadSingleQuoted(left_sq_token, lexer_mode)

            return sq_part

        if self.token_type in (Id.Left_DollarParen, Id.Left_Backtick,
                               Id.Left_ProcSubIn, Id.Left_ProcSubOut):
            return self._ReadCommandSub(self.token_type, d_quoted=False)

        if self.token_type == Id.Left_DollarBrace:
            return self._ReadBracedVarSub(self.cur_token, d_quoted=False)

        if self.token_type == Id.Left_DollarDParen:
            return self._ReadArithSub()

        if self.token_type == Id.Left_DollarBracket:
            return self._ReadExprSub(lex_mode_e.ShCommand)

        raise AssertionError(self.cur_token)

    def _ReadExtGlob(self):
        # type: () -> word_part.ExtGlob
        """
        Grammar:
          Item         = CompoundWord | EPSILON  # important: @(foo|) is allowed
          LEFT         = '@(' | '*(' | '+(' | '?(' | '!('
          RIGHT        = ')'
          ExtGlob      = LEFT (Item '|')* Item RIGHT  # ITEM may be empty
          Compound includes ExtGlob
        """
        left_token = self.cur_token
        right_token = None  # type: Token
        arms = []  # type: List[CompoundWord]

        self.lexer.PushHint(Id.Op_RParen, Id.Right_ExtGlob)
        self._SetNext(lex_mode_e.ExtGlob)  # advance past LEFT

        read_word = False  # did we just a read a word?  To handle @(||).

        while True:
            self._GetToken()

            if self.token_type == Id.Right_ExtGlob:
                if not read_word:
                    arms.append(CompoundWord([]))
                right_token = self.cur_token
                break

            elif self.token_type == Id.Op_Pipe:
                if not read_word:
                    arms.append(CompoundWord([]))
                read_word = False
                self._SetNext(lex_mode_e.ExtGlob)

            # lex mode EXTGLOB should only produce these 4 kinds of tokens
            elif self.token_kind in (Kind.Lit, Kind.Left, Kind.VSub,
                                     Kind.ExtGlob):
                w = self._ReadCompoundWord(lex_mode_e.ExtGlob)
                arms.append(w)
                read_word = True

            elif self.token_kind == Kind.Eof:
                p_die('Unexpected EOF reading extended glob that began here',
                      left_token)

            else:
                raise AssertionError(self.cur_token)

        return word_part.ExtGlob(left_token, arms, right_token)

    def _ReadLikeDQ(self, left_token, is_oil_expr, out_parts):
        # type: (Optional[Token], bool, List[word_part_t]) -> None
        """
        Args:
          left_token: A token if we are reading a double quoted part, or None if
            we're reading a here doc.
          is_oil_expr: Whether to disallow backticks and invalid char escapes
          out_parts: list of word_part to append to
        """
        if left_token:
            expected_end_tokens = 3 if left_token.id == Id.Left_TDoubleQuote else 1
        else:
            expected_end_tokens = 1000  # here doc will break

        num_end_tokens = 0
        while num_end_tokens < expected_end_tokens:
            self._SetNext(lex_mode_e.DQ)
            self._GetToken()

            if self.token_kind == Kind.Lit:
                if self.token_type == Id.Lit_EscapedChar:
                    tok = self.cur_token
                    ch = lexer.TokenSliceLeft(tok, 1)
                    part = word_part.EscapedLiteral(tok,
                                                    ch)  # type: word_part_t
                else:
                    if self.token_type == Id.Lit_BadBackslash:
                        # echo "\z" is OK in shell, but 'x = "\z" is a syntax error in
                        # YSH.
                        # Slight hole: We don't catch 'x = ${undef:-"\z"} because of the
                        # recursion (unless parse_backslash)
                        if is_oil_expr or not self.parse_opts.parse_backslash():
                            p_die("Invalid char escape in double quoted string",
                                  self.cur_token)
                    elif self.token_type == Id.Lit_Dollar:
                        if is_oil_expr or not self.parse_opts.parse_dollar():
                            p_die("Literal $ should be quoted like \$",
                                  self.cur_token)

                    part = self.cur_token
                out_parts.append(part)

            elif self.token_kind == Kind.Left:
                if self.token_type == Id.Left_Backtick and is_oil_expr:
                    p_die("Invalid backtick: use $(cmd) or \\` in YSH strings",
                          self.cur_token)

                part = self._ReadDoubleQuotedLeftParts()
                out_parts.append(part)

            elif self.token_kind == Kind.VSub:
                tok = self.cur_token
                part = SimpleVarSub(tok, lexer.TokenSliceLeft(tok, 1))
                out_parts.append(part)
                # NOTE: parsing "$f(x)" would BREAK CODE.  Could add a more for it
                # later.

            elif self.token_kind == Kind.Right:
                assert self.token_type == Id.Right_DoubleQuote, self.token_type
                if left_token:
                    num_end_tokens += 1

                # In a here doc, the right quote is literal!
                out_parts.append(self.cur_token)

            elif self.token_kind == Kind.Eof:
                if left_token:
                    p_die(
                        'Unexpected EOF reading double-quoted string that began here',
                        left_token)
                else:  # here docs will have an EOF in their token stream
                    break

            else:
                raise AssertionError(self.cur_token)

            if self.token_kind != Kind.Right:
                num_end_tokens = 0  # """ must be CONSECUTIVE

        if expected_end_tokens == 1:
            out_parts.pop()
        elif expected_end_tokens == 3:
            out_parts.pop()
            out_parts.pop()
            out_parts.pop()

        # Remove space from """ in both expression mode and command mode
        if left_token and left_token.id == Id.Left_TDoubleQuote:
            word_compile.RemoveLeadingSpaceDQ(out_parts)

        # Return nothing, since we appended to 'out_parts'

    def _ReadDoubleQuoted(self, left_token):
        # type: (Token) -> DoubleQuoted
        """Helper function for "hello $name".

        Args:
          eof_type: for stopping at }, Id.Lit_RBrace
          here_doc: Whether we are reading in a here doc context

        Also ${foo%%a b c}  # treat this as double quoted.  until you hit
        """
        parts = []  # type: List[word_part_t]
        self._ReadLikeDQ(left_token, False, parts)

        right_quote = self.cur_token
        return DoubleQuoted(left_token, parts, right_quote)

    def ReadDoubleQuoted(self, left_token, parts):
        # type: (Token, List[word_part_t]) -> Token
        """For expression mode.

        Read var x = "${dir:-}/$name"; etc.
        """
        self._ReadLikeDQ(left_token, True, parts)
        return self.cur_token

    def _ReadCommandSub(self, left_id, d_quoted=False):
        # type: (Id_t, bool) -> CommandSub
        """
        NOTE: This is not in the grammar, because word parts aren't in the grammar!

        command_sub = '$(' command_list ')'
                    | '@(' command_list ')'
                    | '<(' command_list ')'
                    | '>(' command_list ')'
                    | ` command_list `
        """
        left_token = self.cur_token

        # Set the lexer in a state so ) becomes the EOF token.
        if left_id in (Id.Left_DollarParen, Id.Left_AtParen, Id.Left_ProcSubIn,
                       Id.Left_ProcSubOut):
            self._SetNext(lex_mode_e.ShCommand)  # advance past $( etc.

            right_id = Id.Eof_RParen
            self.lexer.PushHint(Id.Op_RParen, right_id)
            c_parser = self.parse_ctx.MakeParserForCommandSub(
                self.line_reader, self.lexer, right_id)
            # NOTE: This doesn't use something like main_loop because we don't want
            # to interleave parsing and execution!  Unlike 'source' and 'eval'.
            node = c_parser.ParseCommandSub()

            right_token = c_parser.w_parser.cur_token

        elif left_id == Id.Left_Backtick and self.parse_ctx.one_pass_parse:
            # NOTE: This is an APPROXIMATE solution for translation ONLY.  See
            # test/osh2oil.

            right_id = Id.Eof_Backtick
            self.lexer.PushHint(Id.Left_Backtick, right_id)
            c_parser = self.parse_ctx.MakeParserForCommandSub(
                self.line_reader, self.lexer, right_id)
            node = c_parser.ParseCommandSub()
            right_token = c_parser.w_parser.cur_token

        elif left_id == Id.Left_Backtick:
            if not self.parse_opts.parse_backticks():
                p_die('Use $(cmd) instead of backticks (parse_backticks)',
                      left_token)

            self._SetNext(lex_mode_e.Backtick)  # advance past `

            parts = []  # type: List[str]
            while True:
                self._GetToken()
                #log("TOK %s", self.cur_token)

                if self.token_type == Id.Backtick_Quoted:
                    parts.append(self.cur_token.tval[1:])  # Remove leading \

                elif self.token_type == Id.Backtick_DoubleQuote:
                    # Compatibility: If backticks are double quoted, then double quotes
                    # within them have to be \"
                    # Shells aren't smart enough to match nested " and ` quotes (but OSH
                    # is)
                    if d_quoted:
                        parts.append(
                            self.cur_token.tval[1:])  # Remove leading \
                    else:
                        parts.append(self.cur_token.tval)

                elif self.token_type == Id.Backtick_Other:
                    parts.append(self.cur_token.tval)

                elif self.token_type == Id.Backtick_Right:
                    break

                elif self.token_type == Id.Eof_Real:
                    # Note: this parse error is in the ORIGINAL context.  No code_str yet.
                    p_die('Unexpected EOF while looking for closing backtick',
                          left_token)

                else:
                    raise AssertionError(self.cur_token)

                self._SetNext(lex_mode_e.Backtick)

            # Calculate right SPID on CommandSub BEFORE re-parsing.
            right_token = self.cur_token

            code_str = ''.join(parts)
            #log('code %r', code_str)

            # NOTE: This is similar to how we parse aliases in osh/cmd_parse.py.  It
            # won't have the same location info as MakeParserForCommandSub(), because
            # the lexer is different.
            arena = self.parse_ctx.arena
            #arena = alloc.Arena()
            line_reader = reader.StringLineReader(code_str, arena)
            c_parser = self.parse_ctx.MakeOshParser(line_reader)
            src = source.Reparsed('backticks', left_token, right_token)
            with alloc.ctx_Location(arena, src):
                node = c_parser.ParseCommandSub()

        else:
            raise AssertionError(left_id)

        return CommandSub(left_token, node, right_token)

    def _ReadExprSub(self, lex_mode):
        # type: (lex_mode_t) -> word_part.ExprSub
        """$[d->key]  $[obj.method()]  etc."""
        left_token = self.cur_token

        self._SetNext(lex_mode_e.Expr)
        enode, right_token = self.parse_ctx.ParseYshExpr(
            self.lexer, grammar_nt.oil_expr_sub)

        self._SetNext(lex_mode)  # Move past ]
        return word_part.ExprSub(left_token, enode, right_token)

    def ParseVarDecl(self, kw_token):
        # type: (Token) -> command.VarDecl
        """
        oil_var_decl: name_type_list '=' testlist end_stmt

        Note that assignments must end with \n  ;  }  or EOF.  Unlike shell
        assignments, we disallow:
        
        var x = 42 | wc -l
        var x = 42 && echo hi
        """
        self._SetNext(lex_mode_e.Expr)
        enode, last_token = self.parse_ctx.ParseVarDecl(kw_token, self.lexer)
        # Hack to move } from what the Expr lexer modes gives to what CommandParser
        # wants
        if last_token.id == Id.Op_RBrace:
            last_token.id = Id.Lit_RBrace

        # Let the CommandParser see the Op_Semi or Op_Newline.
        self.buffered_word = last_token
        self._SetNext(lex_mode_e.ShCommand)  # always back to this
        return enode

    def ParsePlaceMutation(self, kw_token, var_checker):
        # type: (Token, VarChecker) -> command.PlaceMutation
        """
        setvar a[i] = 1
        setvar i += 1
        setvar i++
        """
        self._SetNext(lex_mode_e.Expr)
        enode, last_token = self.parse_ctx.ParsePlaceMutation(
            kw_token, self.lexer)
        # Hack to move } from what the Expr lexer modes gives to what CommandParser
        # wants
        if last_token.id == Id.Op_RBrace:
            last_token.id = Id.Lit_RBrace

        for place in enode.lhs:
            UP_place = place
            with tagswitch(place) as case:
                if case(place_expr_e.Var):
                    place = cast(place_expr.Var, UP_place)
                    var_checker.Check(kw_token.id, place.name)
                # TODO: Do indices as well

        # Let the CommandParser see the Op_Semi or Op_Newline.
        self.buffered_word = last_token
        self._SetNext(lex_mode_e.ShCommand)  # always back to this
        return enode

    def ParseBareDecl(self):
        # type: () -> expr_t
        """
        x = {name: val}
        """
        self._SetNext(lex_mode_e.Expr)
        self._GetToken()
        enode, last_token = self.parse_ctx.ParseYshExpr(self.lexer,
                                                        grammar_nt.command_expr)
        if last_token.id == Id.Op_RBrace:
            last_token.id = Id.Lit_RBrace
        self.buffered_word = last_token
        self._SetNext(lex_mode_e.ShCommand)
        return enode

    def ParseCommandExpr(self):
        # type: () -> expr_t
        """
        = 1+2
        """
        enode, last_token = self.parse_ctx.ParseYshExpr(self.lexer,
                                                        grammar_nt.command_expr)

        # In some cases, such as the case statement, we expect *the lexer* to be
        # pointing at the token right after the expression. But the expression
        # parser must have read to the `last_token`. Unreading places the lexer
        # back in the expected state. Ie:
        #
        # case (x) {                           case (x) {
        #   (else) { = x }                       (else) { = x }
        #                 ^ The lexer is here                 ^ Unread to here
        # }                                    }
        assert last_token.id in (Id.Op_Newline, Id.Eof_Real, Id.Op_Semi,
                                 Id.Op_RBrace), last_token
        if last_token.id != Id.Eof_Real:
            # Eof_Real is the only token we cannot unread
            self.lexer.MaybeUnreadOne()

        return enode

    def ParseProc(self, node):
        # type: (command.Proc) -> None

        # proc name-with-hyphens() must be accepted
        self._SetNext(lex_mode_e.ShCommand)
        self._GetToken()
        # example: 'proc f[' gets you Lit_ArrayLhsOpen
        if self.token_type != Id.Lit_Chars:
            p_die('Invalid proc name %s' % ui.PrettyToken(self.cur_token),
                  self.cur_token)

        # TODO: validate this more.  Disallow proc 123 { }, which isn't disallowed
        # for shell functions.  Similar to IsValidVarName().
        node.name = self.cur_token

        last_token = self.parse_ctx.ParseProc(self.lexer, node)
        if last_token.id == Id.Op_LBrace:  # Translate to what CommandParser wants
            last_token.id = Id.Lit_LBrace
        self.buffered_word = last_token
        self._SetNext(lex_mode_e.ShCommand)  # TODO: Do we need this?

    def ParseYshCasePattern(self):
        # type: () -> Tuple[pat_t, Token]
        pat, left_tok, last_token = self.parse_ctx.ParseYshCasePattern(self.lexer)

        if last_token.id == Id.Op_LBrace:
            last_token.id = Id.Lit_LBrace
        self.buffered_word = last_token

        return pat, left_tok

    def NewlineOkForYshCase(self):
        # type: () -> Id_t
        """Check for optional newline and consume it.

        This is a special case of `_NewlineOk` which fixed some "off-by-one" issues
        which crop up while parsing Ysh Case Arms. For more details, see
        #oil-dev > Progress On YSH Case Grammar on zulip.

        Returns a token id which is filled with the choice of

             word { echo word }
             (3)  { echo expr }
             /e/  { echo eggex }
           }        # right brace
        """
        while True:
            next_id = self.lexer.LookAheadOne(lex_mode_e.Expr)

            # Cannot lookahead past lines
            if next_id == Id.Unknown_Tok:
                self.lexer.MoveToNextLine()
                continue

            next_kind = consts.GetKind(next_id)
            if next_id != Id.Op_Newline and next_kind != Kind.Ignored:
                break

            self.lexer.Read(lex_mode_e.Expr)

        if next_id in (Id.Op_RBrace, Id.Op_LParen, Id.Arith_Slash):
            self._SetNext(lex_mode_e.Expr)  # Continue in expression mode
        else:
            #  Consume the trailing Op_Newline
            self._SetNext(lex_mode_e.ShCommand)
            self._GetToken()

        return next_id

    def ParseImport(self, node):
        # type: (command.Import) -> None
        last_token = self.parse_ctx.ParseImport(self.lexer, node)
        self.buffered_word = last_token

    def _ReadArithExpr(self, end_id):
        # type: (Id_t) -> arith_expr_t
        """Read and parse an arithmetic expression in various contexts.

        $(( 1+2 ))
        (( a=1+2 ))
        ${a[ 1+2 ]}
        ${a : 1+2 : 1+2}

        See tests/arith-context.test.sh for ambiguous cases.

        ${a[a[0]]} is valid  # VS_RBRACKET vs Id.Arith_RBracket

        ${s : a<b?0:1 : 1}  # VS_COLON vs Id.Arith_Colon

        See the assertion in ArithParser.Parse() -- unexpected extra input.
        """
        # calls self.ReadWord(lex_mode_e.Arith)
        anode = self.a_parser.Parse()
        cur_id = self.a_parser.CurrentId()
        if end_id != Id.Undefined_Tok and cur_id != end_id:
            p_die(
                'Unexpected token after arithmetic expression (%s != %s)' %
                (ui.PrettyId(cur_id), ui.PrettyId(end_id)),
                loc.Word(self.a_parser.cur_word))
        return anode

    def _ReadArithSub(self):
        # type: () -> word_part.ArithSub
        """Read an arith substitution, which contains an arith expression, e.g.

        $((a + 1)).
        """
        left_tok = self.cur_token

        # The second one needs to be disambiguated in stuff like stuff like:
        # $(echo $(( 1+2 )) )
        self.lexer.PushHint(Id.Op_RParen, Id.Right_DollarDParen)

        # NOTE: To disambiguate $(( as arith sub vs. command sub and subshell, we
        # could save the lexer/reader state here, and retry if the arithmetic parse
        # fails.  But we can almost always catch this at parse time.  There could
        # be some exceptions like:
        # $((echo * foo))  # looks like multiplication
        # $((echo / foo))  # looks like division

        self._SetNext(lex_mode_e.Arith)
        anode = self._ReadArithExpr(Id.Arith_RParen)

        # TODO: This could be DQ or Arith too
        self._SetNext(lex_mode_e.ShCommand)

        # PROBLEM: $(echo $(( 1 + 2 )) )
        # Two right parens break the Id.Eof_RParen scheme
        self._GetToken()
        if self.token_type != Id.Right_DollarDParen:
            p_die('Expected second ) to end arith sub', self.cur_token)

        right_tok = self.cur_token
        return word_part.ArithSub(left_tok, anode, right_tok)

    def ReadDParen(self):
        # type: () -> Tuple[arith_expr_t, Token]
        """Read ((1+ 2))  -- command context.

        We're using the word parser because it's very similar to _ReadArithExpr
        above.

        This also returns the terminating `Op_DRightParen` token for use as location
        tracking.
        """
        # The second one needs to be disambiguated in stuff like stuff like:
        # TODO: Be consistent with ReadForExpression below and use lex_mode_e.Arith?
        # Then you can get rid of this.
        self.lexer.PushHint(Id.Op_RParen, Id.Op_DRightParen)

        self._SetNext(lex_mode_e.Arith)
        anode = self._ReadArithExpr(Id.Arith_RParen)

        self._SetNext(lex_mode_e.ShCommand)

        # PROBLEM: $(echo $(( 1 + 2 )) )
        self._GetToken()
        right = self.cur_token
        if self.token_type != Id.Op_DRightParen:
            p_die('Expected second ) to end arith statement', self.cur_token)

        self._SetNext(lex_mode_e.ShCommand)

        return anode, right

    def _SetNextNonSpace(self):
        # type: () -> None
        """Same logic as _ReadWord, but for ReadForExpression."""
        while True:
            self._SetNext(lex_mode_e.Arith)
            self._GetToken()
            if self.token_kind not in (Kind.Ignored, Kind.WS):
                break

    def ReadForExpression(self):
        # type: () -> command.ForExpr
        """Read ((i=0; i<5; ++i)) -- part of command context."""
        self._SetNextNonSpace()  # skip over ((

        self._GetToken()
        cur_id = self.token_type  # for end of arith expressions

        if cur_id == Id.Arith_Semi:  # for (( ; i < 10; i++ ))
            init_node = None  # type: Optional[arith_expr_t]
        else:
            init_node = self.a_parser.Parse()
            cur_id = self.a_parser.CurrentId()
        self._SetNextNonSpace()

        # It's odd to keep track of both cur_id and self.token_type in this
        # function, but it works, and is tested in 'test/parse_error.sh
        # arith-integration'
        if cur_id != Id.Arith_Semi:  # for (( x=0 b; ... ))
            p_die("Expected ; here", loc.Word(self.a_parser.cur_word))

        self._GetToken()
        cur_id = self.token_type

        if cur_id == Id.Arith_Semi:  # for (( ; ; i++ ))
            cond_node = None  # type: Optional[arith_expr_t]
        else:
            cond_node = self.a_parser.Parse()
            cur_id = self.a_parser.CurrentId()
        self._SetNextNonSpace()

        if cur_id != Id.Arith_Semi:  # for (( x=0; x<5 b ))
            p_die("Expected ; here", loc.Word(self.a_parser.cur_word))

        self._GetToken()
        cur_id = self.token_type

        if cur_id == Id.Arith_RParen:  # for (( ; ; ))
            update_node = None  # type: Optional[arith_expr_t]
        else:
            update_node = self._ReadArithExpr(Id.Arith_RParen)
        self._SetNextNonSpace()

        self._GetToken()
        if self.token_type != Id.Arith_RParen:
            p_die('Expected ) to end for loop expression', self.cur_token)
        self._SetNext(lex_mode_e.ShCommand)

        # redirects is None, will be assigned in CommandEvaluator
        node = command.ForExpr.CreateNull()
        node.init = init_node
        node.cond = cond_node
        node.update = update_node
        return node

    def _ReadArrayLiteral(self):
        # type: () -> word_part_t
        """a=(1 2 3)

        TODO: See osh/cmd_parse.py:164 for Id.Lit_ArrayLhsOpen, for a[x++]=1

        We want:

        A=(['x']=1 ["x"]=2 [$x$y]=3)

        Maybe allow this as a literal string?  Because I think I've seen it before?
        Or maybe force people to patch to learn the rule.

        A=([x]=4)

        Starts with Lit_Other '[', and then it has Lit_ArrayLhsClose
        Maybe enforce that ALL have keys or NONE of have keys.
        """
        self._SetNext(lex_mode_e.ShCommand)  # advance past (
        self._GetToken()
        if self.cur_token.id != Id.Op_LParen:
            p_die('Expected ( after =', self.cur_token)
        left_token = self.cur_token
        right_token = None  # type: Token

        # MUST use a new word parser (with same lexer).
        w_parser = self.parse_ctx.MakeWordParser(self.lexer, self.line_reader)
        words = []  # type: List[CompoundWord]
        done = False
        while not done:
            w = w_parser.ReadWord(lex_mode_e.ShCommand)
            with tagswitch(w) as case:
                if case(word_e.Operator):
                    tok = cast(Token, w)
                    if tok.id == Id.Right_ShArrayLiteral:
                        right_token = tok
                        done = True  # can't use break here
                    # Unlike command parsing, array parsing allows embedded \n.
                    elif tok.id == Id.Op_Newline:
                        continue
                    else:
                        p_die('Unexpected token in array literal', loc.Word(w))

                elif case(word_e.Compound):
                    words.append(cast(CompoundWord, w))

                else:
                    raise AssertionError()

        if len(words) == 0:  # a=() is empty indexed array
            # Needed for type safety, doh
            no_words = []  # type: List[word_t]
            node = ShArrayLiteral(left_token, no_words, right_token)
            return node

        pairs = []  # type: List[AssocPair]
        # If the first one is a key/value pair, then the rest are assumed to be.
        pair = word_.DetectAssocPair(words[0])
        if pair:
            pairs.append(pair)

            n = len(words)
            for i in xrange(1, n):
                w2 = words[i]
                pair = word_.DetectAssocPair(w2)
                if not pair:
                    p_die("Expected associative array pair", loc.Word(w2))

                pairs.append(pair)

            # invariant List?
            return word_part.BashAssocLiteral(left_token, pairs, right_token)

        # Brace detection for arrays but NOT associative arrays
        words2 = braces.BraceDetectAll(words)
        words3 = word_.TildeDetectAll(words2)
        return ShArrayLiteral(left_token, words3, right_token)

    def _ParseInlineCallArgs(self, arg_list):
        # type: (ArgList) -> None
        """For $f(x) and @arrayfunc(x)."""
        #log('t: %s', self.cur_token)

        # Call into expression language.
        arg_list.left = self.cur_token
        self.parse_ctx.ParseYshArgList(self.lexer, arg_list)

    def ParseProcCallArgs(self):
        # type: () -> ArgList
        """For json write (x)"""
        self.lexer.MaybeUnreadOne()

        arg_list = ArgList.CreateNull(alloc_lists=True)
        arg_list.left = self.cur_token
        self.parse_ctx.ParseYshArgList(self.lexer, arg_list)
        return arg_list

    def _MaybeReadWordPart(self, is_first, lex_mode, parts):
        # type: (bool, lex_mode_t, List[word_part_t]) -> bool
        """Helper for _ReadCompoundWord3."""
        done = False

        if self.token_type == Id.Lit_EscapedChar:
            tok = self.cur_token
            assert tok.length == 2
            ch = lexer.TokenSliceLeft(tok, 1)
            if not self.parse_opts.parse_backslash():
                if not pyutil.IsValidCharEscape(ch):
                    p_die('Invalid char escape (parse_backslash)',
                          self.cur_token)

            part = word_part.EscapedLiteral(self.cur_token,
                                            ch)  # type: word_part_t
        else:
            part = self.cur_token

        if is_first and self.token_type == Id.Lit_VarLike:  # foo=
            parts.append(part)
            # Unfortunately it's awkward to pull the check for a=(1 2) up to
            # _ReadWord.
            next_id = self.lexer.LookPastSpace(lex_mode)
            if next_id == Id.Op_LParen:
                self.lexer.PushHint(Id.Op_RParen, Id.Right_ShArrayLiteral)
                part2 = self._ReadArrayLiteral()
                parts.append(part2)

                # Array literal must be the last part of the word.
                self._SetNext(lex_mode)
                self._GetToken()
                # EOF, whitespace, newline, Right_Subshell
                if self.token_kind not in KINDS_THAT_END_WORDS:
                    p_die('Unexpected token after array literal',
                          self.cur_token)
                done = True

        elif (is_first and self.parse_opts.parse_at() and
              self.token_type == Id.Lit_Splice):

            splice_tok = self.cur_token
            part2 = word_part.Splice(splice_tok,
                                     lexer.TokenSliceLeft(splice_tok, 1))

            parts.append(part2)

            # @words must be the last part of the word
            self._SetNext(lex_mode)
            self._GetToken()
            # EOF, whitespace, newline, Right_Subshell
            if self.token_kind not in KINDS_THAT_END_WORDS:
                p_die('Unexpected token after array splice', self.cur_token)
            done = True

        elif (is_first and self.parse_opts.parse_at() and
              self.token_type == Id.Lit_AtLBracket):  # @[split(x)]
            part2 = self._ReadExprSub(lex_mode_e.DQ)
            parts.append(part2)

            # @[split(x)]
            self._SetNext(lex_mode)
            self._GetToken()
            # EOF, whitespace, newline, Right_Subshell
            if self.token_kind not in KINDS_THAT_END_WORDS:
                p_die('Unexpected token after expr splice', self.cur_token)
            done = True

        elif (is_first and self.parse_opts.parse_at() and
              self.token_type == Id.Lit_AtLBraceDot):
            p_die('TODO: @{.myproc builtin sub}', self.cur_token)

        elif (is_first and self.parse_opts.parse_at_all() and
              self.token_type == Id.Lit_At):
            # Because $[x] ${x} and perhaps $/x/ are reserved, it makes sense for @
            # at the beginning of a word to be reserved.

            # Although should we relax 'echo @' ?  I'm tempted to have a shortcut for
            # @_argv and
            p_die('Literal @ starting a word must be quoted (parse_at_all)',
                  self.cur_token)

        else:
            # not a literal with lookahead; append it
            parts.append(part)

        return done

    def _ReadCompoundWord(self, lex_mode):
        # type: (lex_mode_t) -> CompoundWord
        return self._ReadCompoundWord3(lex_mode, Id.Undefined_Tok, True)

    def _ReadCompoundWord3(self, lex_mode, eof_type, empty_ok):
        # type: (lex_mode_t, Id_t, bool) -> CompoundWord
        """
        Precondition: Looking at the first token of the first word part
        Postcondition: Looking at the token after, e.g. space or operator

        NOTE: eof_type is necessary because / is a literal, i.e. Lit_Slash, but it
        could be an operator delimiting a compound word.  Can we change lexer modes
        and remove this special case?
        """
        w = CompoundWord([])
        num_parts = 0
        brace_count = 0
        done = False
        is_triple_quoted = None  # type: Optional[BoolParamBox]

        while not done:
            self._GetToken()

            allow_done = empty_ok or num_parts != 0
            if allow_done and self.token_type == eof_type:
                done = True  # e.g. for ${foo//pat/replace}

            # Keywords like "for" are treated like literals
            elif self.token_kind in (Kind.Lit, Kind.History, Kind.KW,
                                     Kind.ControlFlow, Kind.BoolUnary,
                                     Kind.BoolBinary):

                # Syntax error for { and }
                if self.token_type == Id.Lit_LBrace:
                    brace_count += 1
                elif self.token_type == Id.Lit_RBrace:
                    brace_count -= 1
                elif self.token_type == Id.Lit_Dollar:
                    if not self.parse_opts.parse_dollar():
                        if num_parts == 0 and lex_mode == lex_mode_e.ShCommand:
                            next_byte = self.lexer.ByteLookAhead()
                            # TODO: switch lexer modes and parse $/d+/.  But not ${a:-$/d+/}
                            if next_byte == '/':
                                log('next_byte %r', next_byte)

                        p_die('Literal $ should be quoted like \$',
                              self.cur_token)

                done = self._MaybeReadWordPart(num_parts == 0, lex_mode,
                                               w.parts)

            elif self.token_kind == Kind.VSub:
                vsub_token = self.cur_token

                part = SimpleVarSub(vsub_token,
                                    lexer.TokenSliceLeft(
                                        vsub_token, 1))  # type: word_part_t
                w.parts.append(part)

            elif self.token_kind == Kind.ExtGlob:
                # If parse_at, we can take over @( to start @(seq 3)
                # Users can also use look at ,(*.py|*.sh)
                if (self.parse_opts.parse_at() and
                    self.token_type == Id.ExtGlob_At and num_parts == 0):
                    cs_part = self._ReadCommandSub(Id.Left_AtParen,
                                                   d_quoted=False)
                    # RARE mutation of tok.id!
                    cs_part.left_token.id = Id.Left_AtParen
                    part = cs_part  # for type safety

                    # Same check as _MaybeReadWordPart.  @(seq 3)x is illegal, just like
                    # a=(one two)x and @arrayfunc(3)x.
                    self._GetToken()
                    if self.token_kind not in KINDS_THAT_END_WORDS:
                        p_die('Unexpected token after @()', self.cur_token)
                    done = True

                else:
                    part = self._ReadExtGlob()
                w.parts.append(part)

            elif self.token_kind == Kind.Left:
                try_triple_quote = (self.parse_opts.parse_triple_quote() and
                                    lex_mode == lex_mode_e.ShCommand and
                                    num_parts == 0)

                # Save allocation
                if try_triple_quote:
                    is_triple_quoted = BoolParamBox(False)

                part = self._ReadUnquotedLeftParts(is_triple_quoted)
                w.parts.append(part)

            # NOT done yet, will advance below
            elif self.token_kind == Kind.Right:
                # Still part of the word; will be done on the next iter.
                if self.token_type == Id.Right_DoubleQuote:
                    pass
                # Never happens, no PushHint for this case.
                #elif self.token_type == Id.Right_DollarParen:
                #  pass
                elif self.token_type == Id.Right_Subshell:
                    # LEXER HACK for (case x in x) ;; esac )
                    # Rewind before it's used
                    assert self.next_lex_mode == lex_mode_e.Undefined
                    if self.lexer.MaybeUnreadOne():
                        self.lexer.PushHint(Id.Op_RParen, Id.Right_Subshell)
                        self._SetNext(lex_mode)
                    done = True
                else:
                    done = True

            elif self.token_kind == Kind.Ignored:
                done = True

            else:
                # LEXER HACK for unbalanced case clause.  'case foo in esac' is valid,
                # so to test for ESAC, we can read ) before getting a chance to
                # PushHint(Id.Op_RParen, Id.Right_CasePat).  So here we unread one
                # token and do it again.

                # We get Id.Op_RParen at top level:      case x in x) ;; esac
                # We get Id.Eof_RParen inside ComSub:  $(case x in x) ;; esac )
                if self.token_type in (Id.Op_RParen, Id.Eof_RParen):
                    # Rewind before it's used
                    assert self.next_lex_mode == lex_mode_e.Undefined
                    if self.lexer.MaybeUnreadOne():
                        if self.token_type == Id.Eof_RParen:
                            # Redo translation
                            self.lexer.PushHint(Id.Op_RParen, Id.Eof_RParen)
                        self._SetNext(lex_mode)

                done = True  # anything we don't recognize means we're done

            if not done:
                self._SetNext(lex_mode)
                num_parts += 1

        if self.parse_opts.parse_brace() and num_parts > 1 and brace_count != 0:
            # accept { and }, but not foo{
            p_die(
                'Word has unbalanced { }.  Maybe add a space or quote it like \{',
                loc.Word(w))

        if is_triple_quoted and is_triple_quoted.b and num_parts > 1:
            p_die('Unexpected parts after triple quoted string',
                  loc.WordPart(w.parts[-1]))

        return w

    def _ReadArithWord(self):
        # type: () -> Tuple[Optional[word_t], bool]
        """Helper function for ReadWord."""
        self._GetToken()

        if self.token_kind == Kind.Unknown:
            # e.g. happened during dynamic parsing of unset 'a[$foo]' in gherkin
            p_die(
                'Unexpected token while parsing arithmetic: %r' %
                lexer.TokenVal(self.cur_token), self.cur_token)

        elif self.token_kind == Kind.Eof:
            # Just return EOF token
            return cast(word_t, self.cur_token), False

        elif self.token_kind == Kind.Ignored:
            # Space should be ignored.
            self._SetNext(lex_mode_e.Arith)
            no_word = None  # type: Optional[word_t]
            return no_word, True  # Tell wrapper to try again

        elif self.token_kind in (Kind.Arith, Kind.Right):
            # Id.Right_DollarDParen IS just a normal token, handled by ArithParser
            self._SetNext(lex_mode_e.Arith)
            return cast(word_t, self.cur_token), False

        elif self.token_kind in (Kind.Lit, Kind.Left, Kind.VSub):
            w = self._ReadCompoundWord(lex_mode_e.Arith)
            return cast(word_t, w), False

        else:
            raise AssertionError(self.cur_token)

    def _ReadWord(self, lex_mode):
        # type: (lex_mode_t) -> Tuple[Optional[word_t], bool]
        """Helper function for ReadWord().

        Returns:
          2-tuple (word, need_more)
            word: Word, or None if there was an error, or need_more is set
            need_more: True if the caller should call us again
        """
        no_word = None  # type: Optional[word_t]

        self._GetToken()

        if self.token_kind == Kind.Eof:
            # No advance
            return cast(word_t, self.cur_token), False

        # Allow Arith for ) at end of for loop?
        elif self.token_kind in (Kind.Op, Kind.Redir, Kind.Arith):
            self._SetNext(lex_mode)

            # Newlines are complicated.  See 3x2 matrix in the comment about
            # self.multiline and self.newline_state above.
            if self.token_type == Id.Op_Newline:
                if self.multiline:
                    if self.newline_state > 1:
                        # This points at a blank line, but at least it gives the line number
                        p_die('Invalid blank line in multiline mode',
                              self.cur_token)
                    return no_word, True

                if self.returned_newline:  # skip
                    return no_word, True

            return cast(word_t, self.cur_token), False

        elif self.token_kind == Kind.Right:
            if self.token_type not in (Id.Right_Subshell, Id.Right_ShFunction,
                                       Id.Right_CasePat,
                                       Id.Right_ShArrayLiteral):
                raise AssertionError(self.cur_token)

            self._SetNext(lex_mode)
            return cast(word_t, self.cur_token), False

        elif self.token_kind in (Kind.Ignored, Kind.WS):
            self._SetNext(lex_mode)
            return no_word, True  # tell ReadWord() to try again

        elif self.token_kind in (Kind.VSub, Kind.Lit, Kind.History, Kind.Left,
                                 Kind.KW, Kind.ControlFlow, Kind.BoolUnary,
                                 Kind.BoolBinary, Kind.ExtGlob):
            # We're beginning a word.  If we see Id.Lit_Pound, change to
            # lex_mode_e.Comment and read until end of line.
            if self.token_type == Id.Lit_Pound:
                self._SetNext(lex_mode_e.Comment)
                self._GetToken()

                # NOTE: The # could be the last character in the file.  It can't be
                # Eof_{RParen,Backtick} because #) and #` are comments.
                assert self.token_type in (Id.Ignored_Comment, Id.Eof_Real), \
                    self.cur_token

                # The next iteration will go into Kind.Ignored and set lex state to
                # lex_mode_e.ShCommand/etc.
                return no_word, True  # tell ReadWord() to try again after comment

            elif self.token_type == Id.Lit_TPound:  ### doc comment
                self._SetNext(lex_mode_e.Comment)
                self._GetToken()

                if self.token_type == Id.Ignored_Comment and self.emit_doc_token:
                    return cast(word_t, self.cur_token), False

                return no_word, True  # tell ReadWord() to try again after comment

            else:
                # parse_raw_string: Is there an r'' at the beginning of a word?
                if (self.parse_opts.parse_raw_string() and
                    self.token_type == Id.Lit_Chars and
                    self.cur_token.tval == 'r'):
                    if (self.lexer.LookAheadOne(lex_mode_e.ShCommand) == 
                        Id.Left_SingleQuote):
                        self._SetNext(lex_mode_e.ShCommand)

                w = self._ReadCompoundWord(lex_mode)
                return cast(word_t, w), False

        else:
            raise AssertionError('Unhandled: %s (%s)' %
                                 (self.cur_token, self.token_kind))

    def ParseVarRef(self):
        # type: () -> BracedVarSub
        """DYNAMIC parsing of what's inside ${!ref}

        # Same as VarOf production
        VarRefExpr = VarOf EOF
        """
        self._SetNext(lex_mode_e.VSub_1)

        self._GetToken()
        if self.token_kind != Kind.VSub:
            p_die('Expected var name', self.cur_token)

        part = self._ParseVarOf()
        # NOTE: no ${ } means no part.left and part.right
        part.left = part.token  # cheat to make test pass
        part.right = part.token

        self._GetToken()
        if self.token_type != Id.Eof_Real:
            p_die('Expected end of var ref expression', self.cur_token)
        return part

    def LookPastSpace(self):
        # type: () -> Id_t
        """Look ahead to the next token.

        For the CommandParser to recognize
           array= (1 2 3)
           YSH for (  versus  bash for ((
           YSH if (  versus  if test
           YSH while (  versus  while test
           YSH bare assignment 'grep ='  versus 'grep foo'
        """
        assert self.token_type != Id.Undefined_Tok
        if self.cur_token.id == Id.WS_Space:
            id_ = self.lexer.LookPastSpace(lex_mode_e.ShCommand)
        else:
            id_ = self.cur_token.id
        return id_

    def LookAheadFuncParens(self):
        # type: () -> bool
        """Special lookahead for f( ) { echo hi; } to check for ( )"""
        assert self.token_type != Id.Undefined_Tok

        # We have to handle 2 cases because we buffer a token
        if self.cur_token.id == Id.Op_LParen:  # saw funcname(
            return self.lexer.LookAheadFuncParens(1)  # go back one char

        elif self.cur_token.id == Id.WS_Space:  # saw funcname WHITESPACE
            return self.lexer.LookAheadFuncParens(0)

        else:
            return False

    def ReadWord(self, lex_mode):
        # type: (lex_mode_t) -> word_t
        """Read the next Word.

        Returns:
          Word, or None if there was an error
        """
        # For integration with pgen2
        if self.buffered_word:
            w = self.buffered_word
            self.buffered_word = None
        else:
            # Implementation note: This is an stateful/iterative function that calls
            # the stateless "_ReadWord" function.
            while True:
                if lex_mode == lex_mode_e.Arith:
                    # TODO: Can this be unified?
                    w, need_more = self._ReadArithWord()
                elif lex_mode in (lex_mode_e.ShCommand, lex_mode_e.DBracket,
                                  lex_mode_e.BashRegex):
                    w, need_more = self._ReadWord(lex_mode)
                else:
                    raise AssertionError('Invalid lex state %s' % lex_mode)
                if not need_more:
                    break

        self.returned_newline = (word_.CommandId(w) == Id.Op_Newline)
        return w

    def ReadHereDocBody(self, parts):
        # type: (List[word_part_t]) -> None
        """A here doc is like a double quoted context, except " isn't
        special."""
        self._ReadLikeDQ(None, False, parts)
        # Returns nothing

    def ReadForPlugin(self):
        # type: () -> CompoundWord
        """For $PS1, $PS4, etc.

        This is just like reading a here doc line.  "\n" is allowed, as
        well as the typical substitutions ${x} $(echo hi) $((1 + 2)).
        """
        w = CompoundWord([])
        self._ReadLikeDQ(None, False, w.parts)
        return w

    def EmitDocToken(self, b):
        # type: (bool) -> None
        self.emit_doc_token = b

    def Multiline(self, b):
        # type: (bool) -> None
        self.multiline = b
