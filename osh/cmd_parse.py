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
from core import word
from core.id_kind import Id, Kind, REDIR_DEFAULT_FD

from osh import ast_ as ast 
from osh.lex import LexMode
from osh.bool_parse import BoolParser

assign_scope_e = ast.assign_scope
assign_flags_e = ast.assign_flags
command_e = ast.command_e


def _UnfilledHereDocs(redirects):
  return [
      r for r in redirects
      if r.op_id in (Id.Redir_DLess, Id.Redir_DLessDash) and not r.was_filled
  ]


def _GetHereDocsToFill(node):
  """For CommandParser to fill here docs"""
  # Has to be a POST ORDER TRAVERSAL of here docs, e.g.
  #
  # while read line; do cat <<EOF1; done <<EOF2
  # body
  # EOF1
  # while
  # EOF2

  # These have no redirects at all.
  if node.tag in (command_e.NoOp, command_e.Assignment):
    return []

  # These have redirects but not children.
  if node.tag in (
      command_e.SimpleCommand, command_e.DParen, command_e.DBracket):
    return _UnfilledHereDocs(node.redirects)

  # Everything else has children.
  # NOTE: When we change to heterogeneous children, we need to do something
  # smarter.
  here_docs = []
  for child in node.children:
    here_docs.extend(_GetHereDocsToFill(child))

  # && || and | don't have their own redirects, but have children that may.
  if node.tag not in (
      command_e.AndOr, command_e.Pipeline, command_e.Fork,
      command_e.CommandList):
    here_docs.extend(_UnfilledHereDocs(node.redirects))  # parent

  return here_docs


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
    self.c_kind = Kind.Undefined
    self.c_id = Id.Undefined_Tok

  def Error(self):
    return self.error_stack

  def _BadWord(self, msg, w):
    """Helper function for errors involving a word.

    Args:
      msg: format string with a single %s token
      w: Word
    """
    self.AddErrorContext(msg, w, word=w)

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
        return False
      self.cur_word = w

      self.c_kind = word.CommandKind(self.cur_word)
      self.c_id = word.CommandId(self.cur_word)
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
    """
    Returns:
      A list of new Word instances, or None if there was no brace expansion
      detected.
    """
    # Algorithm:
    #
    # Look for patterns like LBRACE COMMA RBRACE
    # And then form cross product somehow.

    # "A correctly-formed brace expansion must contain unquoted opening and
    # closing braces, and at least one unquoted comma or a valid sequence
    # expression.  Any incorrectly formed brace expansion is left unchanged. "

    # Could this be recursive?  preamble,options,postscript
    #
    # Hm bash also has integer expressions!  {1..3} => {1,2,3}
    # {1..5..2} => {1,3,5}
    # - mksh doesn't have it.

    # look for subseqeuence like '{' ','+ '}'
    # And then make a data structure for this.
    return words

  def _TildeDetectAll(self, words):
    new_words = []
    for w in words:
      t = word.TildeDetect(w)
      if t:
        new_words.append(t)
      else:
        new_words.append(w)
    return new_words

  def _MaybeReadHereDocs(self, node):
    here_docs = _GetHereDocsToFill(node)
    #print('')
    #print('--> FILLING', here_docs)
    #print('')
    for h in here_docs:
      lines = []
      #print(h.here_end)
      while True:
        # If op is <<-, strip off all leading tabs (NOT spaces).
        # (in C++, just bump the start?)
        line_id, line = self.line_reader.GetLine()

        #print("LINE %r %r" % (line, h.here_end))
        if not line:  # EOF
          print('WARNING: unterminated here doc', file=sys.stderr)
          break

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

        # TODO: Move this import
        from osh import parse_lib
        w_parser = parse_lib.MakeWordParserForHereDoc(lines)
        word = w_parser.ReadHereDocBody()
        if not word:
          self.AddErrorContext('Error reading here doc body: %s', w_parser.Error())
          return False
        h.arg_word = word
        h.was_filled = True
      else:
        # TODO: Add line_id etc. to token
        tokens = [ast.token(Id.Lit_Chars, line) for _, line in lines]
        parts = [ast.LiteralPart(t) for t in tokens]
        h.arg_word = ast.CompoundWord(parts)
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
    assert self.c_kind == Kind.Redir, self.cur_word

    first_char = self.cur_word.token.val[0]
    if first_char.isdigit():
      fd = int(first_char)
    else:
      fd = REDIR_DEFAULT_FD[self.c_id]

    if self.c_id in (Id.Redir_DLess, Id.Redir_DLessDash):  # here
      node = ast.HereDoc()
      node.op_id = self.c_id
      node.arg_word = None  # not read yet
      node.fd = fd
      node.was_filled = False
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

    else:
      node = ast.Redirect()
      node.op_id = self.c_id
      node.fd = fd
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
    prefix_bindings = []
    suffix_words = []

    # Second pass: look for assignment words, as well as keywords
    done_prefix = False
    for w in words:
      if done_prefix:
        suffix_words.append(w)
        continue

      kv = word.LooksLikeAssignment(w)
      if kv:
        k, v = kv
        t = word.TildeDetect(v)
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
      if word.HasArrayPart(v):
        self.AddErrorContext(
            'Unexpected array literal in binding: %s', v, word=v)
        return None

    # NOTE: Here is the place to check validity of words at parse time.  Can
    # resolve against builtins, functions, aliases, static PATH, etc.
    for w in suffix_words:  # ls FOO=(1 2 3) is not allowed
      kv = word.LooksLikeAssignment(w)
      if kv:
        k, v = kv
        # Normal assign words like foo=bar are just literal.  But array words
        # foo=(1 2) don't belong.  They can only be prefixes.
        if word.HasArrayPart(v):
          self.AddErrorContext('Unexpected array literal: %s', v, word=v)
          return None

    words2 = self._BraceExpand(suffix_words)
    # NOTE: Must do tilde detection after brace expansion, e.g.
    # {~bob,~jane}/src should work, even though ~ isn't the leading character
    # of the initial word.
    words3 = self._TildeDetectAll(words2)

    node = ast.SimpleCommand()
    node.words = words3
    node.redirects = redirects
    node.more_env = [ast.env_pair(name, val) for name, val in prefix_bindings]
    return node

  def _MakeAssignment(self, assign_scope, assign_flags, suffix_words):
    bindings = []
    var_words = []  # local foo bar, export foo bar
    for i, w in enumerate(suffix_words):
      if i == 0:
        continue  # skip over local, export, etc.
      kv = word.LooksLikeAssignment(w)
      if kv:
        k, v = kv
        t = word.TildeDetect(v)
        if t:
          # t is an unevaluated word with TildeSubPart
          bindings.append((k, t))
        else:
          bindings.append((k, v))  # v is unevaluated word
      else:
        var_words.append(w)

    assign_pairs = [
        ast.assign_pair(ast.LeftVar(lhs), rhs) for lhs, rhs in bindings]
    node = ast.Assignment(
        assign_scope, assign_flags, var_words, assign_pairs)

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
      node = ast.SimpleCommand()
      node.redirects = redirects
      return node

    prefix_bindings, suffix_words = self._SplitSimpleCommandPrefix(words)

    if not suffix_words:  # ONE=1 TWO=2  (with no other words)
      # TODO: Have a strict mode to prevent this?
      if redirects:  # >out.txt g=foo
        print('WARNING: Got redirects in assignment: %s', redirects)
      assign_scope = assign_scope_e.Global
      assign_pairs = [
          ast.assign_pair(ast.LeftVar(lhs), rhs) for lhs, rhs in prefix_bindings]
      node = ast.Assignment(assign_scope, [], [], assign_pairs)
      return node

    assign_kw = word.AssignmentBuiltinId(suffix_words[0])

    assign_flags = []
    assign_scope = assign_scope_e.Global

    if assign_kw in (Id.Assign_Declare, Id.Assign_Local):
      assign_scope = assign_scope_e.Local
      # TODO: Parse declare flags.  Hm is it done before or after evaluation?

    elif assign_kw == Id.Assign_Export:  # global
      assign_flags.append(assign_flags_e.Export)

    elif assign_kw == Id.Assign_Readonly:  # global
      assign_flags.append(assign_flags_e.ReadOnly)

    else:  # ls foo  or  FOO=bar ls foo
      assert assign_kw == Id.Undefined_Tok
      return self._MakeSimpleCommand(prefix_bindings, suffix_words, redirects)

    if redirects:
      print('WARNING: Got redirects in assignment: %s', redirects)

    if prefix_bindings:  # FOO=bar local spam=eggs not allowed
      # Use the location of the first value.  TODO: Use the whole word before
      # splitting.
      _, v0 = prefix_bindings[0]
      self.AddErrorContext(
          'Got prefix bindings in assignment: %s', prefix_bindings, word=v0)
      return None

    return self._MakeAssignment(assign_scope, assign_flags, suffix_words)

  def ParseBraceGroup(self):
    """
    brace_group      : LBrace command_list RBrace ;
    """
    if not self._Eat(Id.Lit_LBrace): return None

    node = self.ParseCommandList()
    if not node: return None

    if not self._Eat(Id.Lit_RBrace): return None

    # CommandList has no redirects; BraceGroup may have redirects.
    if node.tag == command_e.CommandList:
      return ast.BraceGroup(node.children)
    else:
      return ast.BraceGroup([node])

  def ParseDoGroup(self):
    """
    do_group         : Do command_list Done ;          /* Apply rule 6 */
    """
    if not self._Eat(Id.KW_Do): return None

    node = self.ParseCommandList()
    if not node: return None

    if not self._Eat(Id.KW_Done): return None
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

    node.children.append(body_node)
    return node

  def _ParseForEachLoop(self):
    node = ast.ForEach()
    node.do_arg_iter = False

    ok, value, quoted = word.StaticEval(self.cur_word)
    if not ok or quoted:
      self.AddErrorContext(
          "Invalid for loop variable: %s", self.cur_word, word=self.cur_word)
      return None
    node.iter_name = value
    self._Next()  # skip past name

    if not self._NewlineOk(): return None

    if not self._Peek(): return None
    if self.c_id == Id.KW_In:
      self._Next()  # skip in

      iter_words = self.ParseForWords()
      if iter_words is None:  # empty list of words is OK
        return None
      node.iter_words = iter_words

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

    body_node = self.ParseDoGroup()
    if not body_node: return None

    node.children.append(body_node)

    return node

  def ParseFor(self):
    """
    for_clause : For for_name newline_ok (in for_words? for_sep)? do_group ;
               | For '((' ... TODO
    """
    if not self._Eat(Id.KW_For): return None

    if not self._Peek(): return None
    if self.c_id == Id.Op_DLeftParen:
      return self._ParseForExprLoop()
    else:
      return self._ParseForEachLoop()

  def ParseWhile(self):
    """
    while_clause     : While command_list do_group ;
    """
    self._Next()  # skip while

    cond_node = self.ParseCommandList()
    if not cond_node: return None

    body_node = self.ParseDoGroup()
    if not body_node: return None

    return ast.While([cond_node, body_node])

  def ParseUntil(self):
    """
    until_clause     : Until command_list do_group ;
    """
    self._Next()  # skip until

    cond_node = self.ParseCommandList()
    if not cond_node: return None

    body_node = self.ParseDoGroup()
    if not body_node: return None

    return ast.Until([cond_node, body_node])

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

    if self.c_id not in (Id.Op_DSemi, Id.KW_Esac):
      node = self.ParseCommandTerm()
      if not node:
        return None
    else:
      node = ast.NoOp()

    if not self._Peek(): return None
    if self.c_id == Id.KW_Esac:
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
    items = []
    if not self._Peek(): return None

    while True:
      # case item begins with a command word or (
      if self.c_id == Id.KW_Esac:
        break
      if self.c_kind != Kind.Word and self.c_id != Id.Op_LParen:
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
    cn = ast.Case()
    self._Next()  # skip case

    if not self._Peek(): return None
    cn.to_match = self.cur_word
    self._Next()

    if not self._NewlineOk(): return None
    if not self._Eat(Id.KW_In): return None
    if not self._NewlineOk(): return None

    items = []
    if self.c_id != Id.KW_Esac:  # empty case list
      items = self.ParseCaseList()
      if items is None:
        self.AddErrorContext("ParseCase: error parsing case list")
        return None
      # TODO: should it return a list of nodes, and extend?
      if not self._Peek(): return None

    if not self._Eat(Id.KW_Esac): return None
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
    while self.c_id == Id.KW_Elif:
      self._Next()  # skip elif
      cond = self.ParseCommandList()
      if not cond: return None

      if not self._Eat(Id.KW_Then): return None

      body = self.ParseCommandList()
      if not body: return None

      children.append(cond)
      children.append(body)

    if self.c_id == Id.KW_Else:
      self._Next()
      dummy_cond = ast.NoOp()
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
    cn = ast.If()
    self._Next()  # skip if

    cond = self.ParseCommandList()
    if not cond: return None

    if not self._Eat(Id.KW_Then): return None

    body = self.ParseCommandList()
    if not body: return None

    cn.children.append(cond)
    cn.children.append(body)

    if self.c_id in (Id.KW_Elif, Id.KW_Else):
      if not self.ParseElsePart(cn.children):
        return None

    if not self._Eat(Id.KW_Fi): return None

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
    ok, name = word.AsFuncName(self.cur_word)
    if not ok:
      self.AddErrorContext("Invalid function name: %r",
          self.cur_word, word=self.cur_word)
      return None
    self._Next()  # skip function name

    # Must be true beacuse of lookahead
    if not self._Peek(): return None
    assert self.c_id == Id.Op_LParen, self.cur_word

    self.lexer.PushHint(Id.Op_RParen, Id.Right_FuncDef)
    self._Next()

    if not self._Eat(Id.Right_FuncDef): return None

    if not self._NewlineOk(): return None

    func = ast.FuncDef()
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
    ok, name = word.AsFuncName(self.cur_word)
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

    func = ast.FuncDef()
    func.name = name
    if not self.ParseFunctionBody(func):
      return None

    return func

  def ParseCoproc(self):
    """
    TODO:
    """
    raise NotImplementedError

  def ParseSubshell(self):
    cn = ast.Subshell()

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
                     | [[ ... TODO
                     | (( ArithExpr ))
                     ;
    """
    if not self._Peek(): return None

    if self.c_id == Id.KW_Function:
      return self.ParseKshFunctionDef()

    if self.c_id == Id.KW_DLeftBracket:
      return self.ParseDBracket()

    if self.c_id == Id.Op_DLeftParen:
      return self.ParseDParen()

    if self.c_id in (
        Id.Op_LParen, Id.Lit_LBrace, Id.KW_For, Id.KW_While, Id.KW_Until,
        Id.KW_If, Id.KW_Case):
      node = self.ParseCompoundCommand()
      if not node: return None
      redirects = self._ParseRedirectList()
      if redirects is None:
        return None
      node.redirects = redirects
      return node

    if self.c_kind == Kind.Redir:  # Leading redirect
      return self.ParseSimpleCommand()

    if self.c_kind == Kind.Word:
      if self.w_parser.LookAhead() == Id.Op_LParen:  # (
        kv = word.LooksLikeAssignment(self.cur_word)
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
      for child in children:
        self._MaybeReadHereDocs(child)

    node = ast.Pipeline(children, negated)
    node.stderr_indices = stderr_indices
    return node

  def ParseAndOr(self):
    """
    and_or           : pipeline (( AND_IF | OR_IF ) newline_ok pipeline)* ;

    Left recursive / associative:

    and_or           : and_or ( AND_IF | OR_IF ) newline_ok pipeline
                     | pipeline

    TODO: Make it left recursive -- results are wrong otherwise.  I guses you
    have to do it iteratively, and add operators?
    """
    left = self.ParsePipeline()
    if not left: return None

    if not self._Peek(): return None  # because ParsePipeline need not _Peek()
    if self.c_id not in (Id.Op_DPipe, Id.Op_DAmp):
      return left
    op = self.c_id
    self._Next()  # Skip past operator

    # cat <<EOF || <newline>
    if not self._MaybeReadHereDocsAfterNewline(left): return None

    right = self.ParseAndOr()
    if not right: return None

    node = ast.AndOr()
    node.children = [left, right]
    #node.ops = [op]
    node.op_id = op
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
      if not n: return None
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
      node = ast.CommandList(children)
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
      ast.command
    """
    # Word types that will end the command term.
    END_LIST = (
        Id.Eof_Real, Id.Eof_RParen, Id.Eof_Backtick, Id.Right_Subshell,
        Id.Lit_RBrace, Id.Op_DSemi)

    children = []
    done = False
    while not done:
      if not self._Peek(): return False
      #print('====> ParseCommandTerm word', self.cur_word)

      # Most keywords are valid "first words".  But do/done/then do not BEGIN
      # commands, so they are not valid.
      if self.c_id in (
        Id.KW_Do, Id.KW_Done, Id.KW_Then, Id.KW_Fi, Id.KW_Elif, Id.KW_Else,
        Id.KW_Esac):
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
          child = ast.Fork()
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
      node = ast.CommandList(children)
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
    if not node:
      return None

    return node
