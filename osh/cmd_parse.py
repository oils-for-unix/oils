#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
"""
cmd_parse.py - Parse high level shell commands.
"""

from asdl import const

from core import braces
from core import reader
from core import word
from core import util

from osh import match
from osh.meta import ast, Id, Kind, types
from osh.bool_parse import BoolParser

log = util.log
p_die = util.p_die
command_e = ast.command_e
word_e = ast.word_e
assign_op_e = ast.assign_op_e
lex_mode_e = types.lex_mode_e


def _ReadHereLines(line_reader, h, delimiter):
  # NOTE: We read all lines at once, instead of parsing line-by-line,
  # because of cases like this:
  # cat <<EOF
  # 1 $(echo 2
  # echo 3) 4
  # EOF
  here_lines = []
  last_line = None
  while True:
    line_id, line, unused_offset = line_reader.GetLine()
    assert unused_offset == 0

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
    if h.op.id == Id.Redir_DLessDash:
      n = len(line)
      i = 0
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


def _MakeLiteralHereLines(here_lines, arena):
  """Create a line_span and a token for each line."""
  tokens = []
  for line_id, line, start_offset in here_lines:
    line_span = ast.line_span(line_id, start_offset, len(line))
    span_id = arena.AddLineSpan(line_span)
    t = ast.token(Id.Lit_Chars, line[start_offset:], span_id)
    tokens.append(t)
  return [ast.LiteralPart(t) for t in tokens]


def _ParseHereDocBody(parse_ctx, h, line_reader, arena):
  """Fill in attributes of a pending here doc node."""
  # "If any character in word is quoted, the delimiter shall be formed by
  # performing quote removal on word, and the here-document lines shall not
  # be expanded. Otherwise, the delimiter shall be the word itself."
  # NOTE: \EOF counts, or even E\OF
  ok, delimiter, delim_quoted = word.StaticEval(h.here_begin)
  if not ok:
    p_die('Invalid here doc delimiter', word=h.here_begin)

  here_lines, last_line = _ReadHereLines(line_reader, h, delimiter)

  parts = []
  if delim_quoted:  # << 'EOF'
    # LiteralPart for each line.
    h.stdin_parts = _MakeLiteralHereLines(here_lines, arena)
  else:
    line_reader = reader.HereDocLineReader(here_lines, arena)
    w_parser = parse_ctx.MakeWordParserForHereDoc(line_reader)
    w_parser.ReadHereDocBody(h.stdin_parts)  # fills this in

  end_line_id, end_line, end_pos = last_line

  # Create a span with the end terminator.  Maintains the invariant that
  # the spans "add up".
  line_span = ast.line_span(end_line_id, end_pos, len(end_line))
  h.here_end_span_id = arena.AddLineSpan(line_span)


def _AppendMoreEnv(prefix_bindings, more_env):
  """Helper to modify a SimpleCommand node."""
  for name, op, val, left_spid in prefix_bindings:
    if op != assign_op_e.Equal:
      # NOTE: Attributing to RHS, since we don't have one for the op.
      p_die('Expected = in environment binding, got +=', word=val)
    pair = ast.env_pair(name, val)
    pair.spids.append(left_spid)
    more_env.append(pair)


def _MakeAssignment(assign_kw, suffix_words):
  """Create an ast.Assignment node from a keyword and a list of words."""

  # First parse flags, e.g. -r -x -a -A.  None of the flags have arguments.
  flags = []
  n = len(suffix_words)
  i = 1
  while i < n:
    w = suffix_words[i]
    ok, static_val, quoted = word.StaticEval(w)
    if not ok or quoted:
      break  # can't statically evaluate

    if static_val.startswith('-'):
      flags.append(static_val)
    else:
      break  # not a flag, rest are args
    i += 1

  # Now parse bindings or variable names
  assignments = []
  while i < n:
    w = suffix_words[i]
    left_spid = word.LeftMostSpanForWord(w)
    kov = word.LooksLikeAssignment(w)
    if kov:
      k, op, v = kov
      t = word.TildeDetect(v)
      if t:
        # t is an unevaluated word with TildeSubPart
        a = (k, op, t, left_spid)
      else:
        a = (k, op, v, left_spid)  # v is unevaluated word
    else:
      # In aboriginal in variables/sources: export_if_blank does export "$1".
      # We should allow that.

      # Parse this differently then?
      # dynamic-export?
      # It sets global variables.
      ok, static_val, quoted = word.StaticEval(w)
      if not ok or quoted:
        p_die("Variable names must be unquoted constants", word=w)

      # No value is equivalent to ''
      if not match.IsValidVarName(static_val):
        p_die('Invalid variable name %r', static_val, word=w)

      a = (static_val, assign_op_e.Equal, None, left_spid)

    assignments.append(a)
    i += 1

  # TODO: Also make with LhsIndexedName
  pairs = []
  for lhs, op, rhs, spid in assignments:
    p = ast.assign_pair(ast.LhsName(lhs), op, rhs)
    p.spids.append(spid)
    pairs.append(p)

  node = ast.Assignment(assign_kw, flags, pairs)

  return node


