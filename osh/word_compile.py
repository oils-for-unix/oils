#!/usr/bin/env python2
from __future__ import print_function
"""osh/word_compile.py.

These functions are called after parsing, but don't depend on any runtime
values.
"""

from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str
from _devbuild.gen.syntax_asdl import (
    Token,
    CharCode,
    word_part_e,
    word_part_t,
)
from core.error import p_die
from data_lang import j8
from frontend import consts
from frontend import lexer
from mycpp import mylib
from mycpp.mylib import log, switch

from typing import List, Optional, cast


def EvalCharLiteralForRegex(tok):
    # type: (Token) -> CharCode
    """For regex char classes.

    Similar logic as below.
    """
    id_ = tok.id
    value = lexer.TokenVal(tok)

    with switch(id_) as case:
        if case(Id.Char_UBraced):
            s = lexer.TokenSlice(tok, 3, -1)  # \u{123}
            i = int(s, 16)
            return CharCode(tok, i, True)  # u_braced

        elif case(Id.Char_OneChar):  # \'
            # value[1] -> mylib.ByteAt()
            one_char_str = consts.LookupCharC(value[1])
            return CharCode(tok, ord(one_char_str), False)

        elif case(Id.Char_Hex):
            s = lexer.TokenSliceLeft(tok, 2)
            i = int(s, 16)
            return CharCode(tok, i, False)

        elif case(Id.Lit_Chars, Id.Expr_Name, Id.Expr_DecInt):
            # Id.Lit_Chars: Token in single quoted string ['a'] is Id.Lit_Chars
            # Id.Expr_Name: [a-z] is ['a'-'Z'], and [a z] is ['a' 'Z']
            # Id.Expr_DecInt: [0-9] is ['0'-'9'], and [0 9] is ['0' '9']

            assert len(value) == 1, tok
            # value[0] -> mylib.ByteAt()
            return CharCode(tok, ord(value[0]), False)

        else:
            raise AssertionError(tok)


def EvalCStringToken(id_, value):
    # type: (Id_t, str) -> Optional[str]
    """All types of C-style backslash-escaped strings use this function:
    
    - echo -e and printf at runtime
    - $'' and b'' u'' at parse time
    """
    code_point = -1

    if id_ in (Id.Lit_Chars, Id.Lit_CharsWithoutPrefix, Id.Unknown_Backslash):
        # shopt -u parse_backslash detects Unknown_Backslash at PARSE time in YSH.
        return value

    # single quotes in the middle of a triple quoted string
    elif id_ == Id.Right_SingleQuote:
        return value

    elif id_ == Id.Char_OneChar:
        c = value[1]
        return consts.LookupCharC(c)

    elif id_ == Id.Char_Stop:  # \c returns a special sentinel
        return None

    elif id_ in (Id.Char_Octal3, Id.Char_Octal4):
        if id_ == Id.Char_Octal3:  # $'\377'
            s = value[1:]
        else:  # echo -e '\0377'
            s = value[2:]

        i = int(s, 8)
        if i >= 256:
            i = i % 256
            # NOTE: This is for strict mode
            #raise AssertionError('Out of range')
        return chr(i)

    elif id_ in (Id.Char_Hex, Id.Char_YHex):
        s = value[2:]
        i = int(s, 16)
        return chr(i)

    # Note: we're not doing the surrogate range and max code point checks for
    # echo -e and printf:
    #
    # 1. It's not compatible with bash
    # 2. We don't have good error locations anyway

    elif id_ in (Id.Char_Unicode4, Id.Char_Unicode8):
        s = value[2:]
        code_point = int(s, 16)
        return j8.Utf8Encode(code_point)

    elif id_ == Id.Char_UBraced:
        s = value[3:-1]  # \u{123}
        code_point = int(s, 16)
        return j8.Utf8Encode(code_point)

    else:
        raise AssertionError(Id_str(id_))


def EvalSingleQuoted(id_, tokens):
    # type: (Id_t, List[Token]) -> str
    """ Done at parse time """
    if id_ in (Id.Left_SingleQuote, Id.Left_RSingleQuote, Id.Left_TSingleQuote,
               Id.Left_RTSingleQuote):
        strs = [lexer.TokenVal(t) for t in tokens]

    elif id_ in (Id.Left_DollarSingleQuote, Id.Left_USingleQuote,
                 Id.Left_BSingleQuote, Id.Left_UTSingleQuote,
                 Id.Left_BTSingleQuote):
        if 0:
            for t in tokens:
                print('T %s' % t)

        strs = []
        for t in tokens:
            # More parse time validation for code points.
            # EvalCStringToken() redoes some of this work, but right now it's
            # shared with dynamic echo -e / printf, which don't have tokens.

            # Only check J8 style strings, not Char_Unicode4 and Char_Unicode8,
            # which are in OSH
            if t.id == Id.Char_UBraced:
                s = lexer.TokenSlice(t, 3, -1)
                code_point = int(s, 16)
                if code_point > 0x10ffff:
                    p_die("Code point can't be greater than U+10ffff", t)
                if 0xD800 <= code_point and code_point < 0xE000:
                    p_die(
                        r"%s escape is illegal because it's in the surrogate range"
                        % lexer.TokenVal(t), t)

            strs.append(EvalCStringToken(t.id, lexer.TokenVal(t)))

    else:
        raise AssertionError(id_)
    return ''.join(strs)


