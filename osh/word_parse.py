#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
"""
word_parse.py - Parse the shell word language.
"""

from core import base
from core.word_node import (
    CommandWord, TokenWord,
    LiteralPart, EscapedLiteralPart, SingleQuotedPart, DoubleQuotedPart,
    VarSubPart, CommandSubPart, ArithSubPart, ArrayLiteralPart, IndexVarOp,
    TestVarOp, StripVarOp, SliceVarOp, LengthVarOp, PatSubVarOp, RefVarOp)

from core.tokens import *
from core import tdop
from core.cmd_node import ForExpressionNode

from osh import arith_parse
from osh.lex import LexState

# Substitutions can be nested, but which inner subs are allowed depends on the
# outer sub.
#
# Functions that process TokenKind.LEFT, i.e. nested stuff:
#
# _ReadCommandWord
#   _ReadLeftParts 
# _ReadArithWord
#   _ReadCommandWord -- ${} $() $(()) $[] `` 
# _ReadDoubleQuotedPart (also used for here docs, needs a mode)
#   _ReadDoubleQuotedLeftParts -- ${} $() $(()) $[] ``
# _ReadVarOpArg(d_quoted)
#    _ReadCommandWord(lex_state)

# UNQUOTED: LexState.OUTER
#           All subs and quotes are allowed -- 
#           $v ${v}   $() ``   $(())   '' ""   $'' $""  <()  >()
#
# DQ:       LexState.DQ
#           Var, Command, Arith, but no quotes
#           $v ${v}   $() ``   $(()) 
#           No process substitution.
#
# LexState.ARITH:
#           Similar to DQ: Var, Command, Arith sub.  No process sub.  bash has
#           no quotes, but we are changing this in oil.  We are adding ALL FOUR
#           kinds of quotes , because we need those for associtative array
#           indexing.
#
# LexState.VS_ARG_UNQ
#   Like UNQUOTED, except we stop at }.  Everything is allowed, even process
#   substitution.
#
#   ${X:-$v}   ${X:-${v}}  ${X:-$(echo hi)}  ${X:-`echo hi`}  ${X:-$((1+2))}
#   ${X:-'single'}  ${X:-"double"}  ${X:-$'\n'}  ${X:-<(echo hi)}
#
#   But space is SIGNIFICANT.  ${a:-  b   }
#   So you should NOT just read a bunch of words after :-, unless you also
#   preserve the space tokens between.
#   In other words, like DS_VS_ARG, except SINGLE Quotes allowed?
#
# LexState.VS_ARG_DQ -- Can't be LexState.DQ because here we respect $' and $"
#    tokens, while <( token is not respected. 
#
#   Like VS_ARG_UNQ, but single quotes are NOT respected (they appear
#   literally), and process substitution is not respected (ditto).
#
#   "" and $'' and $"" are respected, but not ''.  I need a matrix for this.
#
#   Like DQ, except nested "" and $'' and $"" are RESPECTED.
#
#   It's weird that double quoted is allowed.  Not sure why that would be.
#   Unquoted is also allowed, so " a "b" c " $'' and $"" are lame, because they
#   don't appear in the DQ context.  I think I should parse those but DISALLOW.
#   You should always make $'' and $"" as a separate var!


