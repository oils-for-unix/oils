"""
expr_parse.py
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    Token, double_quoted, single_quoted, command_sub, sh_array_literal,
    compound_word, word_part_t, word_e
)
from _devbuild.gen.id_kind_asdl import Id, Kind, Id_str
from _devbuild.gen.types_asdl import lex_mode_e

from core import error
from core.util import log, p_die
from frontend import lookup
from frontend import reader
from osh import braces
from osh import word_
from pgen2 import parse
from mycpp import mylib

_ = log

from typing import TYPE_CHECKING, Dict, Tuple, List, cast, Optional
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
    self.f = mylib.Stdout()

  def _Print(self, pnode, indent, i):
    # type: (PNode, int, int) -> None

    ind = '  ' * indent
    # NOTE:
    # - why isn't 'tok' None for PRODUCTIONS?  There is some redundancy to get
    #   rid of.
    if pnode.tok:
      assert isinstance(pnode.tok, Token), pnode.tok
      v = pnode.tok.val
      #v = repr(pnode.tok)
    else:
      v = '-'
    self.f.write('%s%d %s %s\n' % (ind, i, self.names[pnode.typ], v))
    if pnode.children is not None:
      for i, child in enumerate(pnode.children):
        self._Print(child, indent+1, i)

  def Print(self, pnode):
    # type: (PNode) -> None
    self._Print(pnode, 0, 0)


def _Classify(gr, tok):
  # type: (Grammar, Token) -> int

  # We have to match up what ParserGenerator.make_grammar() did when
  # calling make_label() and make_first().  See classify() in
  # opy/pgen2/driver.py.

  # 'x' and 'for' are both tokenized as Expr_Name.  This handles the 'for'
  # case.
  if tok.id == Id.Expr_Name:
    if tok.val in gr.keywords:
      return gr.keywords[tok.val]

  # This handles 'x'.
  typ = tok.id
  if typ in gr.tokens:
    return gr.tokens[typ]

  type_str = '' if tok.id == Id.Unknown_Tok else (' (%s)' % mylib.NewStr(Id_str(tok.id)))
  p_die('Unexpected token in expression mode%s', type_str, token=tok)


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
  # type: (ParseContext, Grammar, parse.Parser, Lexer) -> Token
  """Push tokens onto pgen2's parser.

  Returns the last token so it can be reused/seen by the CommandParser.
  """
  #log('keywords = %s', gr.keywords)
  #log('tokens = %s', gr.tokens)

  last_token = None  # type: Optional[Token]

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
    if lookup.LookupKind(tok.id) == Kind.Ignored:
      continue

    # For var x = {
    #   a: 1, b: 2
    # }
    if balance > 0 and tok.id == Id.Op_Newline:
      #log('*** SKIPPING NEWLINE')
      continue

    balance += _OTHER_BALANCE.get(tok.id, 0)
    #log('BALANCE after seeing %s = %d', tok.id, balance)

    #if tok.id == Id.Expr_Name and tok.val in KEYWORDS:
    #  tok.id = KEYWORDS[tok.val]
    #  log('Replaced with %s', tok.id)

    assert tok.id < 256, Id_str(tok.id)

    ilabel = _Classify(gr, tok)
    #log('tok = %s, ilabel = %d', tok, ilabel)

    if p.addtoken(tok.id, tok, ilabel):
      return tok

    #
    # Mututally recursive calls into the command/word parsers.
    #

    if mylib.PYTHON:
      if tok.id == Id.Left_AtParen:
        left_tok = tok
        lex.PushHint(Id.Op_RParen, Id.Right_ShArrayLiteral)

        # Blame the opening token
        line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
        w_parser = parse_ctx.MakeWordParser(lex, line_reader)
        words = []
        close_tok = None  # type: Optional[Token]
        while True:
          w = w_parser.ReadWord(lex_mode_e.ShCommand)
          if 0:
            log('w = %s', w)

          if w.tag_() == word_e.Token:
            tok = cast(Token, w)
            if tok.id == Id.Right_ShArrayLiteral:
              close_tok = tok
              break
            elif tok.id == Id.Op_Newline:  # internal newlines allowed
              continue
            else:
              # Token
              p_die('Unexpected token in array literal: %r', tok.val, word=w)

          assert isinstance(w, compound_word)  # for MyPy
          words.append(w)

        words2 = braces.BraceDetectAll(words)
        words3 = word_.TildeDetectAll(words2)

        typ = Id.Expr_CastedDummy

        lit_part = sh_array_literal(left_tok, words3)
        opaque = cast(Token, lit_part)  # HACK for expr_to_ast
        done = p.addtoken(typ, opaque, gr.tokens[typ])
        assert not done  # can't end the expression

        # Now push the closing )
        ilabel = _Classify(gr, close_tok)
        done = p.addtoken(tok.id, close_tok, ilabel)
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

        typ = Id.Expr_CastedDummy
        opaque = cast(Token, cs_part)  # HACK for expr_to_ast
        done = p.addtoken(typ, opaque, gr.tokens[typ])
        assert not done  # can't end the expression

        # Now push the closing )
        ilabel = _Classify(gr, right_token)
        done = p.addtoken(right_token.id, right_token, ilabel)
        assert not done  # can't end the expression

        continue

      if tok.id == Id.Left_DoubleQuote:
        left_token = tok
        line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
        w_parser = parse_ctx.MakeWordParser(lex, line_reader)

        parts = []  # type: List[word_part_t]
        last_token = w_parser.ReadDoubleQuoted(left_token, parts)
        expr_dq_part = double_quoted(left_token, parts)

        typ = Id.Expr_CastedDummy
        opaque = cast(Token, expr_dq_part)  # HACK for expr_to_ast
        done = p.addtoken(typ, opaque, gr.tokens[typ])
        assert not done  # can't end the expression

        continue

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

      # '' and c''
      if tok.id in (Id.Left_SingleQuoteRaw, Id.Left_SingleQuoteC):
        if tok.id == Id.Left_SingleQuoteRaw:
          sq_mode = lex_mode_e.SQ_Raw
        else:
          sq_mode = lex_mode_e.SQ_C

        left_token = tok
        line_reader = reader.DisallowedLineReader(parse_ctx.arena, tok)
        w_parser = parse_ctx.MakeWordParser(lex, line_reader)

        tokens = []  # type: List[Token]
        no_backslashes = (left_token.val == "'")
        last_token = w_parser.ReadSingleQuoted(sq_mode, left_token, tokens,
                                               no_backslashes)
        sq_part = single_quoted(left_token, tokens)

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

  def __init__(self, parse_ctx, gr):
    # type: (ParseContext, Grammar) -> None
    self.parse_ctx = parse_ctx
    self.gr = gr
    # Reused multiple times.
    self.push_parser = parse.Parser(gr)

  def Parse(self, lexer, start_symbol):
    # type: (Lexer, int) -> Tuple[PNode, Token]

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

      # ParseError has a "too much input" case but I haven't been able to
      # tickle it.  Mabye it's because of the Eof tokens?

      #raise error.Parse('Syntax error in expression (%r)', e, token=e.tok)
      raise error.Parse('Syntax error in expression', token=e.tok)

    return self.push_parser.rootnode, last_token
