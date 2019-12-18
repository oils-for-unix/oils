# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
word_parse.py - Parse the shell word language.

Hairy example:

hi$((1 + 2))"$(echo hi)"${var:-__"$(echo default)"__}

Substitutions can be nested, but which inner subs are allowed depends on the
outer sub.

lex_mode_e.ShCommand (_ReadLeftParts)
  All subs and quotes are allowed:
  $v ${v}   $() ``   $(())   '' ""   $'' $""  <()  >()

lex_mode_e.DQ  (_ReadDoubleQuotedLeftParts)
  Var, Command, Arith, but no quotes.
  $v ${v}   $() ``   $(())
  No process substitution.

lex_mode_e.Arith
  Similar to DQ: Var, Command, and Arith sub, but no process sub.  bash doesn't
  allow quotes, but OSH does.  We allow ALL FOUR kinds of quotes, because we
  need those for associative array indexing.

lex_mode_e.VSub_ArgUnquoted
  Like UNQUOTED, everything is allowed (even process substitutions), but we
  stop at }, and space is SIGNIFICANT.
  
  Example: ${a:-  b   }

  ${X:-$v}   ${X:-${v}}  ${X:-$(echo hi)}  ${X:-`echo hi`}  ${X:-$((1+2))}
  ${X:-'single'}  ${X:-"double"}  ${X:-$'\n'}  ${X:-<(echo hi)}

lex_mode_e.VSub_ArgDQ
  In contrast to DQ, VS_ARG_DQ accepts nested "" and $'' and $"", e.g.
  "${x:-"default"}".

  In contrast, VS_ARG_UNQ respects single quotes and process substitution.

  It's weird that double quotes are allowed.  Space is also significant here,
  e.g. "${x:-a  "b"}".
