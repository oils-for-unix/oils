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
from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str, Kind
from _devbuild.gen.types_asdl import lex_mode_t, lex_mode_e
from _devbuild.gen.syntax_asdl import (
    command, command_t,
    command__Simple, command__BraceGroup,
    command__DoGroup, command__ForExpr, command__ForEach, command__WhileUntil,
    command__Case, command__If, command__ShFunction, command__Subshell,
    command__DBracket, command__DParen, command__CommandList,
    command__Func, command__Proc,
    case_arm,

    sh_lhs_expr, sh_lhs_expr_t,
    redir, redir_t, redir__HereDoc,
    word, word_e, word_t, compound_word, Token,
    word_part_e, word_part_t,

    assign_pair, env_pair,
    assign_op_e,

    source, parse_result, parse_result_t,
    speck, name_type,
)
from _devbuild.gen import syntax_asdl  # token, etc.

from asdl import runtime
from core import error
from core.util import log, p_die
from frontend import match
from frontend import reader
from osh import braces
from osh import bool_parse
from osh import word_
from mycpp.mylib import NewStr

from typing import Optional, List, Tuple, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from core.alloc import Arena
  from frontend.lexer import Lexer
  from frontend.parse_lib import ParseContext, AliasesInFlight
  from frontend.reader import _Reader
  from osh.word_parse import WordParser


def _KeywordSpid(w):
  # type: (word_t) -> int
  """
  TODO: Can be we optimize this?
  Assume that 'while', 'case', etc. are a specific type of compound_word.

  I tested turning LeftMostSpanForWord in a no-op and couldn't observe the
  difference on a ~500 ms parse of testdata/osh-runtime/abuild.  So maybe this
  doesn't make sense.
  """
  return word_.LeftMostSpanForWord(w)


def _KeywordToken(UP_w):
  # type: (word_t) -> Token
  """Given a word that IS A keyword, return the single token at the start.

  In C++, this casts without checking, so BE CAREFUL to call it in the right context.
  """
  assert UP_w.tag_() == word_e.Compound, UP_w
  w = cast(compound_word, UP_w)

  part = w.parts[0]
  assert part.tag_() == word_part_e.Literal, part
  return cast(Token, part)


def _ReadHereLines(line_reader,  # type: _Reader
                   h,  # type: redir__HereDoc
                   delimiter,  # type: str
                   ):
  # type: (...) -> Tuple[List[Tuple[int, str, int]], Tuple[int, str, int]]
  # NOTE: We read all lines at once, instead of parsing line-by-line,
  # because of cases like this:
  # cat <<EOF
  # 1 $(echo 2
  # echo 3) 4
  # EOF
  here_lines = []  # type: List[Tuple[int, str, int]]
  last_line = None  # type: Tuple[int, str, int]
  strip_leading_tabs = (h.op.id == Id.Redir_DLessDash)

  while True:
    line_id, line, unused_offset = line_reader.GetLine()

    if not line:  # EOF
      # An unterminated here doc is just a warning in bash.  We make it
      # fatal because we want to be strict, and because it causes problems
      # reporting other errors.
      # Attribute it to the << in <<EOF for now.
      p_die("Couldn't find terminator for here doc that starts here",
            token=h.op)

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
      last_line = (line_id, line, start_offset)
      break

    here_lines.append((line_id, line, start_offset))

  return here_lines, last_line


def _MakeLiteralHereLines(here_lines,  # type: List[Tuple[int, str, int]]
                          arena,  # type: Arena
                          ):
  # type: (...) -> List[word_part_t]  # less precise because List is invariant type
  """Create a line_span and a token for each line."""
  tokens = []  # type: List[Token]
  for line_id, line, start_offset in here_lines:
    span_id = arena.AddLineSpan(line_id, start_offset, len(line))
    t = Token(Id.Lit_Chars, span_id, line[start_offset:])
    tokens.append(t)
  parts = [cast(word_part_t, t) for t in tokens]
  return parts


def _ParseHereDocBody(parse_ctx, h, line_reader, arena):
  # type: (ParseContext, redir__HereDoc, _Reader, Arena) -> None
  """Fill in attributes of a pending here doc node."""
  # "If any character in word is quoted, the delimiter shall be formed by
  # performing quote removal on word, and the here-document lines shall not
  # be expanded. Otherwise, the delimiter shall be the word itself."
  # NOTE: \EOF counts, or even E\OF
  ok, delimiter, delim_quoted = word_.StaticEval(h.here_begin)
  if not ok:
    p_die('Invalid here doc delimiter', word=h.here_begin)

  here_lines, last_line = _ReadHereLines(line_reader, h, delimiter)

  if delim_quoted:  # << 'EOF'
    # Literal for each line.
    h.stdin_parts = _MakeLiteralHereLines(here_lines, arena)
  else:
    line_reader = reader.VirtualLineReader(here_lines, arena)
    w_parser = parse_ctx.MakeWordParserForHereDoc(line_reader)
    w_parser.ReadHereDocBody(h.stdin_parts)  # fills this in

  end_line_id, end_line, end_pos = last_line

  # Create a span with the end terminator.  Maintains the invariant that
  # the spans "add up".
  h.here_end_span_id = arena.AddLineSpan(end_line_id, end_pos, len(end_line))


def _MakeAssignPair(parse_ctx, preparsed, arena):
  # type: (ParseContext, PreParsedItem, Arena) -> assign_pair
  """Create an assign_pair from a 4-tuples from DetectShAssignment."""

  left_token, close_token, part_offset, w = preparsed

  if left_token.id == Id.Lit_VarLike:  # s=1
    if left_token.val[-2] == '+':
      var_name = left_token.val[:-2]
      op = assign_op_e.PlusEqual
    else:
      var_name = left_token.val[:-1]
      op = assign_op_e.Equal

    tmp = sh_lhs_expr.Name(var_name)
    tmp.spids.append(left_token.span_id)

    lhs = cast(sh_lhs_expr_t, tmp)

  elif left_token.id == Id.Lit_ArrayLhsOpen and parse_ctx.one_pass_parse:
    var_name = left_token.val[:-1]
    if close_token.val[-2] == '+':
      op = assign_op_e.PlusEqual
    else:
      op = assign_op_e.Equal

    left_spid = left_token.span_id + 1
    right_spid = close_token.span_id

    left_span = parse_ctx.arena.GetLineSpan(left_spid)
    right_span = parse_ctx.arena.GetLineSpan(right_spid)
    assert left_span.line_id == right_span.line_id, \
        '%s and %s not on same line' % (left_span, right_span)

    line = parse_ctx.arena.GetLine(left_span.line_id)
    index_str = line[left_span.col : right_span.col]
    lhs = sh_lhs_expr.UnparsedIndex(var_name, index_str)

  elif left_token.id == Id.Lit_ArrayLhsOpen:  # a[x++]=1
    var_name = left_token.val[:-1]
    if close_token.val[-2] == '+':
      op = assign_op_e.PlusEqual
    else:
      op = assign_op_e.Equal

    spid1 = left_token.span_id
    spid2 = close_token.span_id
    span1 = arena.GetLineSpan(spid1)
    span2 = arena.GetLineSpan(spid2)
    if span1.line_id == span2.line_id:
      line = arena.GetLine(span1.line_id)
      # extract what's between brackets
      code_str = line[span1.col + span1.length : span2.col]
    else:
      raise NotImplementedError('%d != %d' % (span1.line_id, span2.line_id))
    a_parser = parse_ctx.MakeArithParser(code_str)
    arena.PushSource(source.LValue(left_token.span_id, close_token.span_id))
    try:
      index_node = a_parser.Parse()  # may raise error.Parse
    finally:
      arena.PopSource()
    tmp3 = sh_lhs_expr.IndexedName(var_name, index_node)
    tmp3.spids.append(left_token.span_id)

    lhs = cast(sh_lhs_expr_t, tmp3)

  else:
    raise AssertionError()

  # TODO: Should we also create a rhs_expr.ArrayLiteral here?
  n = len(w.parts)
  if part_offset == n:
    val = word.Empty()  # type: word_t
  else:
    val = compound_word(w.parts[part_offset:])
    tilde = word_.TildeDetect(val)
    if tilde:
      val = tilde

  pair = syntax_asdl.assign_pair(lhs, op, val, [left_token.span_id])
  return pair