def _TokenConsistsOf(tok, byte_set):
    # type: (Token, str) -> bool
    start = tok.col
    end = tok.col + tok.length
    for i in xrange(start, end):
        b = mylib.ByteAt(tok.line.content, i)
        if not mylib.ByteInSet(b, byte_set):
            return False
    return True


def _IsLeadingSpace(tok):
    # type: (Token) -> bool
    """ Determine if the token before ''' etc. is space to trim """
    return _TokenConsistsOf(tok, ' \t')


def _IsTrailingSpace(tok):
    # type: (Token) -> bool
    """ Determine if the space/newlines after ''' should be trimmed

    Like s.isspace(), without legacy \f \v and Unicode.
    """
    return _TokenConsistsOf(tok, ' \n\r\t')


# Whitespace trimming algorithms:
#
# 1. Trim what's after opening ''' or """, if it's whitespace
# 2. Determine what's before closing ''' or """ -- this is what you strip
# 3. Strip each line by mutating the token
#    - Change the ID from Id.Lit_Chars -> Id.Lit_CharsWithoutPrefix to maintain
#      the lossless invariant


def RemoveLeadingSpaceDQ(parts):
    # type: (List[word_part_t]) -> None
    if len(parts) <= 1:  # We need at least 2 parts to strip anything
        return

    # The first token may have a newline
    UP_first = parts[0]
    if UP_first.tag() == word_part_e.Literal:
        first = cast(Token, UP_first)
        #log('T %s', first_part)
        if _IsTrailingSpace(first):
            # Remove the first part.  TODO: This could be expensive if there are many
            # lines.
            parts.pop(0)

    UP_last = parts[-1]
    to_strip = None  # type: Optional[str]
    if UP_last.tag() == word_part_e.Literal:
        last = cast(Token, UP_last)
        if _IsLeadingSpace(last):
            to_strip = lexer.TokenVal(last)
            parts.pop()  # Remove the last part

    if to_strip is None:
        return

    n = len(to_strip)
    for part in parts:
        if part.tag() != word_part_e.Literal:
            continue

        lit_tok = cast(Token, part)

        if lit_tok.col == 0 and lexer.TokenStartsWith(lit_tok, to_strip):
            # TODO: Lexer should not populate this!
            assert lit_tok.tval is None, lit_tok.tval

            lit_tok.col = n
            lit_tok.length -= n
            #log('n = %d, %s', n, lit_tok)

            assert lit_tok.id == Id.Lit_Chars, lit_tok
            # --tool lossless-cat has a special case for this
            lit_tok.id = Id.Lit_CharsWithoutPrefix


def RemoveLeadingSpaceSQ(tokens):
    # type: (List[Token]) -> None
    """Strip leading whitespace from tokens.

    May return original list unmodified, or a new list.

    Must respect lossless invariant - see test/lossless/multiline-str.sh

    For now we create NEW Id.Ignored_LeadingSpace tokens, and are NOT in the
    arena.
    """
    if 0:
        log('--')
        for tok in tokens:
            #log('tok %s', tok)
            import sys
            from asdl import format as fmt
            ast_f = fmt.DetectConsoleOutput(mylib.Stderr())
            tree = tok.AbbreviatedTree()
            fmt.PrintTree(tree, ast_f)
            print('', file=sys.stderr)
        log('--')

    if len(tokens) <= 1:  # We need at least 2 parts to strip anything
        return

    # var x = '''    # strip initial newline/whitespace
    #   x
    #   '''
    first = tokens[0]
    if first.id == Id.Lit_Chars:
        if _IsTrailingSpace(first):
            tokens.pop(0)  # Remove the first part

    # Figure out what to strip, based on last token
    last = tokens[-1]
    to_strip = None  # type: Optional[str]
    if last.id == Id.Lit_Chars:
        if _IsLeadingSpace(last):
            to_strip = lexer.TokenVal(last)
            tokens.pop()  # Remove the last part

    if to_strip is None:
        return

    #log('SQ Stripping %r', to_strip)
    n = len(to_strip)

    #log('--')
    for tok in tokens:
        #log('tok %s', tok)
        # Strip leading space on tokens that begin lines, by bumping start col
        if tok.col == 0 and lexer.TokenStartsWith(tok, to_strip):
            tok.col = n
            tok.length -= n

            assert tok.id == Id.Lit_Chars, tok
            # --tool lossless-cat has a special case for this
            tok.id = Id.Lit_CharsWithoutPrefix

            #log('STRIP tok %s', tok)


# vim: sw=4
