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
from mycpp import mylib
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
        # TODO: RemoveLeadingSpaceSQ must not modify tval
        #tmp = [EvalCStringToken(t.id, lexer.TokenVal(t)) for t in tokens]
        tmp = [EvalCStringToken(t.id, t.tval) for t in tokens]
        s = ''.join(tmp)

    else:
        raise AssertionError(id_)
    return s


def TokenConsistsOf(tok, byte_set):
    # type: (Token, str) -> bool
    start = tok.col
    end = tok.col + tok.length
    for i in xrange(start, end):
        b = mylib.ByteAt(tok.line.content, i)
        if not mylib.ByteInSet(b, byte_set):
            return False
    return True


def IsLeadingSpace(tok):
    # type: (Token) -> bool
    """Determines if the token before ''' etc. can be stripped.

    Similar to IsWhitespace()
    """
    return TokenConsistsOf(tok, ' \t')


def IsWhitespace(tok):
    # type: (Token) -> bool
    """Like s.isspace(), without legacy \f \v and nicode."""
    return TokenConsistsOf(tok, ' \n\r\t')


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
        if IsWhitespace(first):
            # Remove the first part.  TODO: This could be expensive if there are many
            # lines.
            parts.pop(0)
        if lexer.TokenEndsWith(first, '\n'):
            line_ended = True

    UP_last = parts[-1]
    to_strip = None  # type: Optional[str]
    if UP_last.tag() == word_part_e.Literal:
        last = cast(Token, UP_last)
        if IsLeadingSpace(last):
            to_strip = last.tval
            parts.pop()  # Remove the last part

    if to_strip is not None:
        n = len(to_strip)
        for part in parts:
            if part.tag() != word_part_e.Literal:
                line_ended = False
                continue

            lit_tok = cast(Token, part)

            if line_ended:
                if lexer.TokenStartsWith(lit_tok, to_strip):
                    # MUTATING the part here
                    lit_tok.tval = lit_tok.tval[n:]

            line_ended = False
            if lexer.TokenEndsWith(lit_tok, '\n'):
                line_ended = True
                #log('%s', p)


def RemoveLeadingSpaceSQ(tokens):
    # type: (List[Token]) -> List[Token]
    """Strip leading whitespace from tokens.

    May return original list unmodified, or a new list.

    Must respect lossless invariant - see test/lossless/multiline-str.sh

    TODO: We need to INSERT Id.Ignored_LeadingSpace tokens.  That means
    creating new tokens probably.

    Quirk to make more consistent:
      In $''', we have Char_Literals \n
      In r''' and ''', we have Lit_Chars \n
      In u''' and b''', we have Char_AsciiControl \n
    """
    if 0:
        log('--')
        for tok in tokens:
            log('tok %s', tok)
        log('--')

    if len(tokens) <= 1:  # We need at least 2 parts to strip anything
        return tokens

    line_ended = False

    # var x = '''    # strip initial newline/whitespace
    #   x
    #   '''
    first = tokens[0]
    if first.id in (Id.Lit_Chars, Id.Char_Literals, Id.Char_AsciiControl):
        if IsWhitespace(first):
            tokens.pop(0)  # Remove the first part
        if lexer.TokenEndsWith(first, '\n'):
            line_ended = True

    # Figure out what to strip, based on last token
    last = tokens[-1]
    to_strip = None  # type: Optional[str]
    if last.id in (Id.Lit_Chars, Id.Char_Literals, Id.Char_AsciiControl):
        if IsLeadingSpace(last):
            to_strip = last.tval
            tokens.pop()  # Remove the last part

    if to_strip is None:
        return tokens  # Return original unmodified

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
        if lexer.TokenEndsWith(tok, '\n'):
            line_ended = True

    # TODO: return new tokens
    return tokens

