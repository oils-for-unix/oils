# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
lexer.py - Library for lexing.
"""

from _devbuild.gen.syntax_asdl import Token, SourceLine
from _devbuild.gen.types_asdl import lex_mode_t, lex_mode_e
from _devbuild.gen.id_kind_asdl import Id_t, Id, Id_str, Kind
from asdl import runtime
from mycpp.mylib import log
from frontend import consts
from frontend import match

unused = log, Id_str

from typing import List, Tuple, Optional, Counter, TYPE_CHECKING
if TYPE_CHECKING:
    from core.alloc import Arena
    from frontend.reader import _Reader


def IsPlusEquals(tok):
    # type: (Token) -> bool
    """Common pattern to test if we got foo= or foo+=

    Note: can be replaced by s.find('+', index, index+1), which avoids
    allocation.
    """
    index = tok.col + tok.length - 2
    return tok.line.content[index] == '+'


# Also: IsWhitespace, IsLeadingSpace


def TokenEquals(tok, s):
    # type: (Token, str) -> bool

    # TODO: Use tok.line.content.find(substr, start, end)

    raise NotImplementedError()


def TokenContains(tok, substr):
    # type: (Token, str) -> bool

    # TODO: Use tok.line.content.find(substr, start, end)

    raise NotImplementedError()


def TokenStartsWith(tok, s):
    # type: (Token, str) -> bool

    # TODO: Use tok.line.content.startswith(substr, start, end)

    raise NotImplementedError()


def TokenEndsWith(tok, s):
    # type: (Token, str) -> bool

    # TODO: Use tok.line.content.startswith(substr, start, end)

    raise NotImplementedError()


def TokenVal(tok):
    # type: (Token) -> str
    """Compute string value on demand."""
    return tok.line.content[tok.col:tok.col + tok.length]


def TokenSliceLeft(tok, left_index):
    # type: (Token, int) -> str
    """Slice token directly, without creating intermediate string."""
    assert left_index > 0
    left = tok.col + left_index
    return tok.line.content[left:tok.col + tok.length]


def TokenSliceRight(tok, right_index):
    # type: (Token, int) -> str
    """Slice token directly, without creating intermediate string."""
    assert right_index < 0
    right = tok.col + tok.length + right_index
    return tok.line.content[tok.col:right]


def TokenSlice(tok, left, right):
    # type: (Token, int, int) -> str
    """Slice token directly, without creating intermediate string."""
    assert left > 0
    start = tok.col + left
    end = tok.col + tok.length + right
    return tok.line.content[start:end]


def DummyToken(id_, val):
    # type: (int, str) -> Token

    col = -1
    length = -1
    return Token(id_, col, length, runtime.NO_SPID, None, val)


class LineLexer(object):

    def __init__(self, arena):
        # type: (Arena) -> None
        self.arena = arena
        self.replace_last_token = False  # For MaybeUnreadOne

        # Singleton instance because we don't allow globals.
        # 2023-09: I tried LineLexer::Read() returning None, but that is subtly
        # incorrect, e.g. in Lexer::Read() with NUL bytes.
        self.eol_tok = DummyToken(Id.Eol_Tok, '')

        self.Reset(None, 0)  # Invalid src_line to start

    def __repr__(self):
        # type: () -> str
        return '<LineLexer at pos %d of line %r>' % (self.line_pos,
                                                     self.src_line)

    def Reset(self, src_line, line_pos):
        # type: (SourceLine, int) -> None
        #assert line, repr(line)  # can't be empty or None
        self.src_line = src_line
        self.line_pos = line_pos

    def MaybeUnreadOne(self):
        # type: () -> bool
        """Return True if we can unread one character, or False otherwise.

        NOTE: Only call this when you know the last token was exactly one character!
        """
        if self.line_pos == 0:
            return False
        else:
            self.line_pos -= 1
            self.replace_last_token = True  # don't add the next token to the arena
            return True

    def GetEofToken(self, id_):
        # type: (int) -> Token
        """Create a new span ID for syntax errors involving the EOF token."""
        if self.src_line is None:
            # There are ZERO lines now.  Add a dummy line 0 so the Token has a source
            # to display errors.
            src_line = self.arena.AddLine('', 0)
        else:
            src_line = self.src_line

        return self.arena.NewToken(id_, self.line_pos, 0, src_line, '')

    def LookAheadOne(self, lex_mode):
        # type: (lex_mode_t) -> Id_t
        """Look ahead exactly one token in the given lexer mode."""
        pos = self.line_pos
        line_str = self.src_line.content
        n = len(line_str)
        if pos == n:
            return Id.Unknown_Tok
        else:
            tok_type, _ = match.OneToken(lex_mode, line_str, pos)
            return tok_type

    def AssertAtEndOfLine(self):
        # type: () -> None
        assert self.line_pos == len(self.src_line.content), \
            '%d %s' % (self.line_pos, self.src_line.content)

    def LookPastSpace(self, lex_mode):
        # type: (lex_mode_t) -> Id_t
        """Look ahead in current line for non-space token, using given lexer
        mode.

        Does NOT advance self.line_pos.

        Called with at least the following modes:
          lex_mode_e.Arith -- for ${a[@]} vs ${a[1+2]}
          lex_mode_e.VSub_1
          lex_mode_e.ShCommand

        Note: Only ShCommand emits Id.WS_Space, but other lexer modes don't.
        """
        pos = self.line_pos
        line_str = self.src_line.content
        n = len(line_str)
        #print('Look ahead from pos %d, line %r' % (pos,self.line))
        while True:
            if pos == n:
                # We don't allow lookahead while already at end of line, because it
                # would involve interacting with the line reader, and we never need
                # it.  In lex_mode_e.ShCommand, there is an explicit newline token, but
                # lex_mode_e.Arith doesn't have it.
                return Id.Unknown_Tok

            tok_type, end_pos = match.OneToken(lex_mode, line_str, pos)

            # NOTE: Instead of hard-coding this token, we could pass it in.
            # LookPastSpace(lex_mode, past_token_type)
            # - WS_Space only given in lex_mode_e.ShCommand
            # - Id.Ignored_Space given in lex_mode_e.Expr
            if tok_type != Id.WS_Space and tok_type != Id.Ignored_Space:
                break
            pos = end_pos

        return tok_type

    def LookAheadFuncParens(self, unread):
        # type: (int) -> bool
        """For finding the () in 'f ( ) { echo hi; }'.

        Args:
          unread: either 0 or 1, for the number of characters to go back

        The lookahead is limited to the current line, which sacrifices a rare
        corner case.  This not recognized as a function:

            foo\
            () {}

        whereas this is

            foo()
            {}
        """
        pos = self.line_pos - unread
        assert pos > 0
        tok_type, _ = match.OneToken(lex_mode_e.FuncParens,
                                     self.src_line.content, pos)
        return tok_type == Id.LookAhead_FuncParens

    def ByteLookAhead(self):
        # type: () -> str
        """Lookahead a single byte.

        Useful when you know the token is one char.
        """
        pos = self.line_pos
        if pos == len(self.src_line.content):
            return ''
        else:
            return self.src_line.content[pos]

    def ByteLookBack(self):
        # type: () -> int
        """A little hack for stricter proc arg list syntax.

        There has to be a space before the paren.

        Yes: json write (x)
         No: json write(x)
        """
        pos = self.line_pos - 2
        if pos < 0:
            return -1
        else:
            return ord(self.src_line.content[pos])

    def Read(self, lex_mode):
        # type: (lex_mode_t) -> Token

        # Inner loop optimization
        if self.src_line:
            line_str = self.src_line.content
        else:
            line_str = ''
        line_pos = self.line_pos

        tok_type, end_pos = match.OneToken(lex_mode, line_str, line_pos)
        if tok_type == Id.Eol_Tok:  # Do NOT add a span for this sentinel!
            # LineLexer tells Lexer to read a new line.
            return self.eol_tok

        # TODO: can inline this function with formula on 16-bit Id.
        kind = consts.GetKind(tok_type)

        # Save on allocations!  We often don't look at the token value.
        # Whitelist doesn't work well?  Use blacklist for now.
        # - Kind.KW is sometimes a literal in a word
        # - Kind.Right is for " in here docs.  Lexer isn't involved.
        # - Got an error with Kind.Left too that I don't understand
        # - Kind.ControlFlow doesn't work because we word_.StaticEval()
        # if kind in (Kind.Lit, Kind.VSub, Kind.Redir, Kind.Char, Kind.Backtick, Kind.KW, Kind.Right):
        if kind in (Kind.Arith, Kind.Op, Kind.VTest, Kind.VOp0, Kind.VOp2,
                    Kind.VOp3, Kind.WS, Kind.Ignored, Kind.Eof):
            tok_val = None  # type: Optional[str]
        else:
            tok_val = line_str[line_pos:end_pos]

        # NOTE: We're putting the arena hook in LineLexer and not Lexer because we
        # want it to be "low level".  The only thing fabricated here is a newline
        # added at the last line, so we don't end with \0.
        if self.replace_last_token:  # make another token from the last span
            self.arena.UnreadOne()
            self.replace_last_token = False

        tok_len = end_pos - line_pos
        t = self.arena.NewToken(tok_type, line_pos, tok_len, self.src_line,
                                tok_val)

        self.line_pos = end_pos
        return t


class Lexer(object):
    """Read lines from the line_reader, split them into tokens with line_lexer,
    returning them in a stream."""

    def __init__(self, line_lexer, line_reader):
        # type: (LineLexer, _Reader) -> None
        """
    Args:
      line_lexer: Underlying object to get tokens from
      line_reader: get new lines from here
    """
        self.line_lexer = line_lexer
        self.line_reader = line_reader

        self.line_id = -1  # Invalid one
        self.translation_stack = []  # type: List[Tuple[Id_t, Id_t]]
        self.emit_comp_dummy = False

    def ResetInputObjects(self):
        # type: () -> None
        self.line_lexer.Reset(None, 0)

    def MaybeUnreadOne(self):
        # type: () -> bool
        return self.line_lexer.MaybeUnreadOne()

    def LookAheadOne(self, lex_mode):
        # type: (lex_mode_t) -> Id_t
        return self.line_lexer.LookAheadOne(lex_mode)

    def LookPastSpace(self, lex_mode):
        # type: (lex_mode_t) -> Id_t
        return self.line_lexer.LookPastSpace(lex_mode)

    def LookAheadFuncParens(self, unread):
        # type: (int) -> bool
        return self.line_lexer.LookAheadFuncParens(unread)

    def ByteLookAhead(self):
        # type: () -> str
        return self.line_lexer.ByteLookAhead()

    def ByteLookBack(self):
        # type: () -> int
        return self.line_lexer.ByteLookBack()

    def EmitCompDummy(self):
        # type: () -> None
        """Emit Id.Lit_CompDummy right before EOF, for completion."""
        self.emit_comp_dummy = True

    def PushHint(self, old_id, new_id):
        # type: (Id_t, Id_t) -> None
        """Use cases: Id.Op_RParen -> Id.Right_Subshell -- disambiguate
        Id.Op_RParen -> Id.Eof_RParen.

        Problems for $() nesting.

        - posix:
          - case foo) and case (foo)
          - func() {}
          - subshell ( )
        - bash extensions:
          - precedence in [[,   e.g.  [[ (1 == 2) && (2 == 3) ]]
          - arrays: a=(1 2 3), a+=(4 5)
        """
        #log('   PushHint %s ==> %s', Id_str(old_id), Id_str(new_id))
        self.translation_stack.append((old_id, new_id))

    def MoveToNextLine(self):
        # type: () -> None
        """For lookahead on the next line.

        This is required by `ParseYshCase` and is used in `_NewlineOkForYshCase`.

        We use this because otherwise calling `LookPastSpace` would return
        `Id.Unknown_Tok` when the lexer has reached the end of the line. For an
        example, take this case:

          case (x) {
                   ^--- We are here

            (else) {
            ^--- We want lookahead to here

                echo test
            }
          }

        But, without `MoveToNextLine`, it is impossible to peek the '(' without
        consuming it. And consuming it would be a problem once we want to hand off
        pattern parsing to the expression parser.
        """
        # Only call this when you've seen \n
        self.line_lexer.AssertAtEndOfLine()

        src_line, line_pos = self.line_reader.GetLine()
        self.line_lexer.Reset(src_line, line_pos)  # fill with a new line

    def _Read(self, lex_mode):
        # type: (lex_mode_t) -> Token
        """Read from the normal line buffer, not an alias."""
        t = self.line_lexer.Read(lex_mode)
        if t.id == Id.Eol_Tok:  # We hit \0 aka Eol_Tok, read a new line
            src_line, line_pos = self.line_reader.GetLine()

            if src_line is None:  # no more lines
                if self.emit_comp_dummy:
                    id_ = Id.Lit_CompDummy
                    self.emit_comp_dummy = False  # emit EOF the next time
                else:
                    id_ = Id.Eof_Real
                return self.line_lexer.GetEofToken(id_)

            self.line_lexer.Reset(src_line, line_pos)  # fill with a new line
            t = self.line_lexer.Read(lex_mode)

        # e.g. translate ) or ` into EOF
        if len(self.translation_stack):
            old_id, new_id = self.translation_stack[-1]  # top
            if t.id == old_id:
                #log('==> TRANSLATING %s ==> %s', Id_str(t.id), Id_str(new_id))
                self.translation_stack.pop()
                t.id = new_id

        return t

    def Read(self, lex_mode):
        # type: (lex_mode_t) -> Token
        while True:
            t = self._Read(lex_mode)
            # TODO: Change to ALL IGNORED types, once you have SPACE_TOK.  This means
            # we don't have to handle them in the VSub_1/VSub_2/etc. states.
            if t.id != Id.Ignored_LineCont:
                break

        #ID_HIST[t.id] += 1
        #log('> Read() Returning %s', t)
        return t


if 0:  # mylib.PYTHON: not: breaks tarball build
    import collections
    ID_HIST = collections.Counter()  # type: Counter[Id_t]