def _SplitSimpleCommandPrefix(words):
  """Second pass of SimpleCommand parsing: look for assignment words."""
  prefix_bindings = []
  suffix_words = []

  done_prefix = False
  for w in words:
    if done_prefix:
      suffix_words.append(w)
      continue

    left_spid = word.LeftMostSpanForWord(w)

    kov = word.LooksLikeAssignment(w)
    if kov:
      k, op, v = kov
      t = word.TildeDetect(v)
      if t:
        # t is an unevaluated word with TildeSubPart
        prefix_bindings.append((k, op, t, left_spid))
      else:
        prefix_bindings.append((k, op, v, left_spid))  # v is unevaluated word
    else:
      done_prefix = True
      suffix_words.append(w)

  return prefix_bindings, suffix_words


def _MakeSimpleCommand(prefix_bindings, suffix_words, redirects):
  """Create an ast.SimpleCommand node."""

  # FOO=(1 2 3) ls is not allowed
  for k, _, v, _ in prefix_bindings:
    if word.HasArrayPart(v):
      p_die("Environment bindings can't contain array literals", word=v)

  # echo FOO=(1 2 3) is not allowed
  # NOTE: Other checks can be inserted here.  Can resolve builtins,
  # functions, aliases, static PATH, etc.
  for w in suffix_words:
    kov = word.LooksLikeAssignment(w)
    if kov:
      _, _, v = kov
      if word.HasArrayPart(v):
        p_die("Commands can't contain array literals", word=w)

  # NOTE: # In bash, {~bob,~jane}/src works, even though ~ isn't the leading
  # character of the initial word.
  # However, this means we must do tilde detection AFTER brace EXPANSION, not
  # just after brace DETECTION like we're doing here.
  # The BracedWordTree instances have to be expanded into CompoundWord
  # instances for the tilde detection to work.
  words2 = braces.BraceDetectAll(suffix_words)
  words3 = word.TildeDetectAll(words2)

  node = ast.SimpleCommand()
  node.words = words3
  node.redirects = redirects
  _AppendMoreEnv(prefix_bindings, node.more_env)
  return node


