#!/usr/bin/env python2
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
from data_lang import j8
from frontend import consts
from frontend import lexer
from mycpp.mylib import log, switch

from typing import List, Optional, cast


def EvalCharLiteralForRegex(tok):
    # type: (Token) -> CharCode
    """For regex char classes.

    Similar logic as below.
    """
    id_ = tok.id
    value = tok.tval

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
    """This function is shared between echo -e and $''.

    $'' could use it at compile time, much like brace expansion in braces.py.
    """
    if id_ in (Id.Char_Literals, Id.Unknown_Backslash, Id.Char_AsciiControl):
        # shopt -u parse_backslash detects Unknown_Backslash at PARSE time in YSH.

        # Char_AsciiControl is allowed in YSH code, for newlines in u''
        # strings, just like r'' has
        # TODO: could allow ONLY newline?
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
        if id_ == Id.Char_Octal3:  # $'\377' (disallowed at parse time in YSH)
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

    elif id_ in (Id.Char_Unicode4, Id.Char_Unicode8):
        s = value[2:]
        i = int(s, 16)
        #util.log('i = %d', i)
        return j8.Utf8Encode(i)

    elif id_ == Id.Char_UBraced:
        s = value[3:-1]  # \u{123}
        i = int(s, 16)
        return j8.Utf8Encode(i)

    else:
        raise AssertionError(Id_str(id_))


def EvalSingleQuoted2(id_, tokens):
    # type: (Id_t, List[Token]) -> str
    """ Done at parse time """
    if id_ in (Id.Left_SingleQuote, Id.Left_RSingleQuote, Id.Left_TSingleQuote,
               Id.Left_RTSingleQuote):
        tmp = [t.tval for t in tokens]
        s = ''.join(tmp)

    elif id_ in (Id.Left_DollarSingleQuote, Id.Left_USingleQuote,
                 Id.Left_BSingleQuote, Id.Left_UTSingleQuote,
                 Id.Left_BTSingleQuote):
        #tmp = [EvalCStringToken(t.id, lexer.TokenVal(t)) for t in tokens]
        tmp = [EvalCStringToken(t.id, t.tval) for t in tokens]
        s = ''.join(tmp)

    else:
        raise AssertionError(id_)
    return s


def IsLeadingSpace(s):
    # type: (str) -> bool
    """Determines if the token before ''' etc. can be stripped.

    Similar to IsWhitespace()
    """
    for ch in s:
        if ch not in ' \t':
            return False
    return True


def IsWhitespace(s):
    # type: (str) -> bool
    """Alternative to s.isspace() that doesn't have legacy \f \v codes.
    """
    for ch in s:
        if ch not in ' \n\r\t':
            return False
    return True


# Whitespace stripping algorithm
#
# - First token should be WHITESPACE* NEWLINE.  Omit it
# - Last token should be WHITESPACE*
#   - Then go through all the other tokens that are AFTER token that ends with \n
#   - if tok.tval[:n] is the same as the last token, then STRIP THAT PREFIX
# - Do you need to set a flag on the SingleQuoted part?
#
# TODO: do this all at compile time?

# These functions may mutate tok.tval.  TODO: mutate the parts instead, after
# we remove .tval


def RemoveLeadingSpaceDQ(parts):
    # type: (List[word_part_t]) -> None
    if len(parts) <= 1:  # We need at least 2 parts to strip anything
        return

    line_ended = False  # Think of it as a tiny state machine

    # The first token may have a newline
    UP_first = parts[0]
    if UP_first.tag() == word_part_e.Literal:
        first = cast(Token, UP_first)
        #log('T %s', first_part)
        if IsWhitespace(first.tval):
            # Remove the first part.  TODO: This could be expensive if there are many
            # lines.
            parts.pop(0)
        if first.tval.endswith('\n'):
            line_ended = True

    UP_last = parts[-1]
    to_strip = None  # type: Optional[str]
    if UP_last.tag() == word_part_e.Literal:
        last = cast(Token, UP_last)
        if IsLeadingSpace(last.tval):
            to_strip = last.tval
            parts.pop()  # Remove the last part

    if to_strip is not None:
        n = len(to_strip)
        for UP_p in parts:
            if UP_p.tag() != word_part_e.Literal:
                line_ended = False
                continue

            p = cast(Token, UP_p)

            if line_ended:
                if lexer.TokenStartsWith(p, to_strip):
                    # MUTATING the part here
                    p.tval = p.tval[n:]

            line_ended = False
            if p.tval.endswith('\n'):
                line_ended = True
                #log('%s', p)


def RemoveLeadingSpaceSQ(tokens):
    # type: (List[Token]) -> None
    """
    In $''', we have Char_Literals \n
    In r''' and ''', we have Lit_Chars \n
    In u''' and b''', we have Char_AsciiControl \n

    Should make these more consistent.
    """
    if 0:
        log('--')
        for tok in tokens:
            log('tok %s', tok)
        log('--')

    if len(tokens) <= 1:  # We need at least 2 parts to strip anything
        return

    line_ended = False

    first = tokens[0]
    if first.id in (Id.Lit_Chars, Id.Char_Literals, Id.Char_AsciiControl):
        if IsWhitespace(first.tval):
            tokens.pop(0)  # Remove the first part
        if first.tval.endswith('\n'):
            line_ended = True

    last = tokens[-1]
    to_strip = None  # type: Optional[str]
    if last.id in (Id.Lit_Chars, Id.Char_Literals, Id.Char_AsciiControl):
        if IsLeadingSpace(last.tval):
            to_strip = last.tval
            tokens.pop()  # Remove the last part

    if to_strip is not None:
        #log('SQ Stripping %r', to_strip)
        n = len(to_strip)
        for tok in tokens:
            if tok.id not in (Id.Lit_Chars, Id.Char_Literals,
                              Id.Char_AsciiControl):
                line_ended = False
                continue

            if line_ended:
                if lexer.TokenStartsWith(tok, to_strip):
                    # MUTATING the token here
                    tok.tval = tok.tval[n:]

            line_ended = False
            if tok.tval.endswith('\n'):
                line_ended = True
