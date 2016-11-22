#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
cmd_parse.py - Parse high level shell commands.
"""

from core import base
from core.cmd_node import (
    HereDocRedirectNode, HereWordRedirectNode, FilenameRedirectNode,
    DescriptorRedirectNode, SimpleCommandNode, ElseTrueNode, AssignmentNode,
    DBracketNode, DParenNode, ListNode, SubshellNode, ForkNode, PipelineNode,
    AndOrNode, ForNode, ForExpressionNode, WhileNode, UntilNode,
    FunctionDefNode, IfNode, CaseNode)
from core.word_node import (
    EKeyword, EAssignScope, EAssignKeyword, EAssignFlags,
    LiteralPart, CompoundWord, TildeSubPart)
from core.tokens import Token, Id, CKind

from osh.lex import LexMode
from osh.bool_parse import BoolParser


class CommandParser(object):
  """
  Args:
    word_parse: to get a stream of words
    lexer: for lookahead in function def, PushHint of ()
    line_reader: for here doc
  """
  def __init__(self, w_parser, lexer, line_reader):
    self.w_parser = w_parser  # for normal parsing
    self.lexer = lexer  # for fast lookahead to (, for function defs
    self.line_reader = line_reader  # for here docs

    self.Reset()

  def Reset(self):
    self.error_stack = []
    self.completion_stack = []

    # Cursor state set by _Peek()
    self.next_lex_mode = LexMode.OUTER
    self.cur_word = None  # current word
    self.c_kind = CKind.UNDEFINED
    self.c_id = Id.Undefined_Tok

  def Error(self):
    return self.error_stack

  def AddErrorContext(self, msg, *args, token=None, word=None):
    err = base.MakeError(msg, *args, token=token, word=word)
    self.error_stack.append(err)

  def GetCompletionState(self):
    return self.completion_stack

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
    if self.next_lex_mode != LexMode.NONE:
      w = self.w_parser.ReadWord(self.next_lex_mode)
      if w is None:
        error_stack = self.w_parser.Error()
        self.error_stack.extend(error_stack)
        self.AddErrorContext('Word parse error in CommandParser')
        return False
      self.cur_word = w

      self.c_kind = self.cur_word.CommandKind()
      self.c_id = self.cur_word.CommandId()
      self.next_lex_mode = LexMode.NONE
    #print('_Peek', self.cur_word)
    return True

  def _Next(self, lex_mode=LexMode.OUTER):
    """Helper method."""
    self.next_lex_mode = lex_mode

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

  # TODO: Hook up brace expansion!  Does this work?
  def _BraceExpandIter():  # one iteration
    """
    Args:
      words: list of words

    Returns:
      new_words: list of new words, or None
    """
    expansions = []  # (pos, new_list)
    for i, w in enumerate(words):
      # Call CompoundWord.BraceExpand here.  Returns a list of expansinos, or
      # nullptr?
      exp_words = w.BraceExpand()
      if exp_words:
        expansions.append((i, exp_words))

    # If we got any expansions, create the new word list.
    j = 0
    if expansions:
      new_words = []
      for i, old_word in enumerate(words):
        if j < len(expansions):
          index, exp_words = expansions[j]
          if index == i:
            new_words.extend(exp_words)
          else:
            new_words.append(old_word)
      return new_words
    else:
      return None

  def _BraceExpand(self, words):
    # NOTE: In C++ this will use swap() of vector<Word*> on each iteration.
    while True:
      new_words = self._BraceExpandIter(words)
      if new_words is None:
        return words

    return new_words

  def _BraceExpand2(self, words):
    # Dummy
    return words

  def _TildeDetect(self, word):
    """
    Return a new word if it needs to include a TildeSub, or None to leave it
    alone.

    NOTE: This algorithm would be a simpler if
    1. We could assume some regex for user names.
    2. We didn't need to do brace expansion first, like {~foo,~bar}

    So we have to scan all LiteralPart instances until they contain a '/'.

    http://unix.stackexchange.com/questions/157426/what-is-the-regex-to-validate-linux-users
    "It is usually recommended to only use usernames that begin with a lower
    case letter or an underscore, followed by lower case letters, digits,
    underscores, or dashes. They can end with a dollar sign. In regular
    expression terms: [a-z_][a-z0-9_-]*[$]?

    On Debian, the only constraints are that usernames must neither start with
    a dash ('-') nor contain a colon (':') or a whitespace (space: ' ', end
    of line: '\n', tabulation: '\t', etc.). Note that using a slash ('/') may
    break the default algorithm for the definition of the user's home
    directory.

    """
    if not word.parts:
      return None
    if not word.parts[0].IsLitToken(Id.Lit_Tilde):
      return None

    prefix = ''
    found_slash = False
    # search for the next /
    for i in range(1, len(word.parts)):
      p = word.parts[i].TestLiteralForSlash()

      # Not a literal part, and we did NOT find a slash.  So there is no
      # TildeSub applied.  This would be something like ~X$var, ~$var,
      # ~$(echo), etc..  The slash is necessary.
      if p == -2:
        return None

      elif p == -1:  # no slash yet
        prefix += word.parts[i].UnquotedLiteralValue()

      elif p >= 0:
        # e.g. for ~foo!bar/baz, extract "bar"
        # NOTE: requires downcast to LiteralPart
        pre, post = word.parts[i].SplitAtIndex(p)
        prefix += pre
        tilde_part = TildeSubPart(prefix)
        remainder_part = LiteralPart(Token(Id.Lit_Chars, post))
        found_slash = True
        break

    w = CompoundWord()
    if found_slash:
      w.parts.append(tilde_part)
      w.parts.append(remainder_part)
      j = i + 1
      while j < len(word.parts):
        w.parts.append(word.parts[j])
        j += 1
    else:
      # The whole thing is a tilde sub, e.g. ~foo or ~foo!bar
      w.parts.append(TildeSubPart(prefix))
    return w

  def _TildeDetectAll(self, words):
    new_words = []
    for word in words:
      t = self._TildeDetect(word)
      if t:
        new_words.append(t)
      else:
        new_words.append(word)
    return new_words

  def _MaybeReadHereDocs(self, node):
    here_docs = node.GetHereDocsToFill()
    #print('')
    #print('--> FILLING', here_docs)
    #print('')
    for h in here_docs:
      lines = []
      #print(h.here_end)
      while True:
        # If op is <<-, strip off all leading tabs (NOT spaces).
        # (in C++, just bump the start?)
        pool_index, line = self.line_reader.GetLine()

        #print("LINE %r %r" % (line, h.here_end))
        if not line:  # EOF
          print('WARNING: unterminated here doc', file=sys.stderr)
          break

        if h.op.type == Id.Redir_DLessDash:
          line = line.lstrip('\t')
        if line.rstrip() == h.here_end:
          break

        lines.append((pool_index, line))

      parts = []
      if h.do_expansion:
        # NOTE: We read all lines at once, instead of doing it line-by-line,
        # because of cases like this:
        # cat <<EOF
        # 1 $(echo 2
        # echo 3) 4
        # EOF

        # TODO: Move this import
        from osh import parse_lib
        w_parser = parse_lib.MakeWordParserForHereDoc(lines)
        word = w_parser.ReadHereDocBody()
        if not word:
          self.AddErrorContext(
              'Error reading here doc body: %s', w_parser.Error())
          return False
        h.body_word = word
        h.was_filled = True
      else:
        # TODO: Add pool_index etc. to token
        tokens = [Token(Id.Lit_Chars, line) for _, line in lines]
        parts = [LiteralPart(t) for t in tokens]
        h.body_word.parts.extend(parts)
        h.was_filled = True

    #print('')
    #print('--> FILLED', here_docs)
    #print('')
    return True

  def _MaybeReadHereDocsAfterNewline(self, node):
    """Like _NewlineOk, but also reads here docs."""
    if not self._Peek():
      return False
    #print('_Maybe testing for newline', self.cur_word, node)
    if self.c_id == Id.Op_Newline:
      self._MaybeReadHereDocs(node)
      #print('_Maybe read redirects', node)
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
    assert self.c_kind == CKind.REDIR, self.cur_word

    # TODO: Make the code shorter.  These four cases all read the next word,
    # and interpret it differently.
    # <    filename
    # <<   here doc terminator
    # <&   file descriptor
    # <<<  here word
    if self.c_id in (Id.Redir_DLess, Id.Redir_DLessDash):  # here
      node = HereDocRedirectNode(self.cur_word.token)

      self._Next()
      if not self._Peek(): return None

      # "If any character in word is quoted, the delimiter shall be formed by
      # performing quote removal on word, and the here-document lines shall not
      # be expanded. Otherwise, the delimiter shall be the word itself."
      # NOTE: \EOF counts, or even E\OF
      ok, node.here_end, quoted = self.cur_word.EvalStatic()
      if not ok:
        self.AddErrorContext(
            'Error evaluating here doc delimiter: %s', self.cur_word)
        return None
      node.do_expansion = not quoted
      self._Next()

    elif self.c_id in (
        Id.Redir_Less, Id.Redir_Great, Id.Redir_DGreat, Id.Redir_Clobber):
      node = FilenameRedirectNode(self.cur_word.token)
      self._Next()

      if not self._Peek(): return None
      if self.c_kind != CKind.COMMAND:
        self.AddErrorContext('Expected filename after redirect operator',
            word=self.cur_word)
        return None

      node.filename = self.cur_word
      self._Next()

    elif self.c_id in (Id.Redir_GreatAnd, Id.Redir_LessAnd):  # descriptor
      node = DescriptorRedirectNode(self.cur_word.token)

      # TODO: Check that it's a number?  bash allows 1>&foo as an alias for
      # 1>foo.  I don't like that.
      self._Next()
      if not self._Peek(): return None

      node.target_fd = self.cur_word
      self._Next()

    elif self.c_id == Id.Redir_TLess:  # descriptor
      node = HereWordRedirectNode(self.cur_word.token)
      self._Next()

      if not self._Peek(): return None
      if self.c_kind != CKind.COMMAND:
        self.AddErrorContext('Expected word after <<< operator',
            word=self.cur_word)
        return None

      node.body_word = self.cur_word
      self._Next()

    else:
      self.AddErrorContext(
          'ParseRedirect: unexpected token %s' % self.cur_word)
      return None

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
      if self.c_kind != CKind.REDIR:
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
      if self.c_kind == CKind.REDIR:
        node = self.ParseRedirect()
        if not node: return None  # e.g. EOF
        redirects.append(node)

      elif self.c_kind == CKind.COMMAND:
        words.append(self.cur_word)

      else:
        break
      self._Next()
    return redirects, words

  def _SplitSimpleCommandPrefix(self, words):
    prefix_bindings = []
    suffix_words = []

    # Second pass: look for assignment words, as well as keywords
    done_prefix = False
    for w in words:
      if done_prefix:
        suffix_words.append(w)
        continue

      kv = w.LooksLikeAssignment()
      if kv:
        k, v = kv
        t = self._TildeDetect(v)
        if t:
          # t is an unevaluated word with TildeSubPart
          prefix_bindings.append((k, t))
        else:
          prefix_bindings.append((k, v))  # v is unevaluated word
      else:
        done_prefix = True
        suffix_words.append(w)
    return prefix_bindings, suffix_words

  def _MakeSimpleCommand(self, prefix_bindings, suffix_words, redirects):
    for k, v in prefix_bindings:  # FOO=(1 2 3) ls is not allowed
      if v.HasArrayPart():
        self.AddErrorContext('Unexpected array literal in binding: %s', v)
        return None

    # NOTE: Here is the place to check validity of words at parse time.  Can
    # resolve against builtins, functions, aliases, static PATH, etc.
    for w in suffix_words:  # ls FOO=(1 2 3) is not allowed
      kv = w.LooksLikeAssignment()
      if kv:
        k, v = kv
        # Normal assign words like foo=bar are just literal.  But array words
        # foo=(1 2) don't belong.  They can only be prefixes.
        if v.HasArrayPart():
          self.AddErrorContext('Unexpected array literal: %s', v)
          return None

    words2 = self._BraceExpand2(suffix_words)
    # NOTE: Must do tilde detection after brace expansion, e.g.
    # {~bob,~jane}/src should work, even though ~ isn't the leading character
    # of the initial word.
    words3 = self._TildeDetectAll(words2)

    node = SimpleCommandNode()
    node.more_env = prefix_bindings
    node.words = words3
    node.redirects = redirects
    return node

  def _MakeAssignment(self, assign_scope, assign_flags, suffix_words):
    bindings = []
    var_words = []  # local foo bar, export foo bar
    for i, w in enumerate(suffix_words):
      if i == 0:
        continue  # skip over local, export, etc.
      kv = w.LooksLikeAssignment()
      if kv:
        k, v = kv
        t = self._TildeDetect(v)
        if t:
          # t is an unevaluated word with TildeSubPart
          bindings.append((k, t))
        else:
          bindings.append((k, v))  # v is unevaluated word
      else:
        var_words.append(w)

    node = AssignmentNode(assign_scope, assign_flags)

    node.bindings = bindings
    node.words = var_words
    return node

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
    if not result: return None
    redirects, words = result

    if not words:  # e.g.  >out.txt  # redirect without words
      node = SimpleCommandNode()
      node.redirects = redirects
      return node

    prefix_bindings, suffix_words = self._SplitSimpleCommandPrefix(words)

    if not suffix_words:  # ONE=1 TWO=2  (with no other words)
      # TODO: Have a strict mode to prevent this?
      if redirects:  # >out.txt g=foo
        print('WARNING: Got redirects in assignment: %s', redirects)
      assign_flags = 0
      assign_scope = EAssignScope.GLOBAL
      node = AssignmentNode(assign_scope, assign_flags)
      node.bindings = prefix_bindings
      return node

    assign_kw = suffix_words[0].ResolveAssignmentBuiltin()

    assign_flags = 0
    assign_scope = EAssignScope.GLOBAL

    if assign_kw in (EAssignKeyword.DECLARE, EAssignKeyword.LOCAL):
      assign_scope = EAssignScope.LOCAL
      # TODO: Parse declare flags.  Hm is it done before or after evaluation?

    elif assign_kw == EAssignKeyword.EXPORT:  # global
      assign_flags |= 1 << EAssignFlags.EXPORT.value

    elif assign_kw == EAssignKeyword.READONLY:  # global
      assign_flags |= 1 << EAssignFlags.READONLY.value

    else:  # ls foo  or  FOO=bar ls foo
      assert assign_kw == EAssignKeyword.NONE
      return self._MakeSimpleCommand(prefix_bindings, suffix_words, redirects)

    if redirects:
      print('WARNING: Got redirects in assignment: %s', redirects)

    if prefix_bindings:  # FOO=bar local spam=eggs now allowed
      self.AddErrorContext('Got prefix bindings in assignment: %s',
          prefix_bindings)
      return None

    for k, v in prefix_bindings:  # FOO=(1 2 3) ls is not allowed
      if v.HasArrayPart():
        self.AddErrorContext('Unexpected array literal in binding: %s', v)
        return None

    return self._MakeAssignment(assign_scope, assign_flags, suffix_words)

  def ParseBraceGroup(self):
    """
    brace_group      : LBrace command_list RBrace ;
    """
    if not self._Eat(EKeyword.LBRACE): return None

    node = self.ParseCommandList()
    if not node:
      self.AddErrorContext('ParseBraceGroup: failed to parse command list')
      return None

    if not self._Eat(EKeyword.RBRACE): return None

    return node

  def ParseDoGroup(self):
    """
    do_group         : Do command_list Done ;          /* Apply rule 6 */
    """
    if not self._Eat(EKeyword.DO): return None

    node = self.ParseCommandList()

    if not node:
      self.AddErrorContext('ParseDoGroup: failed to parse command line')
      return None

    if not self._Eat(EKeyword.DONE): return None

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
    while True:
      if not self._Peek(): return None
      if self.c_id == Id.Op_Semi:
        self._Next()
        if not self._NewlineOk(): return None
        break
      elif self.c_id == Id.Op_Newline:
        self._Next()
        break
      words.append(self.cur_word)
      self._Next()
    return words

  def _ParseExpressionForLoop(self):
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
    elif self.c_id == EKeyword.DO:  # missing semicolon/newline allowed
      pass
    else:
      self.AddErrorContext("Unexpected token after for loop: %s",
          self.cur_word)
      return None

    body_node = self.ParseDoGroup()
    if not body_node: return None

    node.children.append(body_node)
    return node

  def _ParseCommandForLoop(self):
    node = ForNode()

    ok, value, _ = self.cur_word.EvalStatic()
    if not ok:
      self.AddErrorContext("Invalid for loop variable: %s", self.cur_word)
      return None
    node.iter_name = value
    self._Next()  # skip past name

    if not self._NewlineOk(): return None

    if not self._Peek(): return None
    if self.c_id == EKeyword.IN:
      self._Next()  # skip in

      iter_words = self.ParseForWords()
      if iter_words is None:  # empty list of words is OK
        return None
      node.iter_words = iter_words

    elif self.c_id == Id.Op_Semi:
      node.do_arg_iter = True  # implicit for loop
      self._Next()

    elif self.c_id == EKeyword.DO:
      node.do_arg_iter = True  # implicit for loop
      # do not advance

    else:
      self.AddErrorContext("Unexpected word in for loop: %s", self.cur_word,
          word=self.cur_word)
      return None

    body_node = self.ParseDoGroup()
    if not body_node: return None

    node.children.append(body_node)

    return node

  def ParseFor(self):
    """
    for_clause : For for_name newline_ok (in for_words? for_sep)? do_group ;
               | For '((' ... TODO
    """
    if not self._Eat(EKeyword.FOR): return None

    if not self._Peek(): return None
    if self.c_id == Id.Op_DLeftParen:
      return self._ParseExpressionForLoop()
    else:
      return self._ParseCommandForLoop()

  def ParseWhile(self):
    """
    while_clause     : While command_list do_group ;
    """
    self._Next()  # skip while

    cond_node = self.ParseCommandList()
    if not cond_node: return None

    body_node = self.ParseDoGroup()
    if not body_node: return None

    return WhileNode([cond_node, body_node])

  def ParseUntil(self):
    """
    until_clause     : Until command_list do_group ;
    """
    self._Next()  # skip until

    cond_node = self.ParseCommandList()
    if not cond_node: return None

    body_node = self.ParseDoGroup()
    if not body_node: return None

    return UntilNode([cond_node, body_node])

  def ParseCaseItem(self):
    """
    case_item: '('? pattern ('|' pattern)* ')'
               newline_ok command_term? trailer? ;
    """
    self.lexer.PushHint(Id.Op_RParen, Id.Right_CasePat)

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

    if not self._Eat(Id.Right_CasePat): return None
    if not self._NewlineOk(): return None

    if self.c_id not in (Id.Op_DSemi, EKeyword.ESAC):
      node = self.ParseCommandTerm()
      if not node:
        return None
    else:
      node = ElseTrueNode()  # TODO: rename to noop node?

    if not self._Peek(): return None
    # TODO: Parse are there any more combinations of SEMI, DSEMI, NEWLINE,
    # ESAC, etc.?  I think SEMI and NEWLINE is taken care of by the term.  So
    # it's just DSEMI and ESAC we worry about.
    if self.c_id == EKeyword.ESAC:
      pass
    elif self.c_id == Id.Op_DSemi:
      self._Next()
    else:
      self.AddErrorContext('Expected DSEMI or ESAC, got %s', self.cur_word,
          word=self.cur_word)
      return None

    if not self._NewlineOk(): return None

    return pat_words, node

  def ParseCaseList(self):
    """
    case_list: case_item (DSEMI newline_ok case_item)* DSEMI? newline_ok;
    """
    # TODO: The word_parser does self.lexer.MaybeUnreadOne for $().  I think I
    # need the same for subshell.  Gah.  The lexer has to get a chance to
    # translate things.

    items = []
    if not self._Peek(): return None

    while True:
      # case item begins with a command word or (
      if self.c_id == EKeyword.ESAC:
        break
      if self.c_kind != CKind.COMMAND and self.c_id != Id.Op_LParen:
        break
      item = self.ParseCaseItem()
      if not item:
        return None
      items.append(item)
      if not self._Peek(): return None
      # Now look for DSEMI or ESAC

    return items

  def ParseCase(self):
    """
    case_clause      : Case WORD newline_ok in newline_ok case_list? Esac ;
    """
    cn = CaseNode()
    self._Next()  # skip case

    if not self._Peek(): return None
    cn.to_match = self.cur_word
    self._Next()

    if not self._NewlineOk(): return None
    if not self._Eat(EKeyword.IN): return None
    if not self._NewlineOk(): return None

    items = []
    if self.c_id != EKeyword.ESAC:  # empty case list
      items = self.ParseCaseList()
      if items is None:
        self.AddErrorContext("ParseCase: error parsing case list")
        return None
      # TODO: should it return a list of nodes, and extend?
      if not self._Peek(): return None

    if not self._Eat(EKeyword.ESAC): return None
    self._Next()

    for (pat, node) in items:
      cn.pat_word_list.append(pat)
      cn.children.append(node)

    return cn

  def ParseElsePart(self, children):
    """
    else_part: (Elif command_list Then command_list)* Else command_list ;
    """
    self._Peek()
    while self.c_id == EKeyword.ELIF:
      self._Next()  # skip elif
      cond = self.ParseCommandList()
      if not cond: return None

      if not self._Eat(EKeyword.THEN): return None

      body = self.ParseCommandList()
      if not body: return None

      children.append(cond)
      children.append(body)

    if self.c_id == EKeyword.ELSE:
      self._Next()
      dummy_cond = ElseTrueNode()
      children.append(dummy_cond)
      body = self.ParseCommandList()
      if not body:
        return None
      children.append(body)

    return children

  def ParseIf(self):
    """
    if_clause        : If command_list Then command_list else_part? Fi ;
    """
    cn = IfNode()
    self._Next()  # skip if

    cond = self.ParseCommandList()
    if not cond: return None

    if not self._Eat(EKeyword.THEN): return None

    body = self.ParseCommandList()
    if not body: return None

    cn.children.append(cond)
    cn.children.append(body)

    if self.c_id in (EKeyword.ELIF, EKeyword.ELSE):
      if not self.ParseElsePart(cn.children):
        return None

    if self.c_id == EKeyword.FI:
      self._Next()
    else:
      self.AddErrorContext("Expected 'fi' to end if, got %s", self.cur_word)
      return None
    #if not self._Eat(EKeyword.FI): return None

    return cn

  def ParseCompoundCommand(self):
    """
    compound_command : brace_group
                     | subshell
                     | for_clause
                     | while_clause
                     | until_clause
                     | case_clause
                     | if_clause
                     ;
    """
    if self.c_id == EKeyword.LBRACE:
      return self.ParseBraceGroup()
    if self.c_id == Id.Op_LParen:
      return self.ParseSubshell()

    if self.c_id == EKeyword.FOR:
      return self.ParseFor()
    if self.c_id == EKeyword.WHILE:
      return self.ParseWhile()
    if self.c_id == EKeyword.UNTIL:
      return self.ParseUntil()

    if self.c_id == EKeyword.IF:
      return self.ParseIf()
    if self.c_id == EKeyword.CASE:
      return self.ParseCase()

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

    func.children.append(body)
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
    ok, name = self.cur_word.AsFuncName()
    if not ok:
      self.AddErrorContext("Invalid function name: %r", self.cur_word)
      return None
    self._Next()  # skip function name

    # Must be true beacuse of lookahead
    if not self._Peek(): return None
    assert self.c_id == Id.Op_LParen, self.cur_word

    self.lexer.PushHint(Id.Op_RParen, Id.Right_FuncDef)
    self._Next()

    if not self._Eat(Id.Right_FuncDef): return None

    if not self._NewlineOk(): return None

    func = FunctionDefNode()
    func.name = name
    if not self.ParseFunctionBody(func):
      return None

    return func

  def ParseKshFunctionDef(self):
    """
    ksh_function_def : 'function' fname ( '(' ')' )? newline_ok function_body
    """
    self._Next()  # skip past 'function'

    if not self._Peek(): return None
    ok, name = self.cur_word.AsFuncName()
    if not ok:
      self.AddErrorContext("Invalid function name: %r", self.cur_word)
      return None
    self._Next()  # skip past 'function name

    if not self._Peek(): return None

    if self.c_id == Id.Op_LParen:
      self.lexer.PushHint(Id.Op_RParen, Id.Right_FuncDef)
      self._Next()
      if not self._Eat(Id.Right_FuncDef): return None

    if not self._NewlineOk(): return None

    func = FunctionDefNode()
    func.name = name
    if not self.ParseFunctionBody(func):
      return None

    return func

  def ParseSubshell(self):
    cn = SubshellNode()

    self._Next()  # skip past (

    # Ensure that something $( (cd / && pwd) ) works.  If ) is already on the
    # translation stack, we want to delay it.

    #print('ParseSubshell lexer.PushHint ) -> )')
    self.lexer.PushHint(Id.Op_RParen, Id.Right_Subshell)

    node = self.ParseCommandList()
    if not node:
      return None
    cn.children.append(node)

    if not self._Eat(Id.Right_Subshell): return None

    return cn

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
    return DBracketNode(bnode)

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
    return DParenNode(anode)

  def ParseCommand(self):
    """
    command          : simple_command
                     | compound_command io_redirect*
                     | function_def
                     | ksh_function_def
                     | [[ ... TODO
                     | (( ArithExpr ))
                     ;
    """
    if not self._Peek(): return None

    if self.c_id == EKeyword.FUNCTION:
      return self.ParseKshFunctionDef()

    if self.c_id == EKeyword.LEFT_DBRACKET:
      node = self.ParseDBracket()
      if not node: return None
      return node

    if self.c_id == Id.Op_DLeftParen:
      node = self.ParseDParen()
      if not node: return None
      return node

    if self.c_id in (
        Id.Op_LParen, EKeyword.LBRACE, EKeyword.FOR, EKeyword.WHILE,
        EKeyword.UNTIL, EKeyword.IF, EKeyword.CASE):
      node = self.ParseCompoundCommand()
      if not node:
        return None
      redirects = self._ParseRedirectList()
      if redirects is None:
        return None
      node.redirects = redirects
      return node

    if self.c_kind == CKind.REDIR:  # Leading redirect
      return self.ParseSimpleCommand()

    if self.c_kind == CKind.COMMAND:
      if self.w_parser.LookAheadForOp() == Id.Op_LParen:  # (
        kv = self.cur_word.LooksLikeAssignment()
        if kv:
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
    if self.c_id == EKeyword.BANG:
      negated = True
      self._Next()

    child = self.ParseCommand()
    if not child: return None

    children = [child]

    if not self._Peek(): return None
    if self.c_id not in (Id.Op_Pipe, Id.Op_PipeAmp):
      if negated:
        node = PipelineNode(children, negated)
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

      # TODO: mutate 'child' if it was Id.Op_PipeAmp

      # cat <<EOF | <newline>
      if not self._MaybeReadHereDocsAfterNewline(child):
        return None

      child = self.ParseCommand()
      if not child:
        self.AddErrorContext('Error parsing command after pipe')
        # TODO: Return partial pipeline here?  All signatures shouldbe (ok,
        # node).  Only the completion uses the node when ok is False.
        return None
      children.append(child)

      if not self._Peek(): return None
      if self.c_id not in (Id.Op_Pipe, Id.Op_PipeAmp):
        break

      if self.c_id == Id.Op_PipeAmp:
        stderr_indices.append(pipe_index)
      pipe_index += 1

    # If the pipeline ended in a newline, we need to read here docs.
    if self.c_id == Id.Op_Newline:
      #print('=============> ParsePipeline CHILD', child.DebugString())
      for child in children:
        self._MaybeReadHereDocs(child)

    node = PipelineNode(children, negated)
    node.stderr_indices = stderr_indices
    return node

  def ParseAndOr(self):
    """
    and_or           : pipeline (( AND_IF | OR_IF ) newline_ok pipeline)* ;

    Left recursive / associative:

    and_or           : and_or ( AND_IF | OR_IF ) newline_ok pipeline
                     | pipeline
    """
    left = self.ParsePipeline()
    if not left:
      self.AddErrorContext('ParseAndOr: ParsePipeline failed')
      return None

    if not self._Peek(): return None  # because ParsePipeline need not _Peek()
    if self.c_id not in (Id.Op_OrIf, Id.Op_AndIf):
      return left
    op = self.c_id
    self._Next()  # Skip past operator

    # cat <<EOF || <newline>
    if not self._MaybeReadHereDocsAfterNewline(left):
      return None

    right = self.ParseAndOr()
    if not right:
      self.AddErrorContext('ParseAndOr: ParseAndOr failed')
      return None

    node = AndOrNode(op)
    node.children = [left, right]
    return node

  def ParseCommandLine(self):
    """
    NOTE: This is only called in InteractiveLoop?  Oh crap I need to really
    read and execute a line at a time then?
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
    while True:
      n = self.ParseAndOr()
      if not n:
        self.AddErrorContext('Error parsing AndOr in ParseCommandLine')
        return None
      children.append(n)

      if not self._Peek(): return None
      if self.c_id in (Id.Op_Semi,):  # also Id.Op_Amp.
                                        # TODO: Also return ForkNode
        self._Next()

        if not self._Peek(): return None
        if self.c_id == Id.Op_Newline:
          self._MaybeReadHereDocs(n)
          break
        elif self.c_id == Id.Eof_Real:
          break

      elif self.c_id == Id.Op_Newline:
        self._MaybeReadHereDocs(n)
        break

      elif self.c_id == Id.Eof_Real:
        break

      else:
        self.AddErrorContext(
            'ParseCommandLine: Unexpected token %s', self.cur_word)
        return None

    if len(children) == 1:
      return children[0]
    else:
      node = ListNode()
      node.children = children
      return node

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
      ListNode with multiple children
    """
    # Word types that will end the command term.  NOTE: there is no
    # Id.Right_CommandSub, because that's a TOKEN and not a WORD (and it gets
    # turned into Id.Eof_Real).
    # NOTE: EKeyword.RBRACE needed for func def; that's probably wrong.
    END_LIST = (
        Id.Eof_Real, Id.Eof_RParen, Id.Eof_Backtick, Id.Right_Subshell,
        EKeyword.RBRACE, Id.Op_DSemi)

    children = []
    done = False
    while not done:
      if not self._Peek(): return False
      #print('====> ParseCommandTerm word', self.cur_word)

      # Most keywords are valid "first words".  But do/done/then do not BEGIN
      # commands, so they are not valid.
      if self.c_id in (
        EKeyword.DO, EKeyword.DONE, EKeyword.THEN, EKeyword.FI, EKeyword.ELIF,
        EKeyword.ELSE, EKeyword.ESAC):
        break

      and_or = self.ParseAndOr()
      if not and_or:
        self.AddErrorContext('Error parsing AndOr in ParseCommandTerm')
        return None
      child = and_or  # default

      # TODO: How to consolidate this duplicated logic with ParseCommandLine?
      if not self._Peek(): return None
      if self.c_id == Id.Op_Newline:
        # Read ALL Here docs so far.  cat <<EOF; echo hi <newline>
        for c in children:
          self._MaybeReadHereDocs(c)
        self._MaybeReadHereDocs(child)  # Read last child's here docs
        self._Next()

        if not self._Peek(): return None
        if self.c_id in END_LIST:
          done = True

      elif self.c_id in (Id.Op_Semi, Id.Op_Amp):
        if self.c_id == Id.Op_Amp:
          child = ForkNode()
          child.children = [and_or]
        self._Next()

        if not self._Peek(): return None
        if self.c_id == Id.Op_Newline:
          for c in children:
            self._MaybeReadHereDocs(c)
          self._MaybeReadHereDocs(child)  # Read last child's

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
    if self.c_id == Id.Op_Newline:
      for c in children:
        self._MaybeReadHereDocs(c)

    if len(children) == 1:
      return children[0]
    else:
      node = ListNode()
      node.children = children
      return node

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
    if not node:
      return None
    return node

  def ParseCommandListOrEmpty(self):
    """Entry point for main() in non-interactive shell.

    Very similar to CommandList, but we allow empty files.
    """
    if not self._NewlineOk(): return None

    #print('ParseFile', self.c_kind, self.cur_word)
    # An empty node to execute
    if self.c_kind == CKind.Eof:
      return ListNode()

    node = self.ParseCommandTerm()
    if not node:
      return None

    return node

  # Alias for now
  ParseFile = ParseCommandListOrEmpty