class CommandParser(object):
  """
  Args:
    word_parse: to get a stream of words
    lexer: for lookahead in function def, PushHint of ()
    line_reader: for here doc
  """
  def __init__(self, parse_ctx, w_parser, lexer_, line_reader, arena=None):
    self.parse_ctx = parse_ctx
    self.w_parser = w_parser  # for normal parsing
    self.lexer = lexer_  # for pushing hints, lookahead to (
    self.line_reader = line_reader  # for here docs
    self.arena = arena or parse_ctx.arena  # for adding here doc and alias spans
    self.aliases = parse_ctx.aliases  # aliases to expand at parse time

    self.Reset()

  def Reset(self):
    """Reset our own internal state.

    Called by the interactive loop.
    """
    self.error_stack = []
    self.completion_stack = []

    # Cursor state set by _Peek()
    self.next_lex_mode = lex_mode_e.OUTER
    self.cur_word = None  # current word
    self.c_kind = Kind.Undefined
    self.c_id = Id.Undefined_Tok

    self.pending_here_docs = []

  def ResetInputObjects(self):
    """Reset the internal state of our inputs.

    Called by the interactive loop.
    """
    self.w_parser.Reset()
    self.lexer.ResetInputObjects()
    self.line_reader.Reset()

  def Error(self):
    return self.error_stack

  def GetCompletionState(self):
    return self.completion_stack

  # NOTE: If our approach to _ExpandAliases isn't sufficient, we could have an
  # expand_alias=True flag here?  We would litter the parser with calls to this
  # like dash and bash.
  #
  # Although it might be possible that you really need to mutate the parser
  # state, and not just provide a parameter to _Next().
  # You might also need a flag to indicate whether the previous expansion ends
  # with ' '.  I didn't see that in dash or bash code.

  def _Next(self, lex_mode=lex_mode_e.OUTER):
    """Helper method."""
    self.next_lex_mode = lex_mode

  def Peek(self):
    """Public method for REPL."""
    self._Peek()
    return self.cur_word

  def _Peek(self):
    """Helper method.

    Returns True for success and False on error.  Error examples: bad command
    sub word, or unterminated quoted string, etc.
    """
    if self.next_lex_mode != lex_mode_e.NONE:
      w = self.w_parser.ReadWord(self.next_lex_mode)
      assert w is not None

      # Here docs only happen in command mode, so other kinds of newlines don't
      # count.
      if w.tag == word_e.TokenWord and w.token.id == Id.Op_Newline:
        for h in self.pending_here_docs:
          _ParseHereDocBody(self.parse_ctx, h, self.line_reader, self.arena)
        del self.pending_here_docs[:]  # No .clear() until Python 3.3.

      self.cur_word = w

      self.c_kind = word.CommandKind(self.cur_word)
      self.c_id = word.CommandId(self.cur_word)
      self.next_lex_mode = lex_mode_e.NONE

  def _Eat(self, c_id):
    """Consume a word of a type.  If it doesn't match, return False.

    Args:
      c_id: either EKeyword.* or a token type like Id.Right_Subshell.
      TODO: Rationalize / type check this.
    """
    self._Peek()
    # TODO: Printing something like KW_Do is not friendly.  We can map
    # backwards using the _KEYWORDS list in osh/lex.py.
    if self.c_id != c_id:
      p_die('Expected word type %s, got %s', c_id,
            word.CommandId(self.cur_word), word=self.cur_word)

    self._Next()

  def _NewlineOk(self):
    """Check for optional newline and consume it."""
    self._Peek()
    if self.c_id == Id.Op_Newline:
      self._Next()
      self._Peek()

  def ParseRedirect(self):
    """
    Problem: You don't know which kind of redir_node to instantiate before
    this?  You could stuff them all in one node, and then have a switch() on
    the type.

    You need different types.
    """
    self._Peek()
    assert self.c_kind == Kind.Redir, self.cur_word

    op = self.cur_word.token

    # For now only supporting single digit descriptor
    first_char = self.cur_word.token.val[0]
    if first_char.isdigit():
      fd = int(first_char)
    else:
      fd = const.NO_INTEGER

    if op.id in (Id.Redir_DLess, Id.Redir_DLessDash):  # here doc
      node = ast.HereDoc()
      node.op = op
      node.fd = fd
      self._Next()

      self._Peek()
      node.here_begin = self.cur_word
      self._Next()

      self.pending_here_docs.append(node)  # will be filled on next newline.

    else:
      node = ast.Redir()
      node.op = op
      node.fd = fd
      self._Next()

      self._Peek()
      if self.c_kind != Kind.Word:
        p_die('Invalid token after redirect operator', word=self.cur_word)

      new_word = word.TildeDetect(self.cur_word)
      node.arg_word = new_word or self.cur_word
      self._Next()

    return node

  def _ParseRedirectList(self):
    """Try parsing any redirects at the cursor.

    This is used for blocks only, not commands.

    Return None on error.
    """
    redirects = []
    while True:
      self._Peek()

      # This prediction needs to ONLY accept redirect operators.  Should we
      # make them a separate TokeNkind?
      if self.c_kind != Kind.Redir:
        break

      node = self.ParseRedirect()
      assert node is not None
      redirects.append(node)
      self._Next()
    return redirects

  def _ScanSimpleCommand(self):
    """First pass: Split into redirects and words."""
    redirects = []
    words = []
    while True:
      self._Peek()
      if self.c_kind == Kind.Redir:
        node = self.ParseRedirect()
        assert node is not None
        redirects.append(node)

      elif self.c_kind == Kind.Word:
        words.append(self.cur_word)

      else:
        break

      self._Next()
    return redirects, words

  def _ExpandAliases(self, words, cur_aliases):
    """Try to expand aliases.

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
      A command node if any aliases were expanded, but None otherwise.
    """
    #log('_ExpandAliases')
    # The last char that we might parse.
    right_spid = word.RightMostSpanForWord(words[-1])
    first_word_str = None  # for error message

    expanded = []
    i = 0
    n = len(words)

    while i < n:
      w = words[i]

      ok, word_str, quoted = word.StaticEval(w)
      if not ok or quoted:
        break

      alias_exp = self.aliases.get(word_str)
      if alias_exp is None:
        break

      # Prevent infinite loops.  This is subtle: we want to prevent infinite
      # expansion of alias echo='echo x'.  But we don't want to prevent
      # expansion of the second word in 'echo echo', so we add 'i' to
      # "cur_aliases".
      if (word_str, i) in cur_aliases:
        break

      if i == 0:
        first_word_str = word_str  # for error message

      #log('%r -> %r', word_str, alias_exp)
      cur_aliases.append((word_str, i))
      expanded.append(alias_exp)
      i += 1


      if not alias_exp.endswith(' '):
        # alias e='echo [ ' is the same expansion as
        # alias e='echo ['
        # The trailing space indicates whether we should continue to expand
        # aliases; it's not part of it.
        expanded.append(' ')
        break  # No more expansions

    if not expanded:  # No expansions; caller does parsing.
      return None

    # We got some expansion.  Now copy the rest of the words.

    # We need each NON-REDIRECT word separately!  For example:
    # $ echo one >out two
    # dash/mksh/zsh go beyond the first redirect!
    while i < n:
      w = words[i]
      left_spid = word.LeftMostSpanForWord(w)
      right_spid = word.RightMostSpanForWord(w)

      # Adapted from tools/osh2oil.py Cursor.PrintUntil
      for span_id in xrange(left_spid, right_spid + 1):
        span = self.arena.GetLineSpan(span_id)
        line = self.arena.GetLine(span.line_id)
        piece = line[span.col : span.col + span.length]
        expanded.append(piece)

      expanded.append(' ')  # Put space back between words.
      i += 1

    code_str = ''.join(expanded)
    lines = code_str.splitlines(True)  # Keep newlines

    line_info = []
    # TODO: Add location information
    self.arena.PushSource(
        '<expansion of alias %r at line %d of %s>' %
        (first_word_str, -1, 'TODO'))
    try:
      for i, line in enumerate(lines):
        line_id = self.arena.AddLine(line, i+1)
        line_info.append((line_id, line, 0))
    finally:
      self.arena.PopSource()

    # TODO: Change name back to VirtualLineReader?
    line_reader = reader.HereDocLineReader(line_info, self.arena)
    _, cp = self.parse_ctx.MakeParser(line_reader)

    try:
      node = cp.ParseCommand(cur_aliases=cur_aliases)
    except util.ParseError as e:
      # Failure to parse alias expansion is a fatal error
      # We don't need more handling here/
      raise

    if 0:
      log('AFTER expansion:')
      from osh import ast_lib
      ast_lib.PrettyPrint(node)
    return node

  # Flags that indicate an assignment should be parsed like a command.
  _ASSIGN_COMMANDS = set([
      (Id.Assign_Declare, '-f'),  # function defs
      (Id.Assign_Declare, '-F'),  # function names
      (Id.Assign_Declare, '-p'),  # print

      (Id.Assign_Typeset, '-f'),
      (Id.Assign_Typeset, '-F'),
      (Id.Assign_Typeset, '-p'),

      (Id.Assign_Local, '-p'),
      (Id.Assign_Readonly, '-p'),
      # Hm 'export -p' is more like a command.  But we're parsing it
      # dynamically now because of some wrappers.
      # Maybe we could change this.
      #(Id.Assign_Export, '-p'),
  ])
  # Flags to parse like assignments: -a -r -x (and maybe -i)

  def ParseSimpleCommand(self, cur_aliases):
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
    result = self._ScanSimpleCommand()
    assert result is not None
    redirects, words = result

    if not words:  # e.g.  >out.txt  # redirect without words
      node = ast.SimpleCommand()
      node.redirects = redirects
      return node

    prefix_bindings, suffix_words = _SplitSimpleCommandPrefix(words)

    if not suffix_words:  # ONE=1 TWO=2  (with no other words)
      if redirects:
        binding1 = prefix_bindings[0]
        _, _, _, spid = binding1
        p_die("Global assignment shouldn't have redirects", span_id=spid)

      pairs = []
      for lhs, op, rhs, spid in prefix_bindings:
        p = ast.assign_pair(ast.LhsName(lhs), op, rhs)
        p.spids.append(spid)
        pairs.append(p)

      node = ast.Assignment(Id.Assign_None, [], pairs)
      left_spid = word.LeftMostSpanForWord(words[0])
      node.spids.append(left_spid)  # no keyword spid to skip past
      return node

    kind, kw_token = word.KeywordToken(suffix_words[0])

    if kind == Kind.Assign:
      # Here we StaticEval suffix_words[1] to see if it's a command like
      # 'typeset -p'.  Then it becomes a SimpleCommand node instead of an
      # Assignment.  Note we're not handling duplicate flags like 'typeset
      # -pf'.  I see this in bashdb (bash debugger) but it can just be changed
      # to 'typeset -p -f'.
      is_command = False
      if len(suffix_words) > 1:
        ok, val, _ = word.StaticEval(suffix_words[1])
        if ok and (kw_token.id, val) in self._ASSIGN_COMMANDS:
          is_command = True

      if is_command:  # declare -f, declare -p, typeset -p, etc.
        node = _MakeSimpleCommand(prefix_bindings, suffix_words,
                                       redirects)
        return node

      else:  # declare str='', declare -a array=()
        if redirects:
          # Attach the error location to the keyword.  It would be more precise
          # to attach it to the
          p_die("Assignments shouldn't have redirects", token=kw_token)

        if prefix_bindings:  # FOO=bar local spam=eggs not allowed
          # Use the location of the first value.  TODO: Use the whole word
          # before splitting.
          _, _, v0, _ = prefix_bindings[0]
          p_die("Assignments shouldn't have environment bindings", word=v0)

        node = _MakeAssignment(kw_token.id, suffix_words)
        assert node is not None
        node.spids.append(kw_token.span_id)
        return node

    elif kind == Kind.ControlFlow:
      if redirects:
        p_die("Control flow shouldn't have redirects", token=kw_token)

      if prefix_bindings:  # FOO=bar local spam=eggs not allowed
        # TODO: Change location as above
        _, _, v0, _ = prefix_bindings[0]
        p_die("Control flow shouldn't have environment bindings", word=v0)

      # Attach the token for errors.  (Assignment may not need it.)
      if len(suffix_words) == 1:
        arg_word = None
      elif len(suffix_words) == 2:
        arg_word = suffix_words[1]
      else:
        p_die('Unexpected argument to %r', kw_token.val, word=suffix_words[2])

      return ast.ControlFlow(kw_token, arg_word)

    else:
      # If any expansions were detected, then parse again.
      node = self._ExpandAliases(suffix_words, cur_aliases)
      if node:
        # NOTE: There are other types of nodes with redirects.  Do they matter?
        if node.tag == command_e.SimpleCommand:
          node.redirects = redirects
          _AppendMoreEnv(prefix_bindings, node.more_env)
        return node

      node = _MakeSimpleCommand(prefix_bindings, suffix_words, redirects)
      return node

  def ParseBraceGroup(self):
    """
    brace_group      : LBrace command_list RBrace ;
    """
    left_spid = word.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.Lit_LBrace)

    c_list = self._ParseCommandList()
    assert c_list is not None

    # Not needed
    #right_spid = word.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.Lit_RBrace)

    node = ast.BraceGroup(c_list.children)
    node.spids.append(left_spid)
    return node

  def ParseDoGroup(self):
    """
    Used by ForEach, ForExpr, While, Until.  Should this be a Do node?

    do_group         : Do command_list Done ;          /* Apply rule 6 */
    """
    self._Eat(Id.KW_Do)
    do_spid = word.LeftMostSpanForWord(self.cur_word)  # after _Eat

    c_list = self._ParseCommandList()  # could be any thing
    assert c_list is not None

    self._Eat(Id.KW_Done)
    done_spid = word.LeftMostSpanForWord(self.cur_word)  # after _Eat

    node = ast.DoGroup(c_list.children)
    node.spids.extend((do_spid, done_spid))
    return node

  def ParseForWords(self):
    """
    for_words        : WORD* for_sep
                     ;
    for_sep          : ';' newline_ok
                     | NEWLINES
                     ;
    """
    words = []
    # The span_id of any semi-colon, so we can remove it.
    semi_spid = const.NO_INTEGER

    while True:
      self._Peek()
      if self.c_id == Id.Op_Semi:
        semi_spid = self.cur_word.token.span_id  # TokenWord
        self._Next()
        self._NewlineOk()
        break
      elif self.c_id == Id.Op_Newline:
        self._Next()
        break
      if self.cur_word.tag != word_e.CompoundWord:
        # TODO: Can we also show a pointer to the 'for' keyword?
        p_die('Invalid word in for loop', word=self.cur_word)

      words.append(self.cur_word)
      self._Next()
    return words, semi_spid

  def _ParseForExprLoop(self):
    """
    for (( init; cond; update )) for_sep? do_group
    """
    node = self.w_parser.ReadForExpression()
    assert node is not None
    self._Next()

    self._Peek()
    if self.c_id == Id.Op_Semi:
      self._Next()
      self._NewlineOk()
    elif self.c_id == Id.Op_Newline:
      self._Next()
    elif self.c_id == Id.KW_Do:  # missing semicolon/newline allowed
      pass
    else:
      p_die('Invalid word after for expression', word=self.cur_word)

    body_node = self.ParseDoGroup()
    assert body_node is not None

    node.body = body_node
    return node

  def _ParseForEachLoop(self):
    node = ast.ForEach()
    node.do_arg_iter = False

    ok, iter_name, quoted = word.StaticEval(self.cur_word)
    if not ok or quoted:
      p_die("Loop variable name should be a constant", word=self.cur_word)
    if not match.IsValidVarName(iter_name):
      p_die("Invalid loop variable name", word=self.cur_word)
    node.iter_name = iter_name
    self._Next()  # skip past name

    self._NewlineOk()

    in_spid = const.NO_INTEGER
    semi_spid = const.NO_INTEGER

    self._Peek()
    if self.c_id == Id.KW_In:
      self._Next()  # skip in

      in_spid = word.LeftMostSpanForWord(self.cur_word) + 1
      iter_words, semi_spid = self.ParseForWords()
      assert iter_words is not None

      words2 = braces.BraceDetectAll(iter_words)
      words3 = word.TildeDetectAll(words2)
      node.iter_words = words3

    elif self.c_id == Id.Op_Semi:
      node.do_arg_iter = True  # implicit for loop
      self._Next()

    elif self.c_id == Id.KW_Do:
      node.do_arg_iter = True  # implicit for loop
      # do not advance

    else:  # for foo BAD
      p_die('Unexpected word after for loop variable', word=self.cur_word)

    node.spids.extend((in_spid, semi_spid))

    body_node = self.ParseDoGroup()
    assert body_node is not None

    node.body = body_node
    return node

  def ParseFor(self):
    """
    for_clause : For for_name newline_ok (in for_words? for_sep)? do_group ;
               | For '((' ... TODO
    """
    self._Eat(Id.KW_For)

    self._Peek()
    if self.c_id == Id.Op_DLeftParen:
      node = self._ParseForExprLoop()
    else:
      node = self._ParseForEachLoop()

    return node

  def ParseWhile(self):
    """
    while_clause     : While command_list do_group ;
    """
    self._Next()  # skip while

    cond_node = self._ParseCommandList()
    assert cond_node is not None

    body_node = self.ParseDoGroup()
    assert body_node is not None

    return ast.While(cond_node.children, body_node)

  def ParseUntil(self):
    """
    until_clause     : Until command_list do_group ;
    """
    self._Next()  # skip until

    cond_node = self._ParseCommandList()
    assert cond_node is not None

    body_node = self.ParseDoGroup()
    assert body_node is not None

    return ast.Until(cond_node.children, body_node)

  def ParseCaseItem(self):
    """
    case_item: '('? pattern ('|' pattern)* ')'
               newline_ok command_term? trailer? ;
    """
    self.lexer.PushHint(Id.Op_RParen, Id.Right_CasePat)

    left_spid = word.LeftMostSpanForWord(self.cur_word)
    if self.c_id == Id.Op_LParen:
      self._Next()

    pat_words = []
    while True:
      self._Peek()
      pat_words.append(self.cur_word)
      self._Next()

      self._Peek()
      if self.c_id == Id.Op_Pipe:
        self._Next()
      else:
        break

    rparen_spid = word.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.Right_CasePat)
    self._NewlineOk()

    if self.c_id not in (Id.Op_DSemi, Id.KW_Esac):
      c_list = self._ParseCommandTerm()
      assert c_list is not None
      action_children = c_list.children
    else:
      action_children = []

    dsemi_spid = const.NO_INTEGER
    last_spid = const.NO_INTEGER
    self._Peek()
    if self.c_id == Id.KW_Esac:
      last_spid = word.LeftMostSpanForWord(self.cur_word)
    elif self.c_id == Id.Op_DSemi:
      dsemi_spid = word.LeftMostSpanForWord(self.cur_word)
      self._Next()
    else:
      # Happens on EOF
      p_die('Expected ;; or esac', word=self.cur_word)

    self._NewlineOk()

    arm = ast.case_arm(pat_words, action_children)
    arm.spids.extend((left_spid, rparen_spid, dsemi_spid, last_spid))
    return arm

  def ParseCaseList(self, arms):
    """
    case_list: case_item (DSEMI newline_ok case_item)* DSEMI? newline_ok;
    """
    self._Peek()

    while True:
      # case item begins with a command word or (
      if self.c_id == Id.KW_Esac:
        break
      if self.c_kind != Kind.Word and self.c_id != Id.Op_LParen:
        break
      arm = self.ParseCaseItem()
      assert arm is not None

      arms.append(arm)
      self._Peek()
      # Now look for DSEMI or ESAC

  def ParseCase(self):
    """
    case_clause      : Case WORD newline_ok in newline_ok case_list? Esac ;
    """
    case_node = ast.Case()

    case_spid = word.LeftMostSpanForWord(self.cur_word)
    self._Next()  # skip case

    self._Peek()
    case_node.to_match = self.cur_word
    self._Next()

    self._NewlineOk()
    in_spid = word.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.KW_In)
    self._NewlineOk()

    if self.c_id != Id.KW_Esac:  # empty case list
      self.ParseCaseList(case_node.arms)
      # TODO: should it return a list of nodes, and extend?
      self._Peek()

    esac_spid = word.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.KW_Esac)
    self._Next()

    case_node.spids.extend((case_spid, in_spid, esac_spid))
    return case_node

  def _ParseElifElse(self, if_node):
    """
    else_part: (Elif command_list Then command_list)* Else command_list ;
    """
    arms = if_node.arms

    self._Peek()
    while self.c_id == Id.KW_Elif:
      elif_spid = word.LeftMostSpanForWord(self.cur_word)

      self._Next()  # skip elif
      cond = self._ParseCommandList()
      assert cond is not None

      then_spid = word.LeftMostSpanForWord(self.cur_word)
      self._Eat(Id.KW_Then)

      body = self._ParseCommandList()
      assert body is not None

      arm = ast.if_arm(cond.children, body.children)
      arm.spids.extend((elif_spid, then_spid))
      arms.append(arm)

    if self.c_id == Id.KW_Else:
      else_spid = word.LeftMostSpanForWord(self.cur_word)
      self._Next()
      body = self._ParseCommandList()
      assert body is not None
      if_node.else_action = body.children
    else:
      else_spid = const.NO_INTEGER

    if_node.spids.append(else_spid)

  def ParseIf(self):
    """
    if_clause        : If command_list Then command_list else_part? Fi ;
    """
    if_node = ast.If()
    self._Next()  # skip if

    cond = self._ParseCommandList()
    assert cond is not None

    then_spid = word.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.KW_Then)

    body = self._ParseCommandList()
    assert body is not None

    arm = ast.if_arm(cond.children, body.children)
    arm.spids.extend((const.NO_INTEGER, then_spid))  # no if spid at first?
    if_node.arms.append(arm)

    if self.c_id in (Id.KW_Elif, Id.KW_Else):
      self._ParseElifElse(if_node)
    else:
      if_node.spids.append(const.NO_INTEGER)  # no else spid

    fi_spid = word.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.KW_Fi)

    if_node.spids.append(fi_spid)
    return if_node

  def ParseTime(self):
    """
    time [-p] pipeline

    According to bash help.
    """
    self._Next()  # skip time

    pipeline = self.ParsePipeline()
    assert pipeline is not None
    return ast.TimeBlock(pipeline)

  def ParseCompoundCommand(self):
    """
    compound_command : brace_group
                     | subshell
                     | for_clause
                     | while_clause
                     | until_clause
                     | if_clause
                     | case_clause
                     | time_clause
                     | [[ BoolExpr ]]
                     | (( ArithExpr ))
                     ;
    """
    if self.c_id == Id.Lit_LBrace:
      return self.ParseBraceGroup()
    if self.c_id == Id.Op_LParen:
      return self.ParseSubshell()

    if self.c_id == Id.KW_For:
      return self.ParseFor()
    if self.c_id == Id.KW_While:
      return self.ParseWhile()
    if self.c_id == Id.KW_Until:
      return self.ParseUntil()

    if self.c_id == Id.KW_If:
      return self.ParseIf()
    if self.c_id == Id.KW_Case:
      return self.ParseCase()
    if self.c_id == Id.KW_Time:
      return self.ParseTime()

    # Example of redirect that is observable:
    # $ (( $(echo one 1>&2; echo 2) > 0 )) 2> out.txt
    if self.c_id == Id.KW_DLeftBracket:
      return self.ParseDBracket()

    if self.c_id == Id.Op_DLeftParen:
      return self.ParseDParen()

    # This never happens?
    p_die('Unexpected word while parsing compound command', word=self.cur_word)

  def ParseFunctionBody(self, func):
    """
    function_body    : compound_command io_redirect* ; /* Apply rule 9 */
    """
    body = self.ParseCompoundCommand()
    assert body is not None

    redirects = self._ParseRedirectList()
    assert redirects is not None

    func.body = body
    func.redirects = redirects

  def ParseFunctionDef(self):
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
    left_spid = word.LeftMostSpanForWord(self.cur_word)

    ok, name = word.AsFuncName(self.cur_word)
    if not ok:
      p_die('Invalid function name', word=self.cur_word)

    self._Next()  # skip function name

    # Must be true beacuse of lookahead
    self._Peek()
    assert self.c_id == Id.Op_LParen, self.cur_word

    self.lexer.PushHint(Id.Op_RParen, Id.Right_FuncDef)
    self._Next()

    self._Eat(Id.Right_FuncDef)
    after_name_spid = word.LeftMostSpanForWord(self.cur_word) + 1

    self._NewlineOk()

    func = ast.FuncDef()
    func.name = name

    self.ParseFunctionBody(func)

    func.spids.append(left_spid)
    func.spids.append(after_name_spid)
    return func

  def ParseKshFunctionDef(self):
    """
    ksh_function_def : 'function' fname ( '(' ')' )? newline_ok function_body
    """
    left_spid = word.LeftMostSpanForWord(self.cur_word)

    self._Next()  # skip past 'function'

    self._Peek()
    ok, name = word.AsFuncName(self.cur_word)
    if not ok:
      p_die('Invalid KSH-style function name', word=self.cur_word)

    after_name_spid = word.LeftMostSpanForWord(self.cur_word) + 1
    self._Next()  # skip past 'function name

    self._Peek()
    if self.c_id == Id.Op_LParen:
      self.lexer.PushHint(Id.Op_RParen, Id.Right_FuncDef)
      self._Next()
      self._Eat(Id.Right_FuncDef)
      # Change it: after )
      after_name_spid = word.LeftMostSpanForWord(self.cur_word) + 1

    self._NewlineOk()

    func = ast.FuncDef()
    func.name = name

    self.ParseFunctionBody(func)

    func.spids.append(left_spid)
    func.spids.append(after_name_spid)
    return func

  def ParseCoproc(self):
    """
    TODO:
    """
    raise NotImplementedError

  def ParseSubshell(self):
    left_spid = word.LeftMostSpanForWord(self.cur_word)
    self._Next()  # skip past (

    # Ensure that something $( (cd / && pwd) ) works.  If ) is already on the
    # translation stack, we want to delay it.

    self.lexer.PushHint(Id.Op_RParen, Id.Right_Subshell)

    c_list = self._ParseCommandList()
    assert c_list is not None

    # Remove singleton CommandList as an optimization.
    if len(c_list.children) == 1:
      child = c_list.children[0]
    else:
      child = c_list
    node = ast.Subshell(child)

    right_spid = word.LeftMostSpanForWord(self.cur_word)
    self._Eat(Id.Right_Subshell)

    node.spids.extend((left_spid, right_spid))
    return node

  def ParseDBracket(self):
    """
    Pass the underlying word parser off to the boolean expression parser.
    """
    maybe_error_word = self.cur_word
    # TODO: Test interactive.  Without closing ]], you should get > prompt
    # (PS2)

    self._Next()  # skip [[
    b_parser = BoolParser(self.w_parser)
    bnode = b_parser.Parse()  # May raise
    return ast.DBracket(bnode)

  def ParseDParen(self):
    maybe_error_word = self.cur_word
    left_spid = word.LeftMostSpanForWord(self.cur_word)

    self._Next()  # skip ((
    anode, right_spid = self.w_parser.ReadDParen()
    assert anode is not None

    node = ast.DParen(anode)

    node.spids.append(left_spid)
    node.spids.append(right_spid)

    return node

  def ParseCommand(self, cur_aliases=None):
    """
    command          : simple_command
                     | compound_command io_redirect*
                     | function_def
                     | ksh_function_def
                     ;
    """
    cur_aliases = cur_aliases or []

    self._Peek()

    if self.c_id == Id.KW_Function:
      return self.ParseKshFunctionDef()

    if self.c_id in (
        Id.KW_DLeftBracket, Id.Op_DLeftParen, Id.Op_LParen, Id.Lit_LBrace,
        Id.KW_For, Id.KW_While, Id.KW_Until, Id.KW_If, Id.KW_Case, Id.KW_Time):
      node = self.ParseCompoundCommand()
      assert node is not None
      if node.tag != command_e.TimeBlock:  # The only one without redirects
        node.redirects = self._ParseRedirectList()
        assert node.redirects is not None
      return node

    # NOTE: I added this to fix cases in parse-errors.test.sh, but it doesn't
    # work because Lit_RBrace is in END_LIST below.

    # TODO: KW_Do is also invalid here.
    if self.c_id == Id.Lit_RBrace:
      p_die('Unexpected right brace', word=self.cur_word)

    if self.c_kind == Kind.Redir:  # Leading redirect
      return self.ParseSimpleCommand(cur_aliases)

    if self.c_kind == Kind.Word:
      if self.w_parser.LookAhead() == Id.Op_LParen:  # (
        kov = word.LooksLikeAssignment(self.cur_word)
        if kov:
          return self.ParseSimpleCommand(cur_aliases)  # f=(a b c)  # array
        else:
          return self.ParseFunctionDef()  # f() { echo; }  # function

      return self.ParseSimpleCommand(cur_aliases)  # echo foo

    if self.c_kind == Kind.Eof:
      p_die("Unexpected EOF while parsing command", word=self.cur_word)

    # e.g. )
    p_die("Invalid word while parsing command", word=self.cur_word)

  def ParsePipeline(self):
    """
    pipeline         : Bang? command ( '|' newline_ok command )* ;
    """
    negated = False

    self._Peek()
    if self.c_id == Id.KW_Bang:
      negated = True
      self._Next()

    child = self.ParseCommand()
    assert child is not None

    children = [child]

    self._Peek()
    if self.c_id not in (Id.Op_Pipe, Id.Op_PipeAmp):
      if negated:
        node = ast.Pipeline(children, negated)
        return node
      else:
        return child

    pipe_index = 0
    stderr_indices = []

    if self.c_id == Id.Op_PipeAmp:
      stderr_indices.append(pipe_index)
    pipe_index += 1

    while True:
      self._Next()  # skip past Id.Op_Pipe or Id.Op_PipeAmp

      self._NewlineOk()

      child = self.ParseCommand()
      assert child is not None
      children.append(child)

      self._Peek()
      if self.c_id not in (Id.Op_Pipe, Id.Op_PipeAmp):
        break

      if self.c_id == Id.Op_PipeAmp:
        stderr_indices.append(pipe_index)
      pipe_index += 1

    node = ast.Pipeline(children, negated)
    node.stderr_indices = stderr_indices
    return node

  def ParseAndOr(self):
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

    ops = []
    children = [child]

    while True:
      ops.append(self.c_id)

      self._Next()  # skip past || &&
      self._NewlineOk()

      child = self.ParsePipeline()
      assert child is not None

      children.append(child)

      self._Peek()
      if self.c_id not in (Id.Op_DPipe, Id.Op_DAmp):
        break

    node = ast.AndOr(ops, children)
    return node

  """
  NOTE: _ParseCommandLine and _ParseCommandTerm are similar, but different.

  At the top level, We want to execute after every line:
  - to process alias
  - to process 'exit', because invalid syntax might appear after it

  But for say a while loop body, we want to parse the whole thing at once, and
  then execute it.  We don't want to parse it over and over again!

  COMPARE
  command_line     : and_or (sync_op and_or)* trailer? ;   # TOP LEVEL
  command_term     : and_or (trailer and_or)* ;            # CHILDREN
  """

  def _ParseCommandLine(self):
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
    children = []
    done = False
    while not done:
      child = self.ParseAndOr()
      assert child is not None

      self._Peek()
      if self.c_id in (Id.Op_Semi, Id.Op_Amp):  # also Id.Op_Amp.
        child = ast.Sentence(child, self.cur_word.token)
        self._Next()

        self._Peek()
        if self.c_id in (Id.Op_Newline, Id.Eof_Real):
          done = True

      elif self.c_id == Id.Op_Newline:
        done = True

      elif self.c_id == Id.Eof_Real:
        done = True

      else:
        # Shouldn't happen?
        assert False, '_ParseCommandLine: Unexpected word %s' % self.cur_word

      children.append(child)

    # Simplify the AST.
    if len(children) > 1:
      return ast.CommandList(children)
    else:
      return children[0]

  def _ParseCommandTerm(self):
    """"
    command_term     : and_or (trailer and_or)* ;
    trailer          : sync_op newline_ok
                     | NEWLINES;
    sync_op          : '&' | ';';

    This is handled in imperative style, like _ParseCommandLine.
    Called by _ParseCommandList for all blocks, and also for ParseCaseItem,
    which is slightly different.  (HOW?  Is it the DSEMI?)

    Returns:
      ast.command
    """
    # Word types that will end the command term.
    END_LIST = (
        Id.Eof_Real, Id.Eof_RParen, Id.Eof_Backtick, Id.Right_Subshell,
        Id.Lit_RBrace, Id.Op_DSemi)

    # NOTE: This is similar to _ParseCommandLine.
    #
    # - Why aren't we doing END_LIST in _ParseCommandLine?
    #   - Because you will never be inside $() at the top level.
    #   - We also know it will end in a newline.  It can't end in "fi"!
    #   - example: if true; then { echo hi; } fi

    children = []
    done = False
    while not done:
      self._Peek()

      # Most keywords are valid "first words".  But do/done/then do not BEGIN
      # commands, so they are not valid.
      if self.c_id in (
        Id.KW_Do, Id.KW_Done, Id.KW_Then, Id.KW_Fi, Id.KW_Elif, Id.KW_Else,
        Id.KW_Esac):
        break

      child = self.ParseAndOr()
      assert child is not None

      self._Peek()
      if self.c_id == Id.Op_Newline:
        self._Next()

        self._Peek()
        if self.c_id in END_LIST:
          done = True

      elif self.c_id in (Id.Op_Semi, Id.Op_Amp):
        child = ast.Sentence(child, self.cur_word.token)
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

      else:
        pass  # e.g. "} done", "fi fi", ") fi", etc. is OK

      children.append(child)

    self._Peek()

    return ast.CommandList(children)

  # TODO: Make this private.
  def _ParseCommandList(self):
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
    assert node is not None
    return node

  def ParseLogicalLine(self):
    """Parse a single line for main_loop.

    A wrapper around _ParseCommandLine().  Similar but not identical to
    _ParseCommandList() and ParseCommandSub().

    Raises:
      ParseError

    We want to be able catch ParseError all in one place.
    """
    self._NewlineOk()
    self._Peek()

    if self.c_id == Id.Eof_Real:
      # TODO: Assert that there are no pending here docs
      return None

    node = self._ParseCommandLine()
    assert node is not None
    return node

  def ParseCommandSub(self):
    """Parse $(echo hi) and `echo hi` for word_parse.py.

    They can have multiple lines, like this:
    echo $(
      echo one
      echo two
    )
    """
    self._NewlineOk()

    if self.c_kind == Kind.Eof:  # e.g. $()
      return ast.NoOp()

    # This calls ParseAndOr(), but I think it should be a loop that calls
    # _ParseCommandLine(), like oil.InteractiveLoop.
    node = self._ParseCommandTerm()
    assert node is not None
    return node

  def CheckForPendingHereDocs(self):
    # NOTE: This happens when there is no newline at the end of a file, like
    # osh -c 'cat <<EOF'
    if self.pending_here_docs:
      node = self.pending_here_docs[0]  # Just show the first one?
      p_die('Unterminated here doc began here', word=node.here_begin)
