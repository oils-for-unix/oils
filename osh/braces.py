#!/usr/bin/env python2
"""
braces.py - Implementation of {andy,bob}@example.com

NOTE: bash implements brace expansion in the braces.c file (835 lines).  It
uses goto!

Possible optimization flags for Compound:
- has Lit_LBrace, LitRBrace -- set during word_parse phase
  - it if has both, then do BraceDetect
- has BracedTuple -- set during BraceDetect
  - if it does, then do the expansion
- has Lit_Star, ?, [ ] -- globbing?
  - but after expansion do you still have those flags?
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Id_t
from _devbuild.gen.syntax_asdl import (
    Token,
    CompoundWord,
    word,
    word_e,
    word_t,
    word_part,
    word_part_e,
    word_part_t,
)
from core.error import p_die
from frontend import lexer
from frontend import match
from mycpp import mylib
from mycpp.mylib import log, tagswitch
from osh import word_

from typing import List, Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from frontend.match import SimpleLexer

_ = log

# Step has to be strictly positive or negative, so we can use 0 for 'not
# specified'.
NO_STEP = 0


# The brace language has no syntax errors!  But we still need to abort the
# parse.  TODO: Should we expose a strict version later?
class _NotARange(Exception):

    def __init__(self, s):
        # type: (str) -> None
        pass


class _RangeParser(object):
    """Grammar for ranges:

    step = Dots Int
    int_range = Int Dots Int step?
    char_range = Char Dots Char step?
    range = (int_range | char_range) Eof  # ensure no extra tokens!
    """

    def __init__(self, lexer, blame_tok):
        # type: (SimpleLexer, Token) -> None
        self.lexer = lexer
        self.blame_tok = blame_tok

        self.token_type = Id.Undefined_Tok
        self.token_val = ''

    def _Next(self):
        # type: () -> None
        """Move to the next token."""
        self.token_type, self.token_val = self.lexer.Next()

    def _Eat(self, token_type):
        # type: (Id_t) -> str
        if self.token_type != token_type:
            raise _NotARange('Expected %d, got %d' %
                             (token_type, self.token_type))
        val = self.token_val
        self._Next()
        return val

    def _ParseStep(self):
        # type: () -> int
        self._Next()  # past Dots
        step = int(self._Eat(Id.Range_Int))
        if step == 0:
            p_die("Step can't be 0", self.blame_tok)
        return step

    def _ParseRange(self, range_kind):
        # type: (Id_t) -> word_part.BracedRange
        start = self.token_val
        self._Next()  # past Char

        self._Eat(Id.Range_Dots)
        end = self._Eat(range_kind)

        if self.token_type == Id.Range_Dots:
            step = self._ParseStep()
        else:
            step = NO_STEP

        part = word_part.BracedRange(self.blame_tok, range_kind, start, end,
                                     step)
        return part

    def Parse(self):
        # type: () -> word_part.BracedRange
        self._Next()
        if self.token_type == Id.Range_Int:
            part = self._ParseRange(self.token_type)

            # Check step validity and fill in a default
            start = int(part.start)
            end = int(part.end)
            if start < end:
                if part.step == NO_STEP:
                    part.step = 1
                if part.step <= 0:  # 0 step is not allowed
                    p_die(
                        'Invalid step %d for ascending integer range' %
                        part.step, self.blame_tok)
            elif start > end:
                if part.step == NO_STEP:
                    part.step = -1
                if part.step >= 0:  # 0 step is not allowed
                    p_die(
                        'Invalid step %d for descending integer range' %
                        part.step, self.blame_tok)
            else:
                # {1..1}  singleton range is dumb but I suppose consistent
                part.step = 1

        elif self.token_type == Id.Range_Char:
            part = self._ParseRange(self.token_type)

            # Compare integers because mycpp doesn't support < on strings!
            start_num = ord(part.start[0])
            end_num = ord(part.end[0])

            # Check step validity and fill in a default
            if start_num < end_num:
                if part.step == NO_STEP:
                    part.step = 1
                if part.step <= 0:  # 0 step is not allowed
                    p_die(
                        'Invalid step %d for ascending character range' %
                        part.step, self.blame_tok)
            elif start_num > end_num:
                if part.step == NO_STEP:
                    part.step = -1
                if part.step >= 0:  # 0 step is not allowed
                    p_die(
                        'Invalid step %d for descending character range' %
                        part.step, self.blame_tok)
            else:
                # {a..a}  singleton range is dumb but I suppose consistent
                part.step = 1

            # Check matching cases
            upper1 = part.start.isupper()
            upper2 = part.end.isupper()
            if upper1 != upper2:
                p_die('Mismatched cases in character range', self.blame_tok)

        else:
            raise _NotARange('')

        # prevent unexpected trailing tokens
        self._Eat(Id.Eol_Tok)
        return part


def _RangePartDetect(tok):
    # type: (Token) -> Optional[word_part.BracedRange]
    """Parse the token and return a new word_part if it looks like a range."""

    lx = match.BraceRangeLexer(lexer.TokenVal(tok))
    p = _RangeParser(lx, tok)
    try:
        part = p.Parse()
    except _NotARange as e:
        return None
    return part


class _StackFrame(object):

    def __init__(self, cur_parts):
        # type: (List[word_part_t]) -> None
        self.cur_parts = cur_parts
        self.alt_part = word_part.BracedTuple([])
        self.saw_comma = False


def BraceDetect(w):
    # type: (CompoundWord) -> Optional[word.BracedTree]
    """Return a new word if the input word looks like a brace expansion.

    e.g. {a,b} or {1..10..2} (TODO)
    Do we want to accept {01..02} ?  zsh does make some attempt to do this too.

    NOTE: This is an iterative algorithm that uses a stack.  The grammar-based
    approach didn't seem natural.

    It's not LL(1) because of 'part*'.  And not LL(k) even?  Maybe it be handled
    with an LR parser?  In any case the imperative algorithm with 'early return'
    for a couple cases is fairly simple.

    Grammar:
      # an alternative is a literal, possibly empty, or another brace_expr

      part = <any part except Literal>
      alt = part* | brace_expr

      # a brace_expr is group of at least 2 braced and comma-separated
      # alternatives, with optional prefix and suffix.
      brace_expr = part* '{' alt ',' alt (',' alt)* '}' part*
    """
    # Errors:
    # }a{    - stack depth dips below 0
    # {a,b}{ - Stack depth doesn't end at 0
    # {a}    - no comma, and also not an numeric range

    # The shortest possible brace expansion is {,}.  This heuristic prevents a
    # lot of garbage from being created, since otherwise nearly every word
    # would be checked.  We could be even more precise but this is cheap.
    if len(w.parts) < 3:
        return None

    cur_parts = []  # type: List[word_part_t]
    stack = []  # type: List[_StackFrame]

    found = False

    for i, part in enumerate(w.parts):
        append = True
        UP_part = part
        if part.tag() == word_part_e.Literal:
            part = cast(Token, UP_part)
            id_ = part.id
            if id_ == Id.Lit_LBrace:
                # Save prefix parts.  Start new parts list.
                new_frame = _StackFrame(cur_parts)
                stack.append(new_frame)
                cur_parts = []  # clear
                append = False
                found = True  # assume found, but can early exit with None later

            elif id_ == Id.Lit_Comma:  # Append a new alternative.
                # NOTE: Should we allow this:
                # ,{a,b}
                # or force this:
                # \,{a,b}
                # ?  We're forcing braces right now but not commas.
                if len(stack):
                    stack[-1].saw_comma = True
                    stack[-1].alt_part.words.append(CompoundWord(cur_parts))
                    cur_parts = []  # clear
                    append = False

            elif id_ == Id.Lit_RBrace:
                if len(stack) == 0:  # e.g. echo {a,b}{  -- unbalanced {
                    return None  # do not expand ANYTHING because of invalid syntax

                # Detect {1..10} and {1..10..2}

                #log('stack[-1]: %s', stack[-1])
                #log('cur_parts: %s', cur_parts)

                range_part = None  # type: Optional[word_part_t]
                # only allow {1..3}, not {a,1..3}
                if not stack[-1].saw_comma and len(cur_parts) == 1:
                    # It must be ONE part.  For example, -1..-100..-2 is initially
                    # lexed as a single Lit_Chars token.
                    part2 = cur_parts[0]
                    if part2.tag() == word_part_e.Literal:
                        tok = cast(Token, part2)
                        if tok.id == Id.Lit_Chars:
                            range_part = _RangePartDetect(tok)
                            if range_part:
                                frame = stack.pop()
                                cur_parts = frame.cur_parts
                                cur_parts.append(range_part)
                                append = False

                # It doesn't look like a range -- process it as the last element in
                # {a,b,c}

                if not range_part:
                    if not stack[
                            -1].saw_comma:  # {foo} is not a real alternative
                        return None  # early return

                    stack[-1].alt_part.words.append(CompoundWord(cur_parts))

                    frame = stack.pop()
                    cur_parts = frame.cur_parts
                    cur_parts.append(frame.alt_part)
                    append = False

        if append:
            cur_parts.append(part)

    if len(stack) != 0:
        return None

    if found:
        return word.BracedTree(cur_parts)
    else:
        return None


def BraceDetectAll(words):
    # type: (List[CompoundWord]) -> List[word_t]
    """Return a new list of words, possibly with BracedTree instances."""
    out = []  # type: List[word_t]
    for w in words:
        brace_tree = BraceDetect(w)
        if brace_tree:
            out.append(brace_tree)
            continue
        out.append(w)
    return out


def _LeadingZeros(s):
    # type: (str) -> int
    n = 0
    for c in s:
        if c == '0':
            n += 1
        else:
            break
    return n


def _IntToString(i, width):
    # type: (int, int) -> str
    s = str(i)
    n = len(s)
    if n < width:  # width might be 0
        # pad with zeros
        pad = '0' * (width - n)
        return pad + s
    else:
        return s


def _RangeStrings(part):
    # type: (word_part.BracedRange) -> List[str]

    if part.kind == Id.Range_Int:
        nums = []  # type: List[str]

        z1 = _LeadingZeros(part.start)
        z2 = _LeadingZeros(part.end)

        if z1 == 0 and z2 == 0:
            width = 0
        else:
            if z1 < z2:
                width = len(part.end)
            else:
                width = len(part.start)

        n = int(part.start)
        end = int(part.end)
        step = part.step
        if step > 0:
            while True:
                nums.append(_IntToString(n, width))
                n += step
                if n > end:
                    break
        else:
            while True:
                nums.append(_IntToString(n, width))
                n += step
                if n < end:
                    break

        return nums

    else:  # Id.Range_Char
        chars = []  # type: List[str]

        n = ord(part.start)
        ord_end = ord(part.end)
        step = part.step
        if step > 0:
            while True:
                chars.append(chr(n))
                n += step
                if n > ord_end:
                    break
        else:
            while True:
                chars.append(chr(n))
                n += step
                if n < ord_end:
                    break

        return chars


def _ExpandPart(
        parts,  # type: List[word_part_t]
        first_alt_index,  # type: int
        suffixes,  # type: List[List[word_part_t]]
):
    # type: (...) -> List[List[word_part_t]]
    """Mutually recursive with _BraceExpand.

    Args:
      parts: input parts
      first_alt_index: index of the first BracedTuple
      suffixes: List of suffixes to append.
    """
    out = []  # type: List[List[word_part_t]]

    prefix = parts[:first_alt_index]
    expand_part = parts[first_alt_index]

    UP_part = expand_part
    with tagswitch(expand_part) as case:
        if case(word_part_e.BracedTuple):
            expand_part = cast(word_part.BracedTuple, UP_part)
            # Call _BraceExpand on each of the inner words too!
            expanded_alts = []  # type: List[List[word_part_t]]
            for w in expand_part.words:
                expanded_alts.extend(_BraceExpand(w.parts))

            for alt_parts in expanded_alts:
                for suffix in suffixes:
                    out_parts = []  # type: List[word_part_t]
                    out_parts.extend(prefix)
                    out_parts.extend(alt_parts)
                    out_parts.extend(suffix)
                    out.append(out_parts)

        elif case(word_part_e.BracedRange):
            expand_part = cast(word_part.BracedRange, UP_part)
            # Not mutually recursive with _BraceExpand
            strs = _RangeStrings(expand_part)

            # Often prefix and suffixes are empty, but there's not that much to
            # optimize
            # log('prefix %s, suffixes %s, strs %s', prefix, suffixes, strs)

            for s in strs:
                for suffix in suffixes:
                    out_parts_ = []  # type: List[word_part_t]
                    out_parts_.extend(prefix)

                    # TODO: Does it help to preserve location info?
                    # t = Token(Id.Lit_Chars, expand_part.locs[0], s)
                    t = lexer.DummyToken(Id.Lit_Chars, s)

                    out_parts_.append(t)
                    out_parts_.extend(suffix)
                    out.append(out_parts_)

        else:
            raise AssertionError()

    return out


def _BraceExpand(parts):
    # type: (List[word_part_t]) -> List[List[word_part_t]]
    """Mutually recursive with _ExpandPart."""

    # manual GC point, because brace expansion is a separate stage that does a
    # bunch of computation outside the interpreter
    mylib.MaybeCollect()

    num_alts = 0
    first_alt_index = -1
    for i, part in enumerate(parts):
        tag = part.tag()
        if tag in (word_part_e.BracedTuple, word_part_e.BracedRange):
            num_alts += 1
            if num_alts == 1:
                first_alt_index = i
            elif num_alts == 2:
                break  # don't need to count anymore

    # NOTE: There are TWO recursive calls here, not just one -- one for
    # nested {}, and one for adjacent {}.  This is hard to do iteratively.
    if num_alts == 0:
        return [parts]

    elif num_alts == 1:
        suffix = parts[first_alt_index + 1:]
        return _ExpandPart(parts, first_alt_index, [suffix])

    else:
        # Now call it on the tail
        tail_parts = parts[first_alt_index + 1:]
        suffixes = _BraceExpand(tail_parts)  # recursive call
        return _ExpandPart(parts, first_alt_index, suffixes)


def BraceExpandWords(words):
    # type: (List[word_t]) -> List[CompoundWord]
    out = []  # type: List[CompoundWord]
    for w in words:
        UP_w = w
        with tagswitch(w) as case:
            if case(word_e.BracedTree):
                w = cast(word.BracedTree, UP_w)
                # Note: for the case of {1..100000}, this is a flat list of Token.
                # Would be nice to optimize, but we don't really know the structure
                # ahead of time
                parts_list = _BraceExpand(w.parts)
                for parts in parts_list:
                    expanded = CompoundWord(parts)

                    # Now do tilde detection on brace-expanded word
                    ti = word_.TildeDetect2(expanded)
                    if ti:
                        out.append(ti)
                    else:
                        out.append(expanded)

            elif case(word_e.Compound):
                w = cast(CompoundWord, UP_w)

                # Already did tilde detection before expansion
                out.append(w)

            else:
                raise AssertionError(w.tag())

    return out
