"""
expr_parse.py
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    loc, Token, double_quoted, single_quoted, command_sub, sh_array_literal,
    compound_word, word_part_t, word_e
)
from _devbuild.gen.id_kind_asdl import Id, Kind, Id_str
from _devbuild.gen.types_asdl import lex_mode_e

from core import ui
from core.pyerror import log, p_die
from frontend import consts
from frontend import reader
from mycpp import mylib
from mycpp.mylib import tagswitch
from osh import braces
from osh import word_
from pgen2 import parse

_ = log

from typing import TYPE_CHECKING, Dict, Tuple, List, cast, Optional
if TYPE_CHECKING:
  from frontend.lexer import Lexer
  from frontend.parse_lib import ParseContext
  from pgen2.grammar import Grammar
  from pgen2.pnode import PNode


if mylib.PYTHON:
  class ParseTreePrinter(object):
    """Prints a tree of PNode instances."""
    def __init__(self, names):
      # type: (Dict[int, str]) -> None
      self.names = names
      self.f = mylib.Stdout()

    def _Print(self, pnode, indent, i):
      # type: (PNode, int, int) -> None

      ind = '  ' * indent
      # NOTE:
      # - why isn't 'tok' None for PRODUCTIONS?  There is some redundancy to get
      #   rid of.
      if pnode.tok:
        if isinstance(pnode.tok, Token):
          v = pnode.tok.val
        else:
          # e.g. command_sub for x = $(echo hi)
          v = repr(pnode.tok)
      else:
        v = '-'
      self.f.write('%s%d %s %s\n' % (ind, i, self.names[pnode.typ], v))
      if pnode.children is not None:
        for i, child in enumerate(pnode.children):
          self._Print(child, indent+1, i)

    def Print(self, pnode):
      # type: (PNode) -> None
      self._Print(pnode, 0, 0)


def _Classify(gr, tok, tea_keywords):
  # type: (Grammar, Token, bool) -> int

  # We have to match up what ParserGenerator.make_grammar() did when
  # calling make_label() and make_first().  See classify() in
  # opy/pgen2/driver.py.

  # Special case for top-level Tea keywords like data/enum/class, etc.
  # TODO: Do this more elegantly at grammar build time.
  if tea_keywords and tok.id == Id.Expr_Name:
    if tok.val in gr.keywords:
      #log('NEW %r', gr.keywords[tok.val])
      return gr.keywords[tok.val]

  # This handles 'x'.
  if tok.id in gr.tokens:
    return gr.tokens[tok.id]

  if tok.id == Id.Unknown_DEqual:
    p_die('Use === to be exact, or ~== to convert types', tok)

  if tok.id == Id.Unknown_Tok:
    type_str = ''
  else:
    type_str = ' (%s)' % ui.PrettyId(tok.id)
  p_die('Unexpected token in expression mode%s' % type_str, tok)


# Newlines are ignored between these pairs.
_OTHER_BALANCE = {
    # Parenthesized expressions (tuples) and func/proc parameter lists
    Id.Op_LParen:  1,
    Id.Op_RParen: -1,

    Id.Op_LBracket:  1,
    Id.Op_RBracket: -1,

    # Dicts are {}, and the grammar respects Op_Newline.
}


def _PushOilTokens(parse_ctx, gr, p, lex, tea_keywords):
  # type: (ParseContext, Grammar, parse.Parser, Lexer, bool) -> Token
  """Push tokens onto pgen2's parser.

  Returns the last token so it can be reused/seen by the CommandParser.
  """
  #log('keywords = %s', gr.keywords)
  #log('tokens = %s', gr.tokens)

  last_token = None  # type: Optional[Token]
  prev_was_newline = False

  balance = 0  # to ignore newlines

  while True:
    if last_token:  # e.g. left over from WordParser
      tok = last_token
      #log('last_token = %s', last_token)
      last_token = None
    else:
      tok = lex.Read(lex_mode_e.Expr)
      #log('tok = %s', tok)

    # Comments and whitespace.  Newlines aren't ignored.
    if consts.GetKind(tok.id) == Kind.Ignored:
      continue

    # For multiline lists, maps, etc.
    if tok.id == Id.Op_Newline:
      if balance > 0 :
        #log('*** SKIPPING NEWLINE')
        continue
      # Eliminate duplicate newline tokens.  It makes the grammar simpler, and
      # it's consistent with CPython's lexer and our own WordParser.
      if prev_was_newline:
        continue
      prev_was_newline = True
    else:
      prev_was_newline = False

    balance += _OTHER_BALANCE.get(tok.id, 0)
    #log('BALANCE after seeing %s = %d', tok.id, balance)

    if tok.id == Id.Op_LParen:
      # For nesting inside $()
      lex.PushHint(Id.Op_RParen, Id.Op_RParen)

    #if tok.id == Id.Expr_Name and tok.val in KEYWORDS:
    #  tok.id = KEYWORDS[tok.val]
    #  log('Replaced with %s', tok.id)

    assert tok.id < 256, Id_str(tok.id)

    ilabel = _Classify(gr, tok, tea_keywords)
    #log('tok = %s, ilabel = %d', tok, ilabel)

    if p.addtoken(tok.id, tok, ilabel):
      return tok

    #
    # Mututally recursive calls into the command/word parsers.
    #

    if tok.id == Id.Left_PercentParen:  # %(
      left_tok = tok
      lex.PushHint(Id.Op_RParen, Id.Right_ShArrayLiteral)

      # Blame the opening token
      line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
      w_parser = parse_ctx.MakeWordParser(lex, line_reader)
      words = []  # type: List[compound_word]
      close_tok = None  # type: Optional[Token]
      done = False
      while not done:
        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        with tagswitch(w) as case:
          if case(word_e.Token):
            tok = cast(Token, w)
            if tok.id == Id.Right_ShArrayLiteral:
              close_tok = tok
              done = True  # can't use break here
            elif tok.id == Id.Op_Newline:  # internal newlines allowed
              continue
            else:
              p_die('Unexpected token in array literal', loc.Word(w))

          elif case(word_e.Compound):
            words.append(cast(compound_word, w))

          else:
            raise AssertionError()

      words2 = braces.BraceDetectAll(words)
      words3 = word_.TildeDetectAll(words2)

      typ = Id.Expr_CastedDummy

      lit_part = sh_array_literal(left_tok, words3)
      opaque = cast(Token, lit_part)  # HACK for expr_to_ast
      done = p.addtoken(typ, opaque, gr.tokens[typ])
      assert not done  # can't end the expression

      # Now push the closing )
      ilabel = _Classify(gr, close_tok, tea_keywords)
      done = p.addtoken(tok.id, close_tok, ilabel)
      assert not done  # can't end the expression

      continue

    # $(  @(  ^(
    if tok.id in (Id.Left_DollarParen, Id.Left_AtParen, Id.Left_CaretParen):

      left_token = tok

      lex.PushHint(Id.Op_RParen, Id.Eof_RParen)
      line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
      c_parser = parse_ctx.MakeParserForCommandSub(line_reader, lex,
                                                   Id.Eof_RParen)
      node = c_parser.ParseCommandSub()
      # A little gross: Copied from osh/word_parse.py
      right_token = c_parser.w_parser.cur_token

      cs_part = command_sub(left_token, node, right_token)

      typ = Id.Expr_CastedDummy
      opaque = cast(Token, cs_part)  # HACK for expr_to_ast
      done = p.addtoken(typ, opaque, gr.tokens[typ])
      assert not done  # can't end the expression

      # Now push the closing )
      ilabel = _Classify(gr, right_token, tea_keywords)
      done = p.addtoken(right_token.id, right_token, ilabel)
      assert not done  # can't end the expression

      continue

    # " and """
    if tok.id in (Id.Left_DoubleQuote, Id.Left_TDoubleQuote):
      left_token = tok
      line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
      w_parser = parse_ctx.MakeWordParser(lex, line_reader)

      parts = []  # type: List[word_part_t]
      last_token = w_parser.ReadDoubleQuoted(left_token, parts)
      expr_dq_part = double_quoted(left_token, parts, last_token)

      typ = Id.Expr_CastedDummy
      opaque = cast(Token, expr_dq_part)  # HACK for expr_to_ast
      done = p.addtoken(typ, opaque, gr.tokens[typ])
      assert not done  # can't end the expression

      continue

    # ${
    if tok.id == Id.Left_DollarBrace:
      left_token = tok
      line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
      w_parser = parse_ctx.MakeWordParser(lex, line_reader)

      part, last_token = w_parser.ReadBracedVarSub(left_token)

      # It's casted word_part__BracedVarSub -> dummy -> expr__BracedVarSub!
      typ = Id.Expr_CastedDummy
      opaque = cast(Token, part)  # HACK for expr_to_ast
      done = p.addtoken(typ, opaque, gr.tokens[typ])
      assert not done  # can't end the expression

      continue

    # 'x'  r'x'  $'x' and '''x'''  r'''x'''  $'''x'''
    if tok.id in (Id.Left_SingleQuote, Id.Left_RSingleQuote,
                  Id.Left_DollarSingleQuote,
                  Id.Left_TSingleQuote, Id.Left_RTSingleQuote,
                  Id.Left_DollarTSingleQuote):
      if tok.id in (Id.Left_DollarSingleQuote, Id.Left_DollarTSingleQuote):
        sq_mode = lex_mode_e.SQ_C
      else:
        sq_mode = lex_mode_e.SQ_Raw

      left_token = tok
      line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
      w_parser = parse_ctx.MakeWordParser(lex, line_reader)

      tokens = []  # type: List[Token]
      last_token = w_parser.ReadSingleQuoted(sq_mode, left_token, tokens,
                                             True)

      sq_part = single_quoted(left_token, tokens, last_token)

      typ = Id.Expr_CastedDummy
      opaque = cast(Token, sq_part)  # HACK for expr_to_ast
      done = p.addtoken(typ, opaque, gr.tokens[typ])
      assert not done  # can't end the expression
      continue

  else:
    # We never broke out -- EOF is too soon (how can this happen???)
    raise parse.ParseError("incomplete input", tok.id, tok)


class ExprParser(object):
  """A wrapper around a pgen2 parser."""

  def __init__(self, parse_ctx, gr, tea_keywords):
    # type: (ParseContext, Grammar, bool) -> None
    self.parse_ctx = parse_ctx
    self.gr = gr
    self.tea_keywords = tea_keywords
    # Reused multiple times.
    self.push_parser = parse.Parser(gr)

  def Parse(self, lexer, start_symbol):
    # type: (Lexer, int) -> Tuple[PNode, Token]

    # Reuse the parser
    self.push_parser.setup(start_symbol)
    try:
      last_token = _PushOilTokens(self.parse_ctx, self.gr, self.push_parser,
                                  lexer, self.tea_keywords)
    except parse.ParseError as e:
      #log('ERROR %s', e)
      # TODO:
      # - Describe what lexer mode we're in (Invalid syntax in regex)
      #   - Maybe say where the mode started
      # - Id.Unknown_Tok could say "This character is invalid"

      # ParseError has a "too much input" case but I haven't been able to
      # tickle it.  Mabye it's because of the Eof tokens?

      p_die('Syntax error in expression (near %s)' % ui.PrettyId(e.tok.id),
            e.tok)

    return self.push_parser.rootnode, last_token
