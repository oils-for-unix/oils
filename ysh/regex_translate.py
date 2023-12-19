#!/usr/bin/env python2
"""regex_translate.py."""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    PosixClass,
    PerlClass,
    CharCode,
    char_class_term,
    char_class_term_e,
    char_class_term_t,
    re,
    re_e,
    re_repeat,
    re_repeat_e,
    EggexFlag,
)
from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.value_asdl import value
from core.error import e_die, p_die
from frontend import lexer
from mycpp.mylib import log, tagswitch
from osh import glob_  # for ExtendedRegexEscape

from typing import List, Optional, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import re_t

from libc import REG_ICASE, REG_NEWLINE

_ = log

PERL_CLASS = {
    'd': '[:digit:]',
    # Python's docs say it's [a-zA-Z0-9_] when NO LOCALE is set.
    'w': '[:alpha:][:digit:]_',
    # Python's doc says \s is [ \t\n\r\f\v] when NO LCOALE
    's': '[:space:]',
}

# ERE's in POSIX:
# https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html
#
# NOTE: They don't support \x00 or \u1234 as in Perl/Python!
#
# It's hard to grep for tabs with BRE or ERE syntax.  You have to use:
#
# (1) a literal tab with Ctrl-V, or
# (2) bash syntax:  grep $'\t' foo.txt
# (3) POSIX shell syntax:  grep "$(echo -e '\t')" foo.txt.
#
# I ran into this in test/lint.sh !!!
#
# https://stackoverflow.com/questions/1825552/grep-a-tab-in-unix

# Algorithm:
# - Unicode escapes in BREs disallowed
# - ASCII codes 1-255 allowed LITERALLY, but NUL \0 disallowed
#
# What about utf-8 encoded characters?  Those work within literals, but are
# problematic within character sets.  There's no way to disallow those in
# general though.

CH_RBRACKET = 0x5d
CH_BACKSLASH = 0x5c
CH_CARET = 0x5e
CH_HYPHEN = 0x2d

FLAG_RBRACKET = 0b0001
FLAG_BACKSLASH = 0b0010
FLAG_CARET = 0b0100
FLAG_HYPHEN = 0b1000


def _CharCodeToEre(term, parts, special_char_flags):
    # type: (CharCode, List[str], List[int]) -> None
    """special_char_flags: list of single int that is mutated."""

    char_int = term.i
    if char_int >= 128 and term.u_braced:
        # \u{ff} can't be represented in ERE because we don't know the encoding
        # \xff can be represented
        e_die("ERE can't express char code %d" % char_int, term.blame_tok)

    # note: mycpp doesn't handle
    # special_char_flags[0] |= FLAG_HYPHEN
    mask = special_char_flags[0]

    if char_int == CH_HYPHEN:
        mask |= FLAG_HYPHEN
    elif char_int == CH_CARET:
        mask |= FLAG_CARET
    elif char_int == CH_RBRACKET:
        mask |= FLAG_RBRACKET
    elif char_int == CH_BACKSLASH:
        mask |= FLAG_BACKSLASH
    else:
        parts.append(chr(char_int))

    special_char_flags[0] = mask


