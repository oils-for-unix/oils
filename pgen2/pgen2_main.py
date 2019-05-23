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


# TODO: need space
ARITH_TOKENS = {
    '+': Id.Arith_Plus,
    '-': Id.Arith_Minus,
    '*': Id.Arith_Star,
    '/': Id.Arith_Slash,
    '%': Id.Arith_Percent,
    '(': Id.Arith_LParen,
    ')': Id.Arith_RParen,
    '[': Id.Arith_LBracket,
    ']': Id.Arith_RBracket,
    '**': Id.Arith_DStar,
    '~': Id.Arith_Tilde,
    ',': Id.Arith_Comma,

    'NAME': Id.Lit_ArithVarLike,
    'NUMBER': Id.Lit_Digits,

    # TODO: Does it ever happen?
    'STRING': Id.Lit_ArithVarLike,
    'NEWLINE': Id.Op_Newline,

    'ENDMARKER': Id.Eof_Real,
}


class CalcTokenDef(object):

  def GetTokenNum(self, label):
    id_ = ARITH_TOKENS[label]
    return id_.enum_id

  def GetTokenNumForOp(self, value):
    id_ = ARITH_TOKENS[value]
    return id_.enum_id


def PushOilTokens(p, lex, debug=False):
    """Parse a series of tokens and return the syntax tree."""
    while True:
      tok = lex.Read(lex_mode_e.Arith)

      # TODO: This should be the kind?
      if tok.id == Id.Ignored_Space:
        continue

      typ = tok.id.enum_id
      if p.addtoken(typ, tok.val, tok):
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

    tok_def = CalcTokenDef() if grammar_name == 'calc' else None
    pg = pgen.ParserGenerator(grammar_path, tok_def=tok_def)
    gr = pg.make_grammar()

    if grammar_name == 'calc':
      arena = alloc.Arena()
      lex = MakeOilLexer(code_str, arena)

      p = parse.Parser(gr, convert=NoSingletonAction)

      p.setup(gr.symbol2number[start_symbol])
      try:
        PushOilTokens(p, lex)
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
        parse_tree = driver.PushTokens(p, tokens, gr.symbol2number[start_symbol])
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

      if grammar_name == 'calc':
        for id_ in ARITH_TOKENS.values():
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
    raise RuntimeError('Invalid actio %r' % action)



if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
