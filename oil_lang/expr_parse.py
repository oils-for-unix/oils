"""
expr_parse.py
"""
from __future__ import print_function

import sys

from _devbuild.gen.syntax_asdl import (
    token, double_quoted, single_quoted, command_sub,
    word__Token, word__Compound, word_part_t,
)
from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.types_asdl import lex_mode_e

from core import meta
from core import util
from core.util import log
from core.util import p_die
from frontend import reader
from osh import braces
from osh import word_
from pgen2 import parse

_ = log

from typing import TYPE_CHECKING, IO, Dict, Tuple, List, cast
if TYPE_CHECKING:
  from frontend.lexer import Lexer
  from frontend.parse_lib import ParseContext
  from pgen2.grammar import Grammar
  from pgen2.parse import PNode


class ParseTreePrinter(object):
  """Prints a tree of PNode instances."""
  def __init__(self, names):
    # type: (Dict[int, str]) -> None
    self.names = names

  def Print(self, pnode, f=sys.stdout, indent=0, i=0):
    # type: (PNode, IO[str], int, int) -> None

    ind = '  ' * indent
    # NOTE:
    # - value is filled in for TOKENS, but it's always None for PRODUCTIONS.
    # - context is (prefix, (lineno, column)), where lineno is 1-based, and
    #   'prefix' is a string of whitespace.
    #   e.g. for 'f(1, 3)', the "3" token has a prefix of ' '.
    if isinstance(pnode.tok, tuple):
      v = pnode.tok[0]
    elif isinstance(pnode.tok, token):
      v = pnode.tok.val
    else:
      v = '-'
    f.write('%s%d %s %s\n' % (ind, i, self.names[pnode.typ], v))
    if pnode.children:  # could be None
      for i, child in enumerate(pnode.children):
        self.Print(child, indent=indent+1, i=i)


def _Classify(gr, tok):
  # type: (Grammar, token) -> int

  # We have to match up what ParserGenerator.make_grammar() did when
  # calling make_label() and make_first().  See classify() in
  # opy/pgen2/driver.py.

  # 'x' and 'for' are both tokenized as Expr_Name.  This handles the 'for'
  # case.
  if tok.id == Id.Expr_Name:
    ilabel = gr.keywords.get(tok.val)
    if ilabel is not None:
      return ilabel

  # This handles 'x'.
  typ = tok.id.enum_id
  ilabel = gr.tokens.get(typ)
  if ilabel is not None:
    return ilabel

  type_str = '' if tok.id == Id.Unknown_Tok else (' (%s)' % tok.id.name)
  p_die('Unexpected token in expression mode%s', type_str, token=tok)


# NOTE: this model is not NOT expressive enough for:
#
# x = func(x, y='default', z={}) {
#   echo hi
# }

# That can probably be handled with some state machine.  Or maybe:
# https://en.wikipedia.org/wiki/Dyck_language
# When you see "func", start matching () and {}, until you hit a new {.
# It's not a regular expression.
#
# Or even more simply:
#   var x = 1 + 2 
# vs.
#   echo hi = 1

# Other issues:
# - What about SingleLine mode?  With a % prefix?
#   - Assumes {} means brace sub, and also makes trailing \ unnecessary?
#   - Allows you to align pipes on the left
#   - does it mean that only \n\n is a newline?

POP = lex_mode_e.Undefined

_MODE_TRANSITIONS = {
    (lex_mode_e.Expr, Id.Left_DollarBrace): lex_mode_e.VSub_1,  # ${x|html}
    # TODO: What about VSub_2 and so forth?
    (lex_mode_e.VSub_1, Id.Right_DollarBrace): POP,

    (lex_mode_e.Expr, Id.Left_DoubleQuote): lex_mode_e.DQ,  # x + "foo"
    (lex_mode_e.DQ, Id.Right_DoubleQuote): POP,

    (lex_mode_e.Expr, Id.Left_SingleQuoteRaw): lex_mode_e.SQ_Raw,  # x + 'foo'
    (lex_mode_e.SQ_Raw, Id.Right_SingleQuote): POP,

    (lex_mode_e.Expr, Id.Left_SingleQuoteC): lex_mode_e.SQ_C,  # x + c'\n'
    (lex_mode_e.SQ_C, Id.Right_SingleQuote): POP,

    # Why don't we need need @() and $() here?  Are ${  ' c'  " also
    # unnecessary?
}

