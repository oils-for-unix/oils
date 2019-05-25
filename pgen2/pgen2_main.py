#!/usr/bin/python
"""
pgen2_main.py
"""
from __future__ import print_function

import cStringIO
import os
import sys

from opy.pgen2 import token
from opy.pgen2 import tokenize
from opy.pgen2 import driver, parse, pgen, grammar

from opy.opy_main import Symbols, ParseTreePrinter, log

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import source
from _devbuild.gen.types_asdl import lex_mode_e
from core import alloc
from frontend import lexer, match, reader


def NoSingletonAction(gr, node):
  """Collapse parse tree."""
  #log('%s', node)
  typ, value, context, children = node

  # collapse
  # hm this was so easy!  Why does it materialize so much then?
  # Does CPython do it, or only pgen2?
  # I think you already know
  if children is not None and len(children) == 1:
    return children[0]

  return node

SEMANTIC_ACTIONS = {
    'calc': NoSingletonAction,
}


def MakeOilLexer(code_str, arena):
  arena.PushSource(source.MainFile('pgen2_main'))
  line_reader = reader.StringLineReader(code_str, arena)
  line_lexer = lexer.LineLexer(match.MATCHER, '', arena)
  lex = lexer.Lexer(line_lexer, line_reader)
  return lex


# Used at grammar BUILD time.
OPS = {
    '+': Id.Arith_Plus,
    '-': Id.Arith_Minus,
    '*': Id.Arith_Star,
    '/': Id.Arith_Slash,
    '^': Id.Arith_Caret,  # exponent

    'div': Id.Expr_Div,
    'mod': Id.Expr_Mod,

    '(': Id.Arith_LParen,
    ')': Id.Arith_RParen,
    '[': Id.Arith_LBracket,
    ']': Id.Arith_RBracket,
    '~': Id.Arith_Tilde,
    ',': Id.Arith_Comma,

    '==': Id.Arith_DEqual,
    '!=': Id.Arith_NEqual,
    '<': Id.Arith_Less,
    '>': Id.Arith_Great,
    '<=': Id.Arith_LessEqual,
    '>=': Id.Arith_GreatEqual,
}

TERMINALS = {
    # What happens in the grammar when you see NAME | NUMBER
    # atom: NAME | NUMBER | STRING+

    'NAME': Id.Expr_Name,
    'NUMBER': Id.Expr_Digits,

    # The grammar seems something like 'for' or '>='
    # These need to be looked up at "_Classify" time?
    #'STRING': Id.Expr_Name,

    'NEWLINE': Id.Op_Newline,

    'ENDMARKER': Id.Eof_Real,
}


KEYWORDS = {
    'div': Id.Expr_Div,
    'mod': Id.Expr_Mod,
    'xor': Id.Expr_Xor,

    'and': Id.Expr_And,
    'or': Id.Expr_Or,
    'not': Id.Expr_Not,

    'for': Id.Expr_For,
    'is': Id.Expr_Is,
    'in': Id.Expr_In,
    'if': Id.Expr_If,
    'else': Id.Expr_Else,

    'match': Id.Expr_Match,
    'func': Id.Expr_Func,
}


class OilTokenDef(object):

  def GetTerminalNum(self, label):
    id_ = TERMINALS[label]
    return id_.enum_id

  def GetOpNum(self, value):
    id_ = OPS[value]
    return id_.enum_id


def _Classify(gr, tok):
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
  #log('typ = %d, id = %s', typ, tok.id)
  ilabel = gr.tokens.get(typ)
  if ilabel is None:
    raise AssertionError('%d not a keyword and not in gr.tokens: %s' % (typ, tok))
  return ilabel


def PushOilTokens(p, lex, gr, debug=False):
  """Parse a series of tokens and return the syntax tree."""
  #log('keywords = %s', gr.keywords)
  #log('tokens = %s', gr.tokens)

  while True:
    tok = lex.Read(lex_mode_e.OilExpr)

    # TODO: Use Kind?
    if tok.id == Id.Ignored_Space:
      continue

    #if tok.id == Id.Expr_Name and tok.val in KEYWORDS:
    #  tok.id = KEYWORDS[tok.val]
    #  log('Replaced with %s', tok.id)

    typ = tok.id.enum_id

    #log('tok = %s', tok)
    ilabel = _Classify(gr, tok)

    if p.addtoken(typ, tok.val, tok, ilabel):
        if debug:
            log("Stop.")
        break
  else:
      # We never broke out -- EOF is too soon (how can this happen???)
      raise parse.ParseError("incomplete input",
                             type_, value, (prefix, start))


def main(argv):
  action = argv[1]
  argv = argv[2:]

  if action == 'parse':
    grammar_path = argv[0]
    start_symbol = argv[1]
    code_str = argv[2]

    # For choosing lexer and semantic actions
    grammar_name, _ = os.path.splitext(os.path.basename(grammar_path))

    using_oil_lexer = (grammar_name in ('calc', 'minimal'))
    #using_oil_lexer = grammar_name in ('calc',)

    tok_def = OilTokenDef() if using_oil_lexer else None

    pg = pgen.ParserGenerator(grammar_path, tok_def=tok_def)
    gr = pg.make_grammar()
    #print(gr.dfas)
    #return
    # TODO: We don't need keywords on our grammar.  Only Python uses that.

    if using_oil_lexer:
      arena = alloc.Arena()
      lex = MakeOilLexer(code_str, arena)

      p = parse.Parser(gr, convert=NoSingletonAction)

      p.setup(gr.symbol2number[start_symbol])
      try:
        PushOilTokens(p, lex, gr)
      except parse.ParseError as e:
        log('Parse Error: %s', e)
        return 1

      parse_tree = p.rootnode

    else:
      f = cStringIO.StringIO(code_str)
      tokens = tokenize.generate_tokens(f.readline)

      # Semantic actions are registered in this code.
      #convert = SEMANTIC_ACTIONS.get(grammar_name)
      convert = NoSingletonAction
      p = parse.Parser(gr, convert=convert)

      try:
        parse_tree = driver.PushTokens(p, tokens, gr, start_symbol)
      except parse.ParseError as e:
        # Extract location information and show it.
        unused, (lineno, offset) = e.context
        # extra line needed for '\n' ?
        lines = code_str.splitlines() + ['']

        line = lines[lineno-1]
        log('  %s', line)
        log('  %s^', ' '*offset)
        log('Parse Error: %s', e)
        return 1

    #n = CountTupleTree(parse_tree)
    #log('%r => %d nodes', expr, n)

    if 1:
      names = {}

      if using_oil_lexer:
        for id_ in (OPS.values() + TERMINALS.values()):
          k = id_.enum_id
          assert k <= 256, (k, id_)
          names[k] = id_.name
      else:
        # NOTE: Similar work for Python is done in transformer.Init()
        for k, v in token.tok_name.items():
            # NT_OFFSET == 256.  Remove?
            assert k <= 256, (k, v)
            names[k] = v

      for k, v in gr.number2symbol.items():
          # eval_input == 256.  Remove?
          assert k >= 256, (k, v)
          names[k] = v

      printer = ParseTreePrinter(names)  # print raw nodes
      printer.Print(parse_tree)
      print()

  elif action == 'stdlib-test':
    # This shows how deep Python's parse tree is.  It doesn't use semantic
    # actions to prune on the fly!

    import parser
    t = parser.expr('1+2')
    print(t)
    t2 = parser.st2tuple(t)
    print(t2)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