def _AppendMoreEnv(preparsed_list, more_env):
  # type: (PreParsedList, List[env_pair]) -> None
  """Helper to modify a SimpleCommand node.

  Args:
    preparsed: a list of 4-tuples from DetectShAssignment
    more_env: a list to append env_pairs to
  """
  for left_token, _, part_offset, w in preparsed_list:
    if left_token.id != Id.Lit_VarLike:  # can't be a[x]=1
      p_die("Environment binding shouldn't look like an array assignment",
            token=left_token)

    if left_token.val[-2] == '+':
      p_die('Expected = in environment binding, got +=', token=left_token)

    var_name = left_token.val[:-1]
    n = len(w.parts)
    if part_offset == n:
      val = word.Empty()  # type: word_t
    else:
      val = compound_word(w.parts[part_offset:])

    pair = syntax_asdl.env_pair(var_name, val, [left_token.span_id])
    more_env.append(pair)


if TYPE_CHECKING:
  PreParsedItem = Tuple[Token, Optional[Token], int, compound_word]
  PreParsedList = List[PreParsedItem]

def _SplitSimpleCommandPrefix(words):
  # type: (List[compound_word]) -> Tuple[PreParsedList, List[compound_word]]
  """Second pass of SimpleCommand parsing: look for assignment words."""
  preparsed_list = []  # type: PreParsedList
  suffix_words = []  # type: List[compound_word]

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


def _MakeSimpleCommand(preparsed_list, suffix_words, redirects, block):
  # type: (PreParsedList, List[compound_word], List[redir_t], Optional[command_t]) -> command__Simple
  """Create an command.Simple node."""

  # FOO=(1 2 3) ls is not allowed.
  for _, _, _, w in preparsed_list:
    if word_.HasArrayPart(w):
      p_die("Environment bindings can't contain array literals", word=w)

  # NOTE: It would be possible to add this check back.  But it already happens
  # at runtime in EvalWordSequence2.
  # echo FOO=(1 2 3) is not allowed (but we should NOT fail on echo FOO[x]=1).
  if 0:
    for w in suffix_words:
      if word_.HasArrayPart(w):
        p_die("Commands can't contain array literals", word=w)

  # NOTE: We only do brace DETECTION here, not brace EXPANSION.  Therefore we
  # can't implement bash's behavior of having say {~bob,~jane}/src work,
  # because we only have a BracedTree.
  # This is documented in spec/brace-expansion.
  # NOTE: Technically we could do expansion outside of 'oshc translate', but it
  # doesn't seem worth it.
  words2 = braces.BraceDetectAll(suffix_words)
  words3 = word_.TildeDetectAll(words2)

  more_env = []  # type: List[env_pair]
  _AppendMoreEnv(preparsed_list, more_env)
  node = command.Simple(words3, redirects, more_env, block)
  return node


# Note: 'do' depends on parse_do
SECONDARY_KEYWORDS = [
    Id.KW_Done, Id.KW_Then, Id.KW_Fi, Id.KW_Elif, Id.KW_Else, Id.KW_Esac
]


