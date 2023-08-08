# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
cmd_parse.py - Parse high level shell commands.
"""
from __future__ import print_function

from _devbuild.gen import grammar_nt
from _devbuild.gen.id_kind_asdl import Id, Id_t, Kind, Kind_str
from _devbuild.gen.types_asdl import lex_mode_e, cmd_mode_e, cmd_mode_t
from _devbuild.gen.syntax_asdl import (
    loc,
    SourceLine,
    source,
    parse_result,
    parse_result_t,
    command,
    command_t,
    condition,
    condition_t,
    for_iter,
    ArgList,
    BraceGroup,
    BlockArg,
    CaseArm,
    case_arg,
    IfArm,
    pat,
    pat_t,
    Redir,
    redir_param,
    redir_loc,
    redir_loc_t,
    word_e,
    word_t,
    CompoundWord,
    Token,
    word_part_e,
    word_part_t,
    rhs_word,
    rhs_word_t,
    sh_lhs_expr,
    sh_lhs_expr_t,
    AssignPair,
    EnvPair,
    assign_op_e,
    NameType,
    proc_sig,
    proc_sig_e,
)
from core import alloc
from core import error
from core.error import p_die
from core import ui
from frontend import consts
from frontend import lexer
from frontend import location
from frontend import match
from frontend import reader
from mycpp.mylib import log
from osh import braces
from osh import bool_parse
from osh import word_

from typing import Optional, List, Dict, Any, Tuple, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from core.alloc import Arena
    from core import optview
    from frontend.lexer import Lexer
    from frontend.parse_lib import ParseContext, AliasesInFlight
    from frontend.reader import _Reader
    from osh.word_parse import WordParser

_ = Kind_str  # for debug prints

TAB_CH = 9  # ord('\t')
SPACE_CH = 32  # ord(' ')


def _ReadHereLines(
        line_reader,  # type: _Reader
        h,  # type: Redir
        delimiter,  # type: str
):
    # type: (...) -> Tuple[List[Tuple[SourceLine, int]], Tuple[SourceLine, int]]
    # NOTE: We read all lines at once, instead of parsing line-by-line,
    # because of cases like this:
    # cat <<EOF
    # 1 $(echo 2
    # echo 3) 4
    # EOF
    here_lines = []  # type: List[Tuple[SourceLine, int]]
    last_line = None  # type: Tuple[SourceLine, int]
    strip_leading_tabs = (h.op.id == Id.Redir_DLessDash)

    while True:
        src_line, unused_offset = line_reader.GetLine()

        if src_line is None:  # EOF
            # An unterminated here doc is just a warning in bash.  We make it
            # fatal because we want to be strict, and because it causes problems
            # reporting other errors.
            # Attribute it to the << in <<EOF for now.
            p_die("Couldn't find terminator for here doc that starts here",
                  h.op)

        assert len(src_line.content) != 0  # None should be the empty line

        line = src_line.content

        # If op is <<-, strip off ALL leading tabs -- not spaces, and not just
        # the first tab.
        start_offset = 0
        if strip_leading_tabs:
            n = len(line)
            i = 0  # used after loop exit
            while i < n:
                if line[i] != '\t':
                    break
                i += 1
            start_offset = i

        if line[start_offset:].rstrip() == delimiter:
            last_line = (src_line, start_offset)
            break

        here_lines.append((src_line, start_offset))

    return here_lines, last_line


def _MakeLiteralHereLines(
        here_lines,  # type: List[Tuple[SourceLine, int]]
        arena,  # type: Arena
):
    # type: (...) -> List[word_part_t]  # less precise because List is invariant type
    """Create a line_span and a token for each line."""
    tokens = []  # type: List[Token]
    for src_line, start_offset in here_lines:
        t = arena.NewToken(Id.Lit_Chars, start_offset, len(src_line.content),
                           src_line, src_line.content[start_offset:])
        tokens.append(t)
    parts = [cast(word_part_t, t) for t in tokens]
    return parts


def _ParseHereDocBody(parse_ctx, r, line_reader, arena):
    # type: (ParseContext, Redir, _Reader, Arena) -> None
    """Fill in attributes of a pending here doc node."""
    h = cast(redir_param.HereDoc, r.arg)
    # "If any character in word is quoted, the delimiter shall be formed by
    # performing quote removal on word, and the here-document lines shall not
    # be expanded. Otherwise, the delimiter shall be the word itself."
    # NOTE: \EOF counts, or even E\OF
    ok, delimiter, delim_quoted = word_.StaticEval(h.here_begin)
    if not ok:
        p_die('Invalid here doc delimiter', loc.Word(h.here_begin))

    here_lines, last_line = _ReadHereLines(line_reader, r, delimiter)

    if delim_quoted:  # << 'EOF'
        # Literal for each line.
        h.stdin_parts = _MakeLiteralHereLines(here_lines, arena)
    else:
        line_reader = reader.VirtualLineReader(here_lines, arena)
        w_parser = parse_ctx.MakeWordParserForHereDoc(line_reader)
        w_parser.ReadHereDocBody(h.stdin_parts)  # fills this in

    end_line, end_pos = last_line

    # Create a Token with the end terminator.  Maintains the invariant that the
    # tokens "add up".
    h.here_end_tok = arena.NewToken(Id.Undefined_Tok, end_pos,
                                    len(end_line.content), end_line, '')


def _MakeAssignPair(parse_ctx, preparsed, arena):
    # type: (ParseContext, PreParsedItem, Arena) -> AssignPair
    """Create an AssignPair from a 4-tuples from DetectShAssignment."""

    left_token, close_token, part_offset, w = preparsed

    if left_token.id == Id.Lit_VarLike:  # s=1
        if lexer.IsPlusEquals(left_token):
            var_name = lexer.TokenSliceRight(left_token, -2)
            op = assign_op_e.PlusEqual
        else:
            var_name = lexer.TokenSliceRight(left_token, -1)
            op = assign_op_e.Equal

        tmp = sh_lhs_expr.Name(left_token, var_name)

        lhs = cast(sh_lhs_expr_t, tmp)

    elif left_token.id == Id.Lit_ArrayLhsOpen and parse_ctx.one_pass_parse:
        var_name = lexer.TokenSliceRight(left_token, -1)
        if lexer.IsPlusEquals(close_token):
            op = assign_op_e.PlusEqual
        else:
            op = assign_op_e.Equal

        assert left_token.line == close_token.line, \
            '%s and %s not on same line' % (left_token, close_token)

        left_pos = left_token.col + left_token.length
        index_str = left_token.line.content[left_pos:close_token.col]
        lhs = sh_lhs_expr.UnparsedIndex(left_token, var_name, index_str)

    elif left_token.id == Id.Lit_ArrayLhsOpen:  # a[x++]=1
        var_name = lexer.TokenSliceRight(left_token, -1)
        if lexer.IsPlusEquals(close_token):
            op = assign_op_e.PlusEqual
        else:
            op = assign_op_e.Equal

        span1 = left_token
        span2 = close_token
        # Similar to SnipCodeString / SnipCodeBlock
        if span1.line == span2.line:
            # extract what's between brackets
            code_str = span1.line.content[span1.col + span1.length:span2.col]
        else:
            raise NotImplementedError('%s != %s' % (span1.line, span2.line))
        a_parser = parse_ctx.MakeArithParser(code_str)

        # a[i+1]= is a place
        src = source.Reparsed('array place', left_token, close_token)
        with alloc.ctx_Location(arena, src):
            index_node = a_parser.Parse()  # may raise error.Parse

        tmp3 = sh_lhs_expr.IndexedName(left_token, var_name, index_node)

        lhs = cast(sh_lhs_expr_t, tmp3)

    else:
        raise AssertionError()

    # TODO: Should we also create a rhs_expr.ArrayLiteral here?
    n = len(w.parts)
    if part_offset == n:
        rhs = rhs_word.Empty  # type: rhs_word_t
    else:
        # tmp2 is for intersection of C++/MyPy type systems
        tmp2 = CompoundWord(w.parts[part_offset:])
        word_.TildeDetectAssign(tmp2)
        rhs = tmp2

    return AssignPair(left_token, lhs, op, rhs)


def _AppendMoreEnv(preparsed_list, more_env):
    # type: (PreParsedList, List[EnvPair]) -> None
    """Helper to modify a SimpleCommand node.

    Args:
      preparsed: a list of 4-tuples from DetectShAssignment
      more_env: a list to append env_pairs to
    """
    for left_token, _, part_offset, w in preparsed_list:
        if left_token.id != Id.Lit_VarLike:  # can't be a[x]=1
            p_die("Environment binding shouldn't look like an array assignment",
                  left_token)

        if lexer.IsPlusEquals(left_token):
            p_die('Expected = in environment binding, got +=', left_token)

        var_name = lexer.TokenSliceRight(left_token, -1)
        n = len(w.parts)
        if part_offset == n:
            val = rhs_word.Empty  # type: rhs_word_t
        else:
            val = CompoundWord(w.parts[part_offset:])

        pair = EnvPair(left_token, var_name, val)
        more_env.append(pair)


if TYPE_CHECKING:
    PreParsedItem = Tuple[Token, Optional[Token], int, CompoundWord]
    PreParsedList = List[PreParsedItem]


def _SplitSimpleCommandPrefix(words):
    # type: (List[CompoundWord]) -> Tuple[PreParsedList, List[CompoundWord]]
    """Second pass of SimpleCommand parsing: look for assignment words."""
    preparsed_list = []  # type: PreParsedList
    suffix_words = []  # type: List[CompoundWord]

    done_prefix = False
    for w in words:
        if done_prefix:
            suffix_words.append(w)
            continue

        left_token, close_token, part_offset = word_.DetectShAssignment(w)
        if left_token:
            preparsed_list.append((left_token, close_token, part_offset, w))
        else:
            done_prefix = True
            suffix_words.append(w)

    return preparsed_list, suffix_words


def _MakeSimpleCommand(
        preparsed_list,  # type: PreParsedList
        suffix_words,  # type: List[CompoundWord]
        redirects,  # type: List[Redir]
        typed_args,  # type: Optional[ArgList]
        block,  # type: Optional[BlockArg]
):
    # type: (...) -> command.Simple
    """Create an command.Simple node."""

    # FOO=(1 2 3) ls is not allowed.
    for _, _, _, w in preparsed_list:
        if word_.HasArrayPart(w):
            p_die("Environment bindings can't contain array literals",
                  loc.Word(w))

    # NOTE: It would be possible to add this check back.  But it already happens
    # at runtime in EvalWordSequence2.
    # echo FOO=(1 2 3) is not allowed (but we should NOT fail on echo FOO[x]=1).
    if 0:
        for w in suffix_words:
            if word_.HasArrayPart(w):
                p_die("Commands can't contain array literals", loc.Word(w))

    assert len(suffix_words) != 0
    # {a,b,c}   # Use { before brace detection
    # ~/bin/ls  # Use ~ before tilde detection
    part0 = suffix_words[0].parts[0]
    blame_tok = location.LeftTokenForWordPart(part0)

    # NOTE: We only do brace DETECTION here, not brace EXPANSION.  Therefore we
    # can't implement bash's behavior of having say {~bob,~jane}/src work,
    # because we only have a BracedTree.
    # This is documented in spec/brace-expansion.
    # NOTE: Technically we could do expansion outside of 'oshc translate', but it
    # doesn't seem worth it.
    words2 = braces.BraceDetectAll(suffix_words)
    words3 = word_.TildeDetectAll(words2)

    more_env = []  # type: List[EnvPair]
    _AppendMoreEnv(preparsed_list, more_env)

    # do_fork by default
    return command.Simple(blame_tok, more_env, words3, redirects, typed_args,
                          block, True)


class VarChecker(object):
    """Statically check for proc and variable usage errors."""

    def __init__(self):
        # type: () -> None
        """
    Args:
      oil_proc: Whether to disallow nested proc/function declarations
    """
        # self.tokens for location info: 'proc' or another token
        self.tokens = []  # type: List[Token]
        self.names = []  # type: List[Dict[str, Id_t]]

    def Push(self, blame_tok):
        # type: (Token) -> None
        """Bash allows this, but it's confusing because it's the same as two
        functions at the top level.

        f() {
          g() {
            echo 'top level function defined in another one'
          }
        }

        YSH disallows nested procs.
        """
        if len(self.tokens) != 0:
            if self.tokens[0].id == Id.KW_Proc or blame_tok.id == Id.KW_Proc:
                p_die("procs and shell functions can't be nested", blame_tok)

        self.tokens.append(blame_tok)
        entry = {}  # type: Dict[str, Id_t]
        self.names.append(entry)

    def Pop(self):
        # type: () -> None
        self.names.pop()
        self.tokens.pop()

    def Check(self, keyword_id, name_tok):
        # type: (Id_t, Token) -> None
        """Check for errors in declaration and mutation errors.

        var x, const x:
          x already declared
        setvar x:
          x is not declared
          x is constant
        setglobal x:
          No errors are possible; we would need all these many conditions to
          statically know the names:
          - no 'source'
          - shopt -u copy_env.
          - AND use lib has to be static
        setref x:
          Should only mutate out params

        Also should p(:out) declare 'out' as well as '__out'?  Then you can't have
        local variables with the same name.
        """
        # Don't check the global level!  Semantics are different here!
        if len(self.names) == 0:
            return

        top = self.names[-1]
        name = name_tok.tval
        if keyword_id in (Id.KW_Const, Id.KW_Var):
            if name in top:
                p_die('%r was already declared' % name, name_tok)
            else:
                top[name] = keyword_id

        if keyword_id == Id.KW_SetVar:
            if name not in top:
                p_die("%r hasn't been declared" % name, name_tok)

            if name in top and top[name] == Id.KW_Const:
                p_die("Can't modify constant %r" % name, name_tok)

        # TODO: setref should only mutate out params.


class ctx_VarChecker(object):

    def __init__(self, var_checker, blame_tok):
        # type: (VarChecker, Token) -> None
        var_checker.Push(blame_tok)
        self.var_checker = var_checker

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.var_checker.Pop()


class ctx_CmdMode(object):

    def __init__(self, cmd_parse, new_cmd_mode):
        # type: (CommandParser, cmd_mode_t) -> None
        self.cmd_parse = cmd_parse
        self.prev_cmd_mode = cmd_parse.cmd_mode
        cmd_parse.cmd_mode = new_cmd_mode

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.cmd_parse.cmd_mode = self.prev_cmd_mode



SECONDARY_KEYWORDS = [
    Id.KW_Do, Id.KW_Done, Id.KW_Then, Id.KW_Fi, Id.KW_Elif, Id.KW_Else,
    Id.KW_Esac
]


class CommandParser(object):
    """Recursive descent parser derived from POSIX shell grammar.

    This is a BNF grammar:
    https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_10

    - Augmented with both bash/OSH and YSH constructs.

    - We use regex-like iteration rather than recursive references
      ?  means  optional (0 or 1)
      *  means  0 or more
      +  means  1 or more

    - Keywords are spelled in Caps:
      If   Elif   Case

    - Operator tokens are quoted:
      '('   '|'

      or can be spelled directly if it matters:

      Op_LParen   Op_Pipe

    - Non-terminals are snake_case:
      brace_group   subshell

    Methods in this class should ROUGHLY CORRESPOND to grammar productions, and
    the production should be in the method docstrings, e.g.

    def ParseSubshell():
      "
      subshell : '(' compound_list ')'

      Looking at Op_LParen   # Comment to say how this method is called
      "

    The grammar may be factored to make parsing easier.
    """

    def __init__(self,
                 parse_ctx,
                 parse_opts,
                 w_parser,
                 lexer,
                 line_reader,
                 eof_id=Id.Eof_Real):
        # type: (ParseContext, optview.Parse, WordParser, Lexer, _Reader, Id_t) -> None
        self.parse_ctx = parse_ctx
        self.aliases = parse_ctx.aliases  # aliases to expand at parse time

        self.parse_opts = parse_opts
        self.w_parser = w_parser  # type: WordParser  # for normal parsing
        self.lexer = lexer  # for pushing hints, lookahead to (
        self.line_reader = line_reader  # for here docs
        self.eof_id = eof_id

        self.arena = line_reader.arena  # for adding here doc and alias spans
        self.aliases_in_flight = []  # type: AliasesInFlight

        # A hacky boolean to remove 'if cd / {' ambiguity.
        self.allow_block = True

        # Stack of booleans for nested SHELL and Attr nodes.  There are cleverer
        # encodings for this, like a uint64, and push 0b10 and 0b11.
        self.allow_block_attrs = []  # type: List[bool]

        # Note: VarChecker is instantiated with each CommandParser, which means
        # that two 'proc foo' -- inside a command sub and outside -- don't
        # conflict, because they use different CommandParser instances.  I think
        # this OK but you can imagine different behaviors.
        self.var_checker = VarChecker()

        self.cmd_mode = cmd_mode_e.Normal  # type: cmd_mode_t

        self.Reset()

    # Init_() function for "keyword arg"
    def Init_AliasesInFlight(self, aliases_in_flight):
        # type: (AliasesInFlight) -> None
        self.aliases_in_flight = aliases_in_flight

    def Reset(self):
        # type: () -> None
        """Reset our own internal state.

        Called by the interactive loop.
        """
        # Cursor state set by _GetWord()
        self.next_lex_mode = lex_mode_e.ShCommand
        self.cur_word = None  # type: word_t  # current word
        self.c_kind = Kind.Undefined
        self.c_id = Id.Undefined_Tok

        self.pending_here_docs = [
        ]  # type: List[Redir]  # should have HereLiteral arg

    def ResetInputObjects(self):
        # type: () -> None
        """Reset the internal state of our inputs.

        Called by the interactive loop.
        """
        self.w_parser.Reset()
        self.lexer.ResetInputObjects()
        self.line_reader.Reset()

    def _SetNext(self):
        # type: () -> None
        """Call this when you no longer need the current token.

        This method is lazy.  A subsequent call to _GetWord() will
        actually read the next Token.
        """
        self.next_lex_mode = lex_mode_e.ShCommand

    def _GetWord(self):
        # type: () -> None
        """Call this when you need to make a decision based on Id or Kind.

        If there was an "unfulfilled" call to _SetNext(), it reads a word and sets
        self.c_id and self.c_kind.

        Otherwise it does nothing.
        """
        if self.next_lex_mode != lex_mode_e.Undefined:
            w = self.w_parser.ReadWord(self.next_lex_mode)
            #log("w %s", w)

            # Here docs only happen in command mode, so other kinds of newlines don't
            # count.
            if w.tag() == word_e.Operator:
                tok = cast(Token, w)
                if tok.id == Id.Op_Newline:
                    for h in self.pending_here_docs:
                        _ParseHereDocBody(self.parse_ctx, h, self.line_reader,
                                          self.arena)
                    del self.pending_here_docs[:]  # No .clear() until Python 3.3.

            self.cur_word = w

            self.c_kind = word_.CommandKind(self.cur_word)
            self.c_id = word_.CommandId(self.cur_word)
            self.next_lex_mode = lex_mode_e.Undefined

    def _Eat(self, c_id, msg=None):
        # type: (Id_t, Optional[str]) -> word_t
        """Consume a word of a type, maybe showing a custom error message.

        Args:
          c_id: the Id we expected
          msg: improved error message
        """
        self._GetWord()
        if self.c_id != c_id:
            if msg is None:
                msg = 'Expected word type %s, got %s' % (ui.PrettyId(c_id),
                                                         ui.PrettyId(self.c_id))
            p_die(msg, loc.Word(self.cur_word))

        skipped = self.cur_word
        self._SetNext()
        return skipped

    def _NewlineOk(self):
        # type: () -> None
        """Check for optional newline and consume it."""
        self._GetWord()
        if self.c_id == Id.Op_Newline:
            self._SetNext()

    def _AtSecondaryKeyword(self):
        # type: () -> bool
        self._GetWord()
        if self.c_id in SECONDARY_KEYWORDS:
            return True
        return False

    def ParseRedirect(self):
        # type: () -> Redir
        self._GetWord()
        assert self.c_kind == Kind.Redir, self.cur_word
        op_tok = cast(Token, self.cur_word)  # for MyPy

        # Note: the lexer could take distinguish between
        #  >out
        #  3>out
        #  {fd}>out
        #
        # which would make the code below faster.  But small string optimization
        # would also speed it up, since redirects are small.

        op_val = lexer.TokenVal(op_tok)
        if op_val[0] == '{':
            pos = op_val.find('}')
            assert pos != -1  # lexer ensures this
            where = redir_loc.VarName(op_val[1:pos])  # type: redir_loc_t

        elif op_val[0].isdigit():
            pos = 1
            if op_val[1].isdigit():
                pos = 2
            where = redir_loc.Fd(int(op_val[:pos]))

        else:
            where = redir_loc.Fd(consts.RedirDefaultFd(op_tok.id))

        self._SetNext()

        self._GetWord()
        # Other redirect
        if self.c_kind != Kind.Word:
            p_die('Invalid token after redirect operator',
                  loc.Word(self.cur_word))

        # Here doc
        if op_tok.id in (Id.Redir_DLess, Id.Redir_DLessDash):
            arg = redir_param.HereDoc.CreateNull()
            arg.here_begin = self.cur_word
            arg.stdin_parts = []

            r = Redir(op_tok, where, arg)

            self.pending_here_docs.append(r)  # will be filled on next newline.

            self._SetNext()
            return r

        arg_word = self.cur_word
        tilde = word_.TildeDetect(arg_word)
        if tilde:
            arg_word = tilde
        self._SetNext()

        # We should never get Empty, Token, etc.
        assert arg_word.tag() == word_e.Compound, arg_word
        return Redir(op_tok, where, cast(CompoundWord, arg_word))

    def _ParseRedirectList(self):
        # type: () -> List[Redir]
        """Try parsing any redirects at the cursor.

        This is used for blocks only, not commands.
        """
        redirects = []  # type: List[Redir]
        while True:
            # This prediction needs to ONLY accept redirect operators.  Should we
            # make them a separate Kind?
            self._GetWord()
            if self.c_kind != Kind.Redir:
                break

            node = self.ParseRedirect()
            redirects.append(node)
            self._SetNext()

        return redirects

    def _ScanSimpleCommand(self):
        # type: () -> Tuple[List[Redir], List[CompoundWord], Optional[ArgList], Optional[BlockArg]]
        """First pass: Split into redirects and words."""
        redirects = []  # type: List[Redir]
        words = []  # type: List[CompoundWord]
        typed_args = None  # type: Optional[ArgList]
        block = None  # type: Optional[BlockArg]

        first_word_caps = False  # does first word look like Caps, but not CAPS

        i = 0
        while True:
            self._GetWord()
            if self.c_kind == Kind.Redir:
                node = self.ParseRedirect()
                redirects.append(node)

            elif self.c_kind == Kind.Word:
                if self.parse_opts.parse_brace():
                    # Treat { and } more like operators
                    if self.c_id == Id.Lit_LBrace:
                        if self.allow_block:  # Disabled for if/while condition, etc.

                            # allow x = 42
                            self.allow_block_attrs.append(first_word_caps)
                            brace_group = self.ParseBraceGroup()

                            # So we can get the source code back later
                            lines = self.arena.SaveLinesAndDiscard(
                                brace_group.left, brace_group.right)
                            block = BlockArg(brace_group, lines)

                            self.allow_block_attrs.pop()

                        if 0:
                            print('--')
                            block.PrettyPrint()
                            print('\n--')
                        break
                    elif self.c_id == Id.Lit_RBrace:
                        # Another thing: { echo hi }
                        # We're DONE!!!
                        break

                w = cast(CompoundWord, self.cur_word)  # Kind.Word ensures this
                words.append(w)
                if i == 0:
                    ok, word_str, quoted = word_.StaticEval(w)
                    # Foo { a = 1 } is OK, but not foo { a = 1 } or FOO { a = 1 }
                    if (ok and len(word_str) and word_str[0].isupper() and
                            not word_str.isupper()):
                        first_word_caps = True
                        #log('W %s', word_str)

            elif self.c_id == Id.Op_LParen:
                # 1. Check that there's a preceding space
                prev_byte = self.lexer.ByteLookBack()
                if prev_byte not in (SPACE_CH, TAB_CH):
                    if self.parse_opts.parse_at():
                        p_die('Space required before (',
                              loc.Word(self.cur_word))
                    else:
                        # inline func call like @sorted(x) is invalid in OSH, but the
                        # solution isn't a space
                        p_die(
                            'Unexpected left paren (might need a space before it)',
                            loc.Word(self.cur_word))

                # 2. Check that it's not ().  We disallow this because it's a no-op and
                #    there could be confusion with shell func defs.
                # For some reason we need to call lexer.LookPastSpace, not
                # w_parser.LookPastSpace.  I think this is because we're at (, which is
                # an operator token.  All the other cases are like 'x=', which is PART
                # of a word, and we don't know if it will end.
                next_id = self.lexer.LookPastSpace(lex_mode_e.ShCommand)
                if next_id == Id.Op_RParen:
                    p_die('Empty arg list not allowed', loc.Word(self.cur_word))

                typed_args = self.w_parser.ParseProcCallArgs()

            else:
                break

            self._SetNext()
            i += 1
        return redirects, words, typed_args, block

    def _MaybeExpandAliases(self, words):
        # type: (List[CompoundWord]) -> Optional[command_t]
        """Try to expand aliases.

        Args:
          words: A list of Compound

        Returns:
          A new LST node, or None.

        Our implementation of alias has two design choices:
        - Where to insert it in parsing.  We do it at the end of ParseSimpleCommand.
        - What grammar rule to parse the expanded alias buffer with.  In our case
          it's ParseCommand().

        This doesn't quite match what other shells do, but I can't figure out a
        better places.

        Most test cases pass, except for ones like:

        alias LBRACE='{'
        LBRACE echo one; echo two; }

        alias MULTILINE='echo 1
        echo 2
        echo 3'
        MULTILINE

        NOTE: dash handles aliases in a totally different way.  It has a global
        variable checkkwd in parser.c.  It assigns it all over the grammar, like
        this:

        checkkwd = CHKNL | CHKKWD | CHKALIAS;

        The readtoken() function checks (checkkwd & CHKALIAS) and then calls
        lookupalias().  This seems to provide a consistent behavior among shells,
        but it's less modular and testable.

        Bash also uses a global 'parser_state & PST_ALEXPNEXT'.

        Returns:
          A command node if any aliases were expanded, or None otherwise.
        """
        # Start a new list if there aren't any.  This will be passed recursively
        # through CommandParser instances.
        aliases_in_flight = (self.aliases_in_flight
                             if len(self.aliases_in_flight) else [])

        # for error message
        first_word_str = None  # type: Optional[str]
        argv0_loc = loc.Word(words[0])

        expanded = []  # type: List[str]
        i = 0
        n = len(words)

        while i < n:
            w = words[i]

            ok, word_str, quoted = word_.StaticEval(w)
            if not ok or quoted:
                break

            alias_exp = self.aliases.get(word_str)
            if alias_exp is None:
                break

            # Prevent infinite loops.  This is subtle: we want to prevent infinite
            # expansion of alias echo='echo x'.  But we don't want to prevent
            # expansion of the second word in 'echo echo', so we add 'i' to
            # "aliases_in_flight".
            if (word_str, i) in aliases_in_flight:
                break

            if i == 0:
                first_word_str = word_str  # for error message

            #log('%r -> %r', word_str, alias_exp)
            aliases_in_flight.append((word_str, i))
            expanded.append(alias_exp)
            i += 1

            if not alias_exp.endswith(' '):
                # alias e='echo [ ' is the same expansion as
                # alias e='echo ['
                # The trailing space indicates whether we should continue to expand
                # aliases; it's not part of it.
                expanded.append(' ')
                break  # No more expansions

        if len(expanded) == 0:  # No expansions; caller does parsing.
            return None

        # We are expanding an alias, so copy the rest of the words and re-parse.
        if i < n:
            left_tok = location.LeftTokenForWord(words[i])
            right_tok = location.RightTokenForWord(words[-1])

            # OLD CONSTRAINT
            #assert left_tok.line_id == right_tok.line_id

            words_str = self.arena.SnipCodeString(left_tok, right_tok)
            expanded.append(words_str)

        code_str = ''.join(expanded)

        # TODO:
        # Aliases break static parsing (like backticks), so use our own Arena.
        # This matters for Hay, which calls SaveLinesAndDiscard().
        # arena = alloc.Arena()
        arena = self.arena

        line_reader = reader.StringLineReader(code_str, arena)
        cp = self.parse_ctx.MakeOshParser(line_reader)
        cp.Init_AliasesInFlight(aliases_in_flight)

        # break circular dep
        from frontend import parse_lib

        # The interaction between COMPLETION and ALIASES requires special care.
        # See docstring of BeginAliasExpansion() in parse_lib.py.
        src = source.Alias(first_word_str, argv0_loc)
        with alloc.ctx_Location(arena, src):
            with parse_lib.ctx_Alias(self.parse_ctx.trail):
                try:
                    # _ParseCommandTerm() handles multiline commands, compound commands, etc.
                    # as opposed to ParseLogicalLine()
                    node = cp._ParseCommandTerm()
                except error.Parse as e:
                    # Failure to parse alias expansion is a fatal error
                    # We don't need more handling here/
                    raise

        if 0:
            log('AFTER expansion:')
            node.PrettyPrint()

        return node

    def ParseSimpleCommand(self):
        # type: () -> command_t
        """Fixed transcription of the POSIX grammar (TODO: port to
        grammar/Shell.g)

        io_file        : '<'       filename
                       | LESSAND   filename
                         ...

        io_here        : DLESS     here_end
                       | DLESSDASH here_end

        redirect       : IO_NUMBER (io_redirect | io_here)

        prefix_part    : ASSIGNMENT_WORD | redirect
        cmd_part       : WORD | redirect

        assign_kw      : Declare | Export | Local | Readonly

        # Without any words it is parsed as a command, not an assignment
        assign_listing : assign_kw

        # Now we have something to do (might be changing assignment flags too)
        # NOTE: any prefixes should be a warning, but they are allowed in shell.
        assignment     : prefix_part* assign_kw (WORD | ASSIGNMENT_WORD)+

        # an external command, a function call, or a builtin -- a "word_command"
        word_command   : prefix_part* cmd_part+

        simple_command : assign_listing
                       | assignment
                       | proc_command

        Simple imperative algorithm:

        1) Read a list of words and redirects.  Append them to separate lists.
        2) Look for the first non-assignment word.  If it's declare, etc., then
        keep parsing words AND assign words.  Otherwise, just parse words.
        3) If there are no non-assignment words, then it's a global assignment.

        { redirects, global assignments } OR
        { redirects, prefix_bindings, words } OR
        { redirects, ERROR_prefix_bindings, keyword, assignments, words }

        THEN CHECK that prefix bindings don't have any array literal parts!
        global assignment and keyword assignments can have the of course.
        well actually EXPORT shouldn't have them either -- WARNING

        3 cases we want to warn: prefix_bindings for assignment, and array literal
        in prefix bindings, or export

        A command can be an assignment word, word, or redirect on its own.

            ls
            >out.txt

            >out.txt FOO=bar   # this touches the file

        Or any sequence:
            ls foo bar
            <in.txt ls foo bar >out.txt
            <in.txt ls >out.txt foo bar

        Or add one or more environment bindings:
            VAR=val env
            >out.txt VAR=val env

        here_end vs filename is a matter of whether we test that it's quoted.  e.g.
        <<EOF vs <<'EOF'.
        """
        redirects, words, typed_args, block = self._ScanSimpleCommand()

        typed_loc = None  # type: Optional[Token]
        if block:
            typed_loc = block.brace_group.left
        if typed_args:
            typed_loc = typed_args.left  # preferred over block location

        if len(words) == 0:  # e.g.  >out.txt  # redirect without words
            assert len(redirects) != 0
            if typed_loc is not None:
                p_die("Unexpected typed args", typed_loc)

            simple = command.Simple.CreateNull()
            simple.blame_tok = redirects[0].op
            simple.more_env = []
            simple.words = []
            simple.redirects = redirects
            return simple

        # Disallow =a because it's confusing
        part0 = words[0].parts[0]
        if part0.tag() == word_part_e.Literal:
            tok = cast(Token, part0)
            if tok.id == Id.Lit_Equals:
                p_die(
                    "=word isn't allowed.  Hint: either quote it or add a space after =\n"
                    "to pretty print an expression", tok)

        preparsed_list, suffix_words = _SplitSimpleCommandPrefix(words)
        if len(preparsed_list):
            left_token, _, _, _ = preparsed_list[0]

            # Disallow X=Y when setvar X = 'Y' is idiomatic.  (Space sensitivity is bad.)
            if not self.parse_opts.parse_sh_assign() and len(suffix_words) == 0:
                p_die(
                    'Use const or var/setvar to assign in YSH (parse_sh_assign)',
                    left_token)

        # Set a reference to words and redirects for completion.  We want to
        # inspect this state after a failed parse.
        self.parse_ctx.trail.SetLatestWords(suffix_words, redirects)

        if len(suffix_words) == 0:
            if typed_loc is not None:
                p_die("Unexpected typed args", typed_loc)

            # ShAssignment: No suffix words like ONE=1 a[x]=1 TWO=2
            pairs = []  # type: List[AssignPair]
            for preparsed in preparsed_list:
                pairs.append(
                    _MakeAssignPair(self.parse_ctx, preparsed, self.arena))

            left_tok = location.LeftTokenForCompoundWord(words[0])
            return command.ShAssignment(left_tok, pairs, redirects)

        kind, kw_token = word_.IsControlFlow(suffix_words[0])

        if (typed_args is not None and kw_token is not None and
                kw_token.id == Id.ControlFlow_Return):
            # typed return (this is special from the other control flow types)
            if self.cmd_mode != cmd_mode_e.Func:
                p_die("Unexpected typed return outside of a func",
                      typed_loc)
            if len(typed_args.positional) != 1:
                p_die("Expected one argument passed to a typed return",
                      typed_loc)
            if len(typed_args.named) != 0:
                p_die("Expected no named arguments passed to a typed return",
                      typed_loc)
            return command.Retval(kw_token, typed_args.positional[0])

        if kind == Kind.ControlFlow:
            if typed_loc is not None:
                p_die("Unexpected typed args", typed_loc)
            if not self.parse_opts.parse_ignored() and len(redirects):
                p_die("Control flow shouldn't have redirects", kw_token)

            if len(preparsed_list):  # FOO=bar local spam=eggs not allowed
                # TODO: Change location as above
                left_token, _, _, _ = preparsed_list[0]
                p_die("Control flow shouldn't have environment bindings",
                      left_token)

            # Attach the token for errors.  (ShAssignment may not need it.)
            if len(suffix_words) == 1:
                arg_word = None  # type: Optional[word_t]
            elif len(suffix_words) == 2:
                arg_word = suffix_words[1]
            else:
                p_die('Unexpected argument to %r' % lexer.TokenVal(kw_token),
                      loc.Word(suffix_words[2]))

            if (kw_token.id == Id.ControlFlow_Return and
                    self.cmd_mode == cmd_mode_e.Func):
                p_die("Unexpected shell_style return inside a func", kw_token)

            return command.ControlFlow(kw_token, arg_word)

        # Alias expansion only understands words, not typed args ( ) or block { }
        if not typed_args and not block and self.parse_opts.expand_aliases():
            # If any expansions were detected, then parse again.
            expanded_node = self._MaybeExpandAliases(suffix_words)
            if expanded_node:
                # Attach env bindings and redirects to the expanded node.
                more_env = []  # type: List[EnvPair]
                _AppendMoreEnv(preparsed_list, more_env)
                exp = command.ExpandedAlias(expanded_node, redirects, more_env)
                return exp

        # TODO: check that we don't have env1=x x[1]=y env2=z here.

        # FOO=bar printenv.py FOO
        node = _MakeSimpleCommand(preparsed_list, suffix_words, redirects,
                                  typed_args, block)
        return node

    def ParseBraceGroup(self):
        # type: () -> BraceGroup
        """
        Original:
          brace_group : LBrace command_list RBrace ;

        YSH:
          brace_group : LBrace (Op_Newline IgnoredComment?)? command_list RBrace ;

        The doc comment can only occur if there's a newline.
        """
        ate = self._Eat(Id.Lit_LBrace)
        left = word_.BraceToken(ate)

        doc_token = None  # type: Token
        self._GetWord()
        if self.c_id == Id.Op_Newline:
            self._SetNext()
            with word_.ctx_EmitDocToken(self.w_parser):
                self._GetWord()

        if self.c_id == Id.Ignored_Comment:
            doc_token = cast(Token, self.cur_word)
            self._SetNext()

        c_list = self._ParseCommandList()

        ate = self._Eat(Id.Lit_RBrace)
        right = word_.BraceToken(ate)

        # Note(andychu): Related ASDL bug #1216.  Choosing the Python [] behavior
        # would allow us to revert this back to None, which was changed in
        # https://github.com/oilshell/oil/pull/1211.  Choosing the C++ nullptr
        # behavior saves allocations, but is less type safe.
        return BraceGroup(left, doc_token, c_list.children, [],
                          right)  # no redirects yet

    def ParseDoGroup(self):
        # type: () -> command.DoGroup
        """Used by ForEach, ForExpr, While, Until.  Should this be a Do node?

        do_group         : Do command_list Done ;          /* Apply rule 6 */
        """
        ate = self._Eat(Id.KW_Do)
        do_kw = word_.AsKeywordToken(ate)

        c_list = self._ParseCommandList()  # could be anything

        ate = self._Eat(Id.KW_Done)
        done_kw = word_.AsKeywordToken(ate)

        return command.DoGroup(do_kw, c_list.children, done_kw)

    def ParseForWords(self):
        # type: () -> Tuple[List[CompoundWord], Optional[Token]]
        """
        for_words        : WORD* for_sep
                         ;
        for_sep          : ';' newline_ok
                         | NEWLINES
                         ;
        """
        words = []  # type: List[CompoundWord]
        # The span_id of any semi-colon, so we can remove it.
        semi_tok = None  # type: Optional[Token]

        while True:
            self._GetWord()
            if self.c_id == Id.Op_Semi:
                tok = cast(Token, self.cur_word)
                semi_tok = tok
                self._SetNext()
                self._NewlineOk()
                break
            elif self.c_id == Id.Op_Newline:
                self._SetNext()
                break
            elif self.parse_opts.parse_brace() and self.c_id == Id.Lit_LBrace:
                break

            if self.cur_word.tag() != word_e.Compound:
                # TODO: Can we also show a pointer to the 'for' keyword?
                p_die('Invalid word in for loop', loc.Word(self.cur_word))

            w2 = cast(CompoundWord, self.cur_word)
            words.append(w2)
            self._SetNext()
        return words, semi_tok

    def _ParseForExprLoop(self, for_kw):
        # type: (Token) -> command.ForExpr
        """
        Shell:
          for '((' init ';' cond ';' update '))' for_sep? do_group

        YSH:
          for '((' init ';' cond ';' update '))' for_sep? brace_group
        """
        node = self.w_parser.ReadForExpression()
        node.keyword = for_kw

        self._SetNext()

        self._GetWord()
        if self.c_id == Id.Op_Semi:
            self._SetNext()
            self._NewlineOk()
        elif self.c_id == Id.Op_Newline:
            self._SetNext()
        elif self.c_id == Id.KW_Do:  # missing semicolon/newline allowed
            pass
        elif self.c_id == Id.Lit_LBrace:  # does NOT require parse_brace
            pass
        else:
            p_die('Invalid word after for expression', loc.Word(self.cur_word))

        if self.c_id == Id.Lit_LBrace:
            node.body = self.ParseBraceGroup()
        else:
            node.body = self.ParseDoGroup()
        return node

    def _ParseForEachLoop(self, for_kw):
        # type: (Token) -> command.ForEach
        node = command.ForEach.CreateNull(alloc_lists=True)
        node.keyword = for_kw

        num_iter_names = 0
        while True:
            w = self.cur_word

            # Hack that makes the language more familiar:
            # - 'x, y' is accepted, but not 'x,y' or 'x ,y'
            # - 'x y' is also accepted but not idiomatic.
            UP_w = w
            if w.tag() == word_e.Compound:
                w = cast(CompoundWord, UP_w)
                if word_.LiteralId(w.parts[-1]) == Id.Lit_Comma:
                    w.parts.pop()

            ok, iter_name, quoted = word_.StaticEval(w)
            if not ok or quoted:  # error: for $x
                p_die('Expected loop variable (a constant word)', loc.Word(w))

            if not match.IsValidVarName(iter_name):  # error: for -
                # TODO: consider commas?
                if ',' in iter_name:
                    p_die('Loop variables look like x, y (fix spaces)',
                          loc.Word(w))
                p_die('Invalid loop variable name %r' % iter_name, loc.Word(w))

            node.iter_names.append(iter_name)
            num_iter_names += 1
            self._SetNext()

            self._GetWord()
            # 'in' or 'do' or ';' or Op_Newline marks the end of variable names
            # Subtlety: 'var' is KW_Var and is a valid loop name
            if self.c_id in (Id.KW_In, Id.KW_Do) or self.c_kind == Kind.Op:
                break

            if num_iter_names == 3:
                p_die('Unexpected word after 3 loop variables',
                      loc.Word(self.cur_word))

        self._NewlineOk()

        self._GetWord()
        if self.c_id == Id.KW_In:

            self._SetNext()  # skip in
            if self.w_parser.LookPastSpace() == Id.Op_LParen:
                enode, last_token = self.parse_ctx.ParseYshExpr(
                    self.lexer, grammar_nt.oil_expr)
                node.iterable = for_iter.YshExpr(enode, last_token)

                # For simplicity, we don't accept for x in (obj); do ...
                self._GetWord()
                if self.c_id != Id.Lit_LBrace:
                    p_die('Expected { after iterable expression',
                          loc.Word(self.cur_word))
            else:
                semi_tok = None  # type: Optional[Token]
                iter_words, semi_tok = self.ParseForWords()
                node.semi_tok = semi_tok

                if not self.parse_opts.parse_bare_word() and len(
                        iter_words) == 1:
                    ok, s, quoted = word_.StaticEval(iter_words[0])
                    if ok and match.IsValidVarName(s) and not quoted:
                        p_die(
                            'Surround this word with either parens or quotes (parse_bare_word)',
                            loc.Word(iter_words[0]))

                words2 = braces.BraceDetectAll(iter_words)
                words3 = word_.TildeDetectAll(words2)
                node.iterable = for_iter.Words(words3)

                # Now that we know there are words, do an extra check
                if num_iter_names > 2:
                    p_die('Expected at most 2 loop variables', for_kw)

        elif self.c_id == Id.KW_Do:
            node.iterable = for_iter.Args  # implicitly loop over "$@"
            # do not advance

        elif self.c_id == Id.Op_Semi:  # for x; do
            node.iterable = for_iter.Args  # implicitly loop over "$@"
            self._SetNext()

        else:  # for foo BAD
            p_die('Unexpected word after for loop variable',
                  loc.Word(self.cur_word))

        self._GetWord()
        if self.c_id == Id.Lit_LBrace:  # parse_opts.parse_brace() must be on
            node.body = self.ParseBraceGroup()
        else:
            node.body = self.ParseDoGroup()

        return node

    def ParseFor(self):
        # type: () -> command_t
        """
        TODO: Update the grammar

        for_clause : For for_name newline_ok (in for_words? for_sep)? do_group ;
                   | For '((' ... TODO
        """
        ate = self._Eat(Id.KW_For)
        for_kw = word_.AsKeywordToken(ate)

        self._GetWord()
        if self.c_id == Id.Op_DLeftParen:
            if not self.parse_opts.parse_dparen():
                p_die("Bash for loops aren't allowed (parse_dparen)",
                      loc.Word(self.cur_word))

            # for (( i = 0; i < 10; i++)
            n1 = self._ParseForExprLoop(for_kw)
            n1.redirects = self._ParseRedirectList()
            return n1
        else:
            # for x in a b; do echo hi; done
            n2 = self._ParseForEachLoop(for_kw)
            n2.redirects = self._ParseRedirectList()
            return n2

    def _ParseConditionList(self):
        # type: () -> condition_t
        """
        condition_list: command_list

        This is a helper to parse a condition list for if commands and while/until
        loops. It will throw a parse error if there are no conditions in the list.
        """
        self.allow_block = False
        commands = self._ParseCommandList()
        self.allow_block = True

        if len(commands.children) == 0:
            p_die("Expected a condition", loc.Word(self.cur_word))

        return condition.Shell(commands.children)

    def ParseWhileUntil(self, keyword):
        # type: (Token) -> command.WhileUntil
        """
        while_clause     : While command_list do_group ;
        until_clause     : Until command_list do_group ;
        """
        self._SetNext()  # skip keyword

        if self.parse_opts.parse_paren() and self.w_parser.LookPastSpace(
        ) == Id.Op_LParen:
            enode, _ = self.parse_ctx.ParseYshExpr(self.lexer,
                                                   grammar_nt.oil_expr)
            cond = condition.YshExpr(enode)  # type: condition_t
        else:
            cond = self._ParseConditionList()

        # NOTE: The LSTs will be different for OSH and YSH, but the execution
        # should be unchanged.  To be sure we should desugar.
        self._GetWord()
        if self.parse_opts.parse_brace() and self.c_id == Id.Lit_LBrace:
            # while test -f foo {
            body_node = self.ParseBraceGroup()  # type: command_t
        else:
            body_node = self.ParseDoGroup()

        # no redirects yet
        return command.WhileUntil(keyword, cond, body_node, None)

    def ParseCaseArm(self):
        # type: () -> CaseArm
        """
        case_item: '('? pattern ('|' pattern)* ')'
                   newline_ok command_term? trailer? ;

        Looking at '(' or pattern
        """
        self.lexer.PushHint(Id.Op_RParen, Id.Right_CasePat)

        left_tok = location.LeftTokenForWord(self.cur_word)  # ( or pat

        if self.c_id == Id.Op_LParen:  # Optional (
            self._SetNext()

        pat_words = []  # type: List[word_t]
        while True:
            self._GetWord()
            if self.c_kind != Kind.Word:
                p_die('Expected case pattern', loc.Word(self.cur_word))
            pat_words.append(self.cur_word)
            self._SetNext()

            self._GetWord()
            if self.c_id == Id.Op_Pipe:
                self._SetNext()
            else:
                break

        ate = self._Eat(Id.Right_CasePat)
        middle_tok = word_.AsOperatorToken(ate)

        self._NewlineOk()

        self._GetWord()
        if self.c_id not in (Id.Op_DSemi, Id.KW_Esac):
            c_list = self._ParseCommandTerm()
            action_children = c_list.children
        else:
            action_children = []

        dsemi_tok = None  # type: Token
        self._GetWord()
        if self.c_id == Id.KW_Esac:  # missing last ;;
            pass
        elif self.c_id == Id.Op_DSemi:
            dsemi_tok = word_.AsOperatorToken(self.cur_word)
            self._SetNext()
        else:
            # Happens on EOF
            p_die('Expected ;; or esac', loc.Word(self.cur_word))

        self._NewlineOk()

        return CaseArm(left_tok, pat.Words(pat_words), middle_tok,
                       action_children, dsemi_tok)

    def ParseYshCaseArm(self, discriminant):
        # type: (Id_t) -> CaseArm
        """
        case_item   : pattern newline_ok brace_group newline_ok
        pattern     : pat_words
                    | pat_exprs
                    | pat_eggex
                    | pat_else
        pat_words   : pat_word (newline_ok '|' newline_ok pat_word)*
        pat_exprs   : pat_expr (newline_ok '|' newline_ok pat_expr)*
        pat_word    : WORD
        pat_eggex   : '/' oil_eggex '/'
        pat_expr    : '(' oil_expr ')'
        pat_else    : '(' Id.KW_Else ')'

        Looking at: 'pattern'

        Note that the trailing `newline_ok` in `case_item` is handled by
        `ParseYshCase`. We do this because parsing that `newline_ok` returns
        the next "discriminant" for the next token, so it makes more sense to
        handle it there.
        """
        left_tok = None  # type: Token
        pattern = None  # type: pat_t

        if discriminant in (Id.Op_LParen, Id.Arith_Slash):
            # pat_exprs, pat_else or pat_eggex
            pattern, left_tok = self.w_parser.ParseYshCasePattern()
        else:
            # pat_words
            pat_words = []  # type: List[word_t]
            while True:
                self._GetWord()
                if self.c_kind != Kind.Word:
                    p_die('Expected case pattern', loc.Word(self.cur_word))
                pat_words.append(self.cur_word)
                self._SetNext()

                if not left_tok:
                    left_tok = location.LeftTokenForWord(self.cur_word)

                self._NewlineOk()

                self._GetWord()
                if self.c_id == Id.Op_Pipe:
                    self._SetNext()
                    self._NewlineOk()
                else:
                    break
            pattern = pat.Words(pat_words)

        self._NewlineOk()
        action = self.ParseBraceGroup()

        # The left token of the action is our "middle" token
        return CaseArm(left_tok, pattern, action.left, action.children,
                       action.right)

    def ParseYshCase(self, case_kw):
        # type: (Token) -> command.Case
        """
        ysh_case : Case '(' expr ')' LBrace newline_ok ysh_case_arm* RBrace ;

        Looking at: token after 'case'
        """
        enode, _ = self.parse_ctx.ParseYshExpr(self.lexer, grammar_nt.oil_expr)
        to_match = case_arg.YshExpr(enode)

        ate = self._Eat(Id.Lit_LBrace)
        arms_start = word_.BraceToken(ate)

        discriminant = self.w_parser.NewlineOkForYshCase()

        # Note: for now, zero arms are accepted, just like POSIX case $x in esac
        arms = []  # type: List[CaseArm]
        while discriminant != Id.Op_RBrace:
            arm = self.ParseYshCaseArm(discriminant)
            arms.append(arm)

            discriminant = self.w_parser.NewlineOkForYshCase()

        # NewlineOkForYshCase leaves the lexer in lex_mode_e.Expr. So the '}'
        # token is read as an Id.Op_RBrace, but we need to store this as a
        # Id.Lit_RBrace.
        ate = self._Eat(Id.Op_RBrace)
        arms_end = word_.AsOperatorToken(ate)
        arms_end.id = Id.Lit_RBrace

        return command.Case(case_kw, to_match, arms_start, arms, arms_end, None)

    def ParseOldCase(self, case_kw):
        # type: (Token) -> command.Case
        """
        case_clause : Case WORD newline_ok In newline_ok case_arm* Esac ;

        -> Looking at WORD

        FYI original POSIX case list, which takes pains for DSEMI

        case_list: case_item (DSEMI newline_ok case_item)* DSEMI? newline_ok;
        """
        self._GetWord()
        w = self.cur_word
        if not self.parse_opts.parse_bare_word():
            ok, s, quoted = word_.StaticEval(w)
            if ok and not quoted:
                p_die(
                    "This is a constant string.  You may want a variable like $x (parse_bare_word)",
                    loc.Word(w))

        if w.tag() != word_e.Compound:
            p_die("Expected a word to match against", loc.Word(w))

        to_match = case_arg.Word(w)
        self._SetNext()  # past WORD

        self._NewlineOk()

        ate = self._Eat(Id.KW_In)
        arms_start = word_.AsKeywordToken(ate)

        self._NewlineOk()

        arms = []  # type: List[CaseArm]
        while True:
            self._GetWord()
            if self.c_id == Id.KW_Esac:  # this is Kind.Word
                break
            # case arm should begin with a pattern word or (
            if self.c_kind != Kind.Word and self.c_id != Id.Op_LParen:
                break

            arm = self.ParseCaseArm()
            arms.append(arm)

        ate = self._Eat(Id.KW_Esac)
        arms_end = word_.AsKeywordToken(ate)

        # no redirects yet
        return command.Case(case_kw, to_match, arms_start, arms, arms_end, None)

    def ParseCase(self):
        # type: () -> command.Case
        """
        case_clause : old_case  # from POSIX
                    | ysh_case
                    ;

        Looking at 'Case'
        """
        case_kw = word_.AsKeywordToken(self.cur_word)
        self._SetNext()  # past 'case'

        if self.w_parser.LookPastSpace() == Id.Op_LParen:
            return self.ParseYshCase(case_kw)
        else:
            return self.ParseOldCase(case_kw)

    def _ParseYshElifElse(self, if_node):
        # type: (command.If) -> None
        """If test -f foo { echo foo.

        } elif test -f bar; test -f spam { ^ we parsed up to here   echo
        bar } else {   echo none }
        """
        arms = if_node.arms

        while self.c_id == Id.KW_Elif:
            elif_kw = word_.AsKeywordToken(self.cur_word)
            self._SetNext()  # skip elif
            if (self.parse_opts.parse_paren() and
                    self.w_parser.LookPastSpace() == Id.Op_LParen):
                enode, _ = self.parse_ctx.ParseYshExpr(self.lexer,
                                                       grammar_nt.oil_expr)
                cond = condition.YshExpr(enode)  # type: condition_t
            else:
                self.allow_block = False
                commands = self._ParseCommandList()
                self.allow_block = True
                cond = condition.Shell(commands.children)

            body = self.ParseBraceGroup()
            self._GetWord()

            arm = IfArm(elif_kw, cond, None, body.children, [elif_kw.span_id])
            arms.append(arm)

        self._GetWord()
        if self.c_id == Id.KW_Else:
            self._SetNext()
            body = self.ParseBraceGroup()
            if_node.else_action = body.children

    def _ParseYshIf(self, if_kw, cond):
        # type: (Token, condition_t) -> command.If
        """if test -f foo {

                     # ^ we parsed up to here
          echo foo
        } elif test -f bar; test -f spam {
          echo bar
        } else {
          echo none
        }
        NOTE: If you do something like if test -n foo{, the parser keeps going, and
        the error is confusing because it doesn't point to the right place.

        I think we might need strict_brace so that foo{ is disallowed.  It has to
        be foo\{ or foo{a,b}.  Or just turn that on with parse_brace?  After you
        form ANY CompoundWord, make sure it's balanced for Lit_LBrace and
        Lit_RBrace?  Maybe this is pre-parsing step in the WordParser?
        """
        if_node = command.If.CreateNull(alloc_lists=True)
        if_node.if_kw = if_kw

        body1 = self.ParseBraceGroup()
        # Every arm has 1 spid, unlike shell-style
        # TODO: We could get the spids from the brace group.
        arm = IfArm(if_kw, cond, None, body1.children, [if_kw.span_id])

        if_node.arms.append(arm)

        self._GetWord()
        if self.c_id in (Id.KW_Elif, Id.KW_Else):
            self._ParseYshElifElse(if_node)
        # the whole if node has the 'else' spid, unlike shell-style there's no 'fi'
        # spid because that's in the BraceGroup.
        return if_node

    def _ParseElifElse(self, if_node):
        # type: (command.If) -> None
        """
        else_part: (Elif command_list Then command_list)* Else command_list ;
        """
        arms = if_node.arms

        self._GetWord()
        while self.c_id == Id.KW_Elif:
            elif_kw = word_.AsKeywordToken(self.cur_word)
            self._SetNext()  # past 'elif'

            cond = self._ParseConditionList()

            ate = self._Eat(Id.KW_Then)
            then_kw = word_.AsKeywordToken(ate)

            body = self._ParseCommandList()
            arm = IfArm(elif_kw, cond, then_kw, body.children,
                        [elif_kw.span_id, then_kw.span_id])

            arms.append(arm)

        self._GetWord()
        if self.c_id == Id.KW_Else:
            else_kw = word_.AsKeywordToken(self.cur_word)
            self._SetNext()  # past 'else'
            body = self._ParseCommandList()
            if_node.else_action = body.children
        else:
            else_kw = None

        if_node.else_kw = else_kw

    def ParseIf(self):
        # type: () -> command.If
        """
        if_clause : If command_list Then command_list else_part? Fi ;

        open      : '{' | Then
        close     : '}' | Fi

        ysh_if    : If ( command_list | '(' expr ')' )
                    open command_list else_part? close;

        There are 2 conditionals here: parse_paren, then parse_brace
        """
        if_node = command.If.CreateNull(alloc_lists=True)
        if_kw = word_.AsKeywordToken(self.cur_word)
        if_node.if_kw = if_kw
        self._SetNext()  # past 'if'

        if self.parse_opts.parse_paren() and self.w_parser.LookPastSpace(
        ) == Id.Op_LParen:
            # if (x + 1)
            enode, _ = self.parse_ctx.ParseYshExpr(self.lexer,
                                                   grammar_nt.oil_expr)
            cond = condition.YshExpr(enode)  # type: condition_t
        else:
            # if echo 1; echo 2; then
            # Remove ambiguity with if cd / {
            cond = self._ParseConditionList()

        self._GetWord()
        if self.parse_opts.parse_brace() and self.c_id == Id.Lit_LBrace:
            return self._ParseYshIf(if_kw, cond)

        ate = self._Eat(Id.KW_Then)
        then_kw = word_.AsKeywordToken(ate)

        body = self._ParseCommandList()

        # First arm
        arm = IfArm(if_kw, cond, then_kw, body.children,
                    [if_kw.span_id, then_kw.span_id])
        if_node.arms.append(arm)

        # 2nd to Nth arm
        if self.c_id in (Id.KW_Elif, Id.KW_Else):
            self._ParseElifElse(if_node)

        ate = self._Eat(Id.KW_Fi)
        if_node.fi_kw = word_.AsKeywordToken(ate)

        return if_node

    def ParseTime(self):
        # type: () -> command_t
        """Time [-p] pipeline.

        According to bash help.
        """
        time_kw = word_.AsKeywordToken(self.cur_word)
        self._SetNext()  # skip time
        pipeline = self.ParsePipeline()
        return command.TimeBlock(time_kw, pipeline)

    def ParseCompoundCommand(self):
        # type: () -> command_t
        """
        Refactoring: we put io_redirect* here instead of in function_body and
        command.

        compound_command : brace_group io_redirect*
                         | subshell io_redirect*
                         | for_clause io_redirect*
                         | while_clause io_redirect*
                         | until_clause io_redirect*
                         | if_clause io_redirect*
                         | case_clause io_redirect*

                         # bash extensions
                         | time_clause
                         | [[ BoolExpr ]]
                         | (( ArithExpr ))
        """
        self._GetWord()
        if self.c_id == Id.Lit_LBrace:
            n1 = self.ParseBraceGroup()
            n1.redirects = self._ParseRedirectList()
            return n1
        if self.c_id == Id.Op_LParen:
            n2 = self.ParseSubshell()
            n2.redirects = self._ParseRedirectList()
            return n2

        if self.c_id == Id.KW_For:
            # Note: Redirects parsed in this call.  POSIX for and bash for (( have
            # redirects, but YSH for doesn't.
            return self.ParseFor()
        if self.c_id in (Id.KW_While, Id.KW_Until):
            keyword = word_.AsKeywordToken(self.cur_word)
            n3 = self.ParseWhileUntil(keyword)
            n3.redirects = self._ParseRedirectList()
            return n3

        if self.c_id == Id.KW_If:
            n4 = self.ParseIf()
            n4.redirects = self._ParseRedirectList()
            return n4
        if self.c_id == Id.KW_Case:
            n5 = self.ParseCase()
            n5.redirects = self._ParseRedirectList()
            return n5

        if self.c_id == Id.KW_DLeftBracket:
            n6 = self.ParseDBracket()
            n6.redirects = self._ParseRedirectList()
            return n6
        if self.c_id == Id.Op_DLeftParen:
            if not self.parse_opts.parse_dparen():
                p_die('You may want a space between parens (parse_dparen)',
                      loc.Word(self.cur_word))
            n7 = self.ParseDParen()
            n7.redirects = self._ParseRedirectList()
            return n7

        # bash extensions: no redirects
        if self.c_id == Id.KW_Time:
            return self.ParseTime()

        # Happens in function body, e.g. myfunc() oops
        p_die('Unexpected word while parsing compound command',
              loc.Word(self.cur_word))
        assert False  # for MyPy

    def ParseFunctionDef(self):
        # type: () -> command.ShFunction
        """
        function_header : fname '(' ')'
        function_def    : function_header newline_ok function_body ;

        Precondition: Looking at the function name.

        NOTE: There is an ambiguity with:

        function foo ( echo hi ) and
        function foo () ( echo hi )

        Bash only accepts the latter, though it doesn't really follow a grammar.
        """
        word0 = cast(CompoundWord, self.cur_word)  # caller ensures validity
        name = word_.ShFunctionName(word0)
        if len(name) == 0:  # example: foo$x is invalid
            p_die('Invalid function name', loc.Word(word0))

        part0 = word0.parts[0]
        # If we got a non-empty string from ShFunctionName, this should be true.
        assert part0.tag() == word_part_e.Literal
        blame_tok = cast(Token, part0)  # for ctx_VarChecker

        self._SetNext()  # move past function name

        # Must be true because of lookahead
        self._GetWord()
        assert self.c_id == Id.Op_LParen, self.cur_word

        self.lexer.PushHint(Id.Op_RParen, Id.Right_ShFunction)
        self._SetNext()

        self._GetWord()
        if self.c_id == Id.Right_ShFunction:
            # 'f ()' implies a function definition, since invoking it with no args
            # would just be 'f'
            self._SetNext()

            self._NewlineOk()

            func = command.ShFunction.CreateNull()
            func.name = name
            with ctx_VarChecker(self.var_checker, blame_tok):
                func.body = self.ParseCompoundCommand()

            func.name_tok = location.LeftTokenForCompoundWord(word0)
            return func
        else:
            p_die('Expected ) in function definition', loc.Word(self.cur_word))
            return None

    def ParseKshFunctionDef(self):
        # type: () -> command.ShFunction
        """
        ksh_function_def : 'function' fname ( '(' ')' )? newline_ok function_body
        """
        keyword_tok = word_.AsKeywordToken(self.cur_word)

        self._SetNext()  # skip past 'function'
        self._GetWord()

        cur_word = cast(CompoundWord, self.cur_word)  # caller ensures validity
        name = word_.ShFunctionName(cur_word)
        if len(name) == 0:  # example: foo$x is invalid
            p_die('Invalid KSH-style function name', loc.Word(cur_word))

        name_word = self.cur_word
        self._SetNext()  # skip past 'function name

        self._GetWord()
        if self.c_id == Id.Op_LParen:
            self.lexer.PushHint(Id.Op_RParen, Id.Right_ShFunction)
            self._SetNext()
            self._Eat(Id.Right_ShFunction)

        self._NewlineOk()

        func = command.ShFunction.CreateNull()
        func.name = name
        with ctx_VarChecker(self.var_checker, keyword_tok):
            func.body = self.ParseCompoundCommand()

        func.keyword = keyword_tok
        func.name_tok = location.LeftTokenForWord(name_word)
        return func

    def ParseYshProc(self):
        # type: () -> command.Proc
        node = command.Proc.CreateNull(alloc_lists=True)

        keyword_tok = word_.AsKeywordToken(self.cur_word)
        node.keyword = keyword_tok

        with ctx_VarChecker(self.var_checker, keyword_tok):
            self.w_parser.ParseProc(node)
            if node.sig.tag() == proc_sig_e.Closed:  # Register params
                sig = cast(proc_sig.Closed, node.sig)

                # Treat params as variables.
                for param in sig.pos_params:
                    self.var_checker.Check(Id.KW_Var, param.name)
                if sig.rest:
                    self.var_checker.Check(Id.KW_Var, sig.rest)
                    # We COULD register __out here but it would require a different API.
                    #if param.prefix and param.prefix.id == Id.Arith_Colon:
                    #  self.var_checker.Check(Id.KW_Var, '__' + param.name)

            self._SetNext()
            node.body = self.ParseBraceGroup()
            # No redirects for YSH procs (only at call site)

        return node

    def ParseYshFunc(self):
        # type: () -> command.Func
        """
        ysh_func: KW_Func Expr_Name '(' [func_params] [';' func_params] ')' brace_group

        Looking at KW_Func
        """
        node = command.Func.CreateNull(alloc_lists=True)

        keyword_tok = word_.AsKeywordToken(self.cur_word)
        node.keyword = keyword_tok

        with ctx_VarChecker(self.var_checker, keyword_tok):
            self.parse_ctx.ParseFunc(self.lexer, node)

            for param in node.pos_params:
                self.var_checker.Check(Id.KW_Var, param.name)
            if node.pos_splat:
                self.var_checker.Check(Id.KW_Var, node.pos_splat)

            self._SetNext()
            with ctx_CmdMode(self, cmd_mode_e.Func):
                node.body = self.ParseBraceGroup()

        return node

    def ParseCoproc(self):
        # type: () -> command_t
        """
        TODO: command.Coproc?
        """
        raise NotImplementedError()

    def ParseSubshell(self):
        # type: () -> command.Subshell
        """
        subshell : '(' compound_list ')'

        Looking at Op_LParen
        """
        left = word_.AsOperatorToken(self.cur_word)
        self._SetNext()  # skip past (

        # Ensure that something $( (cd / && pwd) ) works.  If ) is already on the
        # translation stack, we want to delay it.

        self.lexer.PushHint(Id.Op_RParen, Id.Right_Subshell)

        c_list = self._ParseCommandList()
        if len(c_list.children) == 1:
            child = c_list.children[0]
        else:
            child = c_list

        ate = self._Eat(Id.Right_Subshell)
        right = word_.AsOperatorToken(ate)

        return command.Subshell(left, child, right, None)  # no redirects yet

    def ParseDBracket(self):
        # type: () -> command.DBracket
        """Pass the underlying word parser off to the boolean expression
        parser."""
        left = word_.AsKeywordToken(self.cur_word)
        # TODO: Test interactive.  Without closing ]], you should get > prompt
        # (PS2)

        self._SetNext()  # skip [[
        b_parser = bool_parse.BoolParser(self.w_parser)
        bnode, right = b_parser.Parse()  # May raise
        return command.DBracket(left, bnode, right, None)  # no redirects yet

    def ParseDParen(self):
        # type: () -> command.DParen
        left = word_.AsOperatorToken(self.cur_word)

        self._SetNext()  # skip ((
        anode, right = self.w_parser.ReadDParen()
        assert anode is not None

        return command.DParen(left, anode, right, None)  # no redirects yet

    def ParseCommand(self):
        # type: () -> command_t
        """
        command          : simple_command
                         | compound_command   # OSH edit: io_redirect* folded in
                         | function_def
                         | ksh_function_def

                         # YSH extensions
                         | proc NAME ...
                         | const ...
                         | var ...
                         | setglobal ...
                         | setref ...
                         | setvar ...
                         | _ EXPR
                         | = EXPR
                         ;

        Note: the reason const / var are not part of compound_command is because
        they can't be alone in a shell function body.

        Example:
        This is valid shell   f() if true; then echo hi; fi  
        This is invalid       f() var x = 1
        """
        if self._AtSecondaryKeyword():
            p_die('Unexpected word when parsing command',
                  loc.Word(self.cur_word))

        # YSH Extensions

        if self.c_id == Id.KW_Proc:  # proc p { ... }
            # proc is hidden because of the 'local reasoning' principle
            # Code inside procs should be YSH, full stop.  That means oil:upgrade is
            # on.
            if self.parse_opts.parse_proc():
                return self.ParseYshProc()

            # Otherwise silently pass. This is to support scripts like:
            # $ bash -c 'proc() { echo p; }; proc'

        if self.c_id == Id.KW_Func:  # func f(x) { ... }
            if self.parse_opts.parse_func() and not self.parse_opts.parse_tea():
                return self.ParseYshFunc()

            # Otherwise silently pass, like for the procs.

        if self.c_id in (Id.KW_Var, Id.KW_Const):  # var x = 1
            keyword_id = self.c_id
            kw_token = word_.LiteralToken(self.cur_word)
            self._SetNext()
            n8 = self.w_parser.ParseVarDecl(kw_token)
            for lhs in n8.lhs:
                self.var_checker.Check(keyword_id, lhs.name)
            return n8

        if self.c_id in (Id.KW_SetVar, Id.KW_SetRef, Id.KW_SetGlobal):
            kw_token = word_.LiteralToken(self.cur_word)
            self._SetNext()
            n9 = self.w_parser.ParsePlaceMutation(kw_token, self.var_checker)
            return n9

        if self.c_id in (Id.Lit_Underscore, Id.Lit_Equals):  # = 42 + 1
            keyword = word_.LiteralToken(self.cur_word)
            assert keyword is not None
            self._SetNext()
            enode = self.w_parser.ParseCommandExpr()
            return command.Expr(keyword, enode)

        if self.c_id == Id.KW_Function:
            return self.ParseKshFunctionDef()

        # Top-level keywords to hide: func, data, enum, class/mod.  Not sure about
        # 'use'.
        if self.parse_opts.parse_tea():
            if self.c_id == Id.KW_Func:
                out0 = command.TeaFunc.CreateNull(alloc_lists=True)
                self.parse_ctx.ParseTeaFunc(self.lexer, out0)
                self._SetNext()
                return out0
            if self.c_id == Id.KW_Data:
                out1 = command.Data.CreateNull(alloc_lists=True)
                self.parse_ctx.ParseDataType(self.lexer, out1)
                self._SetNext()
                return out1
            if self.c_id == Id.KW_Enum:
                out2 = command.Enum.CreateNull(alloc_lists=True)
                self.parse_ctx.ParseEnum(self.lexer, out2)
                self._SetNext()
                return out2
            if self.c_id == Id.KW_Class:
                out3 = command.Class.CreateNull(alloc_lists=True)
                self.parse_ctx.ParseClass(self.lexer, out3)
                self._SetNext()
                return out3
            if self.c_id == Id.KW_Import:
                # Needs last_token because it ends with an optional thing?
                out4 = command.Import.CreateNull(alloc_lists=True)
                self.w_parser.ParseImport(out4)
                self._SetNext()
                return out4

        if self.c_id in (Id.KW_DLeftBracket, Id.Op_DLeftParen, Id.Op_LParen,
                         Id.Lit_LBrace, Id.KW_For, Id.KW_While, Id.KW_Until,
                         Id.KW_If, Id.KW_Case, Id.KW_Time):
            return self.ParseCompoundCommand()

        # Syntax error for '}' starting a line, which all shells disallow.
        if self.c_id == Id.Lit_RBrace:
            p_die('Unexpected right brace', loc.Word(self.cur_word))

        if self.c_kind == Kind.Redir:  # Leading redirect
            return self.ParseSimpleCommand()

        if self.c_kind == Kind.Word:
            cur_word = cast(CompoundWord, self.cur_word)  # ensured by Kind.Word

            # NOTE: At the top level, only Token and Compound are possible.
            # Can this be modelled better in the type system, removing asserts?
            #
            # TODO: This can be a proc INVOCATION!  (Doesn't even need parse_paren)
            # Problem: We have to distinguish f( ) { echo ; } and myproc (x, y)
            # That requires 2 tokens of lookahead, which we don't have
            #
            # Or maybe we don't just have ParseSimpleCommand -- we will have
            # ParseYshCommand or something

            if (self.w_parser.LookAheadFuncParens() and
                    not word_.IsVarLike(cur_word)):
                return self.ParseFunctionDef()  # f() { echo; }  # function

            # Parse x = 1+2*3 when inside HayNode { } blocks
            parts = cur_word.parts
            if self.parse_opts.parse_equals() and len(parts) == 1:
                part0 = parts[0]
                if part0.tag() == word_part_e.Literal:
                    tok = cast(Token, part0)
                    # NOTE: tok.id should be Lit_Chars, but that check is redundant
                    if (match.IsValidVarName(tok.tval) and
                            self.w_parser.LookPastSpace() == Id.Lit_Equals):

                        if len(self.allow_block_attrs
                              ) and self.allow_block_attrs[-1]:
                            # Note: no static var_checker.Check() for bare assignment
                            enode = self.w_parser.ParseBareDecl()
                            self._SetNext()  # Somehow this is necessary
                            # TODO: Use BareDecl here.  Well, do that when we treat it as const
                            # or lazy.
                            return command.VarDecl(None, [NameType(tok, None)],
                                                   enode)
                        else:
                            self._SetNext()
                            self._GetWord()
                            p_die(
                                'Unexpected = (Hint: use const/var/setvar, or quote it)',
                                loc.Word(self.cur_word))

            # echo foo
            # f=(a b c)  # array
            # array[1+2]+=1
            return self.ParseSimpleCommand()

        if self.c_kind == Kind.Eof:
            p_die("Unexpected EOF while parsing command",
                  loc.Word(self.cur_word))

        # NOTE: This only happens in batch mode in the second turn of the loop!
        # e.g. )
        p_die("Invalid word while parsing command", loc.Word(self.cur_word))

        assert False  # for MyPy

    def ParsePipeline(self):
        # type: () -> command_t
        """
        pipeline         : Bang? command ( '|' newline_ok command )* ;
        """
        negated = None  # type: Optional[Token]

        self._GetWord()
        if self.c_id == Id.KW_Bang:
            negated = word_.AsKeywordToken(self.cur_word)
            self._SetNext()

        child = self.ParseCommand()
        assert child is not None

        children = [child]

        self._GetWord()
        if self.c_id not in (Id.Op_Pipe, Id.Op_PipeAmp):
            if negated is not None:
                node = command.Pipeline(negated, children, [])
                return node
            else:
                return child  # no pipeline

        # | or |&
        ops = []  # type: List[Token]
        while True:
            op = word_.AsOperatorToken(self.cur_word)
            ops.append(op)

            self._SetNext()  # skip past Id.Op_Pipe or Id.Op_PipeAmp
            self._NewlineOk()

            child = self.ParseCommand()
            children.append(child)

            self._GetWord()
            if self.c_id not in (Id.Op_Pipe, Id.Op_PipeAmp):
                break

        return command.Pipeline(negated, children, ops)

    def ParseAndOr(self):
        # type: () -> command_t
        self._GetWord()
        if self.c_id == Id.Word_Compound:
            first_word_tok = word_.LiteralToken(self.cur_word)
            if first_word_tok is not None and first_word_tok.id == Id.Lit_TDot:
                # We got '...', so parse in multiline mode
                self._SetNext()
                with word_.ctx_Multiline(self.w_parser):
                    return self._ParseAndOr()

        # Parse in normal mode, not multiline
        return self._ParseAndOr()

    def _ParseAndOr(self):
        # type: () -> command_t
        """
        and_or           : and_or ( AND_IF | OR_IF ) newline_ok pipeline
                         | pipeline

        Note that it is left recursive and left associative.  We parse it
        iteratively with a token of lookahead.
        """
        child = self.ParsePipeline()
        assert child is not None

        self._GetWord()
        if self.c_id not in (Id.Op_DPipe, Id.Op_DAmp):
            return child

        ops = []  # type: List[Token]
        children = [child]

        while True:
            ops.append(word_.AsOperatorToken(self.cur_word))

            self._SetNext()  # skip past || &&
            self._NewlineOk()

            child = self.ParsePipeline()
            children.append(child)

            self._GetWord()
            if self.c_id not in (Id.Op_DPipe, Id.Op_DAmp):
                break

        return command.AndOr(children, ops)

    # NOTE: _ParseCommandLine and _ParseCommandTerm are similar, but different.

    # At the top level, we execute after every line, e.g. to
    # - process alias (a form of dynamic parsing)
    # - process 'exit', because invalid syntax might appear after it

    # On the other hand, for a while loop body, we parse the whole thing at once,
    # and then execute it.  We don't want to parse it over and over again!

    # COMPARE
    # command_line     : and_or (sync_op and_or)* trailer? ;   # TOP LEVEL
    # command_term     : and_or (trailer and_or)* ;            # CHILDREN

    def _ParseCommandLine(self):
        # type: () -> command_t
        """
        command_line     : and_or (sync_op and_or)* trailer? ;
        trailer          : sync_op newline_ok
                         | NEWLINES;
        sync_op          : '&' | ';';

        NOTE: This rule causes LL(k > 1) behavior.  We would have to peek to see if
        there is another command word after the sync op.

        But it's easier to express imperatively.  Do the following in a loop:
        1. ParseAndOr
        2. Peek.
           a. If there's a newline, then return.  (We're only parsing a single
              line.)
           b. If there's a sync_op, process it.  Then look for a newline and
              return.  Otherwise, parse another AndOr.
        """
        # This END_LIST is slightly different than END_LIST in _ParseCommandTerm.
        # I don't think we should add anything else here; otherwise it will be
        # ignored at the end of ParseInteractiveLine(), e.g. leading to bug #301.
        END_LIST = [Id.Op_Newline, Id.Eof_Real]

        children = []  # type: List[command_t]
        done = False
        while not done:
            child = self.ParseAndOr()

            self._GetWord()
            if self.c_id in (Id.Op_Semi, Id.Op_Amp):
                tok = cast(Token, self.cur_word)  # for MyPy
                child = command.Sentence(child, tok)
                self._SetNext()

                self._GetWord()
                if self.c_id in END_LIST:
                    done = True

            elif self.c_id in END_LIST:
                done = True

            else:
                # e.g. echo a(b)
                p_die('Invalid word while parsing command line',
                      loc.Word(self.cur_word))

            children.append(child)

        # Simplify the AST.
        if len(children) > 1:
            return command.CommandList(children)
        else:
            return children[0]

    def _ParseCommandTerm(self):
        # type: () -> command.CommandList
        """"
        command_term     : and_or (trailer and_or)* ;
        trailer          : sync_op newline_ok
                         | NEWLINES;
        sync_op          : '&' | ';';

        This is handled in imperative style, like _ParseCommandLine.
        Called by _ParseCommandList for all blocks, and also for ParseCaseArm,
        which is slightly different.  (HOW?  Is it the DSEMI?)

        Returns:
          syntax_asdl.command
        """
        # Token types that will end the command term.
        END_LIST = [self.eof_id, Id.Right_Subshell, Id.Lit_RBrace, Id.Op_DSemi]

        # NOTE: This is similar to _ParseCommandLine.
        #
        # - Why aren't we doing END_LIST in _ParseCommandLine?
        #   - Because you will never be inside $() at the top level.
        #   - We also know it will end in a newline.  It can't end in "fi"!
        #   - example: if true; then { echo hi; } fi

        children = []  # type: List[command_t]
        done = False
        while not done:
            # Most keywords are valid "first words".  But do/done/then do not BEGIN
            # commands, so they are not valid.
            if self._AtSecondaryKeyword():
                break

            child = self.ParseAndOr()

            self._GetWord()
            if self.c_id == Id.Op_Newline:
                self._SetNext()

                self._GetWord()
                if self.c_id in END_LIST:
                    done = True

            elif self.c_id in (Id.Op_Semi, Id.Op_Amp):
                tok = cast(Token, self.cur_word)  # for MyPy
                child = command.Sentence(child, tok)
                self._SetNext()

                self._GetWord()
                if self.c_id == Id.Op_Newline:
                    self._SetNext()  # skip over newline

                    # Test if we should keep going.  There might be another command after
                    # the semi and newline.
                    self._GetWord()
                    if self.c_id in END_LIST:  # \n EOF
                        done = True

                elif self.c_id in END_LIST:  # ; EOF
                    done = True

            elif self.c_id in END_LIST:  # EOF
                done = True

            # For if test -f foo; test -f bar {
            elif self.parse_opts.parse_brace() and self.c_id == Id.Lit_LBrace:
                done = True

            elif self.c_kind != Kind.Word:
                # e.g. f() { echo (( x )) ; }
                # but can't fail on 'fi fi', see osh/cmd_parse_test.py

                #log("Invalid %s", self.cur_word)
                p_die("Invalid word while parsing command list",
                      loc.Word(self.cur_word))

            children.append(child)

        return command.CommandList(children)

    def _ParseCommandList(self):
        # type: () -> command.CommandList
        """
        command_list     : newline_ok command_term trailer? ;

        This one is called by all the compound commands.  It's basically a command
        block.

        NOTE: Rather than translating the CFG directly, the code follows a style
        more like this: more like this: (and_or trailer)+.  It makes capture
        easier.
        """
        self._NewlineOk()
        return self._ParseCommandTerm()

    def ParseLogicalLine(self):
        # type: () -> command_t
        """Parse a single line for main_loop.

        A wrapper around _ParseCommandLine().  Similar but not identical to
        _ParseCommandList() and ParseCommandSub().

        Raises:
          ParseError
        """
        self._NewlineOk()
        self._GetWord()
        if self.c_id == Id.Eof_Real:
            return None  # main loop checks for here docs
        node = self._ParseCommandLine()
        return node

    def ParseInteractiveLine(self):
        # type: () -> parse_result_t
        """Parse a single line for Interactive main_loop.

        Different from ParseLogicalLine because newlines are handled differently.

        Raises:
          ParseError
        """
        self._GetWord()
        if self.c_id == Id.Op_Newline:
            return parse_result.EmptyLine
        if self.c_id == Id.Eof_Real:
            return parse_result.Eof

        node = self._ParseCommandLine()
        return parse_result.Node(node)

    def ParseCommandSub(self):
        # type: () -> command_t
        """Parse $(echo hi) and `echo hi` for word_parse.py.

        They can have multiple lines, like this: echo $(   echo one echo
        two )
        """
        self._NewlineOk()

        self._GetWord()
        if self.c_kind == Kind.Eof:  # e.g. $()
            return command.NoOp

        c_list = self._ParseCommandTerm()
        if len(c_list.children) == 1:
            return c_list.children[0]
        else:
            return c_list

    def CheckForPendingHereDocs(self):
        # type: () -> None
        # NOTE: This happens when there is no newline at the end of a file, like
        # osh -c 'cat <<EOF'
        if len(self.pending_here_docs):
            node = self.pending_here_docs[0]  # Just show the first one?
            h = cast(redir_param.HereDoc, node.arg)
            p_die('Unterminated here doc began here', loc.Word(h.here_begin))