class WordParser(object):

  def __init__(self, lexer, line_reader, words_out=None,
      lex_state=LexState.OUTER):
    self.lexer = lexer
    self.line_reader = line_reader
    # [] if we want to save an array of all words, or None if not.
    self.words_out = words_out
    self.Reset(lex_state=lex_state)

  def _Peek(self):
    """Helper method."""
    if self.next_lex_state is not None:
      self.prev_token = self.cur_token  # for completion
      self.cur_token = self.lexer.Read(self.next_lex_state)
      self.token_kind = self.cur_token.Kind()
      self.token_type = self.cur_token.type

      self.next_lex_state = None
    return self.cur_token

  def _Next(self, lex_state):
    """Set the next lex state, but don't actually read a token.

    We need this for proper interactive parsing.
    """
    self.next_lex_state = lex_state

  def Reset(self, lex_state=LexState.OUTER):
    """Called by interactive loop."""
    # For _Peek()
    self.prev_token = None  # for completion
    self.cur_token = None
    self.token_kind = TokenKind.UNDEFINED
    self.token_type = UNDEFINED_TOK

    self.next_lex_state = lex_state

    # For newline.  TODO: I think we can do this iteratively, without member
    # state.
    self.cursor = None
    self.cursor_was_newline = False

    self.error_stack = []

  # TODO: Factor this into ErrorState class.  Each parser owns one.
  def AddErrorContext(self, msg, *args, token=None, word=None):
    err = base.MakeError(msg, *args, token=token, word=word)
    self.error_stack.append(err)
  
  def Error(self):
    return self.error_stack

  def _BadToken(self, msg, token):
    """
      Args:
        msg: format string with a single %s token
        token: Token
    """
    self.AddErrorContext(msg, token, token=token)

  def PrevToken(self):
    """Inspect state.  Used by completion.

    cur_token is usually OP_NEWLINE \n, so we need the previous one.
    """
    return self.prev_token

  def _ReadVarOpArg(self, arg_lex_state, eof_type=UNDEFINED_TOK, empty_ok=True):
    # NOTE: Operators like | and < are not treated as special, so ${a:- | >} is
    # valid, even when unquoted.
    self._Next(arg_lex_state)
    self._Peek()
    return self._ReadCommandWord(
        lex_state=arg_lex_state, eof_type=eof_type, empty_ok=empty_ok)

  def _ReadSliceArg(self):
    """Read an arithmetic expression for either part of ${a : i+1 : i+2}."""
    anode = self._ReadArithExpr(do_next=False)
    if not anode: return None

    if anode.ArrayVarOpToken() != UNDEFINED_TOK:
      self.AddErrorContext('Unexpected token in slice arg: %s', anode.atype)
      return None
    return anode

  def _ReadSliceVarOp(self):
    """ VarOf ':' ArithExpr (':' ArithExpr )? """
    self._Next(LexState.ARITH)
    self._Peek()
    if self.token_type == AS_OP_COLON:  # AS_OP_COLON is a pun for VS_OP_COLON
      begin = None  # no beginning specified
    else:
      begin = self._ReadSliceArg()
      if not begin: return None
      #print('BEGIN', begin)
      #print('BVS2', self.cur_token)

    if self.token_type == AS_OP_RBRACE:
      return SliceVarOp(begin, None)  # No length specified

    # AS_OP_COLON is a pun for VS_OP_COLON
    elif self.token_type == AS_OP_COLON:
      self._Next(LexState.ARITH)
      length = self._ReadSliceArg()
      if not length: return None

      #print('after colon', self.cur_token)
      return SliceVarOp(begin, length)

    else:
      self.AddErrorContext("Unexpected token in slice: %s", self.cur_token)
      return None

  def _ReadPatSubVarOp(self, lex_state):
    """
    Match     = ('/' | '#' | '%') WORD
    VarSub    = ...
              | VarOf '/' Match '/' WORD 
    """
    do_all = False
    do_prefix = False
    do_suffix = False

    pat = self._ReadVarOpArg(lex_state, eof_type=LIT_SLASH, empty_ok=False)
    if not pat: return None

    if len(pat.parts) == 1:
      ok, s, quoted = pat.EvalStatic()
      if ok and s == '/' and not quoted:  # Looks like ${a////c}, read again
        self._Next(lex_state)
        self._Peek()
        p = LiteralPart(self.cur_token)
        pat.parts.append(p)

    # Check for other modifiers
    if pat.parts[0].IsLitToken(LIT_SLASH):
      do_all = True
      pat.parts.pop(0)
    elif pat.parts[0].IsLitToken(LIT_PERCENT):
      do_prefix = True
      pat.parts.pop(0)
    elif pat.parts[0].IsLitToken(LIT_POUND):
      do_suffix = True
      pat.parts.pop(0)

    #self._Peek()
    if self.token_type == RIGHT_VAR_SUB:
      return PatSubVarOp(pat, None, do_all, do_prefix, do_suffix)

    elif self.token_type == LIT_SLASH:
      replace = self._ReadVarOpArg(lex_state)  # do not stop at /
      if not replace: return None

      self._Peek()
      if self.token_type == RIGHT_VAR_SUB:
        return PatSubVarOp(pat, replace, do_all, do_prefix, do_suffix)

      else:
        self._BadToken("Expected } after pat sub, got %s", self.cur_token)
        return None

    else:
      self._BadToken("Expected } after pat sub, got %s", self.cur_token)
      return None

  def _ReadSubscript(self):
    """ Subscript = '[' ('@' | '*' | ArithExpr) ']' 

    LexState: BVS_1
    """
    anode = self._ReadArithExpr()
    if not anode:
      return None
    token_type = anode.ArrayVarOpToken()
    if token_type != UNDEFINED_TOK:
      op = ArrayVarOp(token_type)
    else:
      op = IndexVarOp(anode)

    # TODO: Write and use an _Eat() method?
    if self.token_type != AS_OP_RBRACKET:  # Should be looking at ]
      self._BadToken('Expected ] after subscript, got %s', self.cur_token)
      return None

    # Advance past ]
    self._Next(LexState.VS_2)
    self._Peek()  # Needed to be in the same spot as no subscript

    return op

  def _ParseVarOf(self):
    """
    No disambiguation now.

    VarOf     = NAME Subscript?
              | NUMBER      # no subscript allowed, none of these are arrays
                            # ${@[1]} doesn't work, even though slicing does
              | VarSymbol
    """
    self._Peek()
    debug_token = self.cur_token
    name = self.cur_token.val
    self._Next(LexState.VS_2)

    #print("NAME", name)
    self._Peek()  # Check for []
    if self.token_type == VS_OP_LBRACKET:
      bracket_op = self._ReadSubscript()
      if not bracket_op: return None
    else:
      bracket_op = None

    part = VarSubPart(name, token=debug_token)
    part.bracket_op = bracket_op
    return part

  def _ParseVarExpr(self, arg_lex_state):
    """
    Start parsing at the op -- we already skipped past the name.
    """
    part = self._ParseVarOf()

    self._Peek()
    if self.token_type == RIGHT_VAR_SUB:
      return part  # no ops

    # Or maybe this is a VarOpKind

    op_kind = self.token_kind

    if op_kind == TokenKind.VS_TEST:
      vtype = self.token_type
      arg_word = self._ReadVarOpArg(arg_lex_state)
      if self.token_type != RIGHT_VAR_SUB:
        self._BadToken('Unexpected token after test arg: %s', self.cur_token)
        return None

      part.test_op = TestVarOp(vtype, arg_word)

    elif op_kind == TokenKind.VS_UNARY:
      vtype = self.token_type
      arg_word = self._ReadVarOpArg(arg_lex_state)
      if self.token_type != RIGHT_VAR_SUB:
        self._BadToken('Unexpected token after unary op: %s', self.cur_token)
        return None

      op = StripVarOp(vtype, arg_word)
      part.transform_ops.append(op)

    elif op_kind == TokenKind.VS_OP:
      if self.token_type == VS_OP_SLASH:
        op = self._ReadPatSubVarOp(arg_lex_state)
        if not op: return None
        # Checked by the method above
        assert self.token_type == RIGHT_VAR_SUB, self.cur_token

      elif self.token_type == VS_OP_COLON:
        op = self._ReadSliceVarOp()
        if not op: return None
        if self.token_type != AS_OP_RBRACE:
          self._BadToken('Unexpected token after slice: %s', self.cur_token)
          return None

      else:
        raise AssertionError(self.cur_token)


      part.transform_ops.append(op)

    # Now look for ops
    return part

  def _ReadBracedVarSubPart(self, d_quoted=False):
    """For the ${} expression language.

    NAME        = [a-zA-Z_][a-zA-Z0-9_]*
    NUMBER      = [0-9]+                    # ${10}, ${11}, ...

    Subscript   = '[' ('@' | '*' | ArithExpr) ']'
    VarSymbol   = '!' | '@' | '#' | ...
    VarOf       = NAME Subscript?
                | NUMBER      # no subscript allowed, none of these are arrays
                              # ${@[1]} doesn't work, even though slicing does
                | VarSymbol

    TEST_OP     = '-' | ':-' | '=' | ':=' | '+' | ':+' | '?' | ':?'
    STRIP_OP    = '#' | '##' | '%' | '%%' 
    CASE_OP     = ',' | ',,' | '^' | '^^'

    UnaryOp     = TEST_OP | STRIP_OP | CASE_OP | ...
    Match       = ('/' | '#' | '%') WORD       # match all / prefix / suffix
    VarExpr     = VarOf
                | VarOf UnaryOp WORD
                | VarOf ':' ArithExpr (':' ArithExpr )?
                | VarOf '/' Match '/' WORD 

    LengthExpr  = '#' VarOf  # can't apply operators after length

    RefOrKeys   = '!' VarExpr  # CAN apply operators after a named ref
                               # ${!ref[0]} vs ${!keys[@]} resolved later

    PrefixQuery = '!' NAME ('*' | '@')  # list variable names with a prefix

    VarSub      = LengthExpr
                | RefOrKeys
                | PrefixQuery
                | VarExpr

    NOTES:
    - Arithmetic expressions are used twice, inside subscripts ${a[x+1]} and
      slicing ${a:x+1:y+2}
    - ${#} and ${!} need LL(2) lookahead (considering how my tokenizer works)
    - @ and * are technically arithmetic expressions in this implementation
    - We don't account for bash 4.4: ${param@operator} -- Q E P A a.  Note that
      it's also vectorized.

    Strictness over bash:
    echo ${a[0][0]} doesn't do anything useful, so we disallow it from the
    grammar
    ! and # prefixes can't be composed, even though named refs can be composed
    with other operators
    '#' means 4 different things: length prefix, VarSymbol, UnaryOp to strip a
    prefix, and it can also be a literal part of WORD.

    From the parser's point of view, the prefix # can't be combined with
    UnaryOp/slicing/matching, and the ! can.  However

    ${a[@]:1:2} is not allowed
    ${#a[@]:1:2} is allowed, but gives the wrong answer
    """
    if d_quoted:
      arg_lex_state = LexState.VS_ARG_DQ
    else:
      arg_lex_state = LexState.VS_ARG_UNQ

    self._Next(LexState.VS_1)
    self._Peek()

    debug_token = self.cur_token
    ty = self.token_type
    #print("T", debug_token)

    if ty == VS_POUND:
      # Disambiguate
      t = self.lexer.LookAheadForOp(LexState.VS_1)
      #print("\t# LOOKAHEAD", t)
      if t.type not in (UNKNOWN_TOK, RIGHT_VAR_SUB):
        # e.g. a name, '#' is the prefix
        self._Next(LexState.VS_1)
        part = self._ParseVarOf()

        self._Peek()
        if self.token_type != RIGHT_VAR_SUB:
          self._BadToken("Expected } after length expression, got %r",
              self.cur_token)
          return None

        op = LengthVarOp()
        part.transform_ops.append(op)

      else:  # not a prefix, '#' is the variable
        part = self._ParseVarExpr(arg_lex_state)
        if not part: return None

    elif ty == VS_BANG:
      t = self.lexer.LookAheadForOp(LexState.VS_1)
      #print("\t! LOOKAHEAD", t)
      if t.type not in (UNKNOWN_TOK, RIGHT_VAR_SUB):
        # e.g. a name, '!' is the prefix
        # ${!a} -- this is a ref
        # ${!3} -- this is ref
        # ${!a[1]} -- this is a ref
        # ${!a[@]} -- this is a keys
        # No lookahead -- do it in a second step, or at runtime
        self._Next(LexState.VS_1)
        part = self._ParseVarExpr(arg_lex_state)
        if not part: return None

        # NOTE: The ref op has to come FIRST, it is evaluated BEFORE any
        # operators, e.g. ${!ref#prefix} -- first deref, then strip prefix.
        op = RefVarOp()
        part.transform_ops.insert(0, op)

      else:  # not a prefix, '!' is the variable
        part = self._ParseVarExpr(arg_lex_state)
        if not part: return None

    # VS_NAME, VS_NUMBER, symbol that isn't # or !
    elif self.token_kind == TokenKind.VS:
      part = self._ParseVarExpr(arg_lex_state)
      if not part: return None

    else:
      raise AssertionError(self.cur_token)

    return part

  def _ReadDollarSqPart(self):
    # Do we need a flag to tell if it's $'' rather than ''?
    quoted_part = SingleQuotedPart()

    done = False
    while not done:
      self._Next(LexState.DOLLAR_SQ)
      self._Peek()

      if self.token_kind == TokenKind.LIT:
        quoted_part.tokens.append(self.cur_token)

      elif self.token_kind == TokenKind.RIGHT:
        done = True  # assume RIGHT_S_QUOTE

      elif self.token_kind == TokenKind.Eof:
        self.AddErrorContext('Unexpected EOF in $ single-quoted string')
        return False

      else:
        raise AssertionError(self.token_kind)

    return quoted_part

  def _ReadSingleQuotedPart(self):
    quoted_part = SingleQuotedPart()

    done = False
    while not done:
      self._Next(LexState.SQ)
      self._Peek()

      if self.token_kind == TokenKind.LIT:
        quoted_part.tokens.append(self.cur_token)

      elif self.token_kind == TokenKind.Eof:
        self.AddErrorContext('Unexpected EOF in single-quoted string')

        return False

      elif self.token_kind == TokenKind.RIGHT:
        done = True  # assume RIGHT_S_QUOTE

      else:
        raise AssertionError(
            'Unhandled token in single-quoted part %s (%d)' %
            (self.cur_token, self.token_kind))

    return quoted_part

  def _ReadDoubleQuotedLeftParts(self):
    """Read substitution parts in a double quoted context."""
    if self.token_type in (LEFT_COMMAND_SUB, LEFT_BACKTICK):
      part = self._ReadCommandSubPart(self.token_type)
      if not part: return None

    elif self.token_type == LEFT_VAR_SUB:
      part = self._ReadBracedVarSubPart(d_quoted=True)
      if not part: return None

    elif self.token_type == LEFT_ARITH_SUB:
      part = self._ReadArithSubPart()
      if not part: return None

    elif self.token_type == LEFT_ARITH_SUB2:
      part = self._ReadArithSub2Part()
      if not part: return None

    else:
      raise AssertionError(self.cur_token)

    return part

  def _ReadLeftParts(self):
    """Read substitutions and quoted strings."""

    if self.token_type == LEFT_D_QUOTE:
      part = self._ReadDoubleQuotedPart()
      if not part: return None

    elif self.token_type == LEFT_S_QUOTE:
      part = self._ReadSingleQuotedPart()
      if not part: return None

    elif self.token_type in (
        LEFT_COMMAND_SUB, LEFT_BACKTICK, LEFT_PROC_SUB_IN, LEFT_PROC_SUB_OUT):
      part = self._ReadCommandSubPart(self.token_type)
      if not part: return None

    elif self.token_type == LEFT_VAR_SUB:
      part = self._ReadBracedVarSubPart(d_quoted=False)
      if not part: return None

    elif self.token_type == LEFT_ARITH_SUB:
      part = self._ReadArithSubPart()
      if not part: return None

    elif self.token_type == LEFT_ARITH_SUB2:
      part = self._ReadArithSub2Part()
      if not part: return None

    elif self.token_type == LEFT_DD_QUOTE:
      # NOTE: $"" is treated as "" for now.  Does it make sense to add the token?
      part = self._ReadDoubleQuotedPart()
      if not part: return None

    elif self.token_type == LEFT_DS_QUOTE:
      part = self._ReadDollarSqPart()
      if not part: return None

    else:
      raise AssertionError('%s not handled' % self.cur_token)

    return part

  def _ReadDoubleQuotedPart(self, eof_type=UNDEFINED_TOK, here_doc=False):
    """
    Args:
      eof_type: for stopping at }, LIT_RBRACE
      here_doc: Whether we are reading in a here doc context

    Also ${foo%%a b c}  # treat this as double quoted.  until you hit
    """
    quoted_part = DoubleQuotedPart()

    done = False
    while not done:
      self._Next(LexState.DQ)
      self._Peek()
      #print(self.cur_token)

      if self.token_type == eof_type:  # e.g. stop at }
        done = True
        continue

      elif self.token_kind == TokenKind.LIT:
        if self.token_type == LIT_ESCAPED_CHAR:
          part = EscapedLiteralPart(self.cur_token)
        else:
          part = LiteralPart(self.cur_token)
        quoted_part.parts.append(part)

      elif self.token_kind == TokenKind.LEFT:
        part = self._ReadDoubleQuotedLeftParts()
        if not part:
          return None
        quoted_part.parts.append(part)

      elif self.token_kind == TokenKind.VS:
        # strip $ off of $name, $$, etc.
        part = VarSubPart(self.cur_token.val[1:], token=self.cur_token)
        quoted_part.parts.append(part)

      elif self.token_kind == TokenKind.RIGHT:
        assert self.token_type == RIGHT_D_QUOTE
        if here_doc:
          # Turn RIGHT_D_QUOTE into a literal part
          quoted_part.parts.append(LiteralPart(self.cur_token))
        else:
          done = True  # assume RIGHT_D_QUOTE

      elif self.token_kind == TokenKind.Eof:
        if here_doc:  # here docs will have an EOF in their token stream
          done = True
        else:
          self.AddErrorContext('Unexpected EOF in double-quoted string')
          return False

      else:
        raise AssertionError(self.cur_token)

    return quoted_part

  def _ReadCommandSubPart(self, token_type):
    """
    NOTE: This is not in the grammar, because word parts aren't in the grammar!

    command_sub = '$(' command_list ')'
    """
    #print('_ReadCommandSubPart', self.cur_token)
    self._Next(LexState.OUTER)  # advance past $( or `

    node_token = self.cur_token

    # Set the lexer in a state so ) becomes the EOF token.
    #print('_ReadCommandSubPart lexer.PushTranslation ) -> EOF')
    if token_type in (LEFT_COMMAND_SUB, LEFT_PROC_SUB_IN, LEFT_PROC_SUB_OUT):
      self.lexer.PushTranslation(OP_RPAREN, Eof_RPAREN)
    elif token_type == LEFT_BACKTICK:
      self.lexer.PushTranslation(LEFT_BACKTICK, Eof_BACKTICK)
    else:
      raise AssertionError(self.token_type)

    from osh import parse_lib
    c_parser = parse_lib.MakeParserForCommandSub(self.line_reader, self.lexer)

    node = c_parser.ParseCommandListOrEmpty()  # `` and $() allowed
    if not node:
      # Example of parse error:
      # echo $(cat |)  OR
      # echo `cat |`
      error_stack = c_parser.Error()
      self.error_stack.extend(error_stack)
      print(self.error_stack)
      self.AddErrorContext('Error parsing commmand list in command sub')
      return None

    cs_part = CommandSubPart(node_token, node)
    return cs_part

  def _ReadArithExpr(self, do_next=True):
    """Read and parse an arithmetic expression in various contexts.

    $(( 1+2 ))
    (( a=1+2 ))
    ${a[ 1+2 ]}
    ${a : 1+2 : 1+2}

    See tests/arith-context.test.sh for ambiguous cases.

    ${a[a[0]]} is valid  # VS_RBRACKET vs AS_OP_RBRACKET

    ${s : a<b?0:1 : 1}  # VS_COLON vs AS_OP_COLON

    TODO: Instead of having an eof_type.  I think we should use just run the
    arith parser until it's done.  That will take care of both : and ].  We
    switch the state back.

    See the assertion in ArithParser.Parse() -- unexpected extra input.
    """
    if do_next:
      self._Next(LexState.ARITH)
    spec = arith_parse.MakeShellSpec()
    a_parser = tdop.TdopParser(spec, self)  # Calls ReadWord(LexState.ARITH)
    anode = a_parser.Parse()
    if not anode:
      error_stack = a_parser.Error()
      self.error_stack.extend(error_stack)
    return anode  # could be None

  def _ReadArithSubPart(self):
    """
    Read an arith substitution, which contains an arith expression, e.g.
    $((a + 1)).
    """
    # The second one needs to be disambiguated in stuff like stuff like:
    # $(echo $(( 1+2 )) )
    self.lexer.PushTranslation(OP_RPAREN, RIGHT_ARITH_SUB)

    # NOTE: To disambiguate $(( as arith sub vs. command sub and subshell, we
    # could save the lexer/reader state here, and retry if the arithmetic parse
    # fails.  But we can almost always catch this at parse time.  There could
    # be some exceptions like:
    # $((echo * foo))  # looks like multiplication
    # $((echo / foo))  # looks like division

    anode = self._ReadArithExpr()
    if not anode:
      self.AddErrorContext("Error parsing arith sub part") 
      return None

    if self.token_type != AS_OP_RPAREN:
      self._BadToken('Expected first paren to end arith sub, got %s',
          self.cur_token)
      return None
    self._Next(LexState.OUTER)  # TODO: This could be DQ or ARITH too

    # PROBLEM: $(echo $(( 1 + 2 )) )
    # Two right parens break the Eof_RPAREN scheme
    self._Peek()
    if self.token_type != RIGHT_ARITH_SUB:
      self._BadToken('Expected second paren to end arith sub, got %s',
          self.cur_token)
      return None

    return ArithSubPart(anode)

  def _ReadArithSub2Part(self):
    """Non-standard arith sub $[a + 1]."""
    anode = self._ReadArithExpr()
    if not anode:
      self.AddErrorContext("Error parsing arith sub part") 
      return None

    if self.token_type != AS_OP_RBRACKET:
      self.AddErrorContext("Expected ], got %s", self.cur_token)
      return None

    return ArithSubPart(anode)

  def ReadDParen(self):
    """Read ((1+ 2))  -- command context.

    We're using the word parser because it's very similar to _ReadArithExpr
    above.
    """
    # The second one needs to be disambiguated in stuff like stuff like:
    # TODO: Be consistent with ReadForExpression below and use LexState.ARITH?
    # Then you can get rid of this.
    self.lexer.PushTranslation(OP_RPAREN, OP_RIGHT_DPAREN)

    anode = self._ReadArithExpr()
    if not anode:
      self.AddErrorContext("Error parsing dparen statement") 
      return None

    #print('xx ((', self.cur_token)
    if self.token_type != AS_OP_RPAREN:
      self._BadToken('Expected first paren to end arith sub, got %s',
          self.cur_token)
      return None
    self._Next(LexState.OUTER)

    # PROBLEM: $(echo $(( 1 + 2 )) )
    self._Peek()
    if self.token_type != OP_RIGHT_DPAREN:
      self._BadToken('Expected second paren to end arith sub, got %s',
          self.cur_token)
      return None
    self._Next(LexState.OUTER)

    return anode

  def ReadForExpression(self):
    """Read ((i=0; i<5; ++i)) -- part of command context.

    """
    # No PushTranslation because we're in arith state.
    #self.lexer.PushTranslation(OP_RPAREN, OP_RIGHT_DPAREN)

    self._Next(LexState.ARITH)  # skip over ((

    self._Peek()
    if self.token_type == AS_OP_SEMI:
      #print('Got empty init')
      init_node = None
    else:
      init_node = self._ReadArithExpr(do_next=False)
      if not init_node:
        self.AddErrorContext("Error parsing for init") 
        return None
    self._Next(LexState.ARITH)
    #print('INIT',init_node)

    self._Peek()
    if self.token_type == AS_OP_SEMI:
      #print('Got empty condition')
      cond_node = None
    else:
      cond_node = self._ReadArithExpr(do_next=False)
      if not cond_node:
        self.AddErrorContext("Error parsing for cond") 
        return None
    self._Next(LexState.ARITH)
    #print('COND',cond_node)

    self._Peek()
    if self.token_type == AS_OP_RPAREN:
      #print('Got empty update')
      update_node = None
    else:
      update_node = self._ReadArithExpr(do_next=False)
      if not update_node:
        self.AddErrorContext("Error parsing for update") 
        return None
    self._Next(LexState.ARITH)
    #print('UPDATE',update_node)

    #print('TT', self.cur_token)
    # Second paren
    self._Peek()
    if self.token_type != AS_OP_RPAREN:
      self._BadToken('Expected right paren to end for loop expression, got %s',
          self.cur_token)
      return None
    self._Next(LexState.OUTER)

    return ForExpressionNode(init_node, cond_node, update_node)

  def _ReadArrayLiteralPart(self):
    array_part = ArrayLiteralPart()

    self._Next(LexState.OUTER)  # advance past (
    self._Peek()
    assert self.cur_token.type == OP_LPAREN, self.cur_token

    # MUST use a new word parser (with same lexer).
    w_parser = WordParser(self.lexer, self.line_reader)
    while True:
      word = w_parser.ReadOuter()
      if word.Type() == RIGHT_ARRAY_LITERAL:
        break
      array_part.words.append(word)

    return array_part

  def _ReadCommandWord(self, eof_type=UNDEFINED_TOK, lex_state=LexState.OUTER,
                       empty_ok=True):
    """
    Precondition: Looking at the first token of the first word part
    Postcondition: Looking at the token after, e.g. space or operator
    """
    #print('_ReadCommandWord', lex_state)
    word = CommandWord()

    num_parts = 0
    done = False
    while not done:
      allow_done = empty_ok or num_parts != 0
      self._Peek()
      #print('CW',self.cur_token)
      if allow_done and self.token_type == eof_type:
        done = True  # e.g. for ${}

      elif self.token_kind == TokenKind.LIT:
        if self.token_type == LIT_ESCAPED_CHAR:
          part = EscapedLiteralPart(self.cur_token)
        else:
          part = LiteralPart(self.cur_token)
        word.parts.append(part)

        if self.token_type == LIT_VAR_LIKE:
          #print('@', self.lexer.LookAheadForOp())
          #print('@', self.cursor)
          #print('@', self.cur_token)

          t = self.lexer.LookAheadForOp(LexState.OUTER)
          if t.type == OP_LPAREN:
            self.lexer.PushTranslation(OP_RPAREN, RIGHT_ARRAY_LITERAL)
            part2 = self._ReadArrayLiteralPart()
            if not part2:
              self.AddErrorContext('_ReadArrayLiteralPart failed')
              return False
            word.parts.append(part2)

      elif self.token_kind == TokenKind.VS:
        part = VarSubPart(self.cur_token.val[1:])  # strip $
        word.parts.append(part)

      elif self.token_kind == TokenKind.LEFT:
        #print('_ReadLeftParts')
        part = self._ReadLeftParts()
        if not part:
          return None
        word.parts.append(part)

      # NOT done yet, will advance below
      elif self.token_kind == TokenKind.RIGHT:
        # Still part of the word; will be done on the next iter.
        if self.token_type == RIGHT_D_QUOTE:
          pass
        elif self.token_type == RIGHT_COMMAND_SUB:
          pass
        elif self.token_type == RIGHT_SUBSHELL:
          # LEXER HACK for (case x in x) ;; esac )
          assert self.next_lex_state == None  # Rewind before it's used
          if self.lexer.MaybeUnreadOne():
            self.lexer.PushTranslation(OP_RPAREN, RIGHT_SUBSHELL)
            self._Next(lex_state)
          done = True
        else:
          done = True

      elif self.token_kind == TokenKind.IGNORED:
        done = True

      else:
        # LEXER HACK for unbalanced case clause.  'case foo in esac' is valid,
        # so to test for ESAC, we can read ) before getting a chance to
        # PushTranslation(OP_RPAREN, RIGHT_CASE_PAT).  So here we unread one
        # token and do it again.

        # We get OP_RPAREN at top level:      case x in x) ;; esac 
        # We get Eof_RPAREN inside ComSub:  $(case x in x) ;; esac )
        if self.token_type in (OP_RPAREN, Eof_RPAREN):
          assert self.next_lex_state == None  # Rewind before it's used
          if self.lexer.MaybeUnreadOne():
            if self.token_type == Eof_RPAREN:
              self.lexer.PushTranslation(OP_RPAREN, Eof_RPAREN)  # Redo translation
            self._Next(lex_state)

        done = True  # anything we don't recognize means we're done

      if not done:
        self._Next(lex_state)
      num_parts += 1
    return word

  def _ReadArithWord(self):
    """Helper function for ReadArithWord."""
    #assert self.token_type != UNDEFINED_TOK
    self._Peek()
    #print('_ReadArithWord', self.cur_token)

    if self.token_kind == TokenKind.UNKNOWN:
      self.AddErrorContext("Unknown token in arith context: %s",
          self.cur_token, token=self.cur_token)
      return None, False

    elif self.token_kind == TokenKind.Eof:
      # Just return EOF token
      w = TokenWord(self.cur_token)
      return w, False
      #self.AddErrorContext("Unexpected EOF in arith context: %s",
      #    self.cur_token, token=self.cur_token)
      #return None, False

    elif self.token_kind == TokenKind.IGNORED:
      # Space should be ignored.  TODO: change this to SPACE_SPACE and
      # SPACE_NEWLINE?  or SPACE_TOK.
      self._Next(LexState.ARITH)
      return None, True  # Tell wrapper to try again

    elif self.token_kind in (TokenKind.AS_OP, TokenKind.RIGHT):
      # RIGHT_ARITH_SUB is just a normal token, handled by ArithParser
      self._Next(LexState.ARITH)
      w = TokenWord(self.cur_token)
      return w, False

    elif self.token_kind in (TokenKind.LIT, TokenKind.LEFT):
      w = self._ReadCommandWord(lex_state=LexState.ARITH)
      if not w:
        return None, True
      return w, False

    elif self.token_kind == TokenKind.VS:
      # strip $ off of $name, $$, etc.
      # TODO: Maybe consolidate with _ReadDoubleQuotedPart
      part = VarSubPart(self.cur_token.val[1:], token=self.cur_token)
      self._Next(LexState.ARITH)
      w = CommandWord(parts=[part])
      return w, False

    else:
      self._BadToken("Unexpected token parsing arith sub: %s", self.cur_token)
      return None, False

    raise AssertionError("Shouldn't get here")

  def _Read(self, lex_state):
    """Helper function for Read().

    Returns:
      2-tuple (word, need_more)
        word: Word, or None if there was an error, or need_more is set
        need_more: True if the caller should call us again
    """
    #print('_Read', lex_state, self.cur_token)
    self._Peek()

    if self.token_kind == TokenKind.Eof:
      # No advance
      return TokenWord(self.cur_token), False

    # Allow AS_OP for ) at end of for loop?
    elif self.token_kind in (TokenKind.OP, TokenKind.REDIR, TokenKind.AS_OP):
      self._Next(lex_state)
      if self.token_type == OP_NEWLINE:
        if self.cursor_was_newline:
          #print('SKIP(nl)', self.cur_token)
          return None, True

      return TokenWord(self.cur_token), False

    elif self.token_kind == TokenKind.RIGHT:
      #print('WordParser.Read: TokenKind.RIGHT', self.cur_token)
      if self.token_type not in (
          RIGHT_SUBSHELL, RIGHT_FUNC_DEF, RIGHT_CASE_PAT, RIGHT_ARRAY_LITERAL):
        raise AssertionError(self.cur_token)

      self._Next(lex_state)
      return TokenWord(self.cur_token), False

    elif self.token_kind in (TokenKind.IGNORED, TokenKind.WS):
      self._Next(lex_state)
      return None, True  # tell Read() to try again

    elif self.token_kind in (TokenKind.VS, TokenKind.LIT, TokenKind.LEFT):
      # We're beginning a word.  If we see LIT_POUND, change to
      # LexState.COMMENT and read until end of line.  (TODO: How to add
      # comments to AST?)
      if self.token_type == LIT_POUND:
        self._Next(LexState.COMMENT)
        self._Peek()
        assert self.token_type == IGNORED_COMMENT, self.cur_token
        # The next iteration will go into TokenKind.IGNORED and set lex state
        # to LexState.OUTER/etc.
        return None, True  # tell Read() to try again after comment

      else:
        # TODO: Pass another lex_state
        w = self._ReadCommandWord(lex_state=lex_state)
        if not w:
          self.AddErrorContext('Error reading command word',
              token=self.cur_token)
          return None, False
        return w, False

    else:
      raise AssertionError(
          'Unhandled: %s (%s)' % (self.cur_token, self.token_kind))

    raise AssertionError("Shouldn't get here")

  def LookAheadForOp(self):
    # Is this correct?  Should we also call self._Peek()  here?
    if self.cur_token is None:
      token = self.lexer.LookAheadForOp(LexState.OUTER)
    elif self.cur_token.type == WS_SPACE:
      token = self.lexer.LookAheadForOp(LexState.OUTER)
    else:
      token = self.cur_token
    return token.type

  def ReadWord(self, lex_state):
    """Read the next Word.

    Returns:
      Word, or None if there was an error
    """
    # Implementation note: This is an stateful/iterative function that calls
    # the stateless "_Read" function.
    while True:
      if lex_state == LexState.ARITH:
        # TODO: Can this be unified?
        word, need_more = self._ReadArithWord()
      elif lex_state in (
          LexState.OUTER, LexState.DBRACKET, LexState.BASH_REGEX):
        word, need_more = self._Read(lex_state)
      else:
        raise AssertionError('Invalid lex state %s' % lex_state)
      if not need_more:
        break

    if not word:
      return None

    if self.words_out is not None:
      self.words_out.append(word)
    self.cursor = word

    # TODO: Do conslidation of newlines in the lexer?
    # Note that there can be an infinite (IGNORED_COMMENT OP_NEWLINE
    # IGNORED_COMMENT OP_NEWLINE) sequence, so we have to keep track of the
    # last non-ignored token.
    self.cursor_was_newline = (self.cursor.Type() == OP_NEWLINE)
    return self.cursor

  def ReadOuter(self):
    return self.ReadWord(LexState.OUTER)

  def ReadHereDocBody(self):
    """
    Sort of like Read(), except we're in a double quoted context, but not using
    double quotes.

    Returns:
      CommandWord.  NOTE: We could also just use a DoubleQuotedPart for both
      cases?
    """
    w = CommandWord()
    dq = self._ReadDoubleQuotedPart(here_doc=True)
    if not dq:
      self.AddErrorContext('Error parsing here doc body')
      return False
    w.parts.append(dq)
    return w

