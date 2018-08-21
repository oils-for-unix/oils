#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
word_parse.py - Parse the shell word language.
"""

from asdl import const

from osh.meta import Id, Kind, LookupKind
from core import braces
from core import word
from core import tdop
from core import util

from osh import arith_parse
from osh.meta import ast, types

word_part_e = ast.word_part_e
word_e = ast.word_e
lex_mode_e = types.lex_mode_e

p_die = util.p_die
log = util.log

# Substitutions can be nested, but which inner subs are allowed depends on the
# outer sub.  See _ReadLeftParts vs. _ReadDoubleQuotedLeftParts.

# lex_mode_e.OUTER
#   All subs and quotes are allowed --
#   $v ${v}   $() ``   $(())   '' ""   $'' $""  <()  >()
#
# lex_mode_e.DQ
#   Var, Command, Arith, but no quotes
#   $v ${v}   $() ``   $(())
#   No process substitution.
#
# lex_mode_e.ARITH:
#   Similar to DQ: Var, Command, Arith sub.  No process sub.  bash has no
#   quotes, but we are changing this in oil.  We are adding ALL FOUR kinds of
#   quotes , because we need those for associtative array indexing.
#
# lex_mode_e.VS_ARG_UNQ
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
# lex_mode_e.VS_ARG_DQ
#   Can't be lex_mode_e.DQ because here we respect $' and $" tokens, while <(
#   token is not respected.
#
#   Like VS_ARG_UNQ, but single quotes are NOT respected (they appear
#   literally), and process substitution is not respected (ditto).
#
#   "" and $'' and $"" are respected, but not ''.  I need a matrix for this.
#
#   Like DQ, except nested "" and $'' and $"" are RESPECTED.
#
#   It's weird that double quotes are allowed.  Not sure why that would be.
#   Unquoted is also allowed, so " a "b" c " $'' and $"" are lame, because they
#   don't appear in the DQ context.  I think I should parse those but DISALLOW.
#   You should always make $'' and $"" as a separate var!

class WordParser(object):

  def __init__(self, lexer, line_reader, lex_mode=lex_mode_e.OUTER):
    self.lexer = lexer
    self.line_reader = line_reader
    self.Reset(lex_mode=lex_mode)

  def _Peek(self):
    """Helper method."""
    if self.next_lex_mode is not None:
      self.prev_token = self.cur_token  # for completion
      self.cur_token = self.lexer.Read(self.next_lex_mode)
      self.token_kind = LookupKind(self.cur_token.id)
      self.token_type = self.cur_token.id

      self.next_lex_mode = None
    return self.cur_token

  def _Next(self, lex_mode):
    """Set the next lex state, but don't actually read a token.

    We need this for proper interactive parsing.
    """
    self.next_lex_mode = lex_mode

  def Reset(self, lex_mode=lex_mode_e.OUTER):
    """Called by interactive loop."""
    # For _Peek()
    self.prev_token = None  # for completion
    self.cur_token = None
    self.token_kind = Kind.Undefined
    self.token_type = Id.Undefined_Tok

    self.next_lex_mode = lex_mode

    # For newline.  TODO: I think we can do this iteratively, without member
    # state.
    self.cursor = None
    self.cursor_was_newline = False

    self.error_stack = []

  def AddErrorContext(self, msg, *args, **kwargs):
    err = util.ParseError(msg, *args, **kwargs)
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

    cur_token is usually Id.Op_Newline \n, so we need the previous one.
    """
    return self.prev_token

  def _ReadVarOpArg(self, arg_lex_mode, eof_type=Id.Undefined_Tok,
                    empty_ok=True):
    # NOTE: Operators like | and < are not treated as special, so ${a:- | >} is
    # valid, even when unquoted.
    self._Next(arg_lex_mode)
    self._Peek()

    w = self._ReadCompoundWord(
        lex_mode=arg_lex_mode, eof_type=eof_type, empty_ok=empty_ok)
    if not w:
      return None

    # This is for "${s:-}", ${s/a//}, etc.  It is analogous to
    # LooksLikeAssignment where we turn x= into x=''.  It has the same
    # potential problem of not having spids.
    #
    # NOTE: empty_ok is False only for the PatSub pattern, which means we'll
    # return a CompoundWord with no parts, which is explicitly checked with a
    # custom error message.
    if not w.parts and arg_lex_mode == lex_mode_e.VS_ARG_DQ and empty_ok:
      w.parts.append(ast.EmptyPart())
    return w

  def _ReadSliceArg(self):
    """Read an arithmetic expression for either part of ${a : i+1 : i+2}."""
    anode = self._ReadArithExpr(do_next=False)
    return anode

  def _ReadSliceVarOp(self):
    """ VarOf ':' ArithExpr (':' ArithExpr )? """
    self._Next(lex_mode_e.ARITH)
    self._Peek()
    if self.token_type == Id.Arith_Colon:  # A pun for Id.VOp2_Colon
      begin = None  # no beginning specified
    else:
      begin = self._ReadSliceArg()
      if not begin: return None
      #print('BEGIN', begin)
      #print('BVS2', self.cur_token)

    if self.token_type == Id.Arith_RBrace:
      return ast.Slice(begin, None)  # No length specified

    # Id.Arith_Colon is a pun for Id.VOp2_Colon
    elif self.token_type == Id.Arith_Colon:
      self._Next(lex_mode_e.ARITH)
      length = self._ReadSliceArg()
      if not length: return None

      #print('after colon', self.cur_token)
      return ast.Slice(begin, length)

    else:
      p_die("Unexpected token in slice: %r", self.cur_token.val,
            token=self.cur_token)

  def _ReadPatSubVarOp(self, lex_mode):
    """
    Match     = ('/' | '#' | '%') WORD
    VarSub    = ...
              | VarOf '/' Match '/' WORD
    """
    do_all = False
    do_prefix = False
    do_suffix = False

    pat = self._ReadVarOpArg(lex_mode, eof_type=Id.Lit_Slash, empty_ok=False)
    if not pat:
      return None

    if len(pat.parts) == 1:
      ok, s, quoted = word.StaticEval(pat)
      if ok and s == '/' and not quoted:  # Looks like ${a////c}, read again
        self._Next(lex_mode)
        self._Peek()
        p = ast.LiteralPart(self.cur_token)
        pat.parts.append(p)

    if len(pat.parts) == 0:
      p_die('Pattern in ${x/pat/replace} must not be empty',
            token=self.cur_token)

    # Check for / # % modifier on pattern.
    first_part = pat.parts[0]
    if first_part.tag == word_part_e.LiteralPart:
      lit_id = first_part.token.id
      if lit_id == Id.Lit_Slash:
        do_all = True
        pat.parts.pop(0)
      elif lit_id == Id.Lit_Pound:
        do_prefix = True
        pat.parts.pop(0)
      elif lit_id == Id.Lit_Percent:
        do_suffix = True
        pat.parts.pop(0)

    if len(pat.parts) == 0:
      # TODO: Print the modifier better.
      p_die('Pattern in ${x/pat/replace} must not be empty (got modifier %s)',
            first_part, token=self.cur_token)

    if self.token_type == Id.Right_VarSub:
      # e.g. ${v/a} is the same as ${v/a/}  -- empty replacement string
      return ast.PatSub(pat, None, do_all, do_prefix, do_suffix)

    elif self.token_type == Id.Lit_Slash:
      replace = self._ReadVarOpArg(lex_mode)  # do not stop at /
      if not replace:
        return None

      self._Peek()
      if self.token_type != Id.Right_VarSub:
        # NOTE: I think this never happens.
        # We're either in the VS_ARG_UNQ or VS_ARG_DQ lex state, and everything
        # there is Lit_ or Left_, except for }.
        p_die("Expected } after replacement string, got %s", self.cur_token,
              token=self.cur_token)

      return ast.PatSub(pat, replace, do_all, do_prefix, do_suffix)

    else:
      # Happens with ${x//} and ${x///foo}, see test/parse-errors.sh
      p_die("Expected } after pat sub, got %r", self.cur_token.val,
            token=self.cur_token)

  def _ReadSubscript(self):
    """ Subscript = '[' ('@' | '*' | ArithExpr) ']'
    """
    # Lookahead to see if we get @ or *.  Otherwise read a full arithmetic
    # expression.
    t2 = self.lexer.LookAhead(lex_mode_e.ARITH)
    if t2.id in (Id.Lit_At, Id.Arith_Star):
      op = ast.WholeArray(t2.id)

      self._Next(lex_mode_e.ARITH)  # skip past [
      self._Peek()
      self._Next(lex_mode_e.ARITH)  # skip past @
      self._Peek()
    else:
      anode = self._ReadArithExpr()
      if not anode:
        return None
      op = ast.ArrayIndex(anode)

    if self.token_type != Id.Arith_RBracket:  # Should be looking at ]
      p_die('Expected ] after subscript, got %r', self.cur_token.val,
            token=self.cur_token)

    self._Next(lex_mode_e.VS_2)  # skip past ]
    self._Peek()  # Needed to be in the same spot as no subscript

    return op

  def _ParseVarOf(self):
    """
    VarOf     = NAME Subscript?
              | NUMBER      # no subscript allowed, none of these are arrays
                            # ${@[1]} doesn't work, even though slicing does
              | VarSymbol
    """
    self._Peek()
    name_token = self.cur_token
    self._Next(lex_mode_e.VS_2)

    self._Peek()  # Check for []
    if self.token_type == Id.VOp2_LBracket:
      bracket_op = self._ReadSubscript()
      if not bracket_op: return None
    else:
      bracket_op = None

    part = ast.BracedVarSub(name_token)
    part.bracket_op = bracket_op
    return part

  def _ParseVarExpr(self, arg_lex_mode):
    """
    Start parsing at the op -- we already skipped past the name.
    """
    part = self._ParseVarOf()
    if not part: return None

    self._Peek()
    if self.token_type == Id.Right_VarSub:
      return part  # no ops

    # Or maybe this is a VarOpKind

    op_kind = self.token_kind

    if op_kind == Kind.VTest:
      op_id = self.token_type
      arg_word = self._ReadVarOpArg(arg_lex_mode)
      if self.token_type != Id.Right_VarSub:
        # NOTE: Not sure how to tickle this.  May not be possible.
        self._BadToken('Unexpected token after test arg: %s', self.cur_token)
        return None

      part.suffix_op = ast.StringUnary(op_id, arg_word)

    elif op_kind == Kind.VOp1:
      op_id = self.token_type
      arg_word = self._ReadVarOpArg(arg_lex_mode)
      if self.token_type != Id.Right_VarSub:
        # NOTE: Not sure how to tickle this.  May not be possible.
        self._BadToken('Unexpected token after unary op: %s', self.cur_token)
        return None

      op = ast.StringUnary(op_id, arg_word)
      part.suffix_op = op

    elif op_kind == Kind.VOp2:
      if self.token_type == Id.VOp2_Slash:
        op = self._ReadPatSubVarOp(arg_lex_mode)
        if not op:
          return None
        # Checked by the method above
        assert self.token_type == Id.Right_VarSub, self.cur_token

      elif self.token_type == Id.VOp2_Colon:
        op = self._ReadSliceVarOp()
        if not op:
          return None
        # NOTE: } in arithmetic mode.
        if self.token_type != Id.Arith_RBrace:
          # Token seems off; doesn't point to X in # ${a:1:2 X
          p_die('Unexpected token after slice: %r', self.cur_token.val,
                token=self.cur_token)

      else:
        p_die('Unexpected token %s', self.cur_token, token=self.cur_token)

      part.suffix_op = op

    # NOTE: Arith_RBrace is for slicing, because it reads } in arithmetic
    # mode.  It's redundantly checked above.
    if self.token_type not in (Id.Right_VarSub, Id.Arith_RBrace):
      # ${a.} or ${!a.}
      p_die('Expected } after var sub, got %r', self.cur_token.val,
            token=self.cur_token)

    # Now look for ops
    return part

  def _ReadBracedBracedVarSub(self, d_quoted=False):
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
    left_spid = self.cur_token.span_id

    if d_quoted:
      arg_lex_mode = lex_mode_e.VS_ARG_DQ
    else:
      arg_lex_mode = lex_mode_e.VS_ARG_UNQ

    self._Next(lex_mode_e.VS_1)
    self._Peek()

    ty = self.token_type

    if ty == Id.VSub_Pound:
      # Disambiguate
      t = self.lexer.LookAhead(lex_mode_e.VS_1)
      #print("\t# LOOKAHEAD", t)
      if t.id not in (Id.Unknown_Tok, Id.Right_VarSub):
        # e.g. a name, '#' is the prefix
        self._Next(lex_mode_e.VS_1)
        part = self._ParseVarOf()

        self._Peek()
        if self.token_type != Id.Right_VarSub:
          p_die("Expected } after length expression, got %r",
                self.cur_token.val, token=self.cur_token)

        part.prefix_op = Id.VSub_Pound  # length

      else:  # not a prefix, '#' is the variable
        part = self._ParseVarExpr(arg_lex_mode)
        if not part: return None

    elif ty == Id.VSub_Bang:
      t = self.lexer.LookAhead(lex_mode_e.VS_1)
      #print("\t! LOOKAHEAD", t)
      if t.id not in (Id.Unknown_Tok, Id.Right_VarSub):
        # e.g. a name, '!' is the prefix
        # ${!a} -- this is a ref
        # ${!3} -- this is ref
        # ${!a[1]} -- this is a ref
        # ${!a[@]} -- this is a keys
        # No lookahead -- do it in a second step, or at runtime
        self._Next(lex_mode_e.VS_1)
        part = self._ParseVarExpr(arg_lex_mode)
        if not part: return None

        part.prefix_op = Id.VSub_Bang

      else:  # not a prefix, '!' is the variable
        part = self._ParseVarExpr(arg_lex_mode)
        if not part: return None

    # VS_NAME, VS_NUMBER, symbol that isn't # or !
    elif self.token_kind == Kind.VSub:
      part = self._ParseVarExpr(arg_lex_mode)
      if not part: return None

    else:
      # e.g. ${^}
      p_die('Unexpected token %s', self.cur_token, token=self.cur_token)

    part.spids.append(left_spid)

    # Does this work?
    right_spid = self.cur_token.span_id
    part.spids.append(right_spid)

    return part

  def _ReadSingleQuotedPart(self, lex_mode):
    left = self.cur_token
    tokens = []

    done = False
    while not done:
      self._Next(lex_mode)
      self._Peek()

      # Kind.Char emitted in DOLLAR_SQ state
      if self.token_kind in (Kind.Lit, Kind.Char):
        tokens.append(self.cur_token)

      elif self.token_kind == Kind.Eof:
        p_die('Unexpected EOF in single-quoted string that began here',
              token=left)

      elif self.token_kind == Kind.Right:
        done = True  # assume Id.Right_SingleQuote

      else:
        raise AssertionError(
            'Unhandled token in single-quoted part %s (%d)' %
            (self.cur_token, self.token_kind))

    return ast.SingleQuotedPart(left, tokens)

  def _ReadDoubleQuotedLeftParts(self):
    """Read substitution parts in a double quoted context."""
    if self.token_type in (Id.Left_CommandSub, Id.Left_Backtick):
      return self._ReadCommandSubPart(self.token_type)

    if self.token_type == Id.Left_VarSub:
      return self._ReadBracedBracedVarSub(d_quoted=True)

    if self.token_type == Id.Left_ArithSub:
      return self._ReadArithSubPart()

    if self.token_type == Id.Left_ArithSub2:
      return self._ReadArithSub2Part()

    raise AssertionError(self.cur_token)

  def _ReadLeftParts(self):
    """Read substitutions and quoted strings."""

    if self.token_type == Id.Left_DoubleQuote:
      return self._ReadDoubleQuotedPart()

    if self.token_type == Id.Left_DollarDoubleQuote:
      # NOTE: $"" is treated as "" for now.  Does it make sense to add the
      # token to the part?
      return self._ReadDoubleQuotedPart()

    if self.token_type == Id.Left_SingleQuote:
      return self._ReadSingleQuotedPart(lex_mode_e.SQ)

    if self.token_type == Id.Left_DollarSingleQuote:
      return self._ReadSingleQuotedPart(lex_mode_e.DOLLAR_SQ)

    if self.token_type in (
        Id.Left_CommandSub, Id.Left_Backtick, Id.Left_ProcSubIn,
        Id.Left_ProcSubOut):
      return self._ReadCommandSubPart(self.token_type)

    if self.token_type == Id.Left_VarSub:
      return self._ReadBracedBracedVarSub(d_quoted=False)

    if self.token_type == Id.Left_ArithSub:
      return self._ReadArithSubPart()

    if self.token_type == Id.Left_ArithSub2:
      return self._ReadArithSub2Part()

    raise AssertionError('%s not handled' % self.cur_token)

  def _ReadExtGlobPart(self):
    """
    Grammar:
      Item         = CompoundWord | EPSILON  # important: @(foo|) is allowed
      LEFT         = '@(' | '*(' | '+(' | '?(' | '!('
      RIGHT        = ')'
      ExtGlob      = LEFT (Item '|')* Item RIGHT  # ITEM may be empty
      CompoundWord includes ExtGlobPart
    """
    left_token = self.cur_token
    arms = []
    part = ast.ExtGlobPart(left_token, arms)  # return value
    part.spids.append(left_token.span_id)

    self.lexer.PushHint(Id.Op_RParen, Id.Right_ExtGlob)
    self._Next(lex_mode_e.EXTGLOB)  # advance past LEFT

    read_word = False  # did we just a read a word?  To handle @(||).

    while True:
      self._Peek()
      #log('t %r', self.cur_token)

      if self.token_type == Id.Right_ExtGlob:
        if not read_word:
          arms.append(ast.CompoundWord())
        part.spids.append(self.cur_token.span_id)
        break

      elif self.token_type == Id.Op_Pipe:
        if not read_word:
          arms.append(ast.CompoundWord())
        read_word = False
        self._Next(lex_mode_e.EXTGLOB)

      # lex mode EXTGLOB should only produce these 4 kinds of tokens
      elif self.token_kind in (Kind.Lit, Kind.Left, Kind.VSub, Kind.ExtGlob):
        w = self._ReadCompoundWord(lex_mode=lex_mode_e.EXTGLOB)
        arms.append(w)
        read_word = True

      elif self.token_kind == Kind.Eof:
        p_die('Unexpected EOF reading extended glob that began here',
              token=left_token)

      else:
        raise AssertionError('Unexpected token %r' % self.cur_token)

    return part

  def _ReadDoubleQuotedPart(self, eof_type=Id.Undefined_Tok, here_doc=False):
    """
    Args:
      eof_type: for stopping at }, Id.Lit_RBrace
      here_doc: Whether we are reading in a here doc context

    Also ${foo%%a b c}  # treat this as double quoted.  until you hit
    """
    quoted_part = ast.DoubleQuotedPart()
    left_spid = const.NO_INTEGER
    right_spid = const.NO_INTEGER  # gets set later

    if self.cur_token is not None:  # None in here doc case
      left_token = self.cur_token

    done = False
    while not done:
      self._Next(lex_mode_e.DQ)
      self._Peek()
      #print(self.cur_token)

      if self.token_type == eof_type:  # e.g. stop at }
        done = True
        continue

      elif self.token_kind == Kind.Lit:
        if self.token_type == Id.Lit_EscapedChar:
          part = ast.EscapedLiteralPart(self.cur_token)
        else:
          part = ast.LiteralPart(self.cur_token)
        quoted_part.parts.append(part)

      elif self.token_kind == Kind.Left:
        part = self._ReadDoubleQuotedLeftParts()
        if not part:
          return None
        quoted_part.parts.append(part)

      elif self.token_kind == Kind.VSub:
        part = ast.SimpleVarSub(self.cur_token)
        quoted_part.parts.append(part)

      elif self.token_kind == Kind.Right:
        assert self.token_type == Id.Right_DoubleQuote
        if here_doc:
          # Turn Id.Right_DoubleQuote into a literal part
          quoted_part.parts.append(ast.LiteralPart(self.cur_token))
        else:
          done = True  # assume Id.Right_DoubleQuote
          right_spid = self.cur_token.span_id

      elif self.token_kind == Kind.Eof:
        if here_doc:  # here docs will have an EOF in their token stream
          done = True
        else:
          p_die('Unexpected EOF reading double-quoted string that began here',
                token=left_token)

      else:
        raise AssertionError(self.cur_token)

    quoted_part.spids.extend((left_spid, right_spid))
    return quoted_part

  def _ReadCommandSubPart(self, token_type):
    """
    NOTE: This is not in the grammar, because word parts aren't in the grammar!

    command_sub = '$(' command_list ')'
    """
    left_token = self.cur_token
    left_spid = left_token.span_id

    #print('_ReadCommandSubPart', self.cur_token)
    self._Next(lex_mode_e.OUTER)  # advance past $( or `

    # Set the lexer in a state so ) becomes the EOF token.
    #print('_ReadCommandSubPart lexer.PushHint ) -> EOF')
    if token_type in (
        Id.Left_CommandSub, Id.Left_ProcSubIn, Id.Left_ProcSubOut):
      self.lexer.PushHint(Id.Op_RParen, Id.Eof_RParen)
    elif token_type == Id.Left_Backtick:
      self.lexer.PushHint(Id.Left_Backtick, Id.Eof_Backtick)
    else:
      raise AssertionError(self.token_type)

    from osh import parse_lib
    c_parser = parse_lib.MakeParserForCommandSub(self.line_reader, self.lexer)

    node = c_parser.ParseWholeFile()  # `` and $() allowed
    if not node:
      # Example of parse error:
      # echo $(cat |)  OR
      # echo `cat |`
      error_stack = c_parser.Error()
      self.error_stack.extend(error_stack)
      print(self.error_stack)
      self.AddErrorContext('Error parsing commmand list in command sub')
      return None

    # Hm this creates its own word parser, which is thrown away?
    #print('X', self.cur_token)
    right_spid = c_parser.w_parser.cur_token.span_id

    cs_part = ast.CommandSubPart(node, left_token)
    cs_part.spids.append(left_spid)
    cs_part.spids.append(right_spid)
    return cs_part

  def _ReadArithExpr(self, do_next=True):
    """Read and parse an arithmetic expression in various contexts.

    $(( 1+2 ))
    (( a=1+2 ))
    ${a[ 1+2 ]}
    ${a : 1+2 : 1+2}

    See tests/arith-context.test.sh for ambiguous cases.

    ${a[a[0]]} is valid  # VS_RBRACKET vs Id.Arith_RBracket

    ${s : a<b?0:1 : 1}  # VS_COLON vs Id.Arith_Colon

    TODO: Instead of having an eof_type.  I think we should use just run the
    arith parser until it's done.  That will take care of both : and ].  We
    switch the state back.

    See the assertion in ArithParser.Parse() -- unexpected extra input.
    """
    if do_next:
      self._Next(lex_mode_e.ARITH)
    # calls self.ReadWord(lex_mode_e.ARITH)
    a_parser = tdop.TdopParser(arith_parse.SPEC, self)
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
    left_span_id = self.cur_token.span_id

    # The second one needs to be disambiguated in stuff like stuff like:
    # $(echo $(( 1+2 )) )
    self.lexer.PushHint(Id.Op_RParen, Id.Right_ArithSub)

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

    if self.token_type != Id.Arith_RParen:
      p_die('Expected first ) to end arith sub, got %r', self.cur_token.val,
            token=self.cur_token)

    self._Next(lex_mode_e.OUTER)  # TODO: This could be DQ or ARITH too

    # PROBLEM: $(echo $(( 1 + 2 )) )
    # Two right parens break the Id.Eof_RParen scheme
    self._Peek()
    if self.token_type != Id.Right_ArithSub:
      p_die('Expected second ) to end arith sub, got %r', self.cur_token.val,
            token=self.cur_token)

    right_span_id = self.cur_token.span_id

    node = ast.ArithSubPart(anode)
    node.spids.append(left_span_id)
    node.spids.append(right_span_id)
    return node

  def _ReadArithSub2Part(self):
    """Non-standard arith sub $[a + 1]."""
    left_span_id = self.cur_token.span_id

    anode = self._ReadArithExpr()
    if not anode:
      self.AddErrorContext("Error parsing arith sub part")
      return None

    if self.token_type != Id.Arith_RBracket:
      p_die('Expected ], got %r', self.cur_token.val, token=self.cur_token)

    right_span_id = self.cur_token.span_id

    node = ast.ArithSubPart(anode)
    node.spids.append(left_span_id)
    node.spids.append(right_span_id)
    return node

  def ReadDParen(self):
    """Read ((1+ 2))  -- command context.

    We're using the word parser because it's very similar to _ReadArithExpr
    above.
    """
    # The second one needs to be disambiguated in stuff like stuff like:
    # TODO: Be consistent with ReadForExpression below and use lex_mode_e.ARITH?
    # Then you can get rid of this.
    self.lexer.PushHint(Id.Op_RParen, Id.Op_DRightParen)

    anode = self._ReadArithExpr()
    if not anode:
      self.AddErrorContext("Error parsing dparen statement")
      return None

    #print('xx ((', self.cur_token)
    if self.token_type != Id.Arith_RParen:
      p_die('Expected first ) to end arith statement, got %r',
            self.cur_token.val, token=self.cur_token)
    self._Next(lex_mode_e.OUTER)

    # PROBLEM: $(echo $(( 1 + 2 )) )
    self._Peek()
    if self.token_type != Id.Op_DRightParen:
      p_die('Expected second ) to end arith statement, got %r',
            self.cur_token.val, token=self.cur_token)
    self._Next(lex_mode_e.OUTER)

    return anode

  def ReadForExpression(self):
    """Read ((i=0; i<5; ++i)) -- part of command context.

    """
    # No PushHint because we're in arith state.
    #self.lexer.PushHint(Id.Op_RParen, Id.Op_DRightParen)

    self._Next(lex_mode_e.ARITH)  # skip over ((

    self._Peek()
    if self.token_type == Id.Arith_Semi:
      #print('Got empty init')
      init_node = None
    else:
      init_node = self._ReadArithExpr(do_next=False)
      if not init_node:
        self.AddErrorContext("Error parsing for init")
        return None
    self._Next(lex_mode_e.ARITH)
    #print('INIT',init_node)

    self._Peek()
    if self.token_type == Id.Arith_Semi:
      #print('Got empty condition')
      cond_node = None
    else:
      cond_node = self._ReadArithExpr(do_next=False)
      if not cond_node:
        self.AddErrorContext("Error parsing for cond")
        return None
    self._Next(lex_mode_e.ARITH)
    #print('COND',cond_node)

    self._Peek()
    if self.token_type == Id.Arith_RParen:
      #print('Got empty update')
      update_node = None
    else:
      update_node = self._ReadArithExpr(do_next=False)
      if not update_node:
        self.AddErrorContext("Error parsing for update")
        return None
    self._Next(lex_mode_e.ARITH)
    #print('UPDATE',update_node)

    #print('TT', self.cur_token)
    # Second paren
    self._Peek()
    if self.token_type != Id.Arith_RParen:
      p_die('Expected ) to end for loop expression, got %r',
            self.cur_token.val, token=self.cur_token)
    self._Next(lex_mode_e.OUTER)

    return ast.ForExpr(init_node, cond_node, update_node)

  def _ReadArrayLiteralPart(self):
    self._Next(lex_mode_e.OUTER)  # advance past (
    self._Peek()
    if self.cur_token.id != Id.Op_LParen:
      p_die('Expected ( after =, got %r', self.cur_token.val,
            token=self.cur_token)

    # MUST use a new word parser (with same lexer).
    w_parser = WordParser(self.lexer, self.line_reader)
    words = []
    while True:
      w = w_parser.ReadWord(lex_mode_e.OUTER)
      if not w:
        self.error_stack.extend(w_parser.Error())
        return None

      if w.tag == word_e.TokenWord:
        word_id = word.CommandId(w)
        if word_id == Id.Right_ArrayLiteral:
          break
        # Unlike command parsing, array parsing allows embedded \n.
        elif word_id == Id.Op_Newline:
          continue
        else:
          # TokenWord
          p_die('Unexpected token in array literal: %r', w.token.val, word=w)

      words.append(w)

    words2 = braces.BraceDetectAll(words)
    words3 = word.TildeDetectAll(words2)

    return ast.ArrayLiteralPart(words3)

  def _ReadCompoundWord(self, eof_type=Id.Undefined_Tok,
                        lex_mode=lex_mode_e.OUTER, empty_ok=True):
    """
    Precondition: Looking at the first token of the first word part
    Postcondition: Looking at the token after, e.g. space or operator

    NOTE: eof_type is necessary because / is a literal, i.e. Lit_Slash, but it
    could be an operator delimiting a compound word.  Can we change lexer modes
    and remove this special case?
    """
    #print('_ReadCompoundWord', lex_mode)
    word = ast.CompoundWord()

    num_parts = 0
    done = False
    while not done:
      allow_done = empty_ok or num_parts != 0
      self._Peek()
      #print('CW',self.cur_token)
      if allow_done and self.token_type == eof_type:
        done = True  # e.g. for ${foo//pat/replace}

      # Keywords like "for" are treated like literals
      elif self.token_kind in (
          Kind.Lit, Kind.KW, Kind.Assign, Kind.ControlFlow, Kind.BoolUnary,
          Kind.BoolBinary):
        if self.token_type == Id.Lit_EscapedChar:
          part = ast.EscapedLiteralPart(self.cur_token)
        else:
          part = ast.LiteralPart(self.cur_token)
          #part.xspans.append(self.cur_token.span_id)

        word.parts.append(part)

        if self.token_type == Id.Lit_VarLike:
          #print('@', self.cursor)
          #print('@', self.cur_token)

          t = self.lexer.LookAhead(lex_mode_e.OUTER)
          if t.id == Id.Op_LParen:
            self.lexer.PushHint(Id.Op_RParen, Id.Right_ArrayLiteral)
            part2 = self._ReadArrayLiteralPart()
            if not part2:
              self.AddErrorContext('_ReadArrayLiteralPart failed')
              return False
            word.parts.append(part2)

      elif self.token_kind == Kind.VSub:
        part = ast.SimpleVarSub(self.cur_token)
        word.parts.append(part)

      elif self.token_kind == Kind.ExtGlob:
        part = self._ReadExtGlobPart()
        if not part:
          return None
        word.parts.append(part)

      elif self.token_kind == Kind.Left:
        #print('_ReadLeftParts')
        part = self._ReadLeftParts()
        if not part:
          return None
        word.parts.append(part)

      # NOT done yet, will advance below
      elif self.token_kind == Kind.Right:
        # Still part of the word; will be done on the next iter.
        if self.token_type == Id.Right_DoubleQuote:
          pass
        elif self.token_type == Id.Right_CommandSub:
          pass
        elif self.token_type == Id.Right_Subshell:
          # LEXER HACK for (case x in x) ;; esac )
          assert self.next_lex_mode is None  # Rewind before it's used
          if self.lexer.MaybeUnreadOne():
            self.lexer.PushHint(Id.Op_RParen, Id.Right_Subshell)
            self._Next(lex_mode)
          done = True
        else:
          done = True

      elif self.token_kind == Kind.Ignored:
        done = True

      else:
        # LEXER HACK for unbalanced case clause.  'case foo in esac' is valid,
        # so to test for ESAC, we can read ) before getting a chance to
        # PushHint(Id.Op_RParen, Id.Right_CasePat).  So here we unread one
        # token and do it again.

        # We get Id.Op_RParen at top level:      case x in x) ;; esac
        # We get Id.Eof_RParen inside ComSub:  $(case x in x) ;; esac )
        if self.token_type in (Id.Op_RParen, Id.Eof_RParen):
          assert self.next_lex_mode is None  # Rewind before it's used
          if self.lexer.MaybeUnreadOne():
            if self.token_type == Id.Eof_RParen:
              # Redo translation
              self.lexer.PushHint(Id.Op_RParen, Id.Eof_RParen)
            self._Next(lex_mode)

        done = True  # anything we don't recognize means we're done

      if not done:
        self._Next(lex_mode)
      num_parts += 1
    return word

  def _ReadArithWord(self):
    """Helper function for ReadArithWord."""
    #assert self.token_type != Id.Undefined_Tok
    self._Peek()
    #print('_ReadArithWord', self.cur_token)

    if self.token_kind == Kind.Unknown:
      self.AddErrorContext("Unknown token in arith context: %s",
          self.cur_token, token=self.cur_token)
      return None, False

    elif self.token_kind == Kind.Eof:
      # Just return EOF token
      w = ast.TokenWord(self.cur_token)
      return w, False

    elif self.token_kind == Kind.Ignored:
      # Space should be ignored.  TODO: change this to SPACE_SPACE and
      # SPACE_NEWLINE?  or SPACE_TOK.
      self._Next(lex_mode_e.ARITH)
      return None, True  # Tell wrapper to try again

    elif self.token_kind in (Kind.Arith, Kind.Right):
      # Id.Right_ArithSub IS just a normal token, handled by ArithParser
      self._Next(lex_mode_e.ARITH)
      w = ast.TokenWord(self.cur_token)
      return w, False

    elif self.token_kind in (Kind.Lit, Kind.Left):
      w = self._ReadCompoundWord(lex_mode=lex_mode_e.ARITH)
      if not w:
        return None, True
      return w, False

    elif self.token_kind == Kind.VSub:
      part = ast.SimpleVarSub(self.cur_token)
      self._Next(lex_mode_e.ARITH)
      w = ast.CompoundWord([part])
      return w, False

    else:
      self._BadToken("Unexpected token parsing arith sub: %s", self.cur_token)
      return None, False

    raise AssertionError("Shouldn't get here")

  def _ReadWord(self, lex_mode):
    """Helper function for Read().

    Returns:
      2-tuple (word, need_more)
        word: Word, or None if there was an error, or need_more is set
        need_more: True if the caller should call us again
    """
    #print('_Read', lex_mode, self.cur_token)
    self._Peek()

    if self.token_kind == Kind.Eof:
      # No advance
      return ast.TokenWord(self.cur_token), False

    # Allow Arith for ) at end of for loop?
    elif self.token_kind in (Kind.Op, Kind.Redir, Kind.Arith):
      self._Next(lex_mode)
      if self.token_type == Id.Op_Newline:
        if self.cursor_was_newline:
          #print('SKIP(nl)', self.cur_token)
          return None, True

      return ast.TokenWord(self.cur_token), False

    elif self.token_kind == Kind.Right:
      #print('WordParser.Read: Kind.Right', self.cur_token)
      if self.token_type not in (
          Id.Right_Subshell, Id.Right_FuncDef, Id.Right_CasePat,
          Id.Right_ArrayLiteral):
        raise AssertionError(self.cur_token)

      self._Next(lex_mode)
      return ast.TokenWord(self.cur_token), False

    elif self.token_kind in (Kind.Ignored, Kind.WS):
      self._Next(lex_mode)
      return None, True  # tell Read() to try again

    elif self.token_kind in (
        Kind.VSub, Kind.Lit, Kind.Left, Kind.KW, Kind.Assign, Kind.ControlFlow,
        Kind.BoolUnary, Kind.BoolBinary, Kind.ExtGlob):
      # We're beginning a word.  If we see Id.Lit_Pound, change to
      # lex_mode_e.COMMENT and read until end of line.  (TODO: How to add
      # comments to AST?)

      # TODO: Can we do the same thing for Tilde here?  Enter a state where we
      # look for / too.
      if self.token_type == Id.Lit_Pound:
        self._Next(lex_mode_e.COMMENT)
        self._Peek()

        # NOTE: The # could be the last character in the file.  It can't be
        # Eof_{RParen,Backtick} because #) and #` are comments.
        assert self.token_type in (Id.Ignored_Comment, Id.Eof_Real), \
            self.cur_token

        # The next iteration will go into Kind.Ignored and set lex state to
        # lex_mode_e.OUTER/etc.
        return None, True  # tell Read() to try again after comment

      else:
        w = self._ReadCompoundWord(lex_mode=lex_mode)
        if not w:
          self.AddErrorContext(
              'Error reading command word', token=self.cur_token)
          return None, False
        return w, False

    else:
      raise AssertionError(
          'Unhandled: %s (%s)' % (self.cur_token, self.token_kind))

    raise AssertionError("Shouldn't get here")

  def LookAhead(self):
    """Look ahead to the next token.

    For the command parser to recognize func () { } and array= (1 2 3).  And
    probably coprocesses.
    """
    assert self.token_type != Id.Undefined_Tok
    if self.cur_token.id == Id.WS_Space:
      t = self.lexer.LookAhead(lex_mode_e.OUTER)
    else:
      t = self.cur_token
    return t.id

  def ReadWord(self, lex_mode):
    """Read the next Word.

    Returns:
      Word, or None if there was an error
    """
    # Implementation note: This is an stateful/iterative function that calls
    # the stateless "_ReadWord" function.
    while True:
      if lex_mode == lex_mode_e.ARITH:
        # TODO: Can this be unified?
        w, need_more = self._ReadArithWord()
      elif lex_mode in (
          lex_mode_e.OUTER, lex_mode_e.DBRACKET, lex_mode_e.BASH_REGEX):
        w, need_more = self._ReadWord(lex_mode)
      else:
        raise AssertionError('Invalid lex state %s' % lex_mode)
      if not need_more:
        break

    if not w:  # Assumes AddErrorContext was already called
      return None

    self.cursor = w

    # TODO: Do consolidation of newlines in the lexer?
    # Note that there can be an infinite (Id.Ignored_Comment Id.Op_Newline
    # Id.Ignored_Comment Id.Op_Newline) sequence, so we have to keep track of
    # the last non-ignored token.
    self.cursor_was_newline = (word.CommandId(self.cursor) == Id.Op_Newline)
    return self.cursor

  def ReadHereDocBody(self):
    """
    Sort of like Read(), except we're in a double quoted context, but not using
    double quotes.

    Returns:
      CompoundWord.  NOTE: We could also just use a DoubleQuotedPart for both
      cases?
    """
    w = ast.CompoundWord()
    dq = self._ReadDoubleQuotedPart(here_doc=True)
    if not dq:
      self.AddErrorContext('Error parsing here doc body')
      return False
    w.parts.append(dq)
    return w