def _CharClassTermToEre(term, parts, special_char_flags):
    # type: (char_class_term_t, List[str], List[int]) -> None
    """special_char_flags: list of single int that is mutated."""

    UP_term = term
    with tagswitch(term) as case:
        if case(char_class_term_e.Range):
            term = cast(char_class_term.Range, UP_term)

            # Create our own flags
            range_no_special = [0]

            _CharCodeToEre(term.start, parts, range_no_special)
            if range_no_special[0] != 0:
                e_die(
                    "Can't use char %d as start of range in ERE syntax" %
                    term.start.i, term.start.blame_tok)

            parts.append('-')  # a-b

            _CharCodeToEre(term.end, parts, range_no_special)
            if range_no_special[0] != 0:
                e_die(
                    "Can't use char %d as end of range in ERE syntax" %
                    term.end.i, term.end.blame_tok)

        elif case(char_class_term_e.CharCode):
            term = cast(CharCode, UP_term)

            _CharCodeToEre(term, parts, special_char_flags)

        elif case(char_class_term_e.PerlClass):
            term = cast(PerlClass, UP_term)
            n = term.name
            chars = PERL_CLASS[term.name]  # looks like '[:digit:]'
            if term.negated:
                e_die("Perl classes can't be negated in ERE", term.negated)
            else:
                pat = '%s' % chars
            parts.append(pat)

        elif case(char_class_term_e.PosixClass):
            term = cast(PosixClass, UP_term)
            n = term.name  # looks like 'digit'
            if term.negated:
                e_die("POSIX classes can't be negated in ERE", term.negated)
            else:
                pat = '[:%s:]' % n
            parts.append(pat)

        else:
            raise AssertionError(term)


def _AsPosixEre(node, parts, capture_names):
    # type: (re_t, List[str], List[Optional[str]]) -> None
    """Translate an Oil regex to a POSIX ERE.

    Appends to a list of parts that you have to join.
    """
    UP_node = node
    tag = node.tag()

    if tag == re_e.Primitive:
        node = cast(re.Primitive, UP_node)
        if node.id == Id.Re_Dot:
            parts.append('.')
        elif node.id == Id.Re_Start:
            parts.append('^')
        elif node.id == Id.Re_End:
            parts.append('$')
        else:
            raise AssertionError(node.id)
        return

    if tag == re_e.LiteralChars:
        node = cast(re.LiteralChars, UP_node)
        # The bash [[ x =~ "." ]] construct also has to do this

        # TODO: What about \0 and unicode escapes?
        # Those won't be as LiteralChars I don't think?
        # Unless you put them there through \0
        # Maybe DISALLOW those.
        # "Unprintable chars should be written as \0 or \x00 or \u0000"

        parts.append(glob_.ExtendedRegexEscape(node.s))
        return

    if tag == re_e.Seq:
        node = cast(re.Seq, UP_node)
        for c in node.children:
            _AsPosixEre(c, parts, capture_names)
        return

    if tag == re_e.Alt:
        node = cast(re.Alt, UP_node)
        for i, c in enumerate(node.children):
            if i != 0:
                parts.append('|')
            _AsPosixEre(c, parts, capture_names)
        return

    if tag == re_e.Repeat:
        node = cast(re.Repeat, UP_node)
        # 'foo' or "foo" or $x or ${x} evaluated to too many chars
        if node.child.tag() == re_e.LiteralChars:
            child = cast(re.LiteralChars, node.child)
            if len(child.s) > 1:
                # Note: Other regex dialects have non-capturing groups since we don't
                # need this.
                e_die(
                    "POSIX EREs don't have groups without capture, so this node "
                    "needs () around it.", child.blame_tok)

        _AsPosixEre(node.child, parts, capture_names)
        op = node.op
        op_tag = op.tag()
        UP_op = op

        if op_tag == re_repeat_e.Op:
            op = cast(re_repeat.Op, UP_op)
            op_id = op.op.id
            if op_id == Id.Arith_Plus:
                parts.append('+')
            elif op_id == Id.Arith_Star:
                parts.append('*')
            elif op_id == Id.Arith_QMark:
                parts.append('?')
            else:
                raise AssertionError(op_id)
            return

        if op_tag == re_repeat_e.Num:
            op = cast(re_repeat.Num, UP_op)
            parts.append('{%s}' % op.times.tval)
            return

        if op_tag == re_repeat_e.Range:
            op = cast(re_repeat.Range, UP_op)
            lower = op.lower.tval if op.lower else ''
            upper = op.upper.tval if op.upper else ''
            parts.append('{%s,%s}' % (lower, upper))
            return

        raise NotImplementedError(op_tag)

    # Special case for familiarity: () is acceptable as a group in ERE
    if tag == re_e.Group:
        node = cast(re.Group, UP_node)

        # placeholder so we know this group is numbered, but not named
        capture_names.append(None)

        parts.append('(')
        _AsPosixEre(node.child, parts, capture_names)
        parts.append(')')
        return

    if tag == re_e.Capture:
        node = cast(re.Capture, UP_node)

        # Collect in order of ( appearance
        # TODO: get the name string, and type string

        capture_str = lexer.TokenVal(node.name) if node.name else None
        capture_names.append(capture_str)

        parts.append('(')
        _AsPosixEre(node.child, parts, capture_names)
        parts.append(')')
        return

    if tag == re_e.PerlClass:
        node = cast(PerlClass, UP_node)
        n = node.name
        chars = PERL_CLASS[node.name]  # looks like [:digit:]
        if node.negated:
            pat = '[^%s]' % chars
        else:
            pat = '[%s]' % chars
        parts.append(pat)
        return

    if tag == re_e.PosixClass:
        node = cast(PosixClass, UP_node)
        n = node.name  # looks like 'digit'
        if node.negated:
            pat = '[^[:%s:]]' % n
        else:
            pat = '[[:%s:]]' % n
        parts.append(pat)
        return

    if tag == re_e.CharClass:
        node = cast(re.CharClass, UP_node)

        # HYPHEN CARET RBRACKET BACKSLASH
        special_char_flags = [0]
        non_special_parts = []  # type: List[str]

        for term in node.terms:
            _CharClassTermToEre(term, non_special_parts, special_char_flags)

        parts.append('[')
        if node.negated:
            parts.append('^')

        # Help the user with some of terrible corner cases

        # - move literal - to end        [ab-] not [a-b]
        # - move literal ^ to end        [x^-] not [^x-]
        # - move literal ] to beginning: []x] not [x]]
        # - double up \\ because of Gawk extension [\\]

        if special_char_flags[0] & FLAG_RBRACKET:
            parts.append(']')

        parts.extend(non_special_parts)

        if special_char_flags[0] & FLAG_BACKSLASH:
            parts.append('\\\\')  # TWO backslashes

        if special_char_flags[0] & FLAG_CARET:
            parts.append('^')

        if special_char_flags[0] & FLAG_HYPHEN:
            parts.append('-')

        parts.append(']')
        return

    raise NotImplementedError(tag)