# For ignoring newlines.
_OTHER_BALANCE = {
    Id.Op_LParen:  1,
    Id.Op_RParen: -1,

    Id.Left_AtBracket:  1,
    Id.Op_LBracket:  1,
    Id.Op_RBracket: -1,

    Id.Op_LBrace:  1,
    Id.Op_RBrace: -1
}


def _PushOilTokens(parse_ctx, gr, p, lex):
  # type: (ParseContext, Grammar, parse.Parser, Lexer) -> token
  """Push tokens onto pgen2's parser.

  Returns the last token so it can be reused/seen by the CommandParser.
  """
  #log('keywords = %s', gr.keywords)
  #log('tokens = %s', gr.tokens)

  mode = lex_mode_e.Expr
  mode_stack = [mode]
  last_token = None

  balance = 0

  from core.util import log
  while True:
    if last_token:  # e.g. left over from WordParser
      tok = last_token
      #log('last_token = %s', last_token)
      last_token = None
    else:
      tok = lex.Read(mode)
      #log('tok = %s', tok)

    # Comments and whitespace.  Newlines aren't ignored.
    if meta.LookupKind(tok.id) == Kind.Ignored:
      continue

    # For var x = {
    #   a: 1, b: 2
    # }
    if balance > 0 and tok.id == Id.Op_Newline:
      #log('*** SKIPPING NEWLINE')
      continue

    action = _MODE_TRANSITIONS.get((mode, tok.id))
    if action == POP:
      mode_stack.pop()
      mode = mode_stack[-1]
      balance -= 1
      #log('POPPED to %s', mode)
    elif action:  # it's an Id
      new_mode = action
      mode_stack.append(new_mode)
      mode = new_mode
      balance += 1  # e.g. var x = $/ NEWLINE /
      #log('PUSHED to %s', mode)
    else:
      # If we didn't already so something with the balance, look at another table.
      balance += _OTHER_BALANCE.get(tok.id, 0)
      #log('BALANCE after seeing %s = %d', tok.id, balance)

    #if tok.id == Id.Expr_Name and tok.val in KEYWORDS:
    #  tok.id = KEYWORDS[tok.val]
    #  log('Replaced with %s', tok.id)

    if tok.id.enum_id >= 256:
      raise AssertionError(str(tok))

    ilabel = _Classify(gr, tok)
    #log('tok = %s, ilabel = %d', tok, ilabel)

    if p.addtoken(tok.id.enum_id, tok, ilabel):
      return tok

    #
    # Extra handling of the body of @() and $().  Lex in the ShCommand mode.
    #

    if tok.id == Id.Left_AtParen:
      lex.PushHint(Id.Op_RParen, Id.Right_ShArrayLiteral)

      # Blame the opening token
      line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
      w_parser = parse_ctx.MakeWordParser(lex, line_reader)
      words = []
      while True:
        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        if 0:
          log('w = %s', w)

        if isinstance(w, word__Token):
          word_id = word_.CommandId(w)
          if word_id == Id.Right_ShArrayLiteral:
            break
          elif word_id == Id.Op_Newline:  # internal newlines allowed
            continue
          else:
            # Token
            p_die('Unexpected token in array literal: %r', w.token.val, word=w)

        assert isinstance(w, word__Compound)  # for MyPy
        words.append(w)

      words2 = braces.BraceDetectAll(words)
      words3 = word_.TildeDetectAll(words2)

      typ = Id.Expr_CastedDummy.enum_id
      opaque = cast(token, words3)  # HACK for expr_to_ast
      done = p.addtoken(typ, opaque, gr.tokens[typ])
      assert not done  # can't end the expression

      # Now push the closing )
      tok = w.token
      ilabel = _Classify(gr, tok)
      done = p.addtoken(tok.id.enum_id, tok, ilabel)
      assert not done  # can't end the expression

      continue

    if tok.id == Id.Left_DollarParen:
      left_token = tok

      lex.PushHint(Id.Op_RParen, Id.Eof_RParen)
      line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
      c_parser = parse_ctx.MakeParserForCommandSub(line_reader, lex,
                                                   Id.Eof_RParen)
      node = c_parser.ParseCommandSub()
      # A little gross: Copied from osh/word_parse.py
      right_token = c_parser.w_parser.cur_token

      cs_part = command_sub(left_token, node)
      cs_part.spids.append(left_token.span_id)
      cs_part.spids.append(right_token.span_id)

      typ = Id.Expr_CastedDummy.enum_id
      opaque = cast(token, cs_part)  # HACK for expr_to_ast
      done = p.addtoken(typ, opaque, gr.tokens[typ])
      assert not done  # can't end the expression

      # Now push the closing )
      ilabel = _Classify(gr, right_token)
      done = p.addtoken(right_token.id.enum_id, right_token, ilabel)
      assert not done  # can't end the expression

      continue

    if tok.id == Id.Left_DoubleQuote:
      left_token = tok
      line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
      w_parser = parse_ctx.MakeWordParser(lex, line_reader)

      parts = []  # type: List[word_part_t]
      last_token = w_parser.ReadDoubleQuoted(left_token, parts)
      expr_dq_part = double_quoted(left_token, parts)

      typ = Id.Expr_CastedDummy.enum_id
      opaque = cast(token, expr_dq_part)  # HACK for expr_to_ast
      done = p.addtoken(typ, opaque, gr.tokens[typ])
      assert not done  # can't end the expression

      continue

    if tok.id == Id.Left_DollarBrace:
      left_token = tok
      line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
      w_parser = parse_ctx.MakeWordParser(lex, line_reader)

      part, last_token = w_parser.ReadBracedBracedVarSub(left_token)

      # It's casted word_part__BracedVarSub -> dummy -> expr__BracedVarSub!
      typ = Id.Expr_CastedDummy.enum_id
      opaque = cast(token, part)  # HACK for expr_to_ast
      done = p.addtoken(typ, opaque, gr.tokens[typ])
      assert not done  # can't end the expression

      continue

    # '' and c''
    if tok.id in (Id.Left_SingleQuoteRaw, Id.Left_SingleQuoteC):
      left_token = tok
      line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
      w_parser = parse_ctx.MakeWordParser(lex, line_reader)

      # mode can be SQ or DollarSQ
      tokens = []  # type: List[token]
      no_backslashes = (left_token.val == "'")
      last_token = w_parser.ReadSingleQuoted(mode, left_token, tokens,
                                             no_backslashes)
      sq_part = single_quoted(left_token, tokens)

      typ = Id.Expr_CastedDummy.enum_id
      opaque = cast(token, sq_part)  # HACK for expr_to_ast
      done = p.addtoken(typ, opaque, gr.tokens[typ])
      assert not done  # can't end the expression

      continue

  else:
    # We never broke out -- EOF is too soon (how can this happen???)
    raise parse.ParseError("incomplete input", tok.id.enum_id, tok)


class ExprParser(object):
  """A wrapper around a pgen2 parser."""

  def __init__(self, parse_ctx, gr):
    # type: (ParseContext, Grammar) -> None
    self.parse_ctx = parse_ctx
    self.gr = gr
    # Reused multiple times.
    self.push_parser = parse.Parser(gr)

  def Parse(self, lexer, start_symbol):
    # type: (Lexer, int) -> Tuple[PNode, token]

    # Reuse the parser
    self.push_parser.setup(start_symbol)
    try:
      last_token = _PushOilTokens(self.parse_ctx, self.gr, self.push_parser,
                                  lexer)
    except parse.ParseError as e:
      #log('ERROR %s', e)
      # TODO:
      # - Describe what lexer mode we're in (Invalid syntax in regex)
      #   - Maybe say where the mode started
      # - Id.Unknown_Tok could say "This character is invalid"
      raise util.ParseError('Syntax error in expression', token=e.opaque)

    return self.push_parser.rootnode, last_token