"""

from _devbuild.gen import grammar_nt
from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str, Kind
from _devbuild.gen.types_asdl import lex_mode_t, lex_mode_e
from _devbuild.gen.syntax_asdl import (
    Token, speck,
    double_quoted, single_quoted, simple_var_sub, braced_var_sub, command_sub,
    sh_array_literal,

    arith_expr_t, bracket_op, bracket_op_t,

    suffix_op, suffix_op_t, suffix_op__Slice, suffix_op__PatSub,

    word, word_e, word_t, compound_word,
    word_part, word_part_e, word_part_t,
    word_part__ArithSub, word_part__ExtGlob, word_part__ExprSub,

    command, command_t, command__ForExpr, command__Proc, command__Func,

    expr_t, source, arg_list,
)
from core.util import p_die
from core.util import log
from core import ui
from frontend import lookup
from frontend import reader
from osh import tdop
from osh import arith_parse
from osh import braces
from osh import word_
from mycpp.mylib import NewStr

from typing import List, Optional, Tuple, cast
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from frontend.lexer import Lexer
  from frontend.parse_lib import ParseContext
  from frontend.reader import _Reader

_ = log

KINDS_THAT_END_WORDS = [Kind.Eof, Kind.WS, Kind.Op, Kind.Right]


class WordEmitter(object):
  """Common interface for [ and [[ """

  def ReadWord(self, lex_mode):
    # type: (lex_mode_t) -> word_t
    raise NotImplementedError()


class WordParser(WordEmitter):

  def __init__(self, parse_ctx, lexer, line_reader):
    # type: (ParseContext, Lexer, _Reader) -> None
    self.parse_ctx = parse_ctx
    self.arena = parse_ctx.arena
    self.lexer = lexer
    self.line_reader = line_reader

    self.parse_opts = parse_ctx.parse_opts
    self.Reset()

  def Init(self, lex_mode):
    # type: (lex_mode_t) -> None
    """Used to parse arithmetic, see ParseContext."""
    self.next_lex_mode = lex_mode

  def Reset(self):
    # type: () -> None
    """Called by interactive loop."""
    # For _Peek()
    self.cur_token = None  # type: Token
    self.token_kind = Kind.Undefined
    self.token_type = Id.Undefined_Tok

    self.next_lex_mode = lex_mode_e.ShCommand

    # For newline.  TODO: I think we can do this iteratively, without member
    # state.
    self.cursor = None  # type: word_t
    self.cursor_was_newline = False

    self.buffered_word = None  # type: word_t

  def _Peek(self):
    # type: () -> None
    """Helper method."""
    if self.next_lex_mode != lex_mode_e.Undefined:
      self.cur_token = self.lexer.Read(self.next_lex_mode)
      self.token_type = self.cur_token.id
      self.token_kind = lookup.LookupKind(self.token_type)
      self.parse_ctx.trail.AppendToken(self.cur_token)   # For completion
      self.next_lex_mode = lex_mode_e.Undefined

  def _Next(self, lex_mode):
    # type: (lex_mode_t) -> None
    """Set the next lex state, but don't actually read a token.

    We need this for proper interactive parsing.
    """
    self.next_lex_mode = lex_mode

  def _ReadVarOpArg(self, arg_lex_mode):
    # type: (lex_mode_t) -> word_t
    return self._ReadVarOpArg3(arg_lex_mode, Id.Undefined_Tok, True)

  def _ReadVarOpArg3(self, arg_lex_mode, eof_type, empty_ok):
    # type: (lex_mode_t, Id_t, bool) -> word_t
    """
    Args:
      empty_ok: Whether Empty can be returned
    """
    # NOTE: Operators like | and < are not treated as special, so ${a:- | >} is
    # valid, even when unquoted.
    self._Next(arg_lex_mode)
    self._Peek()

    w = self._ReadCompoundWord3(arg_lex_mode, eof_type, empty_ok)

    # If the Compound has no parts, and we're in a double-quoted VarSub
    # arg, and empty_ok, then return Empty.  This is so it can evaluate to
    # the empty string and not get elided.
    #
    # Examples:
    # - "${s:-}", "${s/%pat/}"
    # It's similar to LooksLikeShAssignment where we turn x= into x=''.  And it
    # has the same potential problem of not having spids.
    #
    # NOTE: empty_ok is False only for the PatSub pattern, which means we'll
    # return a Compound with no parts, which is explicitly checked with a
    # custom error message.
    if (len(w.parts) == 0 and arg_lex_mode == lex_mode_e.VSub_ArgDQ
        and empty_ok):
      return word.Empty()

    return w

  def _ReadSliceVarOp(self):
    # type: () -> suffix_op__Slice
    """ VarOf ':' ArithExpr (':' ArithExpr )? """
    self._Next(lex_mode_e.Arith)
    self._Peek()
    if self.token_type == Id.Arith_Colon:  # A pun for Id.VOp2_Colon
      # no beginning specified
      begin = None  # type: Optional[arith_expr_t]
    else:
      begin = self._ReadArithExpr()

    if self.token_type == Id.Arith_RBrace:
      no_length = None  # type: Optional[arith_expr_t]  # No length specified
      return suffix_op.Slice(begin, no_length)

    # Id.Arith_Colon is a pun for Id.VOp2_Colon
    if self.token_type == Id.Arith_Colon:
      self._Next(lex_mode_e.Arith)
      length = self._ReadArithExpr()
      return suffix_op.Slice(begin, length)

    p_die("Expected : or } in slice", token=self.cur_token)

  def _ReadPatSubVarOp(self, lex_mode):
    # type: (lex_mode_t) -> suffix_op__PatSub
    """
    Match     = ('/' | '#' | '%') WORD
    VarSub    = ...
              | VarOf '/' Match '/' WORD
    """
    # stop at eof_type=Lit_Slash, empty_ok=False
    UP_pat = self._ReadVarOpArg3(lex_mode, Id.Lit_Slash, False)
    assert UP_pat.tag_() == word_e.Compound, UP_pat  # Because empty_ok=False
    pat = cast(compound_word, UP_pat)

    if len(pat.parts) == 1:
      ok, s, quoted = word_.StaticEval(pat)
      if ok and s == '/' and not quoted:  # Looks like ${a////c}, read again
        self._Next(lex_mode)
        self._Peek()
        pat.parts.append(self.cur_token)

    if len(pat.parts) == 0:
      p_die('Pattern in ${x/pat/replace} must not be empty',
            token=self.cur_token)

    replace_mode = Id.Undefined_Tok
    # Check for / # % modifier on pattern.
    UP_first_part = pat.parts[0]
    if UP_first_part.tag_() == word_part_e.Literal:
      lit_id = cast(Token, UP_first_part).id
      if lit_id in (Id.Lit_Slash, Id.Lit_Pound, Id.Lit_Percent):
        pat.parts.pop(0)
        replace_mode = lit_id

    # NOTE: If there is a modifier, the pattern can be empty, e.g.
    # ${s/#/foo} and ${a/%/foo}.

    if self.token_type == Id.Right_DollarBrace:
      # e.g. ${v/a} is the same as ${v/a/}  -- empty replacement string
      return suffix_op.PatSub(pat, None, replace_mode)

    if self.token_type == Id.Lit_Slash:
      replace = self._ReadVarOpArg(lex_mode)  # do not stop at /

      self._Peek()
      if self.token_type != Id.Right_DollarBrace:
        # NOTE: I think this never happens.
        # We're either in the VS_ARG_UNQ or VS_ARG_DQ lex state, and everything
        # there is Lit_ or Left_, except for }.
        p_die("Expected } after replacement string, got %s",
              NewStr(Id_str(self.token_type)), token=self.cur_token)

      return suffix_op.PatSub(pat, replace, replace_mode)

    # Happens with ${x//} and ${x///foo}, see test/parse-errors.sh
    p_die('Expected } or / to close pattern', token=self.cur_token)

  def _ReadSubscript(self):
    # type: () -> bracket_op_t
    """ Subscript = '[' ('@' | '*' | ArithExpr) ']'
    """
    # Lookahead to see if we get @ or *.  Otherwise read a full arithmetic
    # expression.
    next_id = self.lexer.LookAhead(lex_mode_e.Arith)
    if next_id in (Id.Lit_At, Id.Arith_Star):
      op = bracket_op.WholeArray(next_id)  # type: bracket_op_t

      self._Next(lex_mode_e.Arith)  # skip past [
      self._Peek()
      self._Next(lex_mode_e.Arith)  # skip past @
      self._Peek()
    else:
      self._Next(lex_mode_e.Arith)  # skip past [
      anode = self._ReadArithExpr()
      op = bracket_op.ArrayIndex(anode)

    if self.token_type != Id.Arith_RBracket:  # Should be looking at ]
      p_die('Expected ] to close subscript', token=self.cur_token)

    self._Next(lex_mode_e.VSub_2)  # skip past ]
    self._Peek()  # Needed to be in the same spot as no subscript

    return op

  def _ParseVarOf(self):
    # type: () -> braced_var_sub
    """
    VarOf     = NAME Subscript?
              | NUMBER      # no subscript allowed, none of these are arrays
                            # ${@[1]} doesn't work, even though slicing does
              | VarSymbol
    """
    self._Peek()
    name_token = self.cur_token
    self._Next(lex_mode_e.VSub_2)

    self._Peek()  # Check for []
    if self.token_type == Id.VOp2_LBracket:
      bracket_op = self._ReadSubscript()
    else:
      bracket_op = None

    part = braced_var_sub()
    part.token = name_token
    part.bracket_op = bracket_op
    return part

  def _ParseVarExpr(self, arg_lex_mode, allow_query=False):
    # type: (lex_mode_t, bool) -> braced_var_sub
    """
    Start parsing at the op -- we already skipped past the name.
    """
    part = self._ParseVarOf()

    self._Peek()
    if self.token_type == Id.Right_DollarBrace:
      return part  # no ops

    op_kind = self.token_kind

    if op_kind == Kind.VTest:
      op_id = self.token_type
      arg_word = self._ReadVarOpArg(arg_lex_mode)
      if self.token_type != Id.Right_DollarBrace:
        p_die('Expected } to close ${', token=self.cur_token)

      part.suffix_op = suffix_op.Unary(op_id, arg_word)

    elif op_kind == Kind.VOp0:
      op_id = self.token_type
      part.suffix_op = suffix_op.Nullary(op_id)
      self._Next(lex_mode_e.VSub_2)  # Expecting }
      self._Peek()

    elif op_kind == Kind.VOp1:
      op_id = self.token_type
      arg_word = self._ReadVarOpArg(arg_lex_mode)
      if self.token_type != Id.Right_DollarBrace:
        p_die('Expected } to close ${', token=self.cur_token)

      part.suffix_op = suffix_op.Unary(op_id, arg_word)

    elif op_kind == Kind.VOp2:
      if self.token_type == Id.VOp2_Slash:
        op_spid = self.cur_token.span_id  # for attributing error to /
        patsub_op = self._ReadPatSubVarOp(arg_lex_mode)
        patsub_op.spids.append(op_spid)

        # awkwardness for mycpp; could fix
        temp = cast(suffix_op_t, patsub_op)
        part.suffix_op = temp

        # Checked by the method above
        assert self.token_type == Id.Right_DollarBrace, self.cur_token

      elif self.token_type == Id.VOp2_Colon:
        part.suffix_op = self._ReadSliceVarOp()
        # NOTE: } in arithmetic mode.
        if self.token_type != Id.Arith_RBrace:
          # Token seems off; doesn't point to X in # ${a:1:2 X
          p_die('Expected } to close ${', token=self.cur_token)

      else:
        # TODO: Does this ever happen?
        p_die('Unexpected token in ${} (%s)', 'VOp2', token=self.cur_token)

    elif op_kind == Kind.VOp3:
      if allow_query:
        op_id = self.token_type
        part.suffix_op = suffix_op.Nullary(op_id)
        self._Next(lex_mode_e.VSub_2)  # Expecting }
        self._Peek()
      else:
        p_die("Unexpected token in ${} (%s)", 'VOp3', token=self.cur_token)

    # NOTE: Arith_RBrace is for slicing, because it reads } in arithmetic
    # mode.  It's redundantly checked above.
    if self.token_type not in (Id.Right_DollarBrace, Id.Arith_RBrace):
      # ${a.} or ${!a.}
      p_die('Expected } to close ${', token=self.cur_token)

    # Now look for ops
    return part

  def ReadBracedVarSub(self, left_token):
    # type: (Token) -> Tuple[braced_var_sub, Token]
    """   For Oil expressions like var x = ${x:-"default"}.  """
    part = self._ReadBracedVarSub(left_token, False)  # not quoted
    last_token = self.cur_token
    return part, last_token

  def _ReadBracedVarSub(self, left_token, d_quoted):
    # type: (Token, bool) -> braced_var_sub
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
      arg_lex_mode = lex_mode_e.VSub_ArgDQ
    else:
      arg_lex_mode = lex_mode_e.VSub_ArgUnquoted

    self._Next(lex_mode_e.VSub_1)
    self._Peek()

    ty = self.token_type

    if ty == Id.VSub_Pound:
      # Disambiguate
      next_id = self.lexer.LookAhead(lex_mode_e.VSub_1)
      if next_id not in (Id.Unknown_Tok, Id.Right_DollarBrace):
        # e.g. a name, '#' is the prefix
        self._Next(lex_mode_e.VSub_1)
        part = self._ParseVarOf()

        self._Peek()
        if self.token_type != Id.Right_DollarBrace:
          p_die('Expected } after length expression', token=self.cur_token)

        part.prefix_op = speck(ty, self.cur_token.span_id)

      else:  # not a prefix, '#' is the variable
        part = self._ParseVarExpr(arg_lex_mode)

    elif ty == Id.VSub_Bang:
      next_id = self.lexer.LookAhead(lex_mode_e.VSub_1)
      if next_id not in (Id.Unknown_Tok, Id.Right_DollarBrace):
        # e.g. a name, '!' is the prefix
        # ${!a} -- this is a ref
        # ${!3} -- this is ref
        # ${!a[1]} -- this is a ref
        # ${!a[@]} -- this is a keys
        # No lookahead -- do it in a second step, or at runtime
        self._Next(lex_mode_e.VSub_1)
        part = self._ParseVarExpr(arg_lex_mode, allow_query=True)

        part.prefix_op = speck(ty, self.cur_token.span_id)

      else:  # not a prefix, '!' is the variable
        part = self._ParseVarExpr(arg_lex_mode)

    # VS_NAME, VS_NUMBER, symbol that isn't # or !
    elif self.token_kind == Kind.VSub:
      part = self._ParseVarExpr(arg_lex_mode)

    else:
      # e.g. ${^}
      p_die('Unexpected token in ${}', token=self.cur_token)

    part.spids.append(left_token.span_id)

    # Does this work?
    right_spid = self.cur_token.span_id
    part.spids.append(right_spid)

    return part

  def _ReadSingleQuoted(self, lex_mode):
    # type: (lex_mode_t) -> single_quoted
    """Interal method to read a word_part."""
    left_token = self.cur_token
    tokens = []  # type: List[Token]
    # In command mode, we never disallow backslashes like '\'
    self.ReadSingleQuoted(lex_mode, left_token, tokens, False)

    node = single_quoted(left_token, tokens)
    node.spids.append(left_token.span_id)  # left '
    node.spids.append(self.cur_token.span_id)  # right '
    return node

  def ReadSingleQuoted(self, lex_mode, left_token, tokens, no_backslashes):
    # type: (lex_mode_t, Token, List[Token], bool) -> Token
    """Used by expr_parse.py."""
    done = False
    while not done:
      self._Next(lex_mode)
      self._Peek()

      # Kind.Char emitted in DOLLAR_SQ state
      if self.token_kind in (Kind.Lit, Kind.Char):
        tok = self.cur_token
        if no_backslashes and '\\' in tok.val:
          p_die(r"Strings with backslashes should look like r'\n' or c'\n'",
                token=tok)
        tokens.append(tok)

      elif self.token_kind == Kind.Eof:
        p_die('Unexpected EOF in single-quoted string that began here',
              token=left_token)

      elif self.token_kind == Kind.Right:
        done = True  # assume Id.Right_SingleQuote

      else:
        raise AssertionError(self.cur_token)
    return self.cur_token

  def _ReadDoubleQuotedLeftParts(self):
    # type: () -> word_part_t
    """Read substitution parts in a double quoted context."""
    if self.token_type in (Id.Left_DollarParen, Id.Left_Backtick):
      return self._ReadCommandSub(self.token_type)

    if self.token_type == Id.Left_DollarBrace:
      return self._ReadBracedVarSub(self.cur_token, True)  # DQ

    if self.token_type == Id.Left_DollarDParen:
      return self._ReadArithSub()

    if self.token_type == Id.Left_DollarBracket:
      return self._ReadExprSub(lex_mode_e.DQ)

    raise AssertionError(self.cur_token)

  def _ReadLeftParts(self):
    # type: () -> word_part_t
    """Read substitutions and quoted strings (for lex_mode_e.ShCommand)."""

    if self.token_type == Id.Left_DoubleQuote:
      return self._ReadDoubleQuoted()

    if self.token_type == Id.Left_DollarDoubleQuote:
      # NOTE: $"" is treated as "" for now.  Does it make sense to add the
      # token to the part?
      return self._ReadDoubleQuoted()

    if self.token_type == Id.Left_SingleQuoteRaw:
      return self._ReadSingleQuoted(lex_mode_e.SQ_Raw)

    if self.token_type == Id.Left_SingleQuoteC:
      return self._ReadSingleQuoted(lex_mode_e.SQ_C)

    if self.token_type in (
        Id.Left_DollarParen, Id.Left_Backtick, Id.Left_ProcSubIn,
        Id.Left_ProcSubOut):
      return self._ReadCommandSub(self.token_type)

    if self.token_type == Id.Left_DollarBrace:
      return self._ReadBracedVarSub(self.cur_token, False)  # not DQ

    if self.token_type == Id.Left_DollarDParen:
      return self._ReadArithSub()

    if self.token_type == Id.Left_DollarBracket:
      return self._ReadExprSub(lex_mode_e.ShCommand)

    raise AssertionError(self.cur_token)

  def _ReadExtGlob(self):
    # type: () -> word_part__ExtGlob
    """
    Grammar:
      Item         = compound_word | EPSILON  # important: @(foo|) is allowed
      LEFT         = '@(' | '*(' | '+(' | '?(' | '!('
      RIGHT        = ')'
      ExtGlob      = LEFT (Item '|')* Item RIGHT  # ITEM may be empty
      Compound includes ExtGlob
    """
    left_token = self.cur_token
    arms = []  # type: List[word_t]
    spids = []  # type: List[int]
    spids.append(left_token.span_id)

    self.lexer.PushHint(Id.Op_RParen, Id.Right_ExtGlob)
    self._Next(lex_mode_e.ExtGlob)  # advance past LEFT

    read_word = False  # did we just a read a word?  To handle @(||).

    while True:
      self._Peek()

      if self.token_type == Id.Right_ExtGlob:
        if not read_word:
          arms.append(compound_word())
        spids.append(self.cur_token.span_id)
        break

      elif self.token_type == Id.Op_Pipe:
        if not read_word:
          arms.append(compound_word())
        read_word = False
        self._Next(lex_mode_e.ExtGlob)

      # lex mode EXTGLOB should only produce these 4 kinds of tokens
      elif self.token_kind in (Kind.Lit, Kind.Left, Kind.VSub, Kind.ExtGlob):
        w = self._ReadCompoundWord(lex_mode_e.ExtGlob)
        arms.append(w)
        read_word = True

      elif self.token_kind == Kind.Eof:
        p_die('Unexpected EOF reading extended glob that began here',
              token=left_token)

      else:
        raise AssertionError(self.cur_token)

    part = word_part.ExtGlob(left_token, arms)
    part.spids.extend(spids)
    return part

  def _ReadLikeDQ(self, left_dq_token, out_parts):
    # type: (Optional[Token], List[word_part_t]) -> None
    """
    Args:
      left_dq_token: A token if we are reading a double quoted part, or None if
        we're reading a here doc.
      out_parts: list of word_part to append to
    """
    done = False
    while not done:
      self._Next(lex_mode_e.DQ)
      self._Peek()

      if self.token_kind == Kind.Lit:
        if self.token_type == Id.Lit_EscapedChar:
          part = word_part.EscapedLiteral(self.cur_token)  # type: word_part_t
        else:
          part = self.cur_token
        out_parts.append(part)

      elif self.token_kind == Kind.Left:
        part = self._ReadDoubleQuotedLeftParts()
        out_parts.append(part)

      elif self.token_kind == Kind.VSub:
        part = simple_var_sub(self.cur_token)
        out_parts.append(part)
        # NOTE: parsing "$f(x)" would BREAK CODE.  Could add a more for it
        # later.

      elif self.token_kind == Kind.Right:
        assert self.token_type == Id.Right_DoubleQuote, self.token_type
        if left_dq_token:
          done = True
        else:
          # In a here doc, the right quote is literal!
          out_parts.append(self.cur_token)

      elif self.token_kind == Kind.Eof:
        if left_dq_token:
          p_die('Unexpected EOF reading double-quoted string that began here',
                token=left_dq_token)
        else:  # here docs will have an EOF in their token stream
          done = True

      else:
        raise AssertionError(self.cur_token)
    # Return nothing, since we appended to 'out_parts'

  def _ReadDoubleQuoted(self):
    # type: () -> double_quoted
    """
    Args:
      eof_type: for stopping at }, Id.Lit_RBrace
      here_doc: Whether we are reading in a here doc context

    Also ${foo%%a b c}  # treat this as double quoted.  until you hit
    """
    left_dq_token = self.cur_token
    parts = []  # type: List[word_part_t]
    self._ReadLikeDQ(left_dq_token, parts)

    dq_part = double_quoted(left_dq_token, parts)
    dq_part.spids.append(left_dq_token.span_id)  # Left ", sort of redundant
    dq_part.spids.append(self.cur_token.span_id)  # Right "
    return dq_part

  def ReadDoubleQuoted(self, left_token, parts):
    # type: (Token, List[word_part_t]) -> Token
    """For expression mode.
    
    Read var x = "${dir:-}/$name"; etc.
    """
    self._ReadLikeDQ(left_token, parts)
    return self.cur_token

  def _ReadCommandSub(self, left_id):
    # type: (Id_t) -> command_sub
    """
    NOTE: This is not in the grammar, because word parts aren't in the grammar!

    command_sub = '$(' command_list ')'
                | ` command_list `
                | '<(' command_list ')'
                | '>(' command_list ')'
    """
    left_token = self.cur_token
    left_spid = left_token.span_id

    # Set the lexer in a state so ) becomes the EOF token.
    if left_id in (Id.Left_DollarParen, Id.Left_ProcSubIn, Id.Left_ProcSubOut):
      self._Next(lex_mode_e.ShCommand)  # advance past $( etc.

      right_id = Id.Eof_RParen
      self.lexer.PushHint(Id.Op_RParen, right_id)
      c_parser = self.parse_ctx.MakeParserForCommandSub(self.line_reader,
                                                        self.lexer, right_id)
      # NOTE: This doesn't use something like main_loop because we don't want to
      # interleave parsing and execution!  Unlike 'source' and 'eval'.
      node = c_parser.ParseCommandSub()

      right_spid = c_parser.w_parser.cur_token.span_id

    elif left_id == Id.Left_Backtick and self.parse_ctx.one_pass_parse:
      # NOTE: This is an APPROXIMATE solution for translation ONLY.  See
      # test/osh2oil.

      right_id = Id.Eof_Backtick
      self.lexer.PushHint(Id.Left_Backtick, right_id)
      c_parser = self.parse_ctx.MakeParserForCommandSub(self.line_reader,
                                                        self.lexer, right_id)
      node = c_parser.ParseCommandSub()
      right_spid = c_parser.w_parser.cur_token.span_id

    elif left_id == Id.Left_Backtick:
      self._Next(lex_mode_e.Backtick)  # advance past `

      parts = []  # type: List[str]
      while True:
        self._Peek()
        #print(self.cur_token)
        if self.token_type == Id.Backtick_Quoted:
          parts.append(self.cur_token.val[1:])  # remove leading \
        elif self.token_type == Id.Backtick_Other:
          parts.append(self.cur_token.val)
        elif self.token_type == Id.Backtick_Right:
          break
        elif self.token_type == Id.Eof_Real:
          # Note: this parse error is in the ORIGINAL context.  No code_str yet.
          p_die('Unexpected EOF while looking for closing backtick',
                token=left_token)
        else:
          raise AssertionError(self.cur_token)
        self._Next(lex_mode_e.Backtick)

      # Calculate right SPID on CommandSub BEFORE re-parsing.
      right_spid = self.cur_token.span_id

      code_str = ''.join(parts)
      #log('code %r', code_str)

      # NOTE: This is similar to how we parse aliases in osh/cmd_parse.py.  It
      # won't have the same location info as MakeParserForCommandSub(), because
      # the lexer is different.
      arena = self.parse_ctx.arena
      line_reader = reader.StringLineReader(code_str, arena)
      c_parser = self.parse_ctx.MakeOshParser(line_reader)
      arena.PushSource(source.Backticks(left_spid, right_spid))
      try:
        node = c_parser.ParseCommandSub()
      finally:
        arena.PopSource()

    else:
      raise AssertionError(left_id)

    cs_part = command_sub(left_token, node)
    cs_part.spids.append(left_spid)
    cs_part.spids.append(right_spid)
    return cs_part

  def _ReadExprSub(self, lex_mode):
    # type: (lex_mode_t) -> word_part__ExprSub
    """  $[d->key]  $[obj.method()]  etc.  """
    left_token = self.cur_token
    self._Next(lex_mode_e.Expr)
    enode, _ = self.parse_ctx.ParseOilExpr(self.lexer, grammar_nt.oil_expr_sub)
    self._Next(lex_mode)
    node = word_part.ExprSub(left_token, enode)
    return node

  def ParseVarDecl(self, kw_token):
    # type: (Token) -> command_t
    """
    oil_var_decl: name_type_list '=' testlist end_stmt

    Note that assignments must end with \n  ;  }  or EOF.  Unlike shell
    assignments, we disallow:
    
    var x = 42 | wc -l
    var x = 42 && echo hi
    """
    self._Next(lex_mode_e.Expr)
    enode, last_token = self.parse_ctx.ParseVarDecl(kw_token, self.lexer)
    # Hack to move } from what the Expr lexer modes gives to what CommandParser
    # wants
    if last_token.id == Id.Op_RBrace:
      last_token.id = Id.Lit_RBrace

    # Let the CommandParser see the Op_Semi or Op_Newline.
    self.buffered_word = last_token
    self._Next(lex_mode_e.ShCommand)  # always back to this
    return enode

  def ParsePlaceMutation(self, kw_token):
    # type: (Token) -> command_t
    """
    setvar a[i] = 1
    setvar i += 1
    setvar i++
    """
    self._Next(lex_mode_e.Expr)
    enode, last_token = self.parse_ctx.ParsePlaceMutation(kw_token, self.lexer)
    # Hack to move } from what the Expr lexer modes gives to what CommandParser
    # wants
    if last_token.id == Id.Op_RBrace:
      last_token.id = Id.Lit_RBrace

    # Let the CommandParser see the Op_Semi or Op_Newline.
    self.buffered_word = last_token
    self._Next(lex_mode_e.ShCommand)  # always back to this
    return enode

  def ParseBareDecl(self):
    # type: () -> expr_t
    """
    Parse the RHS of x = {name: val}
    """
    self._Next(lex_mode_e.Expr)
    self._Peek()
    enode, last_token = self.parse_ctx.ParseOilExpr(self.lexer,
                                                    grammar_nt.command_expr)
    if last_token.id == Id.Op_RBrace:
      last_token.id = Id.Lit_RBrace
    self.buffered_word = last_token
    self._Next(lex_mode_e.ShCommand)
    return enode

  def ParseCommandExpr(self):
    # type: () -> expr_t
    enode, last_token = self.parse_ctx.ParseOilExpr(self.lexer,
                                                    grammar_nt.command_expr)
    if last_token.id == Id.Op_RBrace:
      last_token.id = Id.Lit_RBrace
    self.buffered_word = last_token
    return enode

  def ParseProc(self, node):
    # type: (command__Proc) -> None

    # proc name-with-hyphens() must be accepted
    self._Next(lex_mode_e.ShCommand) 
    self._Peek()
    # example: 'proc f[' gets you Lit_ArrayLhsOpen
    if self.token_type != Id.Lit_Chars:
      p_die('Invalid proc name %s', ui.PrettyToken(self.cur_token, self.arena),
            token=self.cur_token)

    node.name = self.cur_token

    last_token = self.parse_ctx.ParseProc(self.lexer, node)
    if last_token.id == Id.Op_LBrace:  # Translate to what CommandParser wants
      last_token.id = Id.Lit_LBrace
    self.buffered_word = last_token
    self._Next(lex_mode_e.ShCommand)  # required

  def ParseFunc(self, node):
    # type: (command__Func) -> None
    last_token = self.parse_ctx.ParseFunc(self.lexer, node)
    if last_token.id == Id.Op_LBrace:  # Translate to what CommandParser wants
      last_token.id = Id.Lit_LBrace
    self.buffered_word = last_token

  def _ReadArithExpr(self):
    # type: () -> arith_expr_t
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
    # calls self.ReadWord(lex_mode_e.Arith)
    a_parser = tdop.TdopParser(arith_parse.Spec(), self)
    anode = a_parser.Parse()
    return anode

  def _ReadArithSub(self):
    # type: () -> word_part__ArithSub
    """
    Read an arith substitution, which contains an arith expression, e.g.
    $((a + 1)).
    """
    left_span_id = self.cur_token.span_id

    # The second one needs to be disambiguated in stuff like stuff like:
    # $(echo $(( 1+2 )) )
    self.lexer.PushHint(Id.Op_RParen, Id.Right_DollarDParen)

    # NOTE: To disambiguate $(( as arith sub vs. command sub and subshell, we
    # could save the lexer/reader state here, and retry if the arithmetic parse
    # fails.  But we can almost always catch this at parse time.  There could
    # be some exceptions like:
    # $((echo * foo))  # looks like multiplication
    # $((echo / foo))  # looks like division

    self._Next(lex_mode_e.Arith)
    anode = self._ReadArithExpr()
    if self.token_type != Id.Arith_RParen:
      p_die('Expected first ) to end arith sub', token=self.cur_token)

    self._Next(lex_mode_e.ShCommand)  # TODO: This could be DQ or ARITH too

    # PROBLEM: $(echo $(( 1 + 2 )) )
    # Two right parens break the Id.Eof_RParen scheme
    self._Peek()
    if self.token_type != Id.Right_DollarDParen:
      p_die('Expected second ) to end arith sub', token=self.cur_token)

    right_span_id = self.cur_token.span_id

    node = word_part.ArithSub(anode)
    node.spids.append(left_span_id)
    node.spids.append(right_span_id)
    return node

  def ReadDParen(self):
    # type: () -> Tuple[arith_expr_t, int]
    """Read ((1+ 2))  -- command context.

    We're using the word parser because it's very similar to _ReadArithExpr
    above.
    """
    # The second one needs to be disambiguated in stuff like stuff like:
    # TODO: Be consistent with ReadForExpression below and use lex_mode_e.Arith?
    # Then you can get rid of this.
    self.lexer.PushHint(Id.Op_RParen, Id.Op_DRightParen)

    self._Next(lex_mode_e.Arith)
    anode = self._ReadArithExpr()

    if self.token_type != Id.Arith_RParen:
      p_die('Expected first ) to end arith statement', token=self.cur_token)
    self._Next(lex_mode_e.ShCommand)

    # PROBLEM: $(echo $(( 1 + 2 )) )
    self._Peek()
    if self.token_type != Id.Op_DRightParen:
      p_die('Expected second ) to end arith statement', token=self.cur_token)

    self._Next(lex_mode_e.ShCommand)

    return anode, self.cur_token.span_id

  def _NextNonSpace(self):
    # type: () -> None
    """Same logic as _ReadWord, but for ReadForExpresion."""
    while True:
      self._Next(lex_mode_e.Arith)
      self._Peek()
      if self.token_kind not in (Kind.Ignored, Kind.WS):
        break

  def ReadForExpression(self):
    # type: () -> command__ForExpr
    """Read ((i=0; i<5; ++i)) -- part of command context."""
    self._NextNonSpace()  # skip over ((

    self._Peek()
    if self.token_type == Id.Arith_Semi:  # for (( ; i < 10; i++ ))
      init_node = None  # type: Optional[arith_expr_t]
    else:
      init_node = self._ReadArithExpr()
    self._NextNonSpace()

    self._Peek()
    if self.token_type == Id.Arith_Semi:  # for (( ; ; i++ ))
      cond_node = None  # type: Optional[arith_expr_t]
    else:
      cond_node = self._ReadArithExpr()
    self._NextNonSpace()

    self._Peek()
    if self.token_type == Id.Arith_RParen:  # for (( ; ; ))
      update_node = None  # type: Optional[arith_expr_t]
    else:
      update_node = self._ReadArithExpr()
    self._NextNonSpace()

    self._Peek()
    if self.token_type != Id.Arith_RParen:
      p_die('Expected ) to end for loop expression', token=self.cur_token)
    self._Next(lex_mode_e.ShCommand)

    node = command.ForExpr()
    node.init = init_node
    node.cond = cond_node
    node.update = update_node
    return node

  def _ReadArrayLiteral(self):
    # type: () -> word_part_t
    """
    a=(1 2 3)

    TODO: See osh/cmd_parse.py:164 for Id.Lit_ArrayLhsOpen, for a[x++]=1

    We want:

    A=(['x']=1 ["x"]=2 [$x$y]=3)

    Maybe allow this as a literal string?  Because I think I've seen it before?
    Or maybe force people to patch to learn the rule.

    A=([x]=4)

    Starts with Lit_Other '[', and then it has Lit_ArrayLhsClose
    Maybe enforce that ALL have keys or NONE of have keys.
    """
    self._Next(lex_mode_e.ShCommand)  # advance past (
    self._Peek()
    if self.cur_token.id != Id.Op_LParen:
      p_die('Expected ( after =', token=self.cur_token)
    left_token = self.cur_token
    paren_spid = self.cur_token.span_id

    # MUST use a new word parser (with same lexer).
    w_parser = self.parse_ctx.MakeWordParser(self.lexer, self.line_reader)
    words = []  # type: List[compound_word]
    while True:
      w = w_parser.ReadWord(lex_mode_e.ShCommand)
      if w.tag_() == word_e.Token:
        tok = cast(Token, w)
        if tok.id == Id.Right_ShArrayLiteral:
          break
        # Unlike command parsing, array parsing allows embedded \n.
        elif tok.id == Id.Op_Newline:
          continue
        else:
          # Token
          p_die('Unexpected token in array literal', word=w)

      words.append(cast(compound_word, w))

    if len(words) == 0:  # a=() is empty indexed array
      # Needed for type safety, doh
      no_words = []  # type: List[word_t]
      node = sh_array_literal(left_token, no_words)
      node.spids.append(left_token.span_id)
      return node
 
    # If the first one is a key/value pair, then the rest are assumed to be.
    pair = word_.DetectAssocPair(words[0])
    if pair:
      k, v = pair
      pairs = [k, v]

      n = len(words)
      for i in xrange(1, n):
        w2 = words[i]
        pair = word_.DetectAssocPair(w2)
        if not pair:
          p_die("Expected associative array pair", word=w2)

        k, v = pair
        pairs.append(k)  # flat representation
        pairs.append(v)

      # invariant List?
      node2 = word_part.AssocArrayLiteral(left_token, pairs)
      node2.spids.append(paren_spid)
      return node2

    # Brace detection for arrays but NOT associative arrays
    words2 = braces.BraceDetectAll(words)
    words3 = word_.TildeDetectAll(words2)
    node = sh_array_literal(left_token, words3)
    node.spids.append(paren_spid)
    return node

  def _ParseCallArguments(self, arglist):
    # type: (arg_list) -> None

    # Needed so ) doesn't get translated to something else
    self.lexer.PushHint(Id.Op_RParen, Id.Op_RParen)

    #log('t: %s', self.cur_token)

    # Call into expression language.
    self.parse_ctx.ParseOilArgList(self.lexer, arglist)

  def _ReadCompoundWord(self, lex_mode):
    # type: (lex_mode_t) -> compound_word
    return self._ReadCompoundWord3(lex_mode, Id.Undefined_Tok, True)

  def _ReadCompoundWord3(self, lex_mode, eof_type, empty_ok):
    # type: (lex_mode_t, Id_t, bool) -> compound_word
    """
    Precondition: Looking at the first token of the first word part
    Postcondition: Looking at the token after, e.g. space or operator

    NOTE: eof_type is necessary because / is a literal, i.e. Lit_Slash, but it
    could be an operator delimiting a compound word.  Can we change lexer modes
    and remove this special case?
    """
    w = compound_word()
    num_parts = 0
    brace_count = 0
    done = False
    while not done:
      self._Peek()

      allow_done = empty_ok or num_parts != 0
      if allow_done and self.token_type == eof_type:
        done = True  # e.g. for ${foo//pat/replace}

      # Keywords like "for" are treated like literals
      elif self.token_kind in (
          Kind.Lit, Kind.History, Kind.KW, Kind.ControlFlow,
          Kind.BoolUnary, Kind.BoolBinary):
        if self.token_type == Id.Lit_EscapedChar:
          part = word_part.EscapedLiteral(self.cur_token)  # type: word_part_t
        else:
          part = self.cur_token

        if self.token_type == Id.Lit_VarLike and num_parts == 0:  # foo=
          w.parts.append(part)
          # Unfortunately it's awkward to pull the check for a=(1 2) up to
          # _ReadWord.
          next_id = self.lexer.LookAhead(lex_mode_e.ShCommand)
          if next_id == Id.Op_LParen:
            self.lexer.PushHint(Id.Op_RParen, Id.Right_ShArrayLiteral)
            part2 = self._ReadArrayLiteral()
            w.parts.append(part2)

            # Array literal must be the last part of the word.
            self._Next(lex_mode)
            self._Peek()
            # EOF, whitespace, newline, Right_Subshell
            if self.token_kind not in KINDS_THAT_END_WORDS:
              p_die('Unexpected token after array literal',
                    token=self.cur_token)
            done = True

        elif (self.parse_opts.parse_at and self.token_type == Id.Lit_Splice and
              num_parts == 0):

          splice_token = self.cur_token

          next_id = self.lexer.LookAhead(lex_mode_e.ShCommand)
          if next_id == Id.Op_LParen:  # @arrayfunc(x)
            arglist = arg_list()
            self._ParseCallArguments(arglist)
            part = word_part.FuncCall(splice_token, arglist)
          else:
            part = word_part.Splice(splice_token)

          w.parts.append(part)

          # @words or @arrayfunc() must be the last part of the word
          self._Next(lex_mode)
          self._Peek()
          # EOF, whitespace, newline, Right_Subshell
          if self.token_kind not in KINDS_THAT_END_WORDS:
            p_die('Unexpected token after array splice',
                  token=self.cur_token)
          done = True

        else:
          # Syntax error for { and }
          if self.token_type == Id.Lit_LBrace:
            brace_count += 1
          elif self.token_type == Id.Lit_RBrace:
            brace_count -= 1

          # not a literal with lookahead; append it
          w.parts.append(part)

      elif self.token_kind == Kind.VSub:
        vsub_token = self.cur_token

        part = simple_var_sub(vsub_token)
        if self.token_type == Id.VSub_DollarName:
          # Look ahead for $strfunc(x)
          #   $f(x) or --name=$f(x) is allowed
          #   but "--name=$f(x)" not allowed?  This would BREAK EXISTING CODE.
          #   It would need a parse option.

          next_id = self.lexer.LookAhead(lex_mode_e.ShCommand)
          if next_id == Id.Op_LParen:
            arglist = arg_list()
            self._ParseCallArguments(arglist)
            part = word_part.FuncCall(vsub_token, arglist)

            # Unlike @arrayfunc(x), it makes sense to allow $f(1)$f(2)
            # var a = f(1); var b = f(2); echo $a$b
            # It's consistent with other uses of $.

        w.parts.append(part)

      elif self.token_kind == Kind.ExtGlob:
        part = self._ReadExtGlob()
        w.parts.append(part)

      elif self.token_kind == Kind.Left:
        part = self._ReadLeftParts()
        w.parts.append(part)

      # NOT done yet, will advance below
      elif self.token_kind == Kind.Right:
        # Still part of the word; will be done on the next iter.
        if self.token_type == Id.Right_DoubleQuote:
          pass
        # Never happens, no PushHint for this case.
        #elif self.token_type == Id.Right_DollarParen:
        #  pass
        elif self.token_type == Id.Right_Subshell:
          # LEXER HACK for (case x in x) ;; esac )
          # Rewind before it's used
          assert self.next_lex_mode == lex_mode_e.Undefined
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
          # Rewind before it's used
          assert self.next_lex_mode == lex_mode_e.Undefined
          if self.lexer.MaybeUnreadOne():
            if self.token_type == Id.Eof_RParen:
              # Redo translation
              self.lexer.PushHint(Id.Op_RParen, Id.Eof_RParen)
            self._Next(lex_mode)

        done = True  # anything we don't recognize means we're done

      if not done:
        self._Next(lex_mode)
        num_parts += 1

    if self.parse_opts.parse_brace and num_parts > 1 and brace_count != 0:
      # accept { and }, but not foo{
      p_die(
          'Word has unbalanced { }.  Maybe add a space or quote it like \{',
          word=w)

    return w

  def _ReadArithWord(self):
    # type: () -> Tuple[Optional[word_t], bool]
    """Helper function for ReadWord."""
    self._Peek()

    if self.token_kind == Kind.Unknown:
      p_die('Unexpected token in arithmetic context', token=self.cur_token)

    elif self.token_kind == Kind.Eof:
      # Just return EOF token
      return cast(word_t, self.cur_token), False

    elif self.token_kind == Kind.Ignored:
      # Space should be ignored.  TODO: change this to SPACE_SPACE and
      # SPACE_NEWLINE?  or SPACE_TOK.
      self._Next(lex_mode_e.Arith)
      no_word = None  # type: Optional[word_t]
      return no_word, True  # Tell wrapper to try again

    elif self.token_kind in (Kind.Arith, Kind.Right):
      # Id.Right_DollarDParen IS just a normal token, handled by ArithParser
      self._Next(lex_mode_e.Arith)
      return cast(word_t, self.cur_token), False

    elif self.token_kind in (Kind.Lit, Kind.Left, Kind.VSub):
      w = self._ReadCompoundWord(lex_mode_e.Arith)
      return cast(word_t, w), False

    else:
      raise AssertionError(self.cur_token)

  def _ReadWord(self, lex_mode):
    # type: (lex_mode_t) -> Tuple[Optional[word_t], bool]
    """Helper function for Read().

    Returns:
      2-tuple (word, need_more)
        word: Word, or None if there was an error, or need_more is set
        need_more: True if the caller should call us again
    """
    no_word = None  # type: Optional[word_t]

    self._Peek()

    if self.token_kind == Kind.Eof:
      # No advance
      return cast(word_t, self.cur_token), False

    # Allow Arith for ) at end of for loop?
    elif self.token_kind in (Kind.Op, Kind.Redir, Kind.Arith):
      self._Next(lex_mode)
      if self.token_type == Id.Op_Newline:
        if self.cursor_was_newline:
          return no_word, True

      return cast(word_t, self.cur_token), False

    elif self.token_kind == Kind.Right:
      if self.token_type not in (
          Id.Right_Subshell, Id.Right_ShFunction, Id.Right_CasePat,
          Id.Right_ShArrayLiteral):
        raise AssertionError(self.cur_token)

      self._Next(lex_mode)
      return cast(word_t, self.cur_token), False

    elif self.token_kind in (Kind.Ignored, Kind.WS):
      self._Next(lex_mode)
      return no_word, True  # tell Read() to try again

    elif self.token_kind in (
        Kind.VSub, Kind.Lit, Kind.History, Kind.Left, Kind.KW,
        Kind.ControlFlow, Kind.BoolUnary, Kind.BoolBinary, Kind.ExtGlob):
      # We're beginning a word.  If we see Id.Lit_Pound, change to
      # lex_mode_e.Comment and read until end of line.
      if self.token_type == Id.Lit_Pound:
        self._Next(lex_mode_e.Comment)
        self._Peek()

        # NOTE: The # could be the last character in the file.  It can't be
        # Eof_{RParen,Backtick} because #) and #` are comments.
        assert self.token_type in (Id.Ignored_Comment, Id.Eof_Real), \
            self.cur_token

        # The next iteration will go into Kind.Ignored and set lex state to
        # lex_mode_e.ShCommand/etc.
        return no_word, True  # tell Read() to try again after comment

      else:
        w = self._ReadCompoundWord(lex_mode)
        return cast(word_t, w), False

    else:
      raise AssertionError(
          'Unhandled: %s (%s)' % (self.cur_token, self.token_kind))

  def LookAhead(self):
    # type: () -> Id_t
    """Look ahead to the next token.

    For the command parser to recognize func () { } and array= (1 2 3).  And
    probably coprocesses.
    """
    assert self.token_type != Id.Undefined_Tok
    if self.cur_token.id == Id.WS_Space:
      return self.lexer.LookAhead(lex_mode_e.ShCommand)
    else:
      return self.cur_token.id

  def ReadWord(self, lex_mode):
    # type: (lex_mode_t) -> word_t
    """Read the next Word.

    Returns:
      Word, or None if there was an error
    """
    # For integration with pgen2
    if self.buffered_word:
      w = self.buffered_word
      self.buffered_word = None
    else:
      # Implementation note: This is an stateful/iterative function that calls
      # the stateless "_ReadWord" function.
      while True:
        if lex_mode == lex_mode_e.Arith:
          # TODO: Can this be unified?
          w, need_more = self._ReadArithWord()
        elif lex_mode in (
            lex_mode_e.ShCommand, lex_mode_e.DBracket, lex_mode_e.BashRegex):
          w, need_more = self._ReadWord(lex_mode)
        else:
          raise AssertionError('Invalid lex state %s' % lex_mode)
        if not need_more:
          break

    self.cursor = w

    # TODO: Do consolidation of newlines in the lexer?
    # Note that there can be an infinite (Id.Ignored_Comment Id.Op_Newline
    # Id.Ignored_Comment Id.Op_Newline) sequence, so we have to keep track of
    # the last non-ignored token.
    self.cursor_was_newline = (word_.CommandId(self.cursor) == Id.Op_Newline)
    return self.cursor

  def ReadHereDocBody(self, parts):
    # type: (List[word_part_t]) -> None
    """A here doc is like a double quoted context, except " isn't special."""
    self._ReadLikeDQ(None, parts)
    # Returns nothing

  def ReadForPlugin(self):
    # type: () -> compound_word
    """For $PS1, $PS4, etc.

    This is just like reading a here doc line.  "\n" is allowed, as well as the
    typical substitutions ${x} $(echo hi) $((1 + 2)).
    """
    w = compound_word()
    self._ReadLikeDQ(None, w.parts)
    return w