class CommandParser(object):
  """
  Args:
    word_parse: to get a stream of words
    lexer: for lookahead in function def, PushHint of ()
    line_reader: for here doc
  """
  def __init__(self, parse_ctx, w_parser, lexer, line_reader):
    # type: (ParseContext, WordParser, Lexer, _Reader) -> None
    self.parse_ctx = parse_ctx
    self.aliases = parse_ctx.aliases  # aliases to expand at parse time

    self.w_parser = w_parser  # type: WordParser  # for normal parsing
    self.lexer = lexer  # for pushing hints, lookahead to (
    self.line_reader = line_reader  # for here docs
    self.arena = parse_ctx.arena  # for adding here doc and alias spans
    self.eof_id = Id.Eof_Real
    self.aliases_in_flight = None  # type: AliasesInFlight

    # A hacky boolean to remove 'if cd / {' ambiguity.
    self.allow_block = True
    # 'return' in proc and func takes an expression
    self.return_expr = False
    self.parse_opts = parse_ctx.parse_opts

    self.Reset()

  # These two Init_() functions simulate "keywords args" in C++.
  def Init_EofId(self, eof_id):
    # type: (Id_t) -> None
    self.eof_id = eof_id

  def Init_AliasesInFlight(self, aliases_in_flight):
    # type: (AliasesInFlight) -> None
    self.aliases_in_flight = aliases_in_flight

  def Reset(self):
    # type: () -> None
    """Reset our own internal state.

    Called by the interactive loop.
    """
    # Cursor state set by _Peek()
    self.next_lex_mode = lex_mode_e.ShCommand
    self.cur_word = None  # type: word_t  # current word
    self.c_kind = Kind.Undefined
    self.c_id = Id.Undefined_Tok

    self.pending_here_docs = []  # type: List[redir__HereDoc]

  def ResetInputObjects(self):
    # type: () -> None
    """Reset the internal state of our inputs.

    Called by the interactive loop.
    """
    self.w_parser.Reset()
    self.lexer.ResetInputObjects()
    self.line_reader.Reset()

  def _Next(self, lex_mode=lex_mode_e.ShCommand):
    # type: (lex_mode_t) -> None
    """Helper method."""
    self.next_lex_mode = lex_mode

  def _Peek(self):
    # type: () -> None
    """Helper method.

    Returns True for success and False on error.  Error examples: bad command
    sub word, or unterminated quoted string, etc.
    """
    if self.next_lex_mode != lex_mode_e.Undefined:
      w = self.w_parser.ReadWord(self.next_lex_mode)

      # Here docs only happen in command mode, so other kinds of newlines don't
      # count.
      if w.tag_() == word_e.Token:
        tok = cast(Token, w)
        if tok.id == Id.Op_Newline:
          for h in self.pending_here_docs:
            _ParseHereDocBody(self.parse_ctx, h, self.line_reader, self.arena)
          del self.pending_here_docs[:]  # No .clear() until Python 3.3.

      self.cur_word = w

      self.c_kind = word_.CommandKind(self.cur_word)
      self.c_id = word_.CommandId(self.cur_word)
      self.next_lex_mode = lex_mode_e.Undefined

  def _Eat(self, c_id):
    # type: (Id_t) -> None
    actual_id = word_.CommandId(self.cur_word)
    msg = 'Expected word type %s, got %s' % (
        NewStr(Id_str(c_id)), NewStr(Id_str(actual_id))
    )
    self._Eat2(c_id, msg)

  def _Eat2(self, c_id, msg):
    # type: (Id_t, str) -> None
    """Consume a word of a type.  If it doesn't match, return False.

    Args:
      c_id: the Id we expected
      msg: improved error message
    """
    self._Peek()
    # TODO: Printing something like KW_Do is not friendly.  We can map
    # backwards using the _KEYWORDS list in osh/lex.py.
    if self.c_id != c_id:
      p_die(msg, word=self.cur_word)
    self._Next()

  def _NewlineOk(self):
    # type: () -> None
    """Check for optional newline and consume it."""
    self._Peek()
    if self.c_id == Id.Op_Newline:
      self._Next()
      self._Peek()

  def _AtSecondaryKeyword(self):
    # type: () -> bool
    if self.c_id in SECONDARY_KEYWORDS:
      return True
    if self.c_id == Id.KW_Do and not self.parse_opts.parse_do:
      return True
    return False

  def ParseRedirect(self):
    # type: () -> redir_t
    """
    Problem: You don't know which kind of redir_node to instantiate before
    this?  You could stuff them all in one node, and then have a switch() on
    the type.

    You need different types.
    """
    self._Peek()
    assert self.c_kind == Kind.Redir, self.cur_word
    op_tok = cast(Token, self.cur_word)  # for MyPy

    # For now only supporting single digit descriptor
    first_char = op_tok.val[0]
    if first_char.isdigit():
      fd = int(first_char)
    else:
      fd = runtime.NO_SPID

    self._Next()
    self._Peek()

    # Here doc
    if op_tok.id in (Id.Redir_DLess, Id.Redir_DLessDash):
      h = redir.HereDoc()  # no stdin_parts yet
      h.op = op_tok
      h.fd = fd
      h.here_begin = self.cur_word
      self.pending_here_docs.append(h)  # will be filled on next newline.

      self._Next()
      return h

    # Other redirect
    if self.c_kind != Kind.Word:
      p_die('Invalid token after redirect operator', word=self.cur_word)

    arg_word = self.cur_word
    tilde = word_.TildeDetect(arg_word)
    if tilde:
      arg_word = tilde
    self._Next()

    return redir.Redir(op_tok, fd, arg_word)

  def _ParseRedirectList(self):
    # type: () -> List[redir_t]
    """Try parsing any redirects at the cursor.

    This is used for blocks only, not commands.

    Return None on error.
    """
    redirects = []  # type: List[redir_t]
    while True:
      self._Peek()

      # This prediction needs to ONLY accept redirect operators.  Should we
      # make them a separate TokeNkind?
      if self.c_kind != Kind.Redir:
        break

      node = self.ParseRedirect()
      redirects.append(node)
      self._Next()
    return redirects

  def _ScanSimpleCommand(self):
    # type: () -> Tuple[List[redir_t], List[compound_word], Optional[command__BraceGroup]]
    """First pass: Split into redirects and words."""
    redirects = []  # type: List[redir_t]
    words = []  # type: List[compound_word]
    block = None  # type: Optional[command__BraceGroup]
    while True:
      self._Peek()
      if self.c_kind == Kind.Redir:
        node = self.ParseRedirect()
        redirects.append(node)

      elif self.c_kind == Kind.Word:
        if self.parse_opts.parse_brace:
          # Treat { and } more like operators
          if self.c_id == Id.Lit_LBrace:
            if self.allow_block:  # Disabled for if/while condition, etc.
              block = self.ParseBraceGroup()
            if 0:
              print('--')
              block.PrettyPrint()
              print('\n--')
            break
          elif self.c_id == Id.Lit_RBrace:
            # Another thing: { echo hi }
            # We're DONE!!!
            break

        w = cast(compound_word, self.cur_word)  # Kind.Word ensures this
        words.append(w)

      else:
        break

      self._Next()
    return redirects, words, block

  def _MaybeExpandAliases(self, words):
    # type: (List[compound_word]) -> Optional[command_t]
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

    NOTE: dash handles aliases in a totally diferrent way.  It has a global
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
    aliases_in_flight = (
        self.aliases_in_flight if self.aliases_in_flight else []
    )

    # for error message
    first_word_str = None  # type: Optional[str]
    argv0_spid = word_.LeftMostSpanForWord(words[0])

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

    # We got some expansion.  Now copy the rest of the words.

    # We need each NON-REDIRECT word separately!  For example:
    # $ echo one >out two
    # dash/mksh/zsh go beyond the first redirect!
    while i < n:
      w = words[i]
      spid1 = word_.LeftMostSpanForWord(w)
      spid2 = word_.RightMostSpanForWord(w)

      span1 = self.arena.GetLineSpan(spid1)
      span2 = self.arena.GetLineSpan(spid2)

      if 0:
        log('spid1 = %d, spid2 = %d', spid1, spid2)
        n1 = self.arena.GetLineNumber(span1.line_id)
        n2 = self.arena.GetLineNumber(span2.line_id)
        log('span1 %s line %d %r', span1, n1, self.arena.GetLine(span1.line_id))
        log('span2 %s line %d %r', span2, n2, self.arena.GetLine(span2.line_id))

      if span1.line_id == span2.line_id:
        line = self.arena.GetLine(span1.line_id)
        piece = line[span1.col : span2.col + span2.length]
        expanded.append(piece)
      else:
        # NOTE: The xrange(left_spid, right_spid) algorithm won't work for
        # commands like this:
        #
        # myalias foo`echo hi`bar
        #
        # That is why we only support words over 1 or 2 lines.

        raise NotImplementedError(
            'line IDs %d != %d' % (span1.line_id, span2.line_id))

      expanded.append(' ')  # Put space back between words.
      i += 1

    code_str = ''.join(expanded)

    # NOTE: self.arena isn't correct here.  Breaks line invariant.
    line_reader = reader.StringLineReader(code_str, self.arena)
    cp = self.parse_ctx.MakeOshParser(line_reader)
    cp.Init_AliasesInFlight(aliases_in_flight)

    # The interaction between COMPLETION and ALIASES requires special care.
    # See docstring of BeginAliasExpansion() in parse_lib.py.
    self.arena.PushSource(source.Alias(first_word_str, argv0_spid))
    trail = self.parse_ctx.trail
    trail.BeginAliasExpansion()
    try:
      # _ParseCommandTerm() handles multiline commands, compound commands, etc.
      # as opposed to ParseLogicalLine()
      node = cp._ParseCommandTerm()
    except error.Parse as e:
      # Failure to parse alias expansion is a fatal error
      # We don't need more handling here/
      raise
    finally:
      trail.EndAliasExpansion()
      self.arena.PopSource()

    if 0:
      log('AFTER expansion:')
      node.PrettyPrint()

    return node

  def ParseSimpleCommand(self):
    # type: () -> command_t
    """
    Fixed transcription of the POSIX grammar (TODO: port to grammar/Shell.g)

    io_file        : '<'       filename
                   | LESSAND   filename
                     ...

    io_here        : DLESS     here_end
                   | DLESSDASH here_end

    redirect       : IO_NUMBER (io_redirect | io_here)

    prefix_part    : ASSIGNMENT_WORD | redirect
    cmd_part       : WORD | redirect

    assign_kw      : Declare | Export | Local | Readonly

    # Without any words it is parsed as a command, not an assigment
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

        >out.txt FOO=bar   # this touches the file, and hten

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
    redirects, words, block = self._ScanSimpleCommand()
    block_spid = block.spids[0] if block else runtime.NO_SPID

    if len(words) == 0:  # e.g.  >out.txt  # redirect without words
      if block:
        p_die("Unexpected block", span_id=block_spid)
      simple = command.Simple()  # no words, more_env, or block,
      simple.redirects = redirects
      return simple

    # Disallow =a because it's confusing
    part0 = words[0].parts[0]
    if part0.tag_() == word_part_e.Literal:
      tok = cast(Token, part0)
      if tok.id == Id.Lit_Equals:
        p_die("=word isn't allowed when shopt 'parse_equals' is on.\n"
              "Hint: add a space after = to pretty print an expression", token=tok)

    preparsed_list, suffix_words = _SplitSimpleCommandPrefix(words)
    if self.parse_opts.parse_equals and len(preparsed_list):
      left_token, _, _, _ = preparsed_list[0]
      p_die("name=val isn't allowed when shopt 'parse_equals' is on.\n"
            "Hint: add 'env' before it, or spaces around =", token=left_token)

    # Set a reference to words and redirects for completion.  We want to
    # inspect this state after a failed parse.
    self.parse_ctx.trail.SetLatestWords(suffix_words, redirects)

    if len(suffix_words) == 0:
      if block:
        p_die("Unexpected block", span_id=block_spid)

      # ShAssignment: No suffix words like ONE=1 a[x]=1 TWO=2
      pairs = []  # type: List[assign_pair]
      for preparsed in preparsed_list:
        pairs.append(_MakeAssignPair(self.parse_ctx, preparsed, self.arena))

      assign = command.ShAssignment(pairs, redirects)
      left_spid = word_.LeftMostSpanForWord(words[0])
      assign.spids.append(left_spid)  # no keyword spid to skip past
      return assign

    kind, kw_token = word_.KeywordToken(suffix_words[0])

    if kind == Kind.ControlFlow:
      if block:
        p_die("Unexpected block", span_id=block_spid)
      if len(redirects):
        p_die("Control flow shouldn't have redirects", token=kw_token)

      if len(preparsed_list):  # FOO=bar local spam=eggs not allowed
        # TODO: Change location as above
        left_token, _, _, _ = preparsed_list[0]
        p_die("Control flow shouldn't have environment bindings",
              token=left_token)

      # Attach the token for errors.  (ShAssignment may not need it.)
      if len(suffix_words) == 1:
        arg_word = None  # type: Optional[word_t]
      elif len(suffix_words) == 2:
        arg_word = suffix_words[1]
      else:
        p_die('Unexpected argument to %r', kw_token.val, word=suffix_words[2])

      return command.ControlFlow(kw_token, arg_word)

    if not block:  # Only expand aliases if we didn't get a block.
      # If any expansions were detected, then parse again.
      expanded_node = self._MaybeExpandAliases(suffix_words)
      if expanded_node:
        # Attach env bindings and redirects to the expanded node.
        more_env = []  # type: List[env_pair]
        _AppendMoreEnv(preparsed_list, more_env)
        exp = command.ExpandedAlias(expanded_node, redirects, more_env)
        return exp

    # TODO check that we don't have env1=x x[1]=y env2=z here.

    # FOO=bar printenv.py FOO
    node = _MakeSimpleCommand(preparsed_list, suffix_words, redirects, block)
    return node

  def ParseBraceGroup(self):
    # type: () -> command__BraceGroup
    """
    brace_group      : LBrace command_list RBrace ;
    """
    left_spid = _KeywordSpid(self.cur_word)
    self._Eat(Id.Lit_LBrace)

    c_list = self._ParseCommandList()

    # Not needed
    #right_spid = word_.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.Lit_RBrace)

    node = command.BraceGroup(c_list.children, None)  # no redirects yet
    node.spids.append(left_spid)
    return node

  def ParseDoGroup(self):
    # type: () -> command__DoGroup
    """
    Used by ForEach, ForExpr, While, Until.  Should this be a Do node?

    do_group         : Do command_list Done ;          /* Apply rule 6 */
    """
    self._Eat(Id.KW_Do)
    do_spid = _KeywordSpid(self.cur_word)  # Must come AFTER _Eat

    c_list = self._ParseCommandList()  # could be any thing

    self._Eat(Id.KW_Done)
    done_spid = _KeywordSpid(self.cur_word)  # after _Eat

    node = command.DoGroup(c_list.children, None)  # no redirects yet
    node.spids.append(do_spid)
    node.spids.append(done_spid)
    return node

  def ParseForWords(self):
    # type: () -> Tuple[List[compound_word], int]
    """
    for_words        : WORD* for_sep
                     ;
    for_sep          : ';' newline_ok
                     | NEWLINES
                     ;
    """
    words = []  # type: List[compound_word]
    # The span_id of any semi-colon, so we can remove it.
    semi_spid = runtime.NO_SPID

    while True:
      self._Peek()
      if self.c_id == Id.Op_Semi:
        tok = cast(Token, self.cur_word)
        semi_spid = tok.span_id
        self._Next()
        self._NewlineOk()
        break
      elif self.c_id == Id.Op_Newline:
        self._Next()
        break
      elif self.parse_opts.parse_brace and self.c_id == Id.Lit_LBrace:
        break

      if self.cur_word.tag_() != word_e.Compound:
        # TODO: Can we also show a pointer to the 'for' keyword?
        p_die('Invalid word in for loop', word=self.cur_word)

      w2 = cast(compound_word, self.cur_word)
      words.append(w2)
      self._Next()
    return words, semi_spid

  def _ParseForExprLoop(self):
    # type: () -> command__ForExpr
    """
    for (( init; cond; update )) for_sep? do_group
    """
    node = self.w_parser.ReadForExpression()
    self._Next()

    self._Peek()
    if self.c_id == Id.Op_Semi:
      self._Next()
      self._NewlineOk()
    elif self.c_id == Id.Op_Newline:
      self._Next()
    elif self.c_id == Id.KW_Do:  # missing semicolon/newline allowed
      pass
    elif self.c_id == Id.Lit_LBrace:  # does NOT require parse_brace
      pass
    else:
      p_die('Invalid word after for expression', word=self.cur_word)

    if self.c_id == Id.Lit_LBrace:
      node.body = self.ParseBraceGroup()
    else:
      node.body = self.ParseDoGroup()
    return node

  def _ParseForEachLoop(self, for_spid):
    # type: (int) -> command__ForEach
    node = command.ForEach()
    node.do_arg_iter = False
    node.spids.append(for_spid)  # for $LINENO and error fallback

    ok, iter_name, quoted = word_.StaticEval(self.cur_word)
    if not ok or quoted:
      p_die("Loop variable name should be a constant", word=self.cur_word)
    if not match.IsValidVarName(iter_name):
      p_die("Invalid loop variable name", word=self.cur_word)
    node.iter_name = iter_name
    self._Next()  # skip past name

    self._NewlineOk()

    in_spid = runtime.NO_SPID
    semi_spid = runtime.NO_SPID

    self._Peek()
    if self.c_id == Id.KW_In:
      self._Next()  # skip in

      # TODO: Do _Peek() here?
      in_spid = word_.LeftMostSpanForWord(self.cur_word) + 1
      iter_words, semi_spid = self.ParseForWords()

      words2 = braces.BraceDetectAll(iter_words)
      words3 = word_.TildeDetectAll(words2)
      node.iter_words = words3

    elif self.c_id == Id.Op_Semi:  # for x; do
      node.do_arg_iter = True  # implicit for loop
      self._Next()

    elif self.c_id == Id.KW_Do:
      node.do_arg_iter = True  # implicit for loop
      # do not advance

    else:  # for foo BAD
      p_die('Unexpected word after for loop variable', word=self.cur_word)

    self._Peek()
    if self.c_id == Id.Lit_LBrace:  # parse_opts.parse_brace must be on
      node.body = self.ParseBraceGroup()
    else:
      node.body = self.ParseDoGroup()

    node.spids.append(in_spid)
    node.spids.append(semi_spid)
    return node

  def ParseFor(self):
    # type: () -> command_t
    """
    for_clause : For for_name newline_ok (in for_words? for_sep)? do_group ;
               | For '((' ... TODO
    """
    for_spid = _KeywordSpid(self.cur_word)
    self._Eat(Id.KW_For)

    if self.w_parser.LookAhead() == Id.Op_LParen:
      # for (x in y) { }
      # NOTE: parse_paren NOT required since it would have been a syntax error.
      lvalue, iterable, _ = (
          self.parse_ctx.ParseOilForExpr(self.lexer, grammar_nt.oil_for)
      )
      self._Peek()
      if self.c_id == Id.Lit_LBrace:
        body = self.ParseBraceGroup()  # type: command_t
      else:
        body = self.ParseDoGroup()
      return command.OilForIn(lvalue, iterable, body)
    else:
      self._Peek()
      if self.c_id == Id.Op_DLeftParen:
        # for (( i = 0; i < 10; i++)
        n1 = self._ParseForExprLoop()
        n1.redirects = self._ParseRedirectList()
        return n1
      else:
        # for x in a b; do echo hi; done
        n2 = self._ParseForEachLoop(for_spid)
        n2.redirects = self._ParseRedirectList()
        return n2

  def ParseWhileUntil(self, keyword):
    # type: (Token) -> command__WhileUntil
    """
    while_clause     : While command_list do_group ;
    until_clause     : Until command_list do_group ;
    """
    self._Next()  # skip keyword

    if self.parse_opts.parse_paren and self.w_parser.LookAhead() == Id.Op_LParen:
      enode, _ = self.parse_ctx.ParseOilExpr(self.lexer, grammar_nt.oil_expr)
      # NOTE: OilCondition could have spids of ( and ) ?
      cond_list = [command.OilCondition(enode)]  # type: List[command_t]
    else:
      self.allow_block = False
      cond = self._ParseCommandList()
      self.allow_block = True
      cond_list = cond.children

    # NOTE: The LSTs will be different for Oil and OSH, but the execution
    # should be unchanged.  To be sure we should desugar.
    self._Peek()
    if self.parse_opts.parse_brace and self.c_id == Id.Lit_LBrace:
      # while test -f foo {
      body_node = self.ParseBraceGroup()  # type: command_t
    else:
      body_node = self.ParseDoGroup()

    node = command.WhileUntil(keyword, cond_list, body_node, None)  # no redirects yet
    node.spids.append(keyword.span_id)  # e.g. for errexit message
    return node

  def ParseCaseItem(self):
    # type: () -> case_arm
    """
    case_item: '('? pattern ('|' pattern)* ')'
               newline_ok command_term? trailer? ;
    """
    self.lexer.PushHint(Id.Op_RParen, Id.Right_CasePat)

    left_spid = word_.LeftMostSpanForWord(self.cur_word)
    if self.c_id == Id.Op_LParen:
      self._Next()

    pat_words = []  # type: List[word_t]
    while True:
      self._Peek()
      pat_words.append(self.cur_word)
      self._Next()

      self._Peek()
      if self.c_id == Id.Op_Pipe:
        self._Next()
      else:
        break

    rparen_spid = word_.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.Right_CasePat)
    self._NewlineOk()

    if self.c_id not in (Id.Op_DSemi, Id.KW_Esac):
      c_list = self._ParseCommandTerm()
      action_children = c_list.children
    else:
      action_children = []

    dsemi_spid = runtime.NO_SPID
    last_spid = runtime.NO_SPID
    self._Peek()
    if self.c_id == Id.KW_Esac:
      last_spid = word_.LeftMostSpanForWord(self.cur_word)
    elif self.c_id == Id.Op_DSemi:
      dsemi_spid = word_.LeftMostSpanForWord(self.cur_word)
      self._Next()
    else:
      # Happens on EOF
      p_die('Expected ;; or esac', word=self.cur_word)

    self._NewlineOk()

    spids = [left_spid, rparen_spid, dsemi_spid, last_spid]
    arm = syntax_asdl.case_arm(pat_words, action_children, spids)
    return arm

  def ParseCaseList(self, arms):
    # type: (List[case_arm]) -> None
    """
    case_list: case_item (DSEMI newline_ok case_item)* DSEMI? newline_ok;
    """
    self._Peek()

    while True:
      # case item begins with a command word or (
      if self.c_id == Id.KW_Esac:
        break
      if self.parse_opts.parse_brace and self.c_id == Id.Lit_RBrace:
        break
      if self.c_kind != Kind.Word and self.c_id != Id.Op_LParen:
        break
      arm = self.ParseCaseItem()

      arms.append(arm)
      self._Peek()
      # Now look for DSEMI or ESAC

  def ParseCase(self):
    # type: () -> command__Case
    """
    case_clause      : Case WORD newline_ok in newline_ok case_list? Esac ;
    """
    case_node = command.Case()

    case_spid = _KeywordSpid(self.cur_word)
    self._Next()  # skip case

    self._Peek()
    case_node.to_match = self.cur_word
    self._Next()

    self._NewlineOk()
    in_spid = word_.LeftMostSpanForWord(self.cur_word)
    self._Peek()
    if self.parse_opts.parse_brace and self.c_id == Id.Lit_LBrace:
      self._Next()
    else:
      self._Eat(Id.KW_In)
    self._NewlineOk()

    if self.c_id != Id.KW_Esac:  # empty case list
      self.ParseCaseList(case_node.arms)
      # TODO: should it return a list of nodes, and extend?
      self._Peek()

    esac_spid = word_.LeftMostSpanForWord(self.cur_word)
    self._Peek()
    if self.parse_opts.parse_brace and self.c_id == Id.Lit_RBrace:
      self._Next()
    else:
      self._Eat(Id.KW_Esac)
    self._Next()

    case_node.spids.append(case_spid)
    case_node.spids.append(in_spid)
    case_node.spids.append(esac_spid)
    return case_node

  def _ParseOilElifElse(self, if_node):
    # type: (command__If) -> None
    """
    if test -f foo {
      echo foo
    } elif test -f bar; test -f spam {
  # ^ we parsed up to here
      echo bar
    } else {
      echo none
    }
    """
    arms = if_node.arms

    while self.c_id == Id.KW_Elif:
      elif_spid = word_.LeftMostSpanForWord(self.cur_word)
      self._Next()  # skip elif
      if self.parse_opts.parse_paren and self.w_parser.LookAhead() == Id.Op_LParen:
        enode, _ = self.parse_ctx.ParseOilExpr(self.lexer, grammar_nt.oil_expr)
        # NOTE: OilCondition could have spids of ( and ) ?
        cond_list = [command.OilCondition(enode)]  # type: List[command_t]
      else:
        self.allow_block = False
        cond = self._ParseCommandList()
        self.allow_block = True
        cond_list = cond.children

      body = self.ParseBraceGroup()

      arm = syntax_asdl.if_arm(cond_list, body.children, [elif_spid])
      arms.append(arm)

    self._Peek()
    if self.c_id == Id.KW_Else:
      else_spid = word_.LeftMostSpanForWord(self.cur_word)
      self._Next()
      body = self.ParseBraceGroup()
      if_node.else_action = body.children
    else:
      else_spid = runtime.NO_SPID

    if_node.spids.append(else_spid)

  def _ParseOilIf(self, if_spid, cond_list):
    # type: (int, List[command_t]) -> command__If
    """
    if test -f foo {
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
    Lit_RBrace?  Maybe this is pre-parsing step in teh WordParser?
    """
    if_node = command.If()

    body1 = self.ParseBraceGroup()
    # Every arm has 1 spid, unlike shell-style
    # TODO: We could get the spids from the brace group.
    arm = syntax_asdl.if_arm(cond_list, body1.children, [if_spid])

    if_node.arms.append(arm)

    self._Peek()
    if self.c_id in (Id.KW_Elif, Id.KW_Else):
      self._ParseOilElifElse(if_node)
    else:
      if_node.spids.append(runtime.NO_SPID)  # no else spid
    # the whole if node has the 'else' spid, unlike shell-style there's no 'fi'
    # spid because that's in the BraceGroup.
    return if_node

  def _ParseElifElse(self, if_node):
    # type: (command__If) -> None
    """
    else_part: (Elif command_list Then command_list)* Else command_list ;
    """
    arms = if_node.arms

    self._Peek()
    while self.c_id == Id.KW_Elif:
      elif_spid = word_.LeftMostSpanForWord(self.cur_word)

      self._Next()  # skip elif
      cond = self._ParseCommandList()

      then_spid = word_.LeftMostSpanForWord(self.cur_word)
      self._Eat(Id.KW_Then)

      body = self._ParseCommandList()

      arm = syntax_asdl.if_arm(cond.children, body.children, [elif_spid, then_spid])
      arms.append(arm)

    if self.c_id == Id.KW_Else:
      else_spid = word_.LeftMostSpanForWord(self.cur_word)
      self._Next()
      body = self._ParseCommandList()
      if_node.else_action = body.children
    else:
      else_spid = runtime.NO_SPID

    if_node.spids.append(else_spid)

  def ParseIf(self):
    # type: () -> command__If
    """
    if_clause        : If command_list Then command_list else_part? Fi ;
    """
    if_spid = _KeywordSpid(self.cur_word)
    if_node = command.If()
    self._Next()  # skip if

    # Remove ambiguity with if cd / {
    if self.parse_opts.parse_paren and self.w_parser.LookAhead() == Id.Op_LParen:
      enode, _ = self.parse_ctx.ParseOilExpr(self.lexer, grammar_nt.oil_expr)
      # NOTE: OilCondition could have spids of ( and ) ?
      cond_list = [command.OilCondition(enode)]  # type: List[command_t]
    else:
      self.allow_block = False
      cond = self._ParseCommandList()
      self.allow_block = True
      cond_list = cond.children

    self._Peek()
    if self.parse_opts.parse_brace and self.c_id == Id.Lit_LBrace:
      # if foo {
      return self._ParseOilIf(if_spid, cond_list)

    then_spid = word_.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.KW_Then)
    body = self._ParseCommandList()

    arm = syntax_asdl.if_arm(cond_list, body.children, [if_spid, then_spid])
    if_node.arms.append(arm)

    if self.c_id in (Id.KW_Elif, Id.KW_Else):
      self._ParseElifElse(if_node)
    else:
      if_node.spids.append(runtime.NO_SPID)  # no else spid

    fi_spid = word_.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.KW_Fi)

    if_node.spids.append(fi_spid)
    return if_node

  def ParseTime(self):
    # type: () -> command_t
    """
    time [-p] pipeline

    According to bash help.
    """
    time_spid = _KeywordSpid(self.cur_word)
    self._Next()  # skip time
    pipeline = self.ParsePipeline()
    node = command.TimeBlock(pipeline)
    node.spids.append(time_spid)
    return node

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

                     # Oil extensions
                     | var ...
                     | setvar ...
                     | set ..>
                     ;
    """
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
      # redirects, but Oil for doesn't.
      return self.ParseFor()
    if self.c_id in (Id.KW_While, Id.KW_Until):
      keyword = _KeywordToken(self.cur_word)
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
      n7 = self.ParseDParen()
      n7.redirects = self._ParseRedirectList()
      return n7

    # bash extensions: no redirects
    if self.c_id == Id.KW_Time:
      return self.ParseTime()

    # Oil extensions
    if self.c_id == Id.KW_Var:
      kw_token = word_.LiteralToken(self.cur_word)
      self._Next()
      return self.w_parser.ParseVarDecl(kw_token)

    if self.c_id == Id.KW_SetVar:
      kw_token = word_.LiteralToken(self.cur_word)
      self._Next()
      return self.w_parser.ParsePlaceMutation(kw_token)

    if self.parse_opts.parse_set and self.c_id == Id.KW_Set:
      kw_token = word_.LiteralToken(self.cur_word)
      self._Next()
      return self.w_parser.ParsePlaceMutation(kw_token)

    # Happens in function body, e.g. myfunc() oops
    p_die('Unexpected word while parsing compound command', word=self.cur_word)
    assert False  # for MyPy

  def ParseFunctionDef(self):
    # type: () -> command__ShFunction
    """
    function_header : fname '(' ')'
    function_def     : function_header newline_ok function_body ;

    Precondition: Looking at the function name.
    Post condition:

    NOTE: There is an ambiguity with:

    function foo ( echo hi ) and
    function foo () ( echo hi )

    Bash only accepts the latter, though it doesn't really follow a grammar.
    """
    left_spid = word_.LeftMostSpanForWord(self.cur_word)

    cur_word = cast(compound_word, self.cur_word)  # caller ensures validity
    name = word_.ShFunctionName(cur_word)
    if len(name) == 0:
      p_die('Invalid function name', word=cur_word)

    self._Next()  # skip function name

    # Must be true beacuse of lookahead
    self._Peek()
    assert self.c_id == Id.Op_LParen, self.cur_word

    self.lexer.PushHint(Id.Op_RParen, Id.Right_ShFunction)
    self._Next()

    self._Eat2(Id.Right_ShFunction, 'Expected ) in function definition')

    after_name_spid = word_.LeftMostSpanForWord(self.cur_word) + 1

    self._NewlineOk()

    func = command.ShFunction()
    func.name = name
    func.body = self.ParseCompoundCommand()

    func.spids.append(left_spid)
    func.spids.append(after_name_spid)
    return func

  def ParseKshFunctionDef(self):
    # type: () -> command__ShFunction
    """
    ksh_function_def : 'function' fname ( '(' ')' )? newline_ok function_body
    """
    left_spid = word_.LeftMostSpanForWord(self.cur_word)

    self._Next()  # skip past 'function'
    self._Peek()

    cur_word = cast(compound_word, self.cur_word)  # caller ensures validity
    name = word_.ShFunctionName(cur_word)
    if len(name) == 0:
      p_die('Invalid KSH-style function name', word=cur_word)

    after_name_spid = word_.LeftMostSpanForWord(self.cur_word) + 1
    self._Next()  # skip past 'function name

    self._Peek()
    if self.c_id == Id.Op_LParen:
      self.lexer.PushHint(Id.Op_RParen, Id.Right_ShFunction)
      self._Next()
      self._Eat(Id.Right_ShFunction)
      # Change it: after )
      after_name_spid = word_.LeftMostSpanForWord(self.cur_word) + 1

    self._NewlineOk()

    func = command.ShFunction()
    func.name = name
    func.body = self.ParseCompoundCommand()

    func.spids.append(left_spid)
    func.spids.append(after_name_spid)
    return func

  def ParseOilProc(self):
    # type: () -> command__Proc
    node = command.Proc()
    self.w_parser.ParseProc(node)

    self._Next()
    self.return_expr = True
    node.body = self.ParseBraceGroup()
    self.return_expr = False
    # No redirects for Oil procs (only at call site)

    return node

  def ParseOilFunc(self):
    # type: () -> command__Func
    node = command.Func()
    self.w_parser.ParseFunc(node)

    self._Next()
    self.return_expr = True
    node.body = self.ParseBraceGroup()
    self.return_expr = False
    # No redirects for Oil funcs (only at call site)

    return node

  def ParseCoproc(self):
    # type: () -> command_t
    """
    TODO: command__Coproc?
    """
    raise NotImplementedError()

  def ParseSubshell(self):
    # type: () -> command__Subshell
    left_spid = word_.LeftMostSpanForWord(self.cur_word)
    self._Next()  # skip past (

    # Ensure that something $( (cd / && pwd) ) works.  If ) is already on the
    # translation stack, we want to delay it.

    self.lexer.PushHint(Id.Op_RParen, Id.Right_Subshell)

    c_list = self._ParseCommandList()
    node = command.Subshell(c_list, None)  # no redirects yet

    right_spid = word_.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.Right_Subshell)

    node.spids.append(left_spid)
    node.spids.append(right_spid)
    return node

  def ParseDBracket(self):
    # type: () -> command__DBracket
    """
    Pass the underlying word parser off to the boolean expression parser.
    """
    left_spid = word_.LeftMostSpanForWord(self.cur_word)
    # TODO: Test interactive.  Without closing ]], you should get > prompt
    # (PS2)

    self._Next()  # skip [[
    b_parser = bool_parse.BoolParser(self.w_parser)
    bnode = b_parser.Parse()  # May raise
    right_spid = word_.LeftMostSpanForWord(self.cur_word)

    node = command.DBracket(bnode, None)  # no redirects yet
    node.spids.append(left_spid)
    node.spids.append(right_spid)
    return node

  def ParseDParen(self):
    # type: () -> command__DParen
    left_spid = word_.LeftMostSpanForWord(self.cur_word)

    self._Next()  # skip ((
    anode, right_spid = self.w_parser.ReadDParen()
    assert anode is not None

    node = command.DParen(anode, None)  # no redirects yet
    node.spids.append(left_spid)
    node.spids.append(right_spid)
    return node

  def ParseCommand(self):
    # type: () -> command_t
    """
    command          : simple_command
                     | compound_command   # Oil edit: io_redirect* folded in
                     | function_def
                     | ksh_function_def
                     ;
    """
    self._Peek()

    if self._AtSecondaryKeyword():
      p_die('Unexpected word when parsing command', word=self.cur_word)

    if self.c_id == Id.KW_Function:
      return self.ParseKshFunctionDef()
    if self.c_id == Id.KW_Func:
      return self.ParseOilFunc()
    if self.c_id == Id.KW_Proc:
      return self.ParseOilProc()

    if self.c_id in (
        Id.KW_DLeftBracket, Id.Op_DLeftParen, Id.Op_LParen, Id.Lit_LBrace,
        Id.KW_For, Id.KW_While, Id.KW_Until, Id.KW_If, Id.KW_Case, Id.KW_Time,
        Id.KW_Var, Id.KW_SetVar):
      return self.ParseCompoundCommand()
    if self.parse_opts.parse_set and self.c_id == Id.KW_Set:
      return self.ParseCompoundCommand()

    # return (x+y).  NOTE: We're not calling ParseCompoundCommand.  That
    # doesn't seem to matter except for f() return x (no braces), which we
    # don't care about.
    if self.return_expr and self.c_id == Id.ControlFlow_Return:
      keyword = _KeywordToken(self.cur_word)
      self._Next()
      enode = self.w_parser.ParseCommandExpr()
      return command.Return(keyword, enode)

    # TODO: Can we have parse_do here?  For do obj.method()
    if self.c_id in (Id.KW_Pass, Id.KW_Do, Id.Lit_Equals):
      keyword = _KeywordToken(self.cur_word)
      self._Next()
      enode = self.w_parser.ParseCommandExpr()
      return command.Expr(speck(keyword.id, keyword.span_id), enode)

    # NOTE: I added this to fix cases in parse-errors.test.sh, but it doesn't
    # work because Lit_RBrace is in END_LIST below.

    # TODO: KW_Do is also invalid here.
    if self.c_id == Id.Lit_RBrace:
      p_die('Unexpected right brace', word=self.cur_word)

    if self.c_kind == Kind.Redir:  # Leading redirect
      return self.ParseSimpleCommand()

    if self.c_kind == Kind.Word:
      cur_word = cast(compound_word, self.cur_word)  # ensured by Kind.Word

      # NOTE: At the top level, only Token and Compound are possible.
      # Can this be modelled better in the type system, removing asserts?
      if (self.w_parser.LookAhead() == Id.Op_LParen and
          not word_.IsVarLike(cur_word)):
          return self.ParseFunctionDef()  # f() { echo; }  # function

      # Parse x = 1+2*3 when parse_equals is set.
      parts = cur_word.parts
      if self.parse_opts.parse_equals and len(parts) == 1:
        part0 = parts[0]
        if part0.tag_() == word_part_e.Literal:
          tok = cast(Token, part0)
          # NOTE: tok.id should be Lit_Chars, but that check is redundant
          if (match.IsValidVarName(tok.val) and
              self.w_parser.LookAhead() == Id.Lit_Equals):
            enode = self.w_parser.ParseBareDecl()
            self._Next()  # Somehow this is necessary

            # TODO: Use BareDecl here.  Well, do that when we treat it as const
            # or lazy.
            return command.VarDecl(None, [name_type(tok, None)], enode)

      # echo foo
      # f=(a b c)  # array
      # array[1+2]+=1
      return self.ParseSimpleCommand()

    if self.c_kind == Kind.Eof:
      p_die("Unexpected EOF while parsing command", word=self.cur_word)

    # NOTE: This only happens in batch mode in the second turn of the loop!
    # e.g. )
    p_die("Invalid word while parsing command", word=self.cur_word)
    assert False  # for MyPy

  def ParsePipeline(self):
    # type: () -> command_t
    """
    pipeline         : Bang? command ( '|' newline_ok command )* ;
    """
    negated = False

    # For blaming failures
    pipeline_spid = runtime.NO_SPID

    self._Peek()
    if self.c_id == Id.KW_Bang:
      pipeline_spid = word_.LeftMostSpanForWord(self.cur_word)
      negated = True
      self._Next()

    child = self.ParseCommand()
    assert child is not None

    children = [child]

    self._Peek()
    if self.c_id not in (Id.Op_Pipe, Id.Op_PipeAmp):
      if negated:
        no_stderrs = []  # type: List[int]
        node = command.Pipeline(children, negated, no_stderrs)
        node.spids.append(pipeline_spid)
        return node
      else:
        return child

    pipe_index = 0
    stderr_indices = []  # type: List[int]

    if self.c_id == Id.Op_PipeAmp:
      stderr_indices.append(pipe_index)
    pipe_index += 1

    while True:
      # Set it to the first | if it isn't already set.
      if pipeline_spid == runtime.NO_SPID:
        pipeline_spid = word_.LeftMostSpanForWord(self.cur_word)

      self._Next()  # skip past Id.Op_Pipe or Id.Op_PipeAmp
      self._NewlineOk()

      child = self.ParseCommand()
      children.append(child)

      self._Peek()
      if self.c_id not in (Id.Op_Pipe, Id.Op_PipeAmp):
        break

      if self.c_id == Id.Op_PipeAmp:
        stderr_indices.append(pipe_index)
      pipe_index += 1

    node = command.Pipeline(children, negated, stderr_indices)
    node.spids.append(pipeline_spid)
    return node

  def ParseAndOr(self):
    # type: () -> command_t
    """
    and_or           : and_or ( AND_IF | OR_IF ) newline_ok pipeline
                     | pipeline

    Note that it is left recursive and left associative.  We parse it
    iteratively with a token of lookahead.
    """
    child = self.ParsePipeline()
    assert child is not None

    self._Peek()
    if self.c_id not in (Id.Op_DPipe, Id.Op_DAmp):
      return child

    ops = []  # type: List[int]
    op_spids = []  # type: List[int]
    children = [child]

    while True:
      ops.append(self.c_id)
      op_spids.append(word_.LeftMostSpanForWord(self.cur_word))

      self._Next()  # skip past || &&
      self._NewlineOk()

      child = self.ParsePipeline()

      children.append(child)

      self._Peek()
      if self.c_id not in (Id.Op_DPipe, Id.Op_DAmp):
        break

    node = command.AndOr(ops, children)
    node.spids = op_spids
    return node

  # NOTE: _ParseCommandLine and _ParseCommandTerm are similar, but different.

  # At the top level, We want to execute after every line:
  # - to process alias
  # - to process 'exit', because invalid syntax might appear after it

  # But for say a while loop body, we want to parse the whole thing at once, and
  # then execute it.  We don't want to parse it over and over again!

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

      self._Peek()
      if self.c_id in (Id.Op_Semi, Id.Op_Amp):  # also Id.Op_Amp.
        tok = cast(Token, self.cur_word)  # for MyPy
        child = command.Sentence(child, tok)
        self._Next()

        self._Peek()
        if self.c_id in END_LIST:
          done = True

      elif self.c_id in END_LIST:
        done = True

      else:
        # e.g. echo a(b)
        p_die('Unexpected word while parsing command line',
              word=self.cur_word)

      children.append(child)

    # Simplify the AST.
    if len(children) > 1:
      return command.CommandList(children)
    else:
      return children[0]

  def _ParseCommandTerm(self):
    # type: () -> command__CommandList
    """"
    command_term     : and_or (trailer and_or)* ;
    trailer          : sync_op newline_ok
                     | NEWLINES;
    sync_op          : '&' | ';';

    This is handled in imperative style, like _ParseCommandLine.
    Called by _ParseCommandList for all blocks, and also for ParseCaseItem,
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
      self._Peek()

      # Most keywords are valid "first words".  But do/done/then do not BEGIN
      # commands, so they are not valid.
      if self._AtSecondaryKeyword():
        break

      child = self.ParseAndOr()

      self._Peek()
      if self.c_id == Id.Op_Newline:
        self._Next()

        self._Peek()
        if self.c_id in END_LIST:
          done = True

      elif self.c_id in (Id.Op_Semi, Id.Op_Amp):
        tok = cast(Token, self.cur_word)  # for MyPy
        child = command.Sentence(child, tok)
        self._Next()

        self._Peek()
        if self.c_id == Id.Op_Newline:
          self._Next()  # skip over newline

          # Test if we should keep going.  There might be another command after
          # the semi and newline.
          self._Peek()
          if self.c_id in END_LIST:  # \n EOF
            done = True

        elif self.c_id in END_LIST:  # ; EOF
          done = True

      elif self.c_id in END_LIST:  # EOF
        done = True

      # For if test -f foo; test -f bar {
      elif self.parse_opts.parse_brace and self.c_id == Id.Lit_LBrace:
        done = True

      else:
        #p_die("OOPS", word=self.cur_word)
        pass  # e.g. "} done", "fi fi", ") fi", etc. is OK

      children.append(child)

    self._Peek()

    return command.CommandList(children)

  # TODO: Make this private.
  def _ParseCommandList(self):
    # type: () -> command__CommandList
    """
    command_list     : newline_ok command_term trailer? ;

    This one is called by all the compound commands.  It's basically a command
    block.

    NOTE: Rather than translating the CFG directly, the code follows a style
    more like this: more like this: (and_or trailer)+.  It makes capture
    easier.
    """
    self._NewlineOk()
    node = self._ParseCommandTerm()
    return node

  def ParseLogicalLine(self):
    # type: () -> command_t
    """Parse a single line for main_loop.

    A wrapper around _ParseCommandLine().  Similar but not identical to
    _ParseCommandList() and ParseCommandSub().

    Raises:
      ParseError
    """
    self._NewlineOk()
    self._Peek()
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
    self._Peek()
    if self.c_id == Id.Op_Newline:
      return parse_result.EmptyLine()
    if self.c_id == Id.Eof_Real:
      return parse_result.Eof()

    node = self._ParseCommandLine()
    return parse_result.Node(node)

  def ParseCommandSub(self):
    # type: () -> command_t
    """Parse $(echo hi) and `echo hi` for word_parse.py.

    They can have multiple lines, like this:
    echo $(
      echo one
      echo two
    )
    """
    self._NewlineOk()

    if self.c_kind == Kind.Eof:  # e.g. $()
      return command.NoOp()

    # This calls ParseAndOr(), but I think it should be a loop that calls
    # _ParseCommandLine(), like oil.InteractiveLoop.
    node = self._ParseCommandTerm()
    return node

  def CheckForPendingHereDocs(self):
    # type: () -> None
    # NOTE: This happens when there is no newline at the end of a file, like
    # osh -c 'cat <<EOF'
    if len(self.pending_here_docs):
      node = self.pending_here_docs[0]  # Just show the first one?
      p_die('Unterminated here doc began here', word=node.here_begin)
