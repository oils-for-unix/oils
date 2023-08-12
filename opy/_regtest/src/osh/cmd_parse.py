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
from core import word
from core import util

from osh.meta import ast, Id, Kind, types
from osh.lex import VAR_NAME_RE
from osh.bool_parse import BoolParser

log = util.log
command_e = ast.command_e
word_e = ast.word_e
assign_op_e = ast.assign_op_e
lex_mode_e = types.lex_mode_e


class CommandParser(object):
  """
  Args:
    word_parse: to get a stream of words
    lexer: for lookahead in function def, PushHint of ()
    line_reader: for here doc
  """
  def __init__(self, w_parser, lexer, line_reader, arena):
    self.w_parser = w_parser  # for normal parsing
    self.lexer = lexer  # for fast lookahead to (, for function defs
    self.line_reader = line_reader  # for here docs
    self.arena = arena

    self.Reset()

  def Reset(self):
    self.error_stack = []
    self.completion_stack = []

    # Cursor state set by _Peek()
    self.next_lex_mode = lex_mode_e.OUTER
    self.cur_word = None  # current word
    self.c_kind = Kind.Undefined
    self.c_id = Id.Undefined_Tok

    self.pending_here_docs = []

  def Error(self):
    return self.error_stack

  def _BadWord(self, msg, w):
    """Helper function for errors involving a word.

    Args:
      msg: format string with a single %s token
      w: Word
    """
    self.AddErrorContext(msg, w, word=w)

  def AddErrorContext(self, msg, *args, **kwargs):
    err = util.ParseError(msg, *args, **kwargs)
    self.error_stack.append(err)

  def GetCompletionState(self):
    return self.completion_stack

  def _MaybeReadHereDocs(self):
    for h in self.pending_here_docs:
      lines = []
      #log('HERE %r' % h.here_end)
      while True:
        # If op is <<-, strip off all leading tabs (NOT spaces).
        # (in C++, just bump the start?)
        line_id, line = self.line_reader.GetLine()

        #print("LINE %r %r" % (line, h.here_end))
        if not line:  # EOF
          # An unterminated here doc is just a warning in bash.  We make it
          # fatal because we want to be strict, and because it causes problems
          # reporting other errors.
          # Attribute it to the << in <<EOF for now.
          self.AddErrorContext('Unterminated here doc', span_id=h.spids[0])
          return False

        # NOTE: Could do this runtime to preserve LST.
        if h.op_id == Id.Redir_DLessDash:
          line = line.lstrip('\t')
        if line.rstrip() == h.here_end:
          break

        lines.append((line_id, line))

      parts = []
      if h.do_expansion:
        # NOTE: We read all lines at once, instead of doing it line-by-line,
        # because of cases like this:
        # cat <<EOF
        # 1 $(echo 2
        # echo 3) 4
        # EOF

        from osh import parse_lib  # Avoid circular import
        w_parser = parse_lib.MakeWordParserForHereDoc(lines, self.arena)
        word = w_parser.ReadHereDocBody()
        if not word:
          self.AddErrorContext(
              'Error reading here doc body: %s', w_parser.Error())
          return False
        h.body = word
        h.was_filled = True
      else:
        # Each line is a single span.  TODO: Add span_id to token.
        tokens = [
            ast.token(Id.Lit_Chars, line, const.NO_INTEGER)
            for _, line in lines]
        parts = [ast.LiteralPart(t) for t in tokens]
        h.body = ast.CompoundWord(parts)
        h.was_filled = True

    # No .clear() until Python 3.3.
    del self.pending_here_docs[:]

    return True

  def _Next(self, lex_mode=lex_mode_e.OUTER):
    """Helper method."""
    self.next_lex_mode = lex_mode

  def Peek(self):
    """Public method for REPL."""
    if not self._Peek():
      return None
    return self.cur_word

  def _Peek(self):
    """Helper method.

    Returns True for success and False on error.  Error examples: bad command
    sub word, or unterminated quoted string, etc.
    """
    if self.next_lex_mode != lex_mode_e.NONE:
      w = self.w_parser.ReadWord(self.next_lex_mode)
      if w is None:
        error_stack = self.w_parser.Error()
        self.error_stack.extend(error_stack)
        return False

      # Here docs only happen in command mode, so other kinds of newlines don't
      # count.
      if w.tag == word_e.TokenWord and w.token.id == Id.Op_Newline:
        if not self._MaybeReadHereDocs():
          return False

      self.cur_word = w

      self.c_kind = word.CommandKind(self.cur_word)
      self.c_id = word.CommandId(self.cur_word)
      self.next_lex_mode = lex_mode_e.NONE
    #print('_Peek', self.cur_word)
    return True

  def _Eat(self, c_id):
    """Consume a word of a type.  If it doesn't match, return False.

    Args:
      c_id: either EKeyword.* or a token type like Id.Right_Subshell.
      TODO: Rationalize / type check this.
    """
    if not self._Peek():
      return False
    # TODO: It would be nicer to print the word type, right now we get a number
    if self.c_id != c_id:
      self.AddErrorContext(
          "Expected word type %s, got %s", c_id, self.cur_word,
          word=self.cur_word)
      return False
    self._Next()
    return True

  def _NewlineOk(self):
    """Check for optional newline and consume it."""
    if not self._Peek():
      return False
    if self.c_id == Id.Op_Newline:
      self._Next()
      if not self._Peek():
        return False
    return True

  def ParseRedirect(self):
    """
    Problem: You don't know which kind of redir_node to instantiate before
    this?  You could stuff them all in one node, and then have a switch() on
    the type.

    You need different types.
    """
    if not self._Peek(): return None
    assert self.c_kind == Kind.Redir, self.cur_word

    left_spid = self.cur_word.token.span_id

    # For now only supporting single digit descriptor
    first_char = self.cur_word.token.val[0]
    if first_char.isdigit():
      fd = int(first_char)
    else:
      fd = const.NO_INTEGER

    if self.c_id in (Id.Redir_DLess, Id.Redir_DLessDash):  # here doc
      node = ast.HereDoc()
      node.op_id = self.c_id
      node.body = None  # not read yet
      node.fd = fd
      node.was_filled = False
      node.spids.append(left_spid)
      self._Next()

      if not self._Peek(): return None
      # "If any character in word is quoted, the delimiter shall be formed by
      # performing quote removal on word, and the here-document lines shall not
      # be expanded. Otherwise, the delimiter shall be the word itself."
      # NOTE: \EOF counts, or even E\OF
      ok, node.here_end, quoted = word.StaticEval(self.cur_word)
      if not ok:
        self._BadWord('Error evaluating here doc delimiter: %s', self.cur_word)
        return None
      node.do_expansion = not quoted
      self._Next()

      self.pending_here_docs.append(node)  # will be filled on next newline.

    else:
      node = ast.Redir()
      node.op_id = self.c_id
      node.fd = fd
      node.spids.append(left_spid)
      self._Next()

      if not self._Peek(): return None
      if self.c_kind != Kind.Word:
        self.AddErrorContext(
            'Expected word after redirect operator', word=self.cur_word)
        return None

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
      if not self._Peek(): return None

      # This prediction needs to ONLY accept redirect operators.  Should we
      # make them a separate TokeNkind?
      if self.c_kind != Kind.Redir:
        break

      node = self.ParseRedirect()
      if not node:
        return None
      redirects.append(node)
      self._Next()
    return redirects

  def _ScanSimpleCommand(self):
    """First pass: Split into redirects and words."""
    redirects = []
    words = []
    while True:
      if not self._Peek(): return None
      if self.c_kind == Kind.Redir:
        node = self.ParseRedirect()
        if not node: return None  # e.g. EOF
        redirects.append(node)

      elif self.c_kind == Kind.Word:
        words.append(self.cur_word)

      else:
        break
      self._Next()
    return redirects, words

  def _SplitSimpleCommandPrefix(self, words):
    """
    Second pass of SimpleCommand parsing: look for assignment words.
    """
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

  def _MakeSimpleCommand(self, prefix_bindings, suffix_words, redirects):
    # FOO=(1 2 3) ls is not allowed
    for k, _, v, _ in prefix_bindings:
      if word.HasArrayPart(v):
        self.AddErrorContext(
            'Unexpected array literal in binding: %s', v, word=v)
        return None

    # echo FOO=(1 2 3) is not allowed
    # NOTE: Other checks can be inserted here.  Can resolve builtins,
    # functions, aliases, static PATH, etc.
    for w in suffix_words:
      kov = word.LooksLikeAssignment(w)
      if kov:
        _, _, v = kov
        if word.HasArrayPart(v):
          self.AddErrorContext('Unexpected array literal: %s', v, word=w)
          return None

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
    for name, op, val, left_spid in prefix_bindings:
      if op != assign_op_e.Equal:
        # NOTE: Using spid of RHS for now, since we don't have one for op.
        self.AddErrorContext('Expected = in environment binding, got +=',
            word=val)
        return None
      pair = ast.env_pair(name, val)
      pair.spids.append(left_spid)
      node.more_env.append(pair)
    return node

  def _MakeAssignment(self, assign_kw, suffix_words):
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
           self.AddErrorContext(
               'Variable names must be constant strings, got %s', w, word=w)
           return None

        # No value is equivalent to ''
        m = VAR_NAME_RE.match(static_val)
        if not m:
          self.AddErrorContext('Invalid variable name %r', static_val, word=w)
          return None
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

  def ParseSimpleCommand(self):
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
    result = self._ScanSimpleCommand()
    if not result: return None
    redirects, words = result

    if not words:  # e.g.  >out.txt  # redirect without words
      node = ast.SimpleCommand()
      node.redirects = redirects
      return node

    prefix_bindings, suffix_words = self._SplitSimpleCommandPrefix(words)

    if not suffix_words:  # ONE=1 TWO=2  (with no other words)
      if redirects:
        binding1 = prefix_bindings[0]
        _, _, _, spid = binding1
        self.AddErrorContext('Got redirects in global assignment',
                             span_id=spid)
        return None

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
        node = self._MakeSimpleCommand(prefix_bindings, suffix_words,
                                       redirects)
        return node

      else:  # declare str='', declare -a array=()
        if redirects:
          # Attach the error location to the keyword.  It would be more precise
          # to attach it to the
          self.AddErrorContext('Got redirects in assignment', token=kw_token)
          return None

        if prefix_bindings:  # FOO=bar local spam=eggs not allowed
          # Use the location of the first value.  TODO: Use the whole word
          # before splitting.
          _, _, v0, _ = prefix_bindings[0]
          self.AddErrorContext(
              'Invalid prefix bindings in assignment: %s', prefix_bindings,
              word=v0)
          return None

        node = self._MakeAssignment(kw_token.id, suffix_words)
        if not node: return None
        node.spids.append(kw_token.span_id)
        return node

    elif kind == Kind.ControlFlow:
      if redirects:
        self.AddErrorContext('Got redirects in control flow: %s', redirects)
        return None

      if prefix_bindings:  # FOO=bar local spam=eggs not allowed
        # Use the location of the first value.  TODO: Use the whole word before
        # splitting.
        _, _, v0, _ = prefix_bindings[0]
        self.AddErrorContext(
            'Invalid prefix bindings in control flow: %s', prefix_bindings,
            word=v0)
        return None

      # Attach the token for errors.  (Assignment may not need it.)
      if len(suffix_words) == 1:
        arg_word = None
      elif len(suffix_words) == 2:
        arg_word = suffix_words[1]
      else:
        # Underline the extra word.
        self.AddErrorContext(
            'Unexpected argument to %r', kw_token.val, word=suffix_words[2])
        return None

      return ast.ControlFlow(kw_token, arg_word)

    else:
      node = self._MakeSimpleCommand(prefix_bindings, suffix_words, redirects)
      return node

  def ParseBraceGroup(self):
    """
    brace_group      : LBrace command_list RBrace ;
    """
    left_spid = word.LeftMostSpanForWord(self.cur_word)
    if not self._Eat(Id.Lit_LBrace): return None

    c_list = self.ParseCommandList()
    if not c_list: return None

    # Not needed
    #right_spid = word.LeftMostSpanForWord(self.cur_word)
    if not self._Eat(Id.Lit_RBrace): return None

    node = ast.BraceGroup(c_list.children)
    node.spids.append(left_spid)
    return node

  def ParseDoGroup(self):
    """
    Used by ForEach, ForExpr, While, Until.  Should this be a Do node?

    do_group         : Do command_list Done ;          /* Apply rule 6 */
    """
    if not self._Eat(Id.KW_Do): return None
    do_spid = word.LeftMostSpanForWord(self.cur_word)  # after _Eat

    c_list = self.ParseCommandList()  # could be any thing
    if not c_list: return None

    if not self._Eat(Id.KW_Done): return None
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
      if not self._Peek(): return None
      if self.c_id == Id.Op_Semi:
        semi_spid = self.cur_word.token.span_id  # TokenWord
        self._Next()
        if not self._NewlineOk(): return None
        break
      elif self.c_id == Id.Op_Newline:
        self._Next()
        break
      if self.cur_word.tag != word_e.CompoundWord:
        # TODO: Can we also show a pointer to the 'for' keyword?
        self.AddErrorContext('Invalid word in for loop', word=self.cur_word)
        return None

      words.append(self.cur_word)
      self._Next()
    return words, semi_spid

  def _ParseForExprLoop(self):
    """
    for (( init; cond; update )) for_sep? do_group
    """
    node = self.w_parser.ReadForExpression()
    if not node:
      error_stack = self.w_parser.Error()
      self.error_stack.extend(error_stack)
      self.AddErrorContext("Parsing for expression failed")
      return None
    self._Next()

    if not self._Peek(): return None
    if self.c_id == Id.Op_Semi:
      self._Next()
      if not self._NewlineOk(): return None
    elif self.c_id == Id.Op_Newline:
      self._Next()
    elif self.c_id == Id.KW_Do:  # missing semicolon/newline allowed
      pass
    else:
      self.AddErrorContext(
          'Unexpected token after for expression: %s', self.cur_word,
          word=self.cur_word)
      return None

    body_node = self.ParseDoGroup()
    if not body_node: return None

    node.body = body_node
    return node

  def _ParseForEachLoop(self):
    node = ast.ForEach()
    node.do_arg_iter = False

    ok, iter_name, quoted = word.StaticEval(self.cur_word)
    if not ok or quoted:
      self.AddErrorContext(
          "Invalid for loop variable", word=self.cur_word)
      return None
    if not VAR_NAME_RE.match(iter_name):
      self.AddErrorContext(
          "Invalid for loop variable name", word=self.cur_word)
      return None
    node.iter_name = iter_name
    self._Next()  # skip past name

    if not self._NewlineOk(): return None

    in_spid = const.NO_INTEGER
    semi_spid = const.NO_INTEGER

    if not self._Peek(): return None
    if self.c_id == Id.KW_In:
      self._Next()  # skip in

      in_spid = word.LeftMostSpanForWord(self.cur_word) + 1
      x = self.ParseForWords()
      if x is None:
        return None
      iter_words, semi_spid = x
      words2 = braces.BraceDetectAll(iter_words)
      words3 = word.TildeDetectAll(words2)

      if iter_words is None:  # empty list of words is OK
        return None
      node.iter_words = words3

    elif self.c_id == Id.Op_Semi:
      node.do_arg_iter = True  # implicit for loop
      self._Next()

    elif self.c_id == Id.KW_Do:
      node.do_arg_iter = True  # implicit for loop
      # do not advance

    else:
      self.AddErrorContext("Unexpected word in for loop: %s", self.cur_word,
          word=self.cur_word)
      return None

    node.spids.extend((in_spid, semi_spid))

    body_node = self.ParseDoGroup()
    if not body_node: return None

    node.body = body_node
    return node

  def ParseFor(self):
    """
    for_clause : For for_name newline_ok (in for_words? for_sep)? do_group ;
               | For '((' ... TODO
    """
    if not self._Eat(Id.KW_For): return None

    if not self._Peek(): return None
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

    cond_node = self.ParseCommandList()
    if not cond_node: return None

    body_node = self.ParseDoGroup()
    if not body_node: return None

    return ast.While(cond_node.children, body_node)

  def ParseUntil(self):
    """
    until_clause     : Until command_list do_group ;
    """
    self._Next()  # skip until

    cond_node = self.ParseCommandList()
    if not cond_node: return None

    body_node = self.ParseDoGroup()
    if not body_node: return None

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
      if not self._Peek(): return None
      pat_words.append(self.cur_word)
      self._Next()

      if not self._Peek(): return None
      if self.c_id == Id.Op_Pipe:
        self._Next()
      else:
        break

    rparen_spid = word.LeftMostSpanForWord(self.cur_word)
    if not self._Eat(Id.Right_CasePat): return None
    if not self._NewlineOk(): return None

    if self.c_id not in (Id.Op_DSemi, Id.KW_Esac):
      c_list = self.ParseCommandTerm()
      if not c_list: return None
      action_children = c_list.children
    else:
      action_children = []

    dsemi_spid = const.NO_INTEGER
    last_spid = const.NO_INTEGER
    if not self._Peek(): return None
    if self.c_id == Id.KW_Esac:
      last_spid = word.LeftMostSpanForWord(self.cur_word)
    elif self.c_id == Id.Op_DSemi:
      dsemi_spid = word.LeftMostSpanForWord(self.cur_word)
      self._Next()
    else:
      self.AddErrorContext('Expected DSEMI or ESAC, got %s', self.cur_word,
          word=self.cur_word)
      return None

    if not self._NewlineOk(): return None

    arm = ast.case_arm(pat_words, action_children)
    arm.spids.extend((left_spid, rparen_spid, dsemi_spid, last_spid))
    return arm

  def ParseCaseList(self, arms):
    """
    case_list: case_item (DSEMI newline_ok case_item)* DSEMI? newline_ok;
    """
    if not self._Peek(): return None

    while True:
      # case item begins with a command word or (
      if self.c_id == Id.KW_Esac:
        break
      if self.c_kind != Kind.Word and self.c_id != Id.Op_LParen:
        break
      arm = self.ParseCaseItem()
      if not arm: return None

      arms.append(arm)
      if not self._Peek(): return None
      # Now look for DSEMI or ESAC

    return True

  def ParseCase(self):
    """
    case_clause      : Case WORD newline_ok in newline_ok case_list? Esac ;
    """
    case_node = ast.Case()

    case_spid = word.LeftMostSpanForWord(self.cur_word)
    self._Next()  # skip case

    if not self._Peek(): return None
    case_node.to_match = self.cur_word
    self._Next()

    if not self._NewlineOk(): return None
    in_spid = word.LeftMostSpanForWord(self.cur_word)
    if not self._Eat(Id.KW_In): return None
    if not self._NewlineOk(): return None

    if self.c_id != Id.KW_Esac:  # empty case list
      if not self.ParseCaseList(case_node.arms):
        self.AddErrorContext("ParseCase: error parsing case list")
        return None
      # TODO: should it return a list of nodes, and extend?
      if not self._Peek(): return None

    esac_spid = word.LeftMostSpanForWord(self.cur_word)
    if not self._Eat(Id.KW_Esac): return None
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
      cond = self.ParseCommandList()
      if not cond: return None

      then_spid = word.LeftMostSpanForWord(self.cur_word)
      if not self._Eat(Id.KW_Then): return None

      body = self.ParseCommandList()
      if not body: return None

      arm = ast.if_arm(cond.children, body.children)
      arm.spids.extend((elif_spid, then_spid))
      arms.append(arm)

    if self.c_id == Id.KW_Else:
      else_spid = word.LeftMostSpanForWord(self.cur_word)
      self._Next()
      body = self.ParseCommandList()
      if not body: return None
      if_node.else_action = body.children
    else:
      else_spid = const.NO_INTEGER

    if_node.spids.append(else_spid)

    return True

  def ParseIf(self):
    """
    if_clause        : If command_list Then command_list else_part? Fi ;
    """
    if_node = ast.If()
    self._Next()  # skip if

    cond = self.ParseCommandList()
    if not cond: return None

    then_spid = word.LeftMostSpanForWord(self.cur_word)
    if not self._Eat(Id.KW_Then): return None

    body = self.ParseCommandList()
    if not body: return None

    arm = ast.if_arm(cond.children, body.children)
    arm.spids.extend((const.NO_INTEGER, then_spid))  # no if spid at first?
    if_node.arms.append(arm)

    if self.c_id in (Id.KW_Elif, Id.KW_Else):
      if not self._ParseElifElse(if_node):
        return None
    else:
      if_node.spids.append(const.NO_INTEGER)  # no else spid

    fi_spid = word.LeftMostSpanForWord(self.cur_word)
    if not self._Eat(Id.KW_Fi): return None

    if_node.spids.append(fi_spid)
    return if_node

  def ParseTime(self):
    """
    time [-p] pipeline

    According to bash help.
    """
    self._Next()  # skip time

    pipeline = self.ParsePipeline()
    if not pipeline: return None
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

    self.AddErrorContext(
        "Expected a compound command (e.g. for while if case), got %s",
        self.cur_word, word=self.cur_word)
    return None

  def ParseFunctionBody(self, func):
    """
    function_body    : compound_command io_redirect* ; /* Apply rule 9 */
    """
    body = self.ParseCompoundCommand()
    if not body: return None

    redirects = self._ParseRedirectList()
    if redirects is None: return None

    func.body = body
    func.redirects = redirects
    return True

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
      self.AddErrorContext('Invalid function name', word=self.cur_word)
      return None
    self._Next()  # skip function name

    # Must be true because of lookahead
    if not self._Peek(): return None
    assert self.c_id == Id.Op_LParen, self.cur_word

    self.lexer.PushHint(Id.Op_RParen, Id.Right_FuncDef)
    self._Next()

    if not self._Eat(Id.Right_FuncDef): return None
    after_name_spid = word.LeftMostSpanForWord(self.cur_word) + 1

    if not self._NewlineOk(): return None

    func = ast.FuncDef()
    func.name = name

    if not self.ParseFunctionBody(func):
      return None

    func.spids.append(left_spid)
    func.spids.append(after_name_spid)
    return func

  def ParseKshFunctionDef(self):
    """
    ksh_function_def : 'function' fname ( '(' ')' )? newline_ok function_body
    """
    left_spid = word.LeftMostSpanForWord(self.cur_word)

    self._Next()  # skip past 'function'

    if not self._Peek(): return None
    ok, name = word.AsFuncName(self.cur_word)
    if not ok:
      self.AddErrorContext("Invalid function name: %r", self.cur_word)
      return None
    after_name_spid = word.LeftMostSpanForWord(self.cur_word) + 1
    self._Next()  # skip past 'function name

    if not self._Peek(): return None
    if self.c_id == Id.Op_LParen:
      self.lexer.PushHint(Id.Op_RParen, Id.Right_FuncDef)
      self._Next()
      if not self._Eat(Id.Right_FuncDef): return None
      # Change it: after )
      after_name_spid = word.LeftMostSpanForWord(self.cur_word) + 1

    if not self._NewlineOk(): return None

    func = ast.FuncDef()
    func.name = name

    if not self.ParseFunctionBody(func):
      return None

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

    #print('ParseSubshell lexer.PushHint ) -> )')
    self.lexer.PushHint(Id.Op_RParen, Id.Right_Subshell)

    c_list = self.ParseCommandList()
    if not c_list: return None

    # Remove singleton CommandList as an optimization.
    if len(c_list.children) == 1:
      child = c_list.children[0]
    else:
      child = c_list
    node = ast.Subshell(child)

    right_spid = word.LeftMostSpanForWord(self.cur_word)
    if not self._Eat(Id.Right_Subshell): return None

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
    bnode = b_parser.Parse()
    if not bnode:
      error_stack = b_parser.Error()
      self.error_stack.extend(error_stack)
      self.AddErrorContext("Error parsing [[", word=maybe_error_word)
      return None
    return ast.DBracket(bnode)

  def ParseDParen(self):
    maybe_error_word = self.cur_word
    self._Next()  # skip ((
    #print('1 ((', self.cur_word)
    anode = self.w_parser.ReadDParen()
    if not anode:
      error_stack = self.w_parser.Error()
      self.error_stack.extend(error_stack)
      self.AddErrorContext("Error parsing ((", word=maybe_error_word)
      return None

    #print('2 ((', self.cur_word)
    return ast.DParen(anode)

  def ParseCommand(self):
    """
    command          : simple_command
                     | compound_command io_redirect*
                     | function_def
                     | ksh_function_def
                     ;
    """
    if not self._Peek(): return None

    if self.c_id == Id.KW_Function:
      return self.ParseKshFunctionDef()

    if self.c_id in (
        Id.KW_DLeftBracket, Id.Op_DLeftParen, Id.Op_LParen, Id.Lit_LBrace,
        Id.KW_For, Id.KW_While, Id.KW_Until, Id.KW_If, Id.KW_Case, Id.KW_Time):
      node = self.ParseCompoundCommand()
      if not node: return None
      if node.tag != command_e.TimeBlock:  # The only one without redirects
        redirects = self._ParseRedirectList()
        if redirects is None:
          return None
        node.redirects = redirects
      return node

    # NOTE: I added this to fix cases in parse-errors.test.sh, but it doesn't
    # work because Lit_RBrace is in END_LIST below.

    # TODO: KW_Do is also invalid here.
    if self.c_id == Id.Lit_RBrace:
      self.AddErrorContext('Unexpected }', word=self.cur_word)
      return None

    if self.c_kind == Kind.Redir:  # Leading redirect
      return self.ParseSimpleCommand()

    if self.c_kind == Kind.Word:
      if self.w_parser.LookAhead() == Id.Op_LParen:  # (
        kov = word.LooksLikeAssignment(self.cur_word)
        if kov:
          return self.ParseSimpleCommand()  # f=(a b c)  # array
        else:
          return self.ParseFunctionDef()  # f() { echo; }  # function

      return self.ParseSimpleCommand()  # echo foo

    self.AddErrorContext(
        "ParseCommand: Expected to parse a command, got %s", self.cur_word,
        word=self.cur_word)
    return None

  def ParsePipeline(self):
    """
    pipeline         : Bang? command ( '|' newline_ok command )* ;
    """
    negated = False

    if not self._Peek(): return None
    if self.c_id == Id.KW_Bang:
      negated = True
      self._Next()

    child = self.ParseCommand()
    if not child: return None

    children = [child]

    if not self._Peek(): return None
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

      if not self._NewlineOk():
        return None

      child = self.ParseCommand()
      if not child:
        self.AddErrorContext('Error parsing command after pipe')
        # TODO: Return partial pipeline here?  All signatures should (ok,
        # node).  Only the completion uses the node when ok is False.
        return None
      children.append(child)

      if not self._Peek(): return None
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
    if not child: return None

    if not self._Peek(): return None
    if self.c_id not in (Id.Op_DPipe, Id.Op_DAmp):
      return child

    ops = []
    children = [child]

    while True:
      ops.append(self.c_id)

      self._Next()  # skip past || &&

      if not self._NewlineOk():
        return None

      child = self.ParsePipeline()
      if not child: return None

      children.append(child)

      if not self._Peek(): return None
      if self.c_id not in (Id.Op_DPipe, Id.Op_DAmp):
        break

    node = ast.AndOr(ops, children)
    return node

  def ParseCommandLine(self):
    """
    NOTE: This is only called in InteractiveLoop.  Oh crap I need to really
    read and execute a line at a time then?

    BUG: sleep 1 & sleep 1 &  doesn't work here, when written in REPL.   But it
    does work with '-c', because that calls ParseFile and not ParseCommandLine
    over and over.

    TODO: Get rid of ParseFile and stuff?  Shouldn't be used for -c and so
    forth.  Just have an ExecuteLoop for now.  But you still need
    ParseCommandList, for internal nodes.

    command_line     : and_or (sync_op and_or)* trailer? ;
    trailer          : sync_op newline_ok
                     | NEWLINES;
    sync_op          : '&' | ';';

    This rule causes LL(k > 1) behavior.  We would have to peek to see if there
    is another command word after the sync op.

    But it's easier to express imperatively.  Do the following in a loop:
    1. ParseAndOr
    2. Peek.
       a. If there's a newline, then return.  (We're only parsing a single
          line.)
       b. If there's a sync_op, process it.  Then look for a newline and
          return.  Otherwise, parse another AndOr.

    COMPARE
    command_line     : and_or (sync_op and_or)* trailer? ;   # TOP LEVEL
    command_term     : and_or (trailer and_or)* ;            # CHILDREN

    I think you should be able to factor these out.
    """
    children = []
    done = False
    while not done:
      child = self.ParseAndOr()
      if not child: return None

      if not self._Peek(): return None
      if self.c_id in (Id.Op_Semi, Id.Op_Amp):  # also Id.Op_Amp.
        child = ast.Sentence(child, self.cur_word.token)
        self._Next()

        if not self._Peek(): return None
        if self.c_id in (Id.Op_Newline, Id.Eof_Real):
          done = True

      elif self.c_id == Id.Op_Newline:
        done = True

      elif self.c_id == Id.Eof_Real:
        done = True

      else:
        self.AddErrorContext(
            'ParseCommandLine: Unexpected token %s', self.cur_word)
        return None

      children.append(child)

    return ast.CommandList(children)

  def ParseCommandTerm(self):
    """"
    command_term     : and_or (trailer and_or)* ;
    trailer          : sync_op newline_ok
                     | NEWLINES;
    sync_op          : '&' | ';';

    This is handled in imperative style, like ParseCommandLine.
    Called by ParseCommandList for all blocks, and also for ParseCaseItem,
    which is slightly different.  (HOW?  Is it the DSEMI?)

    Returns:
      ast.command
    """
    # Word types that will end the command term.
    END_LIST = (
        Id.Eof_Real, Id.Eof_RParen, Id.Eof_Backtick, Id.Right_Subshell,
        Id.Lit_RBrace, Id.Op_DSemi)

    # NOTE: This is similar to ParseCommandLine, except there is a lot of stuff
    # about here docs.  Here docs are inherently line-oriented.
    #
    # - Why aren't we doing END_LIST in ParseCommandLine?
    #   - Because you will never be inside $() at the top level.
    #   - We also know it will end in a newline.  It can't end in "fi"!
    #   - example: if true; then { echo hi; } fi
    # - Why aren't we doing 'for c in children' too?

    children = []
    done = False
    while not done:
      if not self._Peek(): return None
      #print('====> ParseCommandTerm word', self.cur_word)

      # Most keywords are valid "first words".  But do/done/then do not BEGIN
      # commands, so they are not valid.
      if self.c_id in (
        Id.KW_Do, Id.KW_Done, Id.KW_Then, Id.KW_Fi, Id.KW_Elif, Id.KW_Else,
        Id.KW_Esac):
        break

      child = self.ParseAndOr()
      if not child:
        self.AddErrorContext('Error parsing AndOr in ParseCommandTerm')
        return None

      if not self._Peek(): return None
      if self.c_id == Id.Op_Newline:
        self._Next()

        if not self._Peek(): return None
        if self.c_id in END_LIST:
          done = True

      elif self.c_id in (Id.Op_Semi, Id.Op_Amp):
        child = ast.Sentence(child, self.cur_word.token)
        self._Next()

        if not self._Peek(): return None
        if self.c_id == Id.Op_Newline:
          self._Next()  # skip over newline

          # Test if we should keep going.  There might be another command after
          # the semi and newline.
          if not self._Peek(): return None
          if self.c_id in END_LIST:
            done = True

        elif self.c_id in END_LIST:  # ; EOF
          done = True

      elif self.c_id in END_LIST:  # EOF
        done = True

      else:
        pass  # e.g. "} done", "fi fi", ") fi", etc. is OK

      children.append(child)

    if not self._Peek(): return None

    return ast.CommandList(children)

  def ParseCommandList(self):
    """
    command_list     : newline_ok command_term trailer? ;

    This one is called by all the compound commands.  It's basically a command
    block.

    NOTE: Rather than translating the CFG directly, the code follows a style
    more like this: more like this: (and_or trailer)+.  It makes capture
    easier.
    """
    if not self._NewlineOk(): return None

    node = self.ParseCommandTerm()
    if node is None: return None
    assert node is not False
    return node

  def ParseWholeFile(self):
    """Entry point for main() in non-interactive shell.

    Very similar to ParseCommandList, but we allow empty files.

    TODO: This should be turned into a Parse and Execute loop, freeing arenas
    if they don't contain functions.
    """
    if not self._NewlineOk(): return None

    #print('ParseFile', self.c_kind, self.cur_word)
    # An empty node to execute
    if self.c_kind == Kind.Eof:
      return ast.NoOp()

    # This calls ParseAndOr(), but I think it should be a loop that calls
    # ParseCommandLine(), like oil.InteractiveLoop.
    node = self.ParseCommandTerm()
    if node is None: return None
    assert node is not False

    return node