def AsPosixEre(eggex):
    # type: (value.Eggex) -> str
    """
    Lazily fills in fields on the value.Eggex argument.
    """
    if eggex.as_ere is not None:
        return eggex.as_ere

    parts = []  # type: List[str]
    _AsPosixEre(eggex.spliced, parts, eggex.capture_names)

    # These are both indexed by group number, with None for the holes
    # List[str?] vs. List[value?]
    assert len(eggex.capture_names) == len(eggex.convert_funcs)

    eggex.as_ere = ''.join(parts)

    return eggex.as_ere


def CanonicalFlags(flags):
    # type: (List[EggexFlag]) -> str
    """
    Raises PARSE error on invalid flags.

    In theory we could encode directly to integers like REG_ICASE, but a string
    like like 'i' makes the error message slightly more legible.
    """
    letters = []  # type: List[str]
    for flag in flags:
        if flag.negated:
            p_die("Flag can't be negated", flag.flag)
        flag_name = lexer.TokenVal(flag.flag)
        if flag_name in ('i', 'reg_icase'):
            letters.append('i')
        elif flag_name == 'reg_newline':
            letters.append('n')
        else:
            p_die("Invalid regex flag %r" % flag_name, flag.flag)

    # Normalize for comparison
    letters.sort()
    return ''.join(letters)


def LibcFlags(canonical_flags):
    # type: (Optional[str]) -> int
    if canonical_flags is None:
        return 0

    libc_flags = 0
    for ch in canonical_flags:
        if ch == 'i':
            libc_flags |= REG_ICASE
        elif ch == 'n':
            libc_flags |= REG_NEWLINE
        else:
            # regex_translate should prevent this
            raise AssertionError()
    return libc_flags
